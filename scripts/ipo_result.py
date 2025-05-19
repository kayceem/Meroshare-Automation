from collections import defaultdict
from sys import exit
import os
from threading import RLock
from time import sleep, perf_counter
from concurrent.futures import ThreadPoolExecutor
from cryptography.fernet import Fernet

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from database.database import  get_db
from database.models import  Result, User, UserResult
from utils.helpers import create_browser, get_dir_path, get_fernet_key, get_logger
from dotenv import load_dotenv

load_dotenv()
log = get_logger('ipo-result')
DIR_PATH = get_dir_path()


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


def check_result(browser, info, lock, NAME):
    results = defaultdict(list)
    log.info(f"Checking results for {NAME}")
    for index, data in enumerate(info):
        name = data[1]
        type = data[4]
        try:
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, f"(//button[@type='button'])[{index+6}]"))).click()
        except:
            continue
        sleep(1)
        for _ in range(3):
            try:
                status = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "(//div[@class='row'])[10]")))
                remarks = WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, f"(//div[@class='row'])[11]")))
                break
            except:
                browser.refresh()
                sleep(2)
        remarks = remarks.text.split("\n")[1].strip()
        status = status.text.split("\n")[1].strip()
        results[name].append([status, remarks, type])
        browser.find_element(By.XPATH,"/html/body/app-dashboard/div/main/div/app-application-report/div/div[1]/div/div[1]/div/div/div/button",).click()
    log.info(f"Checks completed for {NAME}")
    return results


def get_companies(browser, lock, NAME):
    info = []
    # Navigating to ABSA
    browser.get("https://meroshare.cdsc.com.np/#/asba")
    try:
        WebDriverWait(browser, 2).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/div/div/button"))
        ).click()
        with lock:
            log.debug(f"User was unauthorized  {NAME}")
        return "not_authorized"
    except:
        pass

    for attempt in range(1,5):
        WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.XPATH, "//main[@id='main']//li[3]//a[1]"))).click()
        # Getting all the companies from Apply Issue
        try:
            WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "company-list")))
            # gets lists of web element
            shares_available = browser.find_elements(By.CLASS_NAME, "company-list")
            with lock:
                log.info(f"Got Companies for {NAME} ")
            break
        except:
            with lock:
                log.debug(f"Tried to get Companies for {NAME} ({attempt})")
            browser.get("https://meroshare.cdsc.com.np/#/asba")
            sleep(2 + attempt)
            if attempt == 4:
                log.debug(f"No Comapnies available/loaded  {NAME} ")
                return False
    # Storing all the information of comapnies from the web elements as list in a list : info
    for shares in shares_available[:3]:
        info.append(shares.text.split("\n"))
    return info


def login(browser, DP, USERNAME, PASSWD):
    try:
        # Dp drop down menu
        WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "selectBranch"))).click()
        # Dp field
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


def start(user, lock):
    NAME, DP, USERNAME, PASSWD, _, _, _, USER_ID = user
    with create_browser() as browser:
        log.info(f"Starting for user {NAME} ")
        for attempt in range(4):
            try:
                browser.get("https://meroshare.cdsc.com.np/#/login")
                with lock:
                    log.info(f"Connection established for user {NAME} ")
                sleep(0.5)
                WebDriverWait(browser, 5).until(EC.presence_of_element_located((By.ID, "username")))
                break
            except Exception as e:
                with lock:
                    log.info(f"Connection attempt {attempt + 1} failed for user {NAME}")
                if attempt == 3:
                    with lock:
                        log.info(f"Connection could not be established for user {NAME} after 4 attempts")
                    return False

        for attempt in range(4):
            try:
                logged_in = login(browser, DP, USERNAME, PASSWD)
                if not logged_in:
                    raise Exception
                with lock:
                    log.info(f"Logged in for {NAME} ")
                break
            except:
                browser.get_screenshot_as_file(f"Errors/{NAME.lower()}_{login_failed}.png")
                browser.get("https://meroshare.cdsc.com.np/#/login")
                with lock:
                    log.info(f"Problem Logging in {NAME}")

        if logged_in:
            companies_to_check = get_companies(browser, lock, NAME)
            if companies_to_check == "not_authorized":
                with lock:
                    log.info(f"User unauthorized {NAME}")
                return False

        if not companies_to_check:
            with lock:
                log.info(f"Exited for user {NAME}")
            return False

        #  Check result available companies
        with lock:
            log.debug(f"Checking results for {NAME}")

        results = check_result(browser, companies_to_check, lock, NAME)

        with lock:
            update_database(results, USER_ID)

        # Quiting the browser
        with lock:
            log.info(f"Completed for user {NAME} ")
        return True


def ipo_result():
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
    executor = ThreadPoolExecutor()
    for user in user_data:
        executor.submit(start, user, lock)
        sleep(WAIT_TIME)
    executor.shutdown(wait=True)
    end_time = perf_counter()

    time_delta = end_time - start_time
    minutes, seconds = divmod(time_delta, 60)
    with lock:
        log.debug(f"Completed :: {minutes:.0f} minutes | {seconds:.1f} seconds")

    return

