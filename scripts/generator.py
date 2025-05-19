from os import system, path, mkdir
from cryptography.fernet import Fernet
import stdiomask, base64

user_data = []
USER_NAME = []
options = ["1", "2", "3", "4", "5"]
sub_options = ["1", "2", "3", "4"]

key = ""


def clear_screen():
    system("clear")


def check_for_key():
    try:
        with open("./Source Files/key.key", "r", encoding="utf-8") as fp:
            lines = fp.read().splitlines()
            key = lines[0]
            if len(base64.urlsafe_b64decode(key)) != 32:
                raise Exception("Invalid key!")
            for line in lines[1:]:
                if len(line) != 0:
                    raise Exception("No key Found!")
        return key
    except:
        try:
            with open("./Source Files/key.key", "w", encoding="utf-8") as fp:
                key = Fernet.generate_key().decode()
                fp.write(key)
                return key
        except:
            return False


def load_data_base():
    try:
        with open("./Source Files/dataBase.txt", "r", encoding="utf-8") as fp:
            lines = fp.read().splitlines()
            for line in lines:
                data = line.split(",")
                if len(data) != 7:
                    continue
                user_data.append(data)
                USER_NAME.append(data[0])
        return True
    except:
        return False


def display_user_data(usr=0):
    clear_screen()
    if usr == 0:
        usr = user_data
        print("-" * 50)
    for NAME, DP, USERNAME, _, _, _ ,_ in usr:
        print(f"-> {NAME} | {DP} | {USERNAME} ")
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
            print()
            option = input("Choose one option: ")
            if option in sub_options:
                return option
    # try:
    name = input("Enter name: ")
    while True:
        try:
            dp = int(input("Enter DP: ").strip())
            id = int(input("Enter ID: ").strip())
            pin = int(stdiomask.getpass("Enter pin: ").strip())
            account_number = input("Enter account number: ").strip()
            break
        except:
            print()
            print("Enter numbers!")
            print()

    passwd = stdiomask.getpass("Enter passwd: ").strip()
    crn = input("Enter crn: ").strip()
    fer = Fernet(key)
    passwd = fer.encrypt(passwd.encode()).decode()
    pin = fer.encrypt(str(pin).encode()).decode()
    user_data.append([name, dp, id, passwd, crn, pin, account_number])
    return True
    # except:
    #     return False


def check_user(user_name):
    for name in USER_NAME:
        if name.upper() == user_name:
            return True
    return False


def update_pin_or_passwd(user_name, pin=0, passwd=0, crn=0):
    if pin == passwd == crn == 1:
        return False

    if pin == 1:
        while True:
            try:
                new_pin = int(input("Enter new pin:").strip())
                fer = Fernet(key)
                new_pin = fer.encrypt(str(new_pin).encode()).decode()
                break
            except:
                return False
        for user in user_data:
            if user_name != user[0].upper():
                continue
            user[5] = new_pin
            return True
    if passwd == 1:
        while True:
            try:
                new_passwd = input("Enter new password:").strip()
                fer = Fernet(key)
                new_passwd = fer.encrypt(new_passwd.encode()).decode()
                break
            except:
                return False
        for user in user_data:
            if user_name != user[0].upper():
                continue
            user[3] = new_passwd
            return True
    if crn == 1:
        while True:
            try:
                new_crn = input("Enter crn:").strip()
                break
            except:
                return False
        for user in user_data:
            if user_name != user[0].upper():
                continue
            user[4] = new_crn
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


def add_user():
    added = sub_menu()

    if not added:
        print("Could not add the user!")
        input()
        return False
    return True


def delete_user():
    name = input("Enter name of user: ").upper()
    for data in user_data:
        if name in data[0].upper():
            user_data.remove(data)
            return True
    return False


def update_data_base():
    with open("./Source Files/dataBase.txt", "w", encoding="utf-8") as fp:
        for NAME, DP, USERNAME, PASSWD, CRN, PIN, ACCOUNT_NUMBER in user_data:
            fp.write(f"{NAME},{DP},{USERNAME},{PASSWD},{CRN},{PIN},{ACCOUNT_NUMBER}\n")


def main():
    global key
    if not path.isdir("Source Files"):
        mkdir("Source Files")
    key = check_for_key()
    if not key:
        print("Key not found!")
        exit(1)

    loaded = load_data_base()

    if not loaded:
        print("No data Base available!")
        print()
        print("Press Enter to Continue")
        input()

    if loaded:
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
