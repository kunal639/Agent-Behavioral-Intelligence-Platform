import sys
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="ObserverModel Live Telemetry Replay Simulator")
    parser.add_argument("logfile", help="Path to the .jsonl trace file to replay")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between lines in seconds")
    args = parser.parse_args()

    try:
        with open(args.logfile, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue
                # Print directly to stdout for monitor.py to pick up
                print(clean_line)
                sys.stdout.flush()
                time.sleep(args.delay)
    except FileNotFoundError:
        print(f"Error: Telemetry file '{args.logfile}' not found.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()