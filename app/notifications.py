import hashlib
import logging

import httpx

from app.config import settings

_DISCORD_API_URL = "https://discord.com/api/v10"
_DISCORD_CONTENT_LIMIT = 1900
logger = logging.getLogger(__name__)


def token_fingerprint(token: str) -> str:
    """Short, non-reversible fingerprint so a running process can be matched
    against the token currently in .env without ever exposing the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12] if token else ""


def _discord_credentials() -> tuple[str, str]:
    token = settings.discord_bot_token.strip().strip("\"'")
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    channel_id = settings.discord_channel_id.strip().strip("\"'")
    return token, channel_id


def configured_token_fingerprint() -> str:
    """Fingerprint of the token this process loaded at startup."""
    token, _ = _discord_credentials()
    return token_fingerprint(token)


async def check_discord_configuration() -> dict:
    """Check the bot token and channel access without sending a message."""
    result = await _check_discord_configuration()
    token, _ = _discord_credentials()
    result["token_fingerprint"] = token_fingerprint(token)
    return result


async def _check_discord_configuration() -> dict:
    token, channel_id = _discord_credentials()
    guild_id = settings.discord_guild_id.strip().strip("\"'")
    if not token or not channel_id:
        return {
            "configured": False,
            "valid": False,
            "reason": "Discord credentials not configured",
        }

    headers = {"Authorization": f"Bot {token}"}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            bot_response = await client.get(
                f"{_DISCORD_API_URL}/users/@me", headers=headers
            )
            if bot_response.status_code == 401:
                return {
                    "configured": True,
                    "valid": False,
                    "reason": "Discord rejected the bot token (HTTP 401)",
                }
            if bot_response.status_code != 200:
                return {
                    "configured": True,
                    "valid": False,
                    "status_code": bot_response.status_code,
                    "reason": "Could not validate Discord bot token",
                }

            channel_response = await client.get(
                f"{_DISCORD_API_URL}/channels/{channel_id}", headers=headers
            )
    except httpx.RequestError:
        return {
            "configured": True,
            "valid": False,
            "reason": "Could not reach Discord",
        }

    if channel_response.status_code in (403, 404):
        reason = (
            "Bot lacks access to the configured channel"
            if channel_response.status_code == 403
            else "Channel not found or bot has no access to it"
        )
        return {
            "configured": True,
            "valid": True,
            "channel_accessible": False,
            "reason": reason,
        }
    if channel_response.status_code != 200:
        return {
            "configured": True,
            "valid": True,
            "channel_accessible": False,
            "status_code": channel_response.status_code,
            "reason": "Could not validate channel access",
        }
    if guild_id:
        try:
            channel_data = channel_response.json()
        except ValueError:
            channel_data = {}
        channel_guild = str(channel_data.get("guild_id") or "")
        if channel_guild != guild_id:
            return {
                "configured": True,
                "valid": True,
                "channel_accessible": False,
                "reason": (
                    "The configured channel is not in the configured server "
                    "(guild mismatch). Check DISCORD_CHANNEL_ID and "
                    "DISCORD_GUILD_ID."
                ),
            }
    return {
        "configured": True,
        "valid": True,
        "channel_accessible": True,
        "reason": (
            "Bot token and channel access are valid; send-message permission "
            "was not tested"
        ),
    }


async def send_discord_alert(content: str) -> dict:
    token, channel_id = _discord_credentials()
    if not token or not channel_id:
        return {"sent": False, "reason": "Discord credentials not configured"}

    url = f"{_DISCORD_API_URL}/channels/{channel_id}/messages"
    payload = {
        "content": content[:_DISCORD_CONTENT_LIMIT],
        "allowed_mentions": {"parse": []},
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bot {token}"},
                json=payload,
            )
    except httpx.RequestError as exc:
        logger.warning("Could not reach Discord to send alert: %s", exc)
        return {"sent": False, "reason": "Could not reach Discord"}

    if response.status_code not in (200, 201):
        try:
            error_body = response.json()
        except ValueError:
            error_body = response.text
        logger.warning(
            "Discord rejected alert with HTTP %s: %s", response.status_code, error_body
        )
        return {
            "sent": False,
            "reason": "Discord rejected the alert",
            "status_code": response.status_code,
            "discord_error": error_body,
        }

    try:
        message_id = response.json().get("id")
    except ValueError:
        logger.warning("Discord returned invalid JSON after accepting an alert")
        return {"sent": False, "reason": "Discord returned an invalid response"}
    return {
        "sent": True,
        "reason": "Alert sent successfully",
        "message_id": message_id,
    }
