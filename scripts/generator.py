import os
import stdiomask
from database.accessors import get_accessor
from database.schemas import UserUpsert
from utils.helpers import get_dir_path, get_fernet_key, get_logger
from dotenv import load_dotenv
import csv
load_dotenv()


USERS = []
options = ["1", "2", "3", "4", "5", "6"]
sub_options = ["1", "2", "3", "4", "5"]
DIR_PATH = get_dir_path()

log = get_logger("generator")

fernet = get_fernet_key()
if not fernet:
    log.error("Key not found")
    exit(1)
    
def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def load_data_base():
    try:
        USERS.clear()
        with get_accessor() as db:
            users = db.users.list_all()
            if not users:
                return False
            for user in users:
                user_dict = {
                    "name": user.name,
                    "dp": user.dp,
                    "boid": user.boid,
                    "passsword": user.passsword,
                    "crn": user.crn,
                    "pin": user.pin,
                    "account": user.account,
                    "apply_ipo": user.apply_ipo,
                }
                USERS.append(user_dict)
            return True
    except:
        return False


def display_user_data():
    if not USERS:
        print("No users found!")
        return
    clear_screen()
    print("-" * 50)
    for user in USERS:
        print(f"-> {user.get('name')} | {user.get('dp')} | {user.get('boid')} ")
        print()
    print("-" * 50)



def menu():
    while True:
        clear_screen()
        print("-" * 50)
        print()
        print("1. Add new user")
        print("2. Update user")
        print("3. Delete user")
        print("4. Display")
        print("5. Exit")
        print("6. Import users from CSV")   # <-- new option
        print()
        option = input("Choose one option: ")
        if option in options:
            return option


def sub_menu(user_exists=0):
    if user_exists:
        while True:
            print()
            print("1. Update password")
            print("2. Update PIN")
            print("3. Cancel")
            print("4. Update CRN")
            print("5. Update IPO Application Status")
            print()
            option = input("Choose one option: ")
            if option in sub_options:
                return option
    # try:
    name = input("Enter name: ")
    while True:
        try:
            dp = int(input("Enter DP: ").strip())
            id = int(input("Enter BOID: ").strip())
            pin = int(stdiomask.getpass("Enter pin: ").strip())
            account_number = input("Enter account number: ").strip()
            break
        except:
            print()
            print("Enter numbers!")
            print()

    passwd = stdiomask.getpass("Enter passwd: ").strip()
    crn = input("Enter crn: ").strip()
    passwd = fernet.encrypt(passwd.encode()).decode()
    pin = fernet.encrypt(str(pin).encode()).decode()
    apply_ipo = input("Apply for IPO? (y/n): ").strip().lower() in {"y", "yes", "1", "true"}
    USERS.append({
        "name": name.upper(),
        "dp": dp,
        "boid": id,
        "passsword": passwd,
        "crn": crn,
        "pin": pin,
        "account": account_number,
        "apply_ipo": apply_ipo,
    })
    return True

def check_user(user_name):
    for user in USERS:
        if user.get('name').upper() == user_name:
            return True
    return False


def update_pin_or_passwd(user_name, pin=0, passwd=0, crn=0, apply_ipo=0):
    if pin == passwd == crn == apply_ipo == 1:
        return False

    if pin == 1:
        while True:
            try:
                new_pin = int(input("Enter new pin:").strip())
                new_pin = fernet.encrypt(str(new_pin).encode()).decode()
                break
            except:
                return False
        for user in USERS:
            if user_name.upper() != user.get('name').upper():
                continue
            user['pin'] = new_pin
            return True
    if passwd == 1:
        while True:
            try:
                new_passwd = input("Enter new password:").strip()
                new_passwd = fernet.encrypt(new_passwd.encode()).decode()
                break
            except:
                return False
        for user in USERS:
            if user_name.upper() != user.get('name').upper():
                continue
            user['passsword'] = new_passwd
            return True
    if crn == 1:
        while True:
            try:
                new_crn = input("Enter crn:").strip()
                break
            except:
                return False
        for user in USERS:
            if user_name != user.get('name').upper():
                continue
            user['crn'] = new_crn
            return True
    if apply_ipo == 1:
        while True:
            try:
                new_apply_ipo = input("Apply for IPO? (y/n): ").strip().lower() in {"y", "yes", "1", "true"}
                break
            except:
                return False
        for user in USERS:
            if user_name != user.get('name').upper():
                continue
            user['apply_ipo'] = new_apply_ipo
            return True

def update_user():
    user_name = input("Enter user name: ").upper().strip()
    user_exits = check_user(user_name)

    if not user_exits:
        return False

    print("-" * 50)
    print(f"\t\t\t{user_name}")
    print("-" * 50)

    option = sub_menu(1)
    if option == "3":
        return False

    if option == "2":
        val = update_pin_or_passwd(user_name, pin=1, passwd=0)
        if not val:
            print("Could not update pin!")
            input()
            return False
        return True

    if option == "1":
        val = update_pin_or_passwd(user_name, pin=0, passwd=1)
        if not val:
            print("Could not update password!")
            input()
            return False
        return True

    if option == "4":
        val = update_pin_or_passwd(user_name, pin=0, passwd=0, crn=1)
        if not val:
            print("Could not update crn!")
            input()
            return False
        return True

    if option == "5":
        val = update_pin_or_passwd(user_name, pin=0, passwd=0, crn=0, apply_ipo=1)
        if not val:
            print("Could not update IPO application status!")
            input()
            return False
        return True

def add_user():
    added = sub_menu()

    if not added:
        print("Could not add the user!")
        input()
        return False
    return True


def delete_user():
    name = input("Enter name of user: ").upper()
    for user in USERS:
        if name == user.get('name').upper():
            with get_accessor() as db:
                db.users.delete_by_name(user.get('name'))
            return True
    return False


def update_data_base():
    with get_accessor() as db:
        for user in USERS:
            db.users.upsert(UserUpsert(**user))
def import_from_csv():
    file_path = input("Enter CSV file path: ").strip()
    if not os.path.exists(file_path):
        print("File not found!")
        input()
        return False

    try:
        with open(file_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    passwd = fernet.encrypt(row["passsword"].strip().encode()).decode()
                    pin = fernet.encrypt(str(row["pin"]).encode()).decode()

                    user_dict = {
                        "name": row["name"].upper().strip(),
                        "dp": int(row["dp"]),
                        "boid": int(row["boid"]),
                        "passsword": passwd,
                        "crn": row["crn"].strip(),
                        "pin": pin,
                        "account": row["account"].strip(),
                        "apply_ipo": str(row.get("apply_ipo", "")).strip().lower() in {"1", "true", "yes", "y"},
                    }

                    # Skip duplicates
                    if not check_user(user_dict["name"]):
                        USERS.append(user_dict)

                except Exception as e:
                    print(f"Skipping row due to error: {e}")
                    continue

        update_data_base()
        print("CSV import complete!")
        input()
        return True

    except Exception as e:
        print(f"Error reading CSV: {e}")
        input()
        return False
    
def main():
    users_exists = load_data_base()

    if not users_exists:
        print("No data Base available!")
        print()
        print("Press Enter to Continue")
        input()

    display_user_data()
    input()

    while True:
        option = menu()

        if option == "5":
            clear_screen()
            print("Terminated!")
            return

        if option == "4":
            display_user_data()
            input()
            continue

        if option == "3":
            if not delete_user():
                print("No user found!")
            else:
                print("Deleted!")
            input()
            continue

        if option == "2":
            clear_screen()
            updated = update_user()
            if updated:
                print("User updated!")
                input()
                update_data_base()
            continue
        
        if option == "6":
            import_from_csv()
            continue

        added = add_user()
        if added:
            print("User added!")
            input()
            update_data_base()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Interrupted!")
        exit(1)
