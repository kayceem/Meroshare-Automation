import os
from os.path import dirname as up
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


DIR_PATH = os.getcwd()
DRIVER_PATH = up(up(DIR_PATH))
PATH = f"{DRIVER_PATH}\Driver\msedgedriver.exe"
WEBSITE = "NepaliPaisa"


def main(start_file=True):
    data = []
    # Opening edge driver
    ser = Service(PATH)
    option = Options()
    option.use_chromium = True
    option.add_argument("headless")
    option.add_experimental_option("excludeSwitches", ["enable-logging"])
    option.add_argument("--disable-extensions")
    option.add_argument("dom.disable_beforeunload=true")
    option.add_argument("--no-sandbox")
    option.add_argument("--disable-dev-shm-usage")
    option.add_argument("--disable-gpu")
    option.add_argument("--log-level=3")

    browser = webdriver.Edge(service=ser, options=option)
    print(f"{WEBSITE} :: Starting...")
    try:
        browser.get("https://www.nepalipaisa.com/ipo")
        print(f"{WEBSITE} :: Request successful!")
    except:
        print(f"{WEBSITE} :: Request failed!")
        return
    count = 1
    while True:
        try:
            if start_file:
                print(f"{WEBSITE} :: Fetching table")
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.ID, "tblIpo"))
            )
            table_body = browser.find_element(
                By.XPATH,
                "/html/body/section[1]/div/div/div/div/div/div/div[3]/div/div/div[1]/table",
            )
            break
        except:
            browser.get(browser.current_url)
            count += 1
            print(f"{WEBSITE} :: Could not load ipo table ({count})")
            if count > 3:
                print(f"{WEBSITE} :: Exited")
                browser.quit()
                return

    rows = table_body.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        if start_file:
            print(f"{WEBSITE} :: Fetching data")
        col = row.find_elements(By.TAG_NAME, "td")
        if len(col) != 8:
            continue
        if not "Ordinary" in col[1].text or "Closed" in col[6].text:
            continue
        name, share_type, quantity, opening_date, closing_date, _, status = (
            col[0].text,
            col[1].text,
            col[2].text,
            col[3].text,
            col[4].text,
            col[5].text,
            col[6].text,
        )
        data.append([name, quantity, opening_date, closing_date, status])
    print(f"{WEBSITE} :: Fetch success!")

    browser.quit()

    file_path = rf"{DIR_PATH}\\Results\\Upcoming IPO.txt"
    with open(file_path, "w", encoding="utf-8") as fp:
        print("PC :: Writing data")
        for item in data:
            name, quantity, opening_date, closing_date, status = item
            fp.write(
                f"{name} | {quantity} | {opening_date} | {closing_date} | {status}"
            )
            fp.write("\n\n")
    print("PC :: Write success!")
    if start_file:
        os.startfile(file_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted!")
        exit(1)
