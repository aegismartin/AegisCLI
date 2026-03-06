import argparse
import aegiscli.core.utils.logger as logger
import aegiscli.core.utils.flagger as flagger

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

    # profiler category, inherits global flags
    profiler_parser = subparsers.add_parser(
        "profiler",
        help="Profiler tool",
        parents=[global_parser]
    )

    profiler_parser.add_argument("submodule", choices=["whois", "dns", "web"])
    profiler_parser.add_argument("target")

    args = parser.parse_args()

    if getattr(args, "log", False):
        logger.start_log()

    if args.v:
        flagger.verbose.enable()
        

    try:
        if args.command == "profiler":
            from aegiscli.tools.profiler.selector import Profiler_Selector
            initializator = Profiler_Selector(settings=None, submodule=args.submodule, advanced=False, target=args.target)
            initializator.selector()

    except Exception as e:
        logger.log(f"[ERROR]: {e}")

    finally:
        if getattr(args, "log", False):
            logger.stop_log()



if __name__ == "__main__":
    main()
