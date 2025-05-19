#!/home/kayc/Code/Python/MeroShare-IPO/.venv/bin/python

import argparse
from sys import exit
import os
from scripts.ipo import ipo
from scripts.ipo_result import ipo_result
from scripts.edis import edis
import logging

from utils.helpers import get_logger

# log = get_logger("main", logging.INFO)

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")

        ipo_parser = subparsers.add_parser("ipo")
        ipo_parser.add_argument(
            "--noskip",
            action="store_false",
            help="Whether to ask for input from user",
        )
        ipo_parser.add_argument(
            "--noheadless",
            action="store_false",
            help="Whether to use headless browser",
        )

        edis_parser = subparsers.add_parser("edis")
        edis_parser.add_argument(
            "--noheadless",
            action="store_false",
            help="Whether to use headless browser",
        )
        edis_parser.add_argument(
            "--user",
            type=str,
            help="Specify the username",
            default=None,
        )

        ipo_results_parser = subparsers.add_parser("ipo-results")
        args = parser.parse_args()

        if args.command == "ipo":
            ipo(args.noskip, args.noheadless)
        elif args.command == "ipo-results":
            ipo_result()
        elif args.command == "edis":
            edis(args.user, args.noheadless)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        input("Interrupted!!!")
        try:
            exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        # log.error(e)
        try:
            exit(1)
        except SystemExit:
            os._exit(1)