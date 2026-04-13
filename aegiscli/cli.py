import argparse
import aegiscli.core.utils.logger as logger
import aegiscli.core.utils.flagger as flagger
from colorama import Fore, Style
import sys
def main():
    parser = argparse.ArgumentParser(
        prog="aegiscli",
        description="AegisCLI - modular recon framework"
    )

    # global parser (shared flags)
    global_parser = argparse.ArgumentParser(add_help=False)
    global_parser.add_argument("--log", action="store_true")
    global_parser.add_argument("-v", action="store_true")



    # main categories
    subparsers = parser.add_subparsers(dest="command", required=True)

    # profiler tool
    profiler_parser = subparsers.add_parser(
        "profiler",
        help="Profiler tool",
        parents=[global_parser]
    )
    profiler_parser.add_argument("submodule", choices=["whois", "dns", "web"])
    profiler_parser.add_argument("target")

    # scanner tool
    scanner_parser = subparsers.add_parser(
        "scanner",
        help="Scanner tool",
        parents=[global_parser]
    )

    scanner_parser.add_argument("submodule", choices=["port", "host"])
    scanner_parser.add_argument("--ports", type=str)
    scanner_parser.add_argument("target")



    args = parser.parse_args()

    if getattr(args, "log", False):
        logger.start_log()

    if args.v:
        flagger.verbose.enable()
        

    try:
        if args.command == "profiler":
            from aegiscli.tools.profiler.selector import Profiler_Selector
            initializator = Profiler_Selector(settings=None, submodule=args.submodule, target=args.target)
            initializator.selector()
        elif args.command == "scanner":
            from aegiscli.tools.scanner.selector import Scanner_Selector
            initializator = Scanner_Selector(settings=None, submodule=args.submodule, target=args.target, ports=args.ports)
            initializator.selector()

    except Exception as e:
        logger.log(f"{Fore.RED}[ERROR]{Style.RESET_ALL}: {e}")
        sys.exit(1)

    finally:
        if getattr(args, "log", False):
            logger.stop_log()



if __name__ == "__main__":
    main()