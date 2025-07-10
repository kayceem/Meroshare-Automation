#!/home/kayc/Code/Python/MeroShare-IPO/.venv/bin/python

import os
import asyncio
from time import perf_counter
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from cryptography.fernet import Fernet

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from database.database import get_db
from database.models import Application, User
from utils.helpers import get_bank_id, get_dir_path, get_fernet_key, get_logger, get_time
from dotenv import load_dotenv

load_dotenv()
DIR_PATH = None
log = None

async def save_screenshot(page, NAME, name, share_applied=""):
    now = get_time()
    filename = f"{DIR_PATH}/screenshots/{name}/{share_applied}/{NAME}-[{now}].png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    await page.screenshot(path=filename)
    return


def update_database(username, user_id, applied_shares):
    try:
        log.info(f"Updating database for {username}")
        if len(applied_shares) == 0:
            return
        
        with get_db() as db:
            for shares in applied_shares:
                ipo_name, _, _, ipo, share_type, button = shares
                existing_entry = db.query(Application).filter(
                    Application.name == username, 
                    Application.ipo_name == ipo_name
                ).first()
                
                if existing_entry:
                    existing_entry.button = button
                    existing_entry.share_type = share_type
                else:
                    db.add(Application(
                        user_id=user_id, 
                        name=username, 
                        ipo_name=ipo_name, 
                        ipo=ipo, 
                        share_type=share_type, 
                        button=button
                    ))
            
            db.commit()
            log.info(f"Database updated for {username}")
    except Exception as e:
        log.error(f"Error updating database for {username}: {e}")
        raise
    return


async def apply_share(page, CRN, PIN, DP, ipo, ACCOUNT_NUMBER):
    bank_id = get_bank_id()
    try:
        await page.wait_for_selector("#selectBank", timeout=10000)
    except PlaywrightTimeoutError:
        return False
    
    # Select bank
    await page.select_option("#selectBank", value=str(bank_id[DP]))
    await asyncio.sleep(0.5)
    
    # Select account number
    await page.select_option("#accountNumber", value=str(ACCOUNT_NUMBER))
    await asyncio.sleep(0.5)
    
    # Handle quantity
    quantity_input = page.locator("#appliedKitta")
    if ipo == "IPO" or ipo == "FPO":
        await quantity_input.clear()
        QUANTITY = 10
        await quantity_input.fill(str(QUANTITY))
        await asyncio.sleep(0.5)
    
    text = await quantity_input.input_value()

    # Enter CRN
    crn_input = page.locator("#crnNumber")
    await crn_input.clear()
    await asyncio.sleep(0.5)
    await crn_input.fill(str(CRN))
    await asyncio.sleep(0.5)
    
    # Check privacy policy
    await page.check("#disclaimer")
    await asyncio.sleep(0.5)
    
    # Click proceed button
    try:
        await page.click("xpath=/html/body/app-dashboard/div/main/div/app-issue/div/wizard/div/wizard-step[1]/form/div[2]/div/div[5]/div[2]/div/button[1]")
    except:
        await page.click("xpath=/html/body/app-dashboard/div/main/div/app-re-apply/div/div/wizard/div/wizard-step[1]/form/div[2]/div/div[4]/div[2]/div/button[1]")
    await asyncio.sleep(1)

    # Enter PIN
    try:
        await page.wait_for_selector("#transactionPIN", timeout=2000)
        await page.fill("#transactionPIN", str(PIN))
        await asyncio.sleep(1)
    except PlaywrightTimeoutError:
        return False

    # Click apply button
    try:
        await page.click("xpath=/html/body/app-dashboard/div/main/div/app-issue/div/wizard/div/wizard-step[2]/div[2]/div/form/div[2]/div/div/div/button[1]")
    except:
        await page.click("xpath=/html/body/app-dashboard/div/main/div/app-re-apply/div/div/wizard/div/wizard-step[2]/div[2]/div/form/div[2]/div/div/div/button[1]")
    
    try:
        await page.wait_for_selector(".toast-message", timeout=5000)
        toast_text = await page.locator(".toast-message").text_content()
        if "Share has been applied successfully." not in toast_text:
            return False
    except PlaywrightTimeoutError:
        return False
    
    await asyncio.sleep(3)
    return int(text)


async def check_to_apply(page, user, info, lock):
    applied_shares = []
    quantities = []
    NAME, DP, _, _, CRN, PIN, ACCOUNT_NUMBER, USER_ID = user

    for index, data in enumerate(info):
        # Check if there is a button
        try:
            name, _, _, ipo, share_type, button = data
        except:
            name = data[0]
            button = "No button"
            log.info(f"Already applied for {NAME} : {name} | {button}")
            continue
            
        if not share_type == "Ordinary Shares" and "Local" not in share_type:
            log.info(f"Not applied for {NAME} : {share_type} | {name}")
            continue

        if button == "Edit":
            log.info(f"Already applied for {NAME} : {name} : {button}")
            continue

        # Check if the share is IPO and can be applied
        if not (ipo == "IPO" or ipo == "FPO") and not ipo == "RESERVED (RIGHT SHARE)":
            continue
        if not (button == "Apply" or button == "Reapply"):
            continue

        try:
            await page.click(f"xpath=/html/body/app-dashboard/div/main/div/app-asba/div/div[2]/app-applicable-issue/div/div/div/div/div[{index+1}]/div/div[2]/div/div[4]/button")
        except:
            await page.click(f"xpath=/html/body/app-dashboard/div/main/div/app-asba/div/div[2]/app-applicable-issue/div/div/div/div/div[{index+1}]/div/div[2]/div/div[3]/button")

        for attempt in range(4):
            try:
                share_applied = await apply_share(page, CRN, PIN, DP, ipo, ACCOUNT_NUMBER)
                if share_applied:
                    await save_screenshot(page, NAME, name, share_applied)
                    log.info(f"Applied shares for {NAME} : {name} : {share_applied} shares")
                    quantities.append(share_applied)
                    applied_shares.append(data)
                    break
            except Exception as e:
                await page.goto(page.url)
            log.info(f"Could not apply {NAME} : {name} (Attempt {attempt + 1})")
                
    with lock:
        update_database(NAME, USER_ID, applied_shares)
    return


async def check_for_companies(page, lock, NAME):
    info = []

    # Navigate to ASBA
    await page.goto("https://meroshare.cdsc.com.np/#/asba")
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector("xpath=/html/body/div/div/div/button", timeout=2000)
        await page.click("xpath=/html/body/div/div/div/button")
        log.info(f"User was unauthorized {NAME}")
        return "not_authorized"
    except PlaywrightTimeoutError:
        pass

    for attempt in range(1, 5):
        try:
            await page.wait_for_selector(".company-list", timeout=5000)
            shares_available = await page.locator(".company-list").all()
            log.info(f"Got Companies for {NAME}")
            break
        except PlaywrightTimeoutError:
            log.info(f"Tried to get Companies for {NAME} ({attempt})")
            await page.goto("https://meroshare.cdsc.com.np/#/asba")
            await asyncio.sleep(2 + attempt)

        if attempt == 4:
            log.info(f"No Companies available/loaded {NAME}")
            return False
        
    # Store all company information
    for shares in shares_available:
        share_text = await shares.inner_text()
        # print((await (shares.locator('[tooltip="Company Name"]')).text_content()).strip())
        # print((await (shares.locator('[tooltip="Company Name"]')).inner_text()))
        info.append(share_text.split("\n"))
    return info


async def login(page, DP, USERNAME, PASSWD):
    try:
        # DP dropdown menu
        await page.wait_for_selector("#selectBranch", timeout=5000)
        await page.click("#selectBranch")
        
        # DP field
        await page.fill("xpath=/html/body/span/span/span[1]/input", str(DP))
        await page.press("xpath=/html/body/span/span/span[1]/input", "Enter")
    except PlaywrightTimeoutError:
        return False

    # Username field
    await page.fill("#username", str(USERNAME))

    # Password field
    await page.fill("#password", str(PASSWD))
    await asyncio.sleep(0.5)
    
    # Login button
    await page.click("xpath=/html/body/app-login/div/div/div/div/div/div/div[1]/div/form/div/div[4]/div/button")
    await asyncio.sleep(1)
    
    try:
        await page.wait_for_selector("xpath=/html/body/div/div/div/button", timeout=3000)
        await page.click("xpath=/html/body/div/div/div/button")
        return False
    except PlaywrightTimeoutError:
        if page.url == "https://meroshare.cdsc.com.np/#/dashboard":
            return True
        return False


async def start(user, lock, headless):
    try:
        NAME, DP, USERNAME, PASSWD, _, _, _, _ = user
        log.info(f"Starting for user {NAME}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            
            # Set viewport and user agent
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            for attempt in range(4):
                try:
                    await page.goto("https://meroshare.cdsc.com.np/#/login")
                    await page.wait_for_selector("#username", timeout=5000)
                    log.info(f"Connection established for user {NAME}")
                    await asyncio.sleep(1)
                    break
                except Exception as e:
                    log.info(f"Connection attempt {attempt + 1} failed for user {NAME}")
                    if attempt == 3:
                        log.info(f"Connection could not be established for user {NAME} after {attempt} attempts")
                        await browser.close()
                        return False

            logged_in = False
            for attempt in range(4):
                try:
                    logged_in = await login(page, DP, USERNAME, PASSWD)
                    if not logged_in:
                        raise Exception
                    log.info(f"Logged in for {NAME}")
                    break
                except Exception as e:
                    current_url = page.url
                    if "accountExpire" in current_url:
                        await save_screenshot(page, NAME.lower(), "Expired")
                        account = current_url.split("/")[-1]
                        log.error(f"{account} for {NAME}")
                        await browser.close()
                        return False

                    if "PasswordChange" in current_url:
                        await save_screenshot(page, NAME.lower(), "PasswordChange")
                        account = current_url.split("/")[-1]
                        log.error(f"{account} for {NAME}")
                        await browser.close()
                        return False
                    
                    await save_screenshot(page, NAME.lower(), "Login")
                    await page.goto("https://meroshare.cdsc.com.np/#/login")
                    log.info(f"Problem Logging in {NAME}")
                    log.error(e)

            # Check for companies available
            if not logged_in:
                return False

            companies_available = await check_for_companies(page, lock, NAME)
            if companies_available == "not_authorized":
                log.info(f"User unauthorized {NAME}")
                await browser.close()
                return False

            if not companies_available:
                log.info(f"Exited for user {NAME}")
                await browser.close()
                return False

            await check_to_apply(page, user, companies_available, lock)

            # Close browser
            await browser.close()
            log.info(f"Completed for user {NAME}")
            return True
            
    except Exception as e:
        log.error(f"Error: {e}")
        return False


async def ipo_async(skip_input, headless):
    """Async version of the main IPO function"""
    global DIR_PATH, log 
    DIR_PATH = get_dir_path()
    log = get_logger("ipo")

    user_data = []
    lock = RLock()
    WAIT_TIME = 3

    if not skip_input:
        user = (input("Enter the user you want to apply: ")).lower().strip()

    fernet = get_fernet_key()
    if not fernet:
        log.error("Key not found")
        return

    with get_db() as db:
        if skip_input:
            users = db.query(User).all()
            if not users:
                log.debug("No users available")
                return
            user_data = [[user.name, user.dp, user.boid, (fernet.decrypt(user.passsword.encode())).decode(), user.crn, (fernet.decrypt(user.pin.encode())).decode(), user.account, user.id] for user in users]
        else:
            users = db.query(User).filter(User.name == user).first()
            user_data = [[users.name, users.dp, users.boid, (fernet.decrypt(users.passsword.encode())).decode(), users.crn, (fernet.decrypt(users.pin.encode())).decode(), users.account, users.id]]

    start_time = perf_counter()
    
    # Run all users concurrently
    tasks = []
    for i, user in enumerate(user_data):
        if i > 0:
            await asyncio.sleep(WAIT_TIME)
        task = asyncio.create_task(start(user, lock, headless))
        tasks.append((task, user[0]))
    
    completed_users = []
    failed_users = []
    
    for task, username in tasks:
        try:
            result = await asyncio.wait_for(task, timeout=300)  # 5 minute timeout per user
            if result:
                completed_users.append(username)
                log.info(f"Successfully completed for user: {username}")
            else:
                failed_users.append(username)
                log.warning(f"Failed to complete for user: {username}")
        except asyncio.TimeoutError:
            failed_users.append(username)
            log.error(f"Timeout for user {username}")
        except Exception as e:
            failed_users.append(username)
            log.error(f"Exception for user {username}: {e}")
    
    log.info(f"Completed users: {len(completed_users)}")
    log.info(f"Failed users: {len(failed_users)}")
    if failed_users:
        log.warning(f"Failed users: {', '.join(failed_users)}")

    end_time = perf_counter()
    time_delta = end_time - start_time
    minutes, seconds = divmod(time_delta, 60)
    log.info(f"Completed :: {minutes:.0f} minutes | {seconds:.1f} seconds")
    return


def ipo(skip_input, headless):
    return asyncio.run(ipo_async(skip_input, headless))
