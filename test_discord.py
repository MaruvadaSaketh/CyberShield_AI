"""Standalone Discord bot-token check for CyberShield.

Usage:
    python test_discord.py
    python test_discord.py --env-file "C:/path/to/.env"

The token is never printed. Only the HTTP status and Discord's response body
are shown, so this is safe to paste into a chat or an issue.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

DISCORD_API = "https://discord.com/api/v10"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Discord bot token.")
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).resolve().parent / ".env"),
        help="Path to the .env file holding DISCORD_BOT_TOKEN (default: next to this script).",
    )
    args = parser.parse_args()

    env_path = Path(args.env_file).expanduser().resolve()
    if not env_path.is_file():
        print(f"ERROR: env file not found: {env_path}")
        return 2

    load_dotenv(env_path, override=True)
    token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip().strip("\"'")
    channel_id = (os.getenv("DISCORD_CHANNEL_ID") or "").strip().strip("\"'")
    if token.lower().startswith("bot "):
        token = token[4:].strip()

    print(f"Env file: {env_path}")
    print(f"Token present: {bool(token)} (length {len(token)})")
    print(f"Channel ID present: {bool(channel_id)}")
    if not token:
        print("ERROR: Discord token not loaded")
        return 1

    try:
        response = requests.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"Request failed: {type(exc).__name__}: {exc}")
        return 1

    print("Status:", response.status_code)
    print("Response:", response.text)

    if response.status_code == 200:
        print("RESULT: bot token is valid")
        return 0
    if response.status_code == 401:
        print("RESULT: Discord rejected the token (401). Regenerate it in the Developer Portal.")
        return 1
    print("RESULT: unexpected response from Discord")
    return 1


if __name__ == "__main__":
    sys.exit(main())
