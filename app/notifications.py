import logging

import httpx

from app.config import settings

_DISCORD_API_URL = "https://discord.com/api/v10"
_DISCORD_CONTENT_LIMIT = 1900
logger = logging.getLogger(__name__)


async def send_discord_alert(content: str) -> dict:
    token = settings.discord_bot_token.strip()
    channel_id = settings.discord_channel_id.strip()
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
        logger.warning("Discord rejected alert with HTTP %s", response.status_code)
        return {
            "sent": False,
            "reason": "Discord rejected the alert",
            "status_code": response.status_code,
        }

    try:
        message_id = response.json().get("id")
    except ValueError:
        logger.warning("Discord returned invalid JSON after accepting an alert")
        return {"sent": False, "reason": "Discord returned an invalid response"}
    return {"sent": True, "message_id": message_id}
