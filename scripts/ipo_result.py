import os
import asyncio
from threading import RLock
from time import perf_counter
from collections import defaultdict

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from database.database import  get_db
from database.models import  Result, User, UserResult
from utils.helpers import get_dir_path, get_fernet_key, get_logger
from dotenv import load_dotenv

load_dotenv()
log = None
DIR_PATH = None 


def update_database(data, USER_ID):
    if len(data) == 0:
        return
    log.info("Updating results in database")
    try:
        with get_db() as db:
            for script, values in data.items():
                result = db.query(Result).filter(Result.script == script).first()
                if not result:
                    result = Result(script=script)
                    db.add(result)
                    db.commit()
                    db.refresh(result)
                for value in values:
                    user_result_value = value[0] + " - " + value[1]
                    user_result = (db.query(UserResult).filter(UserResult.user_id == USER_ID,UserResult.type == value[2],UserResult.result_id == result.id,).first())
                    if user_result:
                        user_result.value = user_result_value
                    else:
                        db.add(UserResult(user_id=USER_ID, type=value[2], value=user_result_value, result=result))
                db.commit()

            log.info("Database updated")
    except Exception as e:
        log.error(f"Error updating database: {USER_ID} - {e}")
    return

async def check_result(page, info, NAME):
    results = defaultdict(list)
    log.info(f"Checking results for {NAME}")
    
    for index, data in enumerate(info):
        name = data[1]
        type = data[4]
        
        try:
            # Click the button for the specific index
            await page.click(f"(//button[@type='button'])[{index+6}]", timeout=10000)
        except PlaywrightTimeoutError:
            continue
        
        await asyncio.sleep(1)
        
        # Retry logic for getting status and remarks
        for attempt in range(3):
            try:
                status_element = await page.wait_for_selector("(//div[@class='row'])[10]", timeout=5000)
                remarks_element = await page.wait_for_selector("(//div[@class='row'])[11]", timeout=5000)
                break
            except PlaywrightTimeoutError:
                await page.reload()
                await asyncio.sleep(2)
        
        remarks_text = await remarks_element.text_content()
        status_text = await status_element.text_content()
        
        remarks = remarks_text.split("\n")[1].strip()
        status = status_text.split("\n")[1].strip()
        
        results[name].append([status, remarks, type])
        
        # Click back button
        await page.click("xpath=/html/body/app-dashboard/div/main/div/app-application-report/div/div[1]/div/div[1]/div/div/div/button")
    
    log.info(f"Checks completed for {NAME}")
    return results


async def get_companies(page, NAME):
    info = []
    
    # Navigate to ABSA
    await page.goto("https://meroshare.cdsc.com.np/#/asba")
    await asyncio.sleep(1)
    await page.wait_for_load_state("networkidle")

    if page.url != "https://meroshare.cdsc.com.np/#/asba":
        log.debug(f"User was unauthorized {NAME}")
        return "not_authorized"
    # try:
    #     # Check for unauthorized popup
    #     await page.click("xpath=/html/body/div/div/div/button", timeout=2000)
    #     log.debug(f"User was unauthorized {NAME}")
    #     return "not_authorized"
    # except PlaywrightTimeoutError:
    #     pass

    for attempt in range(1, 5):
        try:
            # Navigate to Apply Issue
            await page.click("//main[@id='main']//li[3]//a[1]", timeout=5000)
            
            # Wait for company list to load
            await page.wait_for_selector(".company-list", timeout=5000)
            
            # Get all company elements
            shares_available = await page.query_selector_all(".company-list")
            
            log.info(f"Got Companies for {NAME}")
            break
            
        except PlaywrightTimeoutError:
            log.debug(f"Tried to get Companies for {NAME} ({attempt})")
            
            await page.goto("https://meroshare.cdsc.com.np/#/asba")
            await asyncio.sleep(2 + attempt)
            
            if attempt == 4:
                log.debug(f"No Companies available/loaded {NAME}")
                return False

    # Extract information from company elements (limit to first 3)
    for i, shares in enumerate(shares_available[:3]):
        text_content = await shares.text_content()
        info.append(text_content.split("\n"))
    
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

    await page.wait_for_load_state("networkidle")

    if page.url == "https://meroshare.cdsc.com.np/#/dashboard":
        return True
    return False

async def start(user, lock):
    NAME, DP, USERNAME, PASSWD, _, _, _, USER_ID = user
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        log.info(f"Starting for user {NAME}")
        
        # Connection establishment with retries
        for attempt in range(4):
            try:
                await page.goto("https://meroshare.cdsc.com.np/#/login")
                log.info(f"Connection established for user {NAME}")
                
                await asyncio.sleep(0.5)
                await page.wait_for_selector("#username", timeout=5000)
                break
                
            except Exception as e:
                log.info(f"Connection attempt {attempt + 1} failed for user {NAME}")
                
                if attempt == 3:
                    log.info(f"Connection could not be established for user {NAME} after 4 attempts")
                    await browser.close()
                    return False

        # Login with retries
        logged_in = False
        for attempt in range(4):
            try:
                logged_in = await login(page, DP, USERNAME, PASSWD)
                if not logged_in:
                    raise Exception("Login failed")
                
                log.info(f"Logged in for {NAME}")
                break
                
            except Exception as e:
                # Take screenshot on login failure
                await page.screenshot(path=f"Errors/{NAME.lower()}_login_failed.png")
                await page.goto("https://meroshare.cdsc.com.np/#/login")
                
                log.info(f"Problem Logging in {NAME}")

        if not logged_in:
            await browser.close()
            return False

        # Get companies to check
        companies_to_check = await get_companies(page, NAME)
        
        if companies_to_check == "not_authorized":
            log.info(f"User unauthorized {NAME}")
            await browser.close()
            return False

        if not companies_to_check:
            log.info(f"Exited for user {NAME}")
            await browser.close()
            return False

        # Check results
        results = await check_result(page, companies_to_check, NAME)

        # Update database (assuming this function exists)
        with lock:
            await update_database(results, USER_ID)  # You might need to make this async too

        log.info(f"Completed for user {NAME}")
        
        return True


async def ipo_result_async():
    global log, DIR_PATH
    
    log = get_logger("ipo-result")
    DIR_PATH = get_dir_path()
    
    lock = RLock()
    WAIT_TIME = 3

    fernet = get_fernet_key()
    if not fernet:
        log.error("Key not found")
        return
        
    with get_db() as db:
        users = db.query(User).all()
        user_data = [[user.name, user.dp, user.boid, (fernet.decrypt(user.passsword.encode())).decode(), user.crn, (fernet.decrypt(user.pin.encode())).decode(), user.account, user.id] for user in users]

    log.debug("Starting IPO Result")
    start_time = perf_counter()
    tasks = []
    for i, user in enumerate(user_data):
        if i > 0:
            await asyncio.sleep(WAIT_TIME)
        task = asyncio.create_task(start(user, lock))
        tasks.append((task, user[0]))
        break
    
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

def ipo_result():
    return asyncio.run(ipo_result_async())