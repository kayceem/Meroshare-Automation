from sys import exit
import os
from time import sleep, perf_counter
from concurrent.futures import ThreadPoolExecutor

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from database.database import  get_db
from database.models import  Result, User
from utils.helpers import create_browser, get_dir_path, get_logger, get_fernet_key, get_time
from dotenv import load_dotenv


load_dotenv()
log = get_logger('edis')
DIR_PATH = get_dir_path()

def save_screenshot(browser, NAME):
    now = get_time()
    filename = f"{DIR_PATH}/screenshots/EDIS/[{now}] {NAME}.png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    browser.save_screenshot(filename)
    return

def transfer_shares(browser, NAME, scripts):
    edis_url = "https://meroshare.cdsc.com.np/#/edis"
    browser.get(edis_url)
    for attempt in range(1,2):
        WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[1]/div/div/ul/li[2]/a"))).click()
        try:
            view_detail_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div/div/table/tbody/tr/td[4]/button")))
            view_detail_button.click()
            sleep(1)

            select_all_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[2]/div/div/table/thead/tr/th[2]/input")))
            select_all_box.click()
            sleep(0.5)

            proceed_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div/button")))
            proceed_button.click()
            sleep(1)

            disclaimer_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div[1]/div/input")))
            disclaimer_box.click()
            sleep(0.5)

            update_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[2]/app-transfer-shares/div/div/div[3]/div[2]/button[1]"))) 
            update_button.click()
            sleep(3)
            
            save_screenshot(browser, NAME)
        
        except:
            log.debug(f"No edis transfer menu for {NAME} ({attempt})")
            browser.get(edis_url)
            sleep(2 + attempt)
            if attempt == 2:
                log.debug(f"Could not EDIS for {NAME} ")
            return False
    
def calculate_holding_days(browser, NAME, scripts):
    purchase_source_url = "https://meroshare.cdsc.com.np/#/purchase"

    for script in scripts:
        browser.get(purchase_source_url)
        try:
            WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[1]/div/div/ul/li[2]/a"))).click()
        except: 
            log.debug(f"Unable to click on My Holdings for {script} for {NAME}")
            continue

        select_script = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "isin")))
        select_script = Select(select_script)
        select_script.select_by_visible_text(script)
        sleep(0.5)

        search_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/form/div/div/div/div/div/div[2]/button[1]")))
        search_button.click()
        sleep(0.5)

        select_all_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/div/div/div/div/table/thead/tr/th[2]/input")))
        select_all_box.click()
        sleep(0.5)

        proceed_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/button")))
        proceed_button.click()
        sleep(0.5)

        disclaimer_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/div/div[2]/div/input")))
        disclaimer_box.click()
        sleep(0.5)

        update_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-holdings/div/button[1]"))) 
        update_button.click()
        sleep(3)

        log.info(f"Updated holding days for {script} for {NAME}")
        
def calculate_wacc(browser, NAME, scripts):
    purchase_source_url = "https://meroshare.cdsc.com.np/#/purchase"

    for script in scripts:
        browser.get(purchase_source_url)
        WebDriverWait(browser, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

        select_script = browser.find_element(By.ID, "script")
        select_script.send_keys(f"{script}")
        sleep(0.5)

        select_script.send_keys(Keys.RETURN)
        sleep(0.5)

        select_all_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/div/div/div/div[2]/table/thead/tr/th[2]/input")))
        select_all_box.click()
        sleep(0.5)

        proceed_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/button")))
        proceed_button.click()
        sleep(0.5)

        disclaimer_box = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/div[2]/div/input")))
        disclaimer_box.click()
        sleep(0.5)

        update_button = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-purchase/div/div[2]/app-my-purchase-direct/div/button[1]"))) 
        update_button.click()
        sleep(3)

        log.info(f"Calculated WACC for {script} for {NAME}")

        select_script.clear()
        sleep(0.5)


def check_for_edis(browser, NAME):
    edis_url = "https://meroshare.cdsc.com.np/#/edis"
    browser.get(edis_url)

    try:
        WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/button"))).click()
        log.debug(f"User was unauthorized  {NAME}")
        return "not-authorized"
    except:
        pass

    for attempt in range(1,5):
            WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='main']/div/app-my-edis/div/div[1]/div/div/ul/li[2]/a"))).click()
            try:
                fallback_message = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "fallback-title-message")))
                fallback_message = fallback_message.text
                if "No EDIS" in fallback_message.upper():
                    log.info(f"No EDIS available for {NAME} ")
                    return "no-edis"
                if "PLEASE CALCULATE" in fallback_message.upper():
                    scripts = fallback_message.split(": ")[1].split(",")
                    log.info(f"EDIS available for {scripts} ")
                    break
            except:
                log.debug(f"Checking edis for {NAME} ({attempt})")
                browser.get(edis_url)
                sleep(2 + attempt)
                if attempt == 4:
                    log.debug(f"No EDIS available for {NAME} ")
                return False
    return scripts

def login(browser, DP, USERNAME, PASSWD):
    try:
        # Dp drop down menu
        WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "selectBranch"))).click()
        # Dp feild
        dp = browser.find_element(By.XPATH, "/html/body/span/span/span[1]/input")
        dp.send_keys(f"{DP}")
        dp.send_keys(Keys.RETURN)
    except:
        return False

    # Username filed
    username = browser.find_element(By.ID, "username")
    username.send_keys(f"{USERNAME}")

    # Password feild
    passwd = browser.find_element(By.ID, "password")
    passwd.send_keys(f"{PASSWD}")
    sleep(0.5)
    # Login button
    LOGIN = browser.find_element(By.XPATH,"/html/body/app-login/div/div/div/div/div/div/div[1]/div/form/div/div[4]/div/button",)
    LOGIN.click()
    sleep(0.5)
    try:
        WebDriverWait(browser, 3).until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/button"))).click()
        return False
    except:
        if browser.current_url == "https://meroshare.cdsc.com.np/#/dashboard":
            return True
        return False

def start(user, headless):
    NAME, DP, USERNAME, PASSWD, _, _, _, _ = user
    with create_browser(headless) as browser:

        log.info(f"Starting for user {NAME} ")
        for attempt in range(4):
            try:
                browser.get("https://meroshare.cdsc.com.np/#/login")
                log.info(f"Connection established for user {NAME} ")
                sleep(0.5)
                WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "username")))
                break
            except Exception as e:
                log.info(f"Connection attempt {attempt + 1} failed for user {NAME}: {e}")
                if attempt == 3:
                    log.info(f"Connection could not be established for user {NAME} after 4 attempts")
                    return False

        for attempt in range(4):
            try:
                logged_in = login(browser, DP, USERNAME, PASSWD)
                if not logged_in:
                    raise Exception
                log.info(f"Logged in for {NAME} ")
                break
            except:
                current_url = browser.current_url
                if "accountExpire" in current_url:
                    save_screenshot(browser, NAME.lower(), "Expired", USERNAME)
                    account = current_url.split("/")[-1]
                    log.error(f"{account}Account expired for {NAME}")
                    return False
                save_screenshot(browser, NAME.lower(), "Login", USERNAME)
                browser.get("https://meroshare.cdsc.com.np/#/login")
                login_failed += 1
                log.info(f"Problem Logging in {NAME}")

        if not logged_in:
            return False

        edis_scripts = check_for_edis(browser, NAME)
        if edis_scripts == "not_authorized":
            log.info(f"User unauthorized {NAME}")
            return False

        if edis_scripts == "no-edis":
            log.info(f"Exited for user {NAME}")
            return True
            
        if edis_scripts:
            calculate_wacc(browser, NAME, edis_scripts)   
            calculate_holding_days(browser, NAME, edis_scripts)

        transfer_shares(browser, NAME, edis_scripts)
            
        log.info(f"Completed for user {NAME} ")
        return True


def edis(user, headless):
    user_data = []
    WAIT_TIME = 3

    user = user.strip().lower()
    fernet = get_fernet_key()
    if not fernet:
        log.error("Key not found")
        return

    with get_db() as db:
        users = db.query(User).filter(User.name == user).first()
        user_data = [[users.name, users.dp, users.boid, (fernet.decrypt(users.passsword.encode())).decode(), users.crn, (fernet.decrypt(users.pin.encode())).decode(), users.account, users.id]]
        
    start_time = perf_counter()
    executor = ThreadPoolExecutor()
    # print(executor._max_workers)
    for user in user_data:
        executor.submit(start, user, headless)
        sleep(WAIT_TIME)
    executor.shutdown(wait=True)
    end_time = perf_counter()

    time_delta = end_time - start_time
    minutes, seconds = divmod(time_delta, 60)
    log.info(f"Completed :: {minutes:.0f} minutes | {seconds:.1f} seconds")
    return
