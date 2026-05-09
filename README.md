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

- **API mode** — `mock` (no credentials, good for a first run), `real` (your live VA account), or `sandbox` (VA test environment — developers only)
- **Authentication** — OAuth 2.0 (recommended) or browser cookies (legacy fallback)
- **Claim ID** — one or multiple
- **Notifications** — email, ntfy.sh, Pushover, or none

It writes `config.json` and optionally runs a test check when done.

> **Just want to check your own claim?** Use `real` mode — no API key required. OAuth 2.0 authenticates directly with your VA.gov account. `sandbox` mode is only needed if you are developing or testing against the VA's test environment.

---

## Authentication

### OAuth 2.0 (recommended)

```bash
python3 init.py
```

Choose **real** mode and **OAuth 2.0** when prompted. A browser window will open for your VA.gov login. After that, tokens refresh automatically — no further interaction needed. No API key or developer account required.

---

### Sandbox mode (developers only)

Sandbox mode connects to VA's test environment with synthetic claim data. It requires a separate developer API key and is not needed to check your real claims.

#### 1. Apply for a sandbox API key

1. Go to https://developer.va.gov/apply and create a free developer account
2. Click **Request API Access** and select **Benefits Claims**
3. When prompted for a redirect URI, enter exactly: `http://localhost:8080/callback`
4. Submit the form — VA will email you a `client_id` and `client_secret` (typically within a few business days)

#### 2. Configure credentials

```bash
cp config.example.json config.json
```

Edit `config.json`:

```json
"mode": "sandbox",
"oauth": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
}
```

Or use environment variables instead:

```bash
export VA_CLIENT_ID=your_client_id
export VA_CLIENT_SECRET=your_client_secret
```

#### 3. Authenticate

```bash
python3 init.py
```

Choose **sandbox** mode and **OAuth 2.0** when prompted.

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
config.example.json   — template configuration with placeholder values
config.json           — your configuration (created by init.py, gitignored)
tests/                — pytest test suite
```
