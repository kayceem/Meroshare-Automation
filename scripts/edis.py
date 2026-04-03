import os
import asyncio
from time import perf_counter
from threading import RLock

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from database.database import  get_db
from database.models import  Result, User
from utils.helpers import get_dir_path, get_logger, get_fernet_key, get_time
from dotenv import load_dotenv


load_dotenv()
log = None
DIR_PATH = None 

async def save_screenshot(page, NAME):
    now = get_time()
    filename = f"{DIR_PATH}/screenshots/EDIS/[{now}] {NAME}.png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    await page.screenshot(path=filename)
    return

async def transfer_shares(page, NAME, scripts):
    edis_url = "https://meroshare.cdsc.com.np/#/edis"
    await page.goto(edis_url)
    for attempt in range(1,2):
        await page.click("//*[@id='main']/div/app-my-edis/div/div[1]/div/div/ul/li[2]/a")
        try:
            await page.click("//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div/div/table/tbody/tr/td[4]/button", timeout=5000)
            await asyncio.sleep(1)

            await page.click("//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[2]/div/div/table/thead/tr/th[2]/input", timeout=5000)
            await asyncio.sleep(0.5)

            await page.click("//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div/button", timeout=5000)
            await asyncio.sleep(1)

            await page.click("//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div[1]/div/input", timeout=5000)
            await asyncio.sleep(0.5)

            await page.click("//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div[2]/button[1]", timeout=5000)
            await asyncio.sleep(3)

            await save_screenshot(page, NAME)

        except PlaywrightTimeoutError:
            log.debug(f"No edis transfer menu for {NAME} ({attempt})")
            await page.goto(edis_url)
            await asyncio.sleep(2 + attempt)
            if attempt == 2:
                log.debug(f"Could not EDIS for {NAME} ")
            return False
    
async def calculate_holding_days(page, NAME, scripts):
    purchase_source_url = "https://meroshare.cdsc.com.np/#/purchase"

    for script in scripts:
        await page.goto(purchase_source_url)
        try:
            await page.click("//*[@id='main']/div/app-my-purchase/div/div[1]/div/div/ul/li[2]/a", timeout=5000)
        except PlaywrightTimeoutError:
            log.debug(f"Unable to click on My Holdings for {script} for {NAME}")
            continue

        await page.select_option("#isin", label=script)
        await asyncio.sleep(0.5)

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/form/div/div/div/div/div/div[2]/button[1]", timeout=5000)
        await asyncio.sleep(0.5)
        try:
            await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/div/div/div/div/table/thead/tr/th[2]/input", timeout=5000)
            await asyncio.sleep(0.5)
        except PlaywrightTimeoutError:
            log.debug(f"Unable to select all for {script} for {NAME}")
            continue
        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/button", timeout=5000)
        await asyncio.sleep(0.5)

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/div/div[2]/div/input", timeout=5000)
        await asyncio.sleep(0.5)

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/button[1]", timeout=5000)
        await asyncio.sleep(3)

        log.info(f"Updated holding days for {script} for {NAME}")
        
async def calculate_wacc(page, NAME, scripts):
    purchase_source_url = "https://meroshare.cdsc.com.np/#/purchase"

    for script in scripts:
        await page.goto(purchase_source_url)
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        select_script = page.locator("#script")
        await select_script.fill(f"{script}")
        await asyncio.sleep(0.5)

        await select_script.press("Enter")
        await asyncio.sleep(0.5)
        try:
            await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/div/div/div/div[2]/table/thead/tr/th[2]/input", timeout=5000)
            await asyncio.sleep(0.5)
        except PlaywrightTimeoutError:
            log.debug(f"Unable to select all for {script} for {NAME}")
            continue

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/button", timeout=5000)
        await asyncio.sleep(0.5)

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/div[2]/div/input", timeout=5000)
        await asyncio.sleep(0.5)

        await page.click("//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/button[1]", timeout=5000)
        await asyncio.sleep(3)

        log.info(f"Calculated WACC for {script} for {NAME}")

        await select_script.clear()
        await asyncio.sleep(0.5)


async def check_for_edis(page, NAME):
    edis_url = "https://meroshare.cdsc.com.np/#/edis"
    await page.goto(edis_url)

    try:
        await page.click("xpath=/html/body/div/div/div/button", timeout=2000)
        log.debug(f"User was unauthorized  {NAME}")
        return "not-authorized"
    except PlaywrightTimeoutError:
        pass

    for attempt in range(1,5):
            await page.click("//*[@id='main']/div/app-my-edis/div/div[1]/div/div/ul/li[2]/a", timeout=5000)
            try:
                fallback_message = await page.wait_for_selector(".fallback-title-message", timeout=5000)
                fallback_message_text = await fallback_message.text_content()
                if "No EDIS" in fallback_message_text.upper():
                    log.info(f"No EDIS available for {NAME} ")
                    return "no-edis"
                if "PLEASE CALCULATE" in fallback_message_text.upper():
                    scripts = fallback_message_text.split(": ")[1].split(",")
                    log.info(f"EDIS available for {scripts} ")
                    break
            except PlaywrightTimeoutError:
                log.debug(f"Checking edis for {NAME} ({attempt})")
                await page.goto(edis_url)
                await asyncio.sleep(2 + attempt)
                if attempt == 4:
                    log.debug(f"No EDIS available for {NAME} ")
                return False
    return scripts

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

async def start(user, headless):
    NAME, DP, USERNAME, PASSWD, _, _, _, _ = user

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()

        # Set viewport
        await page.set_viewport_size({"width": 1600, "height": 800})

        log.info(f"Starting for user {NAME} ")
        for attempt in range(4):
            try:
                await page.goto("https://meroshare.cdsc.com.np/#/login")
                log.info(f"Connection established for user {NAME} ")
                await asyncio.sleep(0.5)
                await page.wait_for_selector("#username", timeout=5000)
                break
            except Exception as e:
                log.info(f"Connection attempt {attempt + 1} failed for user {NAME}: {e}")
                if attempt == 3:
                    log.info(f"Connection could not be established for user {NAME} after 4 attempts")
                    await browser.close()
                    return False

        logged_in = False
        for attempt in range(4):
            try:
                logged_in = await login(page, DP, USERNAME, PASSWD)
                if not logged_in:
                    raise Exception
                log.info(f"Logged in for {NAME} ")
                break
            except Exception as e:
                current_url = page.url
                if "accountExpire" in current_url:
                    await save_screenshot(page, f"{NAME.lower()}_Expired")
                    account = current_url.split("/")[-1]
                    log.error(f"{account} Account expired for {NAME}")
                    await browser.close()
                    return False
                await save_screenshot(page, f"{NAME.lower()}_Login")
                await page.goto("https://meroshare.cdsc.com.np/#/login")
                log.info(f"Problem Logging in {NAME}")

        if not logged_in:
            await browser.close()
            return False

        edis_scripts = await check_for_edis(page, NAME)
        if edis_scripts == "not_authorized":
            log.info(f"User unauthorized {NAME}")
            await browser.close()
            return False

        if edis_scripts == "no-edis":
            log.info(f"Exited for user {NAME}")
            await browser.close()
            return True

        if len(edis_scripts) > 0:
            await calculate_wacc(page, NAME, edis_scripts)
            await calculate_holding_days(page, NAME, edis_scripts)

        await transfer_shares(page, NAME, edis_scripts)

        await browser.close()
        log.info(f"Completed for user {NAME} ")
        return True


async def edis_async(user, headless):
    global log, DIR_PATH
    log = get_logger('edis')
    DIR_PATH = get_dir_path()
    user_data = []
    WAIT_TIME = 3

    if user is None:
        log.error("User argument is required. Please specify --user <username>")
        return

    user = user.strip().upper()
    fernet = get_fernet_key()
    if not fernet:
        log.error("Key not found")
        return

    with get_db() as db:
        users = db.query(User).filter(User.name == user).first()
        user_data = [[users.name, users.dp, users.boid, (fernet.decrypt(users.passsword.encode())).decode(), users.crn, (fernet.decrypt(users.pin.encode())).decode(), users.account, users.id]]

    start_time = perf_counter()

    # Run all users concurrently
    tasks = []
    for i, user in enumerate(user_data):
        if i > 0:
            await asyncio.sleep(WAIT_TIME)
        task = asyncio.create_task(start(user, headless))
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


def edis(user, headless):
    return asyncio.run(edis_async(user, headless))
