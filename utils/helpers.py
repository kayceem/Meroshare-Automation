import os
import logging
import datetime
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from pathlib import Path

def get_dir_path() -> Path:
    return Path(__file__).parent.parent
    
def get_logger(app="app", level=logging.INFO):
    logs_dir = os.path.join(get_dir_path(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logging.basicConfig(
    level=level,
    datefmt='%Y-%m-%d %H:%M:%S',
    format='%(asctime)s - %(module)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(os.path.join(get_dir_path(), "logs", f"{app}.log"), mode='a'),logging.StreamHandler()]
    )
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