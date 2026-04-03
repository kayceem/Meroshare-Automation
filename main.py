import argparse
from sys import exit
import os
from scripts.ipo import ipo
from scripts.ipo_result import ipo_result
from scripts.edis import edis

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
        ipo_results_parser.add_argument(
            "--noheadless",
            action="store_false",
            dest="headless",
            help="Run with visible browser (default: headless)",
        )
        ipo_results_parser.add_argument(
            "--delay",
            type=int,
            default=5,
            help="Delay in seconds between starting each user (default: 5)",
        )

        generator_parser = subparsers.add_parser("generator")

        migrate_parser = subparsers.add_parser("migrate")

        view_results_parser = subparsers.add_parser("view-results")

        args = parser.parse_args()

        if args.command == "ipo":
            ipo(args.noskip, args.noheadless)
        elif args.command == "ipo-results":
            ipo_result(user_delay=args.delay)
        elif args.command == "edis":
            edis(args.user, args.noheadless)
        elif args.command == "generator":
            from scripts import generator
            generator.main()
        elif args.command == "view-results":
            from scripts.webapp.app import app
            app.run(host='0.0.0.0')

        else:
            parser.print_help()
    except KeyboardInterrupt:
        input("Interrupted!!!")
        try:
            exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            exit(1)
        except SystemExit:
            os._exit(1)