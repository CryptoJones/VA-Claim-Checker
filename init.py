#!/usr/bin/env python3
"""
Interactive setup utility for VA Claim Checker.
Writes config.json and optionally runs a test check.
"""

import getpass
import json
import os
import subprocess
import sys


# ── helpers ──────────────────────────────────────────────────────────────────

def ask(prompt, default=None, secret=False):
    display = f"{prompt} [{default}]: " if default else f"{prompt}: "
    while True:
        value = (getpass.getpass(display) if secret else input(display)).strip()
        if value:
            return value
        if default is not None:
            return default
        print("  This field is required.")


def choose(prompt, options):
    print(f"\n{prompt}")
    for i, (label, desc) in enumerate(options, 1):
        print(f"  [{i}] {label:<12} {desc}")
    while True:
        raw = input(f"  Choice [1-{len(options)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        print(f"  Please enter a number between 1 and {len(options)}.")


def banner(text):
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def ok(text):
    print(f"  ✓ {text}")


def info(text):
    print(f"  → {text}")


# ── setup steps ──────────────────────────────────────────────────────────────

def step_mode():
    banner("Step 1 of 5 — API Mode")
    return choose("Which mode should the checker run in?", [
        ("mock",    "Test locally — no VA API calls, no credentials needed"),
        ("real",    "Production  — your live VA account, login via VA.gov (login.gov)"),
        ("sandbox", "Developer   — VA test environment, requires a developer API key"),
    ])


def step_auth(mode):
    if mode == "mock":
        return "none", {}, {}

    banner("Step 2 of 5 — Authentication")

    oauth_cfg = {"client_id": "", "client_secret": ""}
    cookies = {k: "" for k in [
        "_ga", "_ga_CSLL4ZEK4L", "_ga_YPB3FD0PQ9",
        "TS01f27c67", "TS0189a5f9", "TS014c0a39",
        "api_session", "CERNER_ELIGIBLE", "vagov_saml_request_prod",
    ]}

    if mode == "real":
        method = choose("Authentication method:", [
            ("oauth",   "Recommended — log in once via VA.gov, tokens refresh automatically"),
            ("cookies", "Legacy      — manual cookie extraction from Chrome every 12 hours"),
        ])
        if method == "oauth":
            idp = choose("Identity provider:", [
                ("logingov", "Login.gov   — government identity, recommended"),
                ("idme",     "ID.me       — widely used, supports MFA"),
            ])
            oauth_cfg["idp"] = idp
            info(f"A browser will open for you to log in via {'Login.gov' if idp == 'logingov' else 'ID.me'}.")
            info("No developer credentials needed.\n")
        else:
            print()
            info("Cookie extraction steps:")
            info("1. Install the 'Cookie Viewer' Chrome extension")
            info("2. Log in at https://www.va.gov/track-claims/your-claims/")
            info("3. Open https://api.va.gov/v0/benefits_claims/ in a new tab")
            info("4. Click Cookie Viewer and paste each value below.\n")
            for key in cookies:
                cookies[key] = ask(f"  Cookie: {key}", default="")
    else:
        # sandbox — developer credentials required
        method = choose("Authentication method:", [
            ("oauth",   "Recommended — browser login once, tokens refresh automatically"),
            ("cookies", "Legacy      — manual cookie extraction from Chrome every 12 hours"),
        ])
        info("Register a developer account at: https://developer.va.gov/apply")
        info("Select the Benefits Claims API and use redirect URI: http://localhost:8080/callback\n")
        if method == "oauth":
            oauth_cfg["client_id"]     = ask("Client ID (from developer.va.gov)")
            oauth_cfg["client_secret"] = ask("Client Secret", secret=True)
        else:
            print()
            info("Cookie extraction steps:")
            info("1. Install the 'Cookie Viewer' Chrome extension")
            info("2. Log in at https://www.va.gov/track-claims/your-claims/")
            info("3. Open https://api.va.gov/v0/benefits_claims/ in a new tab")
            info("4. Click Cookie Viewer and paste each value below.\n")
            for key in cookies:
                cookies[key] = ask(f"  Cookie: {key}", default="")

    return method, oauth_cfg, cookies


def step_claim_ids():
    banner("Step 3 of 5 — Claim ID(s)")
    info("Find your claim ID at: https://www.va.gov/track-claims/your-claims/")
    raw = ask("Claim ID(s) — separate multiple with commas", default="117877436")
    ids = [c.strip() for c in raw.split(",") if c.strip()]
    return ids[0] if len(ids) == 1 else ids


def step_notifications():
    banner("Step 4 of 5 — Notifications")
    method = choose("How should the checker notify you of changes?", [
        ("none",     "No notifications — changes are logged and printed only"),
        ("email",    "Email via SMTP  — works with Gmail, Outlook, etc."),
        ("ntfy",     "ntfy.sh push    — free, open-source mobile/desktop push"),
        ("pushover", "Pushover push   — $5 one-time, reliable mobile push"),
    ])

    send_email = False
    email_cfg = {
        "sender": "", "receiver": "", "smtp_server": "",
        "smtp_port": 587, "username": "", "password": "",
    }
    push_cfg = {"enabled": False, "provider": "ntfy", "topic": "va-claim-checker", "token": ""}

    if method == "email":
        send_email = True
        print()
        email_cfg["sender"]      = ask("Sender email address")
        email_cfg["receiver"]    = ask("Recipient email address")
        email_cfg["smtp_server"] = ask("SMTP server", default="smtp.gmail.com")
        port_raw                 = ask("SMTP port", default="587")
        email_cfg["smtp_port"]   = int(port_raw)
        email_cfg["username"]    = ask("SMTP username", default=email_cfg["sender"])
        email_cfg["password"]    = ask("SMTP password (or app password)", secret=True)

    elif method == "ntfy":
        push_cfg["enabled"]  = True
        push_cfg["provider"] = "ntfy"
        print()
        info("Create a free account at https://ntfy.sh or use a self-hosted instance.")
        push_cfg["topic"] = ask("ntfy topic name", default="va-claim-checker")
        push_cfg["token"] = ask("Access token (leave blank if topic is public)", default="")

    elif method == "pushover":
        push_cfg["enabled"]    = True
        push_cfg["provider"]   = "pushover"
        print()
        info("Create an app at https://pushover.net/apps/build to get your app token.")
        push_cfg["app_token"] = ask("Pushover app token")
        push_cfg["user_key"]  = ask("Pushover user key")

    return send_email, email_cfg, push_cfg


def step_write_config(mode, environment, auth_method, oauth_cfg, cookies,
                      claim_id, send_email, email_cfg, push_cfg):
    banner("Step 5 of 5 — Writing config.json")

    config = {
        "mode": mode,
        "environment": environment,
        "claim_id": claim_id,
        "oauth": oauth_cfg,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.6943.141 Safari/537.36"
        ),
        "cookies": cookies,
        "send_email": send_email,
        "email": email_cfg,
        "push": push_cfg,
        "state_file": ".va_state.json",
        "log_file": "agent_log.txt",
    }

    config_path = "config.json"
    if os.path.exists(config_path):
        overwrite = input("\n  config.json already exists. Overwrite? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("  Skipped — existing config.json kept.")
            return

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    ok("config.json written.")

    if auth_method == "oauth" and mode != "mock":
        print()
        info("OAuth credentials saved. On first run, a browser window will open")
        info("for you to log in with your VA.gov account. After that, tokens")
        info("refresh automatically — no further interaction needed.")


def step_test(mode):
    print()
    run_test = input("  Run a test check now? [Y/n]: ").strip().lower()
    if run_test in ("", "y"):
        print()
        result = subprocess.run(
            [sys.executable, "cli.py", "status"],
            capture_output=False,
        )
        if result.returncode == 0 and mode != "mock":
            print()
            ok("Connection successful.")
    else:
        print()
        info("Skipped. Run 'python3 cli.py status' whenever you're ready.")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 50)
    print("  VA Claim Checker — Setup")
    print("=" * 50)
    print("  This utility will create your config.json.")
    print("  Press Ctrl+C at any time to cancel.\n")

    try:
        mode = step_mode()

        environment = "sandbox" if mode == "sandbox" else "real" if mode == "real" else "sandbox"
        auth_method, oauth_cfg, cookies = step_auth(mode)

        claim_id = step_claim_ids()

        send_email, email_cfg, push_cfg = step_notifications()

        step_write_config(
            mode, environment, auth_method, oauth_cfg, cookies,
            claim_id, send_email, email_cfg, push_cfg,
        )

        print()
        print("=" * 50)
        ok("Setup complete!")
        print()
        info("Useful commands:")
        info("  python3 cli.py status          — show current claim status")
        info("  python3 cli.py check           — check for changes, send notification")
        info("  python3 cli.py watch           — poll every 30 minutes")
        info("  python3 cli.py claims          — list all your claims")
        info("  python3 cli.py reset           — clear saved state")
        print("=" * 50)

        step_test(mode)

    except KeyboardInterrupt:
        print("\n\n  Setup cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
