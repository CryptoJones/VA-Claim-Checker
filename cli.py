import argparse
import time

from agent import VAClaimAgent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VA Claim Checker — monitors VA benefits claim status."
    )
    parser.add_argument(
        "--config", default="config.json",
        help="Path to the agent configuration file.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # check
    check_p = sub.add_parser("check", help="Run a claim status check and notify on change.")
    check_p.add_argument("--claim-id", nargs="+", help="One or more claim IDs to check.")

    # status
    status_p = sub.add_parser("status", help="Show current claim status (no notification).")
    status_p.add_argument("--claim-id", help="Override the claim ID from config.")

    # claims
    claims_p = sub.add_parser("claims", help="List all claims for the veteran.")
    claims_p.add_argument("--veteran-id", help="Veteran ICN (required for real/sandbox mode).")

    # reset
    reset_p = sub.add_parser("reset", help="Reset saved state for a claim (or all claims).")
    reset_p.add_argument("--claim-id", help="Claim ID to reset (omit to reset all).")

    # watch
    watch_p = sub.add_parser("watch", help="Poll claim status on a recurring interval.")
    watch_p.add_argument("--claim-id", nargs="+", help="One or more claim IDs to watch.")
    watch_p.add_argument(
        "--interval", type=int, default=1800,
        help="Seconds between checks (default: 1800 = 30 min).",
    )

    # logout
    sub.add_parser("logout", help="Remove stored OAuth tokens.")

    args = parser.parse_args()
    agent = VAClaimAgent(config_file=args.config)

    if args.command == "check":
        agent.run_check(claim_ids=args.claim_id)

    elif args.command == "status":
        print(agent.get_claim_analysis(args.claim_id))

    elif args.command == "claims":
        veteran_id = getattr(args, "veteran_id", None)
        claims = agent.list_claims(veteran_id=veteran_id)
        if not claims:
            print("No claims found.")
        for c in claims:
            print(
                f"  #{c['claim_id']}  {c['status']:<12}  {c['stage']:<35}  "
                f"updated {c['last_updated']}"
            )

    elif args.command == "reset":
        agent.state.reset(claim_id=args.claim_id)
        target = args.claim_id or "all claims"
        print(f"State reset for {target}.")

    elif args.command == "watch":
        claim_ids = args.claim_id
        interval = args.interval
        print(f"Watching every {interval}s. Press Ctrl+C to stop.")
        while True:
            agent.run_check(claim_ids=claim_ids)
            time.sleep(interval)

    elif args.command == "logout":
        if agent.api_client.oauth:
            agent.api_client.oauth.logout()
        else:
            print("OAuth is not configured.")


if __name__ == "__main__":
    main()
