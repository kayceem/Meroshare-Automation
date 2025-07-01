import os
import platform
import shutil
import requests
import zipfile

def download_file(url, destination):
    if os.path.exists(destination):
        return
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(destination, 'wb') as file:
        for chunk in response.iter_content(8192):
            file.write(chunk)

def get_platform_config():
    base_url = "https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.91"

    system = platform.system()

    if system == "Windows":
        folder = "win64"
        chrome_zip = "chrome-win64.zip"
        binary_name = "chrome.exe"
    elif system == "Linux":
        folder = "linux64"
        chrome_zip = "chrome-linux64.zip"
        binary_name = "chrome"
    else:
        raise Exception("Unsupported OS")

    return {
        "chrome_url": f"{base_url}/{folder}/{chrome_zip}",
        "chrome_zip_name": chrome_zip,
        "binary_name": binary_name
    }

def setup_chrome_and_driver(base_dir):
    config = get_platform_config()
    chrome_folder = base_dir / "chrome"
    chrome_folder.mkdir(exist_ok=True)

    chrome_zip_path = chrome_folder / config["chrome_zip_name"]
    extracted_folder = chrome_folder
    chrome_binary_path = chrome_folder / config["binary_name"]

    print(f"Downloading Chrome for {platform.system()}...")
    download_file(config["chrome_url"], chrome_zip_path)

    with zipfile.ZipFile(chrome_zip_path, 'r') as zip_ref:
        zip_ref.extractall(chrome_folder)

    if extracted_folder.exists():
        subfolder = extracted_folder / config["chrome_zip_name"].replace(".zip", "")
        for item in subfolder.iterdir():
            shutil.move(str(item), chrome_folder)
        shutil.rmtree(subfolder)

    chrome_zip_path.unlink()

    if platform.system() != "Windows":
        chrome_binary_path.chmod(0o755)
        crashpad = chrome_folder / "chrome_crashpad_handler"
        if crashpad.exists():
            crashpad.chmod(0o755)
