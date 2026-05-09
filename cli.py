import argparse
from pathlib import Path

from agent import VAClaimAgent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VA Claim Checker Agent CLI (mock mode)."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the agent configuration file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Run a claim status check.")

    status_parser = subparsers.add_parser("status", help="Show current claim status.")
    status_parser.add_argument(
        "--claim-id",
        help="Override the claim ID from config.",
    )

    reset_parser = subparsers.add_parser("reset", help="Reset the results halt flag.")
    reset_parser.add_argument(
        "--value",
        choices=["0", "1"],
        default="0",
        help="Set results.txt to 0 or 1.",
    )

    args = parser.parse_args()
    agent = VAClaimAgent(config_file=args.config)

    if args.command == "check":
        agent.run_check()
    elif args.command == "status":
        claim_id = args.claim_id or agent.config.get("claim_id")
        analysis = agent.get_claim_analysis(claim_id)
        print(analysis)
    elif args.command == "reset":
        Path(agent.results_file).write_text(args.value)
        print(f"results.txt set to {args.value}")


if __name__ == "__main__":
    main()
