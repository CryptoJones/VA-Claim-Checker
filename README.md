# VA Claim Checker

Monitors the status of a VA benefits claim and sends you a notification whenever it moves to a new phase — email, ntfy.sh push, or Pushover.

For VA API documentation see: https://developer.va.gov/explore/api/benefits-claims

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the setup utility

```bash
python3 init.py
```

The setup utility walks you through everything interactively:

- **API mode** — `mock` (no credentials, good for a first run), `sandbox` (VA test environment), or `real` (your live VA account)
- **Authentication** — OAuth 2.0 (recommended) or browser cookies (legacy fallback)
- **Claim ID** — one or multiple
- **Notifications** — email, ntfy.sh, Pushover, or none

It writes `config.json` and optionally runs a test check when done.

---

## Authentication

### OAuth 2.0 (recommended)

1. Register a free developer account at https://developer.va.gov/apply
2. Request access to the **Benefits Claims** API
3. Set the redirect URI to `http://localhost:8080/callback`
4. VA will email you a `client_id` and `client_secret`
5. Enter them when `init.py` asks — or set environment variables:

```bash
export VA_CLIENT_ID=your_client_id
export VA_CLIENT_SECRET=your_client_secret
```

On first run a browser window opens for your VA.gov login. After that, tokens refresh automatically — no further interaction needed.

### Browser cookies (legacy)

If you are waiting for OAuth approval, you can use browser session cookies as a temporary workaround. Note: **cookies expire every 12 hours** and must be manually refreshed.

1. Install the [Cookie Viewer](https://chromewebstore.google.com/detail/cookie-viewer/dedhcncdjkmjpebfohadfeeaopiponca) Chrome extension
2. Log in at https://www.va.gov/track-claims/your-claims/
3. Open https://api.va.gov/v0/benefits_claims/ in a new tab
4. Click Cookie Viewer and paste the values into `config.json` under `"cookies"`

Run `python3 init.py` and choose **cookies** to be guided through this.

---

## Usage

```bash
python3 cli.py status                      # show current claim status
python3 cli.py check                       # check for changes, notify if any
python3 cli.py check --claim-id 123 456    # check specific claim IDs
python3 cli.py claims                      # list all your claims
python3 cli.py watch                       # poll every 30 minutes (daemon mode)
python3 cli.py watch --interval 3600       # poll every hour
python3 cli.py reset                       # clear saved state (re-enables notifications)
python3 cli.py reset --claim-id 123        # reset a specific claim
python3 cli.py logout                      # remove stored OAuth tokens
```

### Scheduling automatic checks

Use `watch` mode to keep the checker running, or add a cron job:

```bash
# Check every 30 minutes via cron
*/30 * * * * cd /path/to/VA-Claim-Checker && python3 cli.py check
```

---

## Notifications

Configure in `config.json` or via the `init.py` setup utility.

| Method | What to set |
|---|---|
| Email (SMTP) | `send_email: true`, fill in the `email` block |
| ntfy.sh | `push.enabled: true`, `push.provider: "ntfy"`, set `push.topic` |
| Pushover | `push.enabled: true`, `push.provider: "pushover"`, set `push.app_token` and `push.user_key` |

Sensitive values (SMTP password, push tokens) can be kept out of `config.json` by using environment variables:

```bash
export VA_SMTP_PASSWORD=your_password
export VA_NTFY_TOKEN=your_token
export VA_PUSHOVER_APP_TOKEN=your_app_token
export VA_PUSHOVER_USER_KEY=your_user_key
```

---

## Running tests

```bash
python3 -m pytest tests/ -v
```

252 tests cover every module:

| File | Tests | What's covered |
|---|---|---|
| `test_init.py` | 84 | Setup utility — ask, choose, all 5 steps, main flow, keyboard interrupt |
| `test_agent.py` | 30 | Config loading, analyze_status, run_check, multi-claim, fetch, list |
| `test_va_api_client.py` | 27 | Mock + real mode, legacy + v2 URLs, headers, retry config |
| `test_auth.py` | 25 | TokenStore, resolve_secret, OAuthClient token/refresh/fallback/logout |
| `test_cli.py` | 24 | All 6 subcommands, multi-claim flag, watch loop, help output |
| `test_state.py` | 24 | StateStore get/save/has_changed/diff_summary/reset |
| `test_notifier.py` | 20 | Mock output, SMTP, ntfy, Pushover, env var overrides |
| `test_va_response_parser.py` | 18 | normalize() — flat passthrough, v2 response, missing fields, contentions |

---

## Project structure

```
init.py               — interactive setup utility (start here)
cli.py                — command-line interface
agent.py              — orchestrates check → diff → notify loop
va_api_client.py      — VA API requests (mock + real), retry logic
va_response_parser.py — normalizes Lighthouse v2 API response fields
auth.py               — OAuth 2.0 flow, token storage, auto-refresh
state.py              — persists last-known claim state across runs
notifier.py           — email, ntfy.sh, and Pushover notifications
config.json           — your configuration (created by init.py)
tests/                — pytest test suite
```
