import os
import logging
import datetime
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from pathlib import Path
from utils.chrome_helper import setup_chrome_and_driver

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from contextlib import contextmanager
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import read_version_from_cmd 
from webdriver_manager.core.os_manager import PATTERN

def get_dir_path() -> Path:
    return Path(__file__).parent.parent
    
@contextmanager
def create_browser(headless: bool = True): 
        BINARY_PATH = get_dir_path() / "chrome/chrome"
        if not BINARY_PATH.exists():
            setup_chrome_and_driver(get_dir_path())
        version = read_version_from_cmd(f"{BINARY_PATH} --version", PATTERN["google-chrome"])
        print(f"Chrome Version: {version}")
        
        option = Options()
        option.binary_location = str(BINARY_PATH)
        option.use_chromium = True
        ser = Service(ChromeDriverManager(driver_version=version).install())
        if headless:
            option.add_argument("headless")
        option.add_experimental_option("excludeSwitches", ["enable-logging"])
        option.add_argument("--disable-extensions")
        option.add_argument("--disable-gpu")
        option.add_argument("start-maximized")
        option.add_argument("--disable-inforbars")
        option.add_argument("--no-sandbox")
        option.add_argument("dom.disable_beforeunload=true")
        option.add_argument("--log-level=3")
        try:
            browser = webdriver.Chrome(service=ser, options=option)
            yield browser
        except:
            pass
        finally:
            if browser:
                browser.quit()
                
def get_logger(app="app", level=logging.DEBUG):
    logs_dir = os.path.join(get_dir_path(), "logs")
    os.makedirs(os.path.dirname(logs_dir), exist_ok=True)
    logging.basicConfig(
    level=level,
    datefmt='%Y-%m-%d %H:%M:%S',
    format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(get_dir_path(), "logs", f"{app}.log"), mode='a'),logging.StreamHandler()]
    )
    logging.getLogger('selenium').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    logging.getLogger('WDM').setLevel(logging.ERROR)

    log = logging.getLogger(__name__)
    return log

def get_fernet_key(key=None):
    if not key:
        key = os.getenv("KEY")
    if not key:
        return None
    return Fernet(key)

def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

def encrypt_string(string: str, key=None):
    fernet = get_fernet_key(key)
    if not fernet:
        return None
    encrypted = fernet.encrypt(string.encode())
    return encrypted.decode()

def get_bank_id():
    bank_id = {"11500": "49", "17300": "42", "10400": "37", "13700": "44", "12600": "48", "11000": "45"}
    return bank_id