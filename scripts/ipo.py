#!/home/kayc/Code/Python/MeroShare-IPO/.venv/bin/python

import os
from time import sleep, perf_counter
from threading import RLock
from concurrent.futures import ThreadPoolExecutor
from cryptography.fernet import Fernet

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from database.database import get_db
from database.models import Application, User
from utils.helpers import create_browser, get_bank_id, get_dir_path, get_fernet_key, get_logger, get_time
from dotenv import load_dotenv

load_dotenv()
DIR_PATH = None
log = None
# select_DP = {
#     '11500' : '171',
#     '17300' : '162',
#     '10400' : '164',
#     '13700' : '174',
#     '12600' : '179',
#     '11000' : '175',
# }


def save_screenshot(browser, NAME, name, share_applied=""):
    now = get_time()
    filename = f"{DIR_PATH}/screenshots/{name}/{share_applied}/{NAME}-[{now}].png"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    browser.save_screenshot(filename)
    return

def update_database(username,user_id, applied_shares):
    try:
        log.info(f"Updating database for {username}")
        if len(applied_shares) == 0:
            return
        with get_db() as db:
            for shares in applied_shares:
                ipo_name, _, _, ipo, share_type, button = shares
                existing_entry = db.query(Application).filter(Application.name == username and Application.ipo_name == ipo_name).first()
                if existing_entry:
                    existing_entry.button = button
                    existing_entry.share_type = share_type
                else:
                    db.add(Application(user_id=user_id, name=username, ipo_name=ipo_name, ipo=ipo, share_type=share_type, button=button))
            db.commit()
        log.info(f"Database updated for {username}")
    except Exception as e:
        log.error(f"Error updating database for {username}: {e}")
    return


def apply_share(browser, CRN, PIN, DP, ipo, ACCOUNT_NUMBER):
    bank_id = get_bank_id()
    try:
        check = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "selectBank")))
    except:
        return False
    """
    select_bank = browser.find_element(By.ID, "selectBank")
    select_bank.click()
    sleep(0.5)
    select_bank.send_keys(Keys.DOWN)
    select_bank.send_keys(Keys.DOWN)
    select_bank.send_keys(Keys.RETURN)
    """
    option = Select(browser.find_element(By.ID, "selectBank"))
    option.select_by_value(f"{bank_id[DP]}")
    sleep(0.5)
    option = Select(browser.find_element(By.ID, "accountNumber"))
    option.select_by_value(f"{ACCOUNT_NUMBER}")
    sleep(0.5)
    
    quantity = browser.find_element(By.ID, "appliedKitta")
    if ipo == "IPO" or ipo == "FPO":
        ########### Clearing the quantity if any ############
        browser.find_element(By.ID, "appliedKitta").clear()
        ############## DO NOT CHANGE THIS ###################
        QUANTITY = 10
        if QUANTITY != 10:
            QUANTITY = 10
        quantity.send_keys(f"{QUANTITY}")
        #####################################################
    text = quantity.get_attribute("value")

    # Entering CRN
    crn = browser.find_element(By.ID, "crnNumber")
    crn.clear()
    crn.send_keys(f"{CRN}")
    # Checking privacy policy and clicking on proceed button
    browser.find_element(By.ID, "disclaimer").click()
    try:
        browser.find_element(By.XPATH, "/html/body/app-dashboard/div/main/div/app-issue/div/wizard/div/wizard-step[1]/form/div[2]/div/div[5]/div[2]/div/button[1]").click()
    except:
        browser.find_element(By.XPATH, "/html/body/app-dashboard/div/main/div/app-re-apply/div/div/wizard/div/wizard-step[1]/form/div[2]/div/div[4]/div[2]/div/button[1]").click()
    sleep(1)

    # Entering pin
    pin = WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.ID, "transactionPIN")))
    pin.send_keys(f"{PIN}")
    # breakpoint()

    # Clicking on apply button
    try:
        browser.find_element(By.XPATH, "/html/body/app-dashboard/div/main/div/app-issue/div/wizard/div/wizard-step[2]/div[2]/div/form/div[2]/div/div/div/button[1]").click()
    except:
        browser.find_element(By.XPATH, "/html/body/app-dashboard/div/main/div/app-re-apply/div/div/wizard/div/wizard-step[2]/div[2]/div/form/div[2]/div/div/div/button[1]").click()
    try:
        toast = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "toast-message")))
        if not "Share has been applied successfully." in toast.text:
            return False
    except: 
        return False
    sleep(3)
    return int(text)


def check_to_apply(browser, user, info, lock):
    applied_shares = []
    quantities = []
    NAME, DP, _, _, CRN, PIN,ACCOUNT_NUMBER, USER_ID = user

    for index, data in enumerate(info):
        # Checking if there is a button
        try:
            name, _, _, ipo, share_type, button = data
        # If not continue to another share
        except:
            name = data[0]
            button = "No button"
            log.info(f"Already applied for {NAME} : {name} | {button} ")

            continue
        if not share_type == "Ordinary Shares" and "Local" not in share_type:
            log.info(f"Not applied for {NAME} : {share_type} | {name}")
            continue

        if button == "Edit":
            log.info(f"Already applied for {NAME} : {name} : {button}")
            continue

        # Checking if the share is IPO | can be applied | and is not debenture
        if not (ipo == "IPO" or ipo == "FPO") and not ipo == "RESERVED (RIGHT SHARE)":
            continue
        if not (button == "Apply" or button == "Reapply"):
            continue

        try:
            browser.find_element(By.XPATH, f"/html/body/app-dashboard/div/main/div/app-asba/div/div[2]/app-applicable-issue/div/div/div/div/div[{index+1}]/div/div[2]/div/div[4]/button").click()
        except:
            browser.find_element(By.XPATH, f"/html/body/app-dashboard/div/main/div/app-asba/div/div[2]/app-applicable-issue/div/div/div/div/div[{index+1}]/div/div[2]/div/div[3]/button").click()

        for attempt in range(4):
            try:
                share_applied = apply_share(browser, CRN, PIN, DP, ipo, ACCOUNT_NUMBER)
                if share_applied:
                    save_screenshot(browser, NAME, name, share_applied)
                    log.info(f"Applied shares for {NAME} : {name} : {share_applied} shares")
                    quantities.append(share_applied)
                    applied_shares.append(data)
                    break
            except Exception as e:
                browser.get(browser.current_url)
            log.info(f"Could not apply {NAME} : {name} (Attempt {attempt + 1})")
                
    with lock:
        update_database(NAME,USER_ID,applied_shares)
    return


def check_for_companies(browser, lock, NAME):
    info = []

    # Navigating to ABSA
    browser.get("https://meroshare.cdsc.com.np/#/asba")
    try:
        WebDriverWait(browser, 2).until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/button"))).click()
        log.info(f"User was unauthorized  {NAME} ")
        return "not_authorized"
    except:
        pass

    for attempt in range(1,5):
      
        # Getting all the companies from Apply Issue
        try:
            WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "company-list")))
            # gets lists of web element
            shares_available = browser.find_elements(By.CLASS_NAME, "company-list")
            log.info(f"Got Companies for {NAME} ")
            break
        except:
            log.info(f"Tried to get Companies for {NAME} ({attempt})")
            browser.get("https://meroshare.cdsc.com.np/#/asba")
            sleep(2 + attempt)

        if attempt == 4:
            log.info(f"No Comapnies available/loaded  {NAME} ")
            return False
        
    # Storing all the information of comapnies from the web elements as list in a list : info
    for shares in shares_available:
        info.append(shares.text.split("\n"))
    return info


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
    LOGIN = browser.find_element(By.XPATH, "/html/body/app-login/div/div/div/div/div/div/div[1]/div/form/div/div[4]/div/button")
    LOGIN.click()
    sleep(0.5)
    try:
        WebDriverWait(browser, 3).until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/button"))).click()
        return False
    except:
        if browser.current_url == "https://meroshare.cdsc.com.np/#/dashboard":
            return True
        return False


def start(user, lock, headless):
    try:
        NAME, DP, USERNAME, PASSWD, _, _, _, _ = user
        log.info(f"Starting for user {NAME} ")

        with create_browser(headless) as browser:

            for attempt in range(4):
                try:
                    browser.get("https://meroshare.cdsc.com.np/#/login")
                    WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "username")))
                    log.info(f"Connection established for user {NAME} ")
                    sleep(0.5)
                    break
                except Exception as e:
                    log.info(f"Connection attempt {attempt + 1} failed for user {NAME}")
                    if attempt == 3:
                        log.info(f"Connection could not be established for user {NAME} after {attempt} attempts")
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
                        save_screenshot(browser, NAME.lower(), "Expired")
                        account = current_url.split("/")[-1]
                        log.error(f"{account}  for {NAME}")
                        return False

                    if "PasswordChange" in current_url:
                        save_screenshot(browser, NAME.lower(), "PasswordChange")
                        account = current_url.split("/")[-1]
                        log.error(f"{account} for {NAME}")
                        return False
                    
                    save_screenshot(browser, NAME.lower(), f"Login")
                    browser.get("https://meroshare.cdsc.com.np/#/login")
                    login_failed += 1
                    log.info(f"Problem Logging in {NAME}")

            # Checks for companies available
            if logged_in:
                companies_available = check_for_companies(browser, lock, NAME)
                if companies_available == "not_authorized":
                    log.info(f"User unauthorized {NAME}")
                    return False

            if not companies_available:
                log.info(f"Exited for user {NAME}")
                return False

            check_to_apply(browser, user, companies_available, lock)

            # Quiting the browser
            log.info(f"Completed for user {NAME} ")
            return True
    except Exception as e:
        log.error(f"Error: {e}")
        return False

def ipo(skip_input, headless):
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
    executor = ThreadPoolExecutor()
    # print(executor._max_workers)
    # print(os.cpu_count())
    for user in user_data:
        executor.submit(start, user, lock, headless)
        sleep(WAIT_TIME)
    executor.shutdown(wait=True)
    end_time = perf_counter()

    time_delta = end_time - start_time
    minutes, seconds = divmod(time_delta, 60)
    log.info(f"Completed :: {minutes:.0f} minutes | {seconds:.1f} seconds")
    return
