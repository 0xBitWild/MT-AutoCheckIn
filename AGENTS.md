# AGENTS.md

## Project

Single-file Python script (`MT-AutoCheckIn.py`) that automates daily M-Team site check-in via Playwright (headless Chromium). Runs as a long-lived daemon with `schedule` library, picking a random time between 09:00-11:59 each day. Supports multiple accounts.

## Commands

```bash
# One-time setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium && playwright install-deps

# Run daemon (supports multi-account)
python MT-AutoCheckIn.py

# Run a single check-in directly (for testing)
# Edit main block to call: asyncio.run(MTeamSpider(...).check_in())
```

## Env vars (required)

Set in `.env` (loaded via `python-dotenv`):

**Single account:**
| Var | Purpose |
|---|---|
| `MTEAM_USERNAME` | M-Team username |
| `MTEAM_PASSWORD` | M-Team password |
| `MTEAM_TOTP_SECRET` | TOTP secret for 2FA |

**Multiple accounts:** Use numbered suffixes (`_1`, `_2`, etc.):
```
MTEAM_USERNAME_1=user1
MTEAM_PASSWORD_1=pass1
MTEAM_TOTP_SECRET_1=totp1
MTEAM_USERNAME_2=user2
MTEAM_PASSWORD_2=pass2
MTEAM_TOTP_SECRET_2=totp2
```
If numbered vars exist, single-account vars are ignored.

Notification vars (`NOTIFY_TYPE` + provider creds) are optional; default is no notifications.

## Architecture

- **Entry point**: `if __name__ == '__main__'` calls `schedule_check_in()` which loads all accounts and schedules each.
- **Multi-account**: `load_accounts()` detects `_1`, `_2` suffixes. Each account gets its own `MTeamSpider` instance.
- **Login flow**: Try `mteam_localstorage_{username}.json` first. If that fails, fall back to password + TOTP login via Playwright.
- **State files**: Per-account localStorage files (`mteam_localstorage_Bytewild.json`, etc.) at repo root.
- **2FA handling**: Site may skip 2FA input if session is valid, or show `input[id="otp-code"]` or a "確認" button. Script handles all cases.
- **Profile interception**: Intercepts `/api/member/profile` XHR to confirm login success and extract user data.
- **No tests, no lint CI**: `.flake8` exists (max-line-length=120) but is not wired into any CI or pre-commit.

## Docker / K8s

- `Dockerfile` uses `python:3.12.7-bookworm`, installs Chromium via Playwright.
- `docker compose up -d` starts the daemon. Healthcheck uses `pgrep -f "python MT-AutoCheckIn.py"`.
- `kubernetes-manifests/deployment.yaml` provides a K8s Deployment template.
- `docker-compose.dev.yml` and `kubernetes-manifests/deployment.dev.yaml` are gitignored and contain real credentials — do not commit them.

## Gotchas

- The script uses `time.sleep()` (blocking) inside an async context for the initial random delay. This is intentional but means the event loop is blocked during that period.
- `schedule_check_in()` is an infinite `while True` loop — the process never exits on its own.
- Python 3.12.7 is the pinned version (`.python-version`). Dockerfile uses 3.12.7-bookworm.
- The `.env` file in this repo contains real credentials. Never commit or expose it.
- LocalStorage login has a 60s `wait_for_timeout` — this is intentional to let the page fully load.
