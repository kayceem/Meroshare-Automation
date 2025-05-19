import check_ipo
import ipo as IPO
from os import system


def check_for_open():
    data = []
    try:
        with open(r"Results\Upcoming IPO.txt", "r", encoding="utf-8") as fp:
            lines = fp.read().splitlines()
            for line in lines:
                if len(line) < 10:
                    continue
                line = line.split(" | ")
                if line[-1] == "Open":
                    data.append(line[0])
            return data
    except:
        return False


def main():
    system("cls")
    check_ipo.main(start_file=False)
    available = check_for_open()
    data = []
    try:
        with open(r"Results\Applied.txt", "r", encoding="utf-8") as fp:
            lines = fp.read().splitlines()
            data = [x for x in lines if len(x) > 5]
    except:
        pass

    try:
        with open(r"Results\Applied.txt", "w", encoding="utf-8") as fp:
            temp = available + data
            already = []
            for name in temp:
                if name not in already:
                    fp.write(f"{name}\n")
                    already.append(name)
    except:
        pass

    count = 0
    for i in range(len(available)):
        if available[i] in data:
            count += 1

    if count != len(available):
        IPO.main(default=True)


if __name__ == "__main__":
    main()
