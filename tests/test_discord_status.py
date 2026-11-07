import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.notifications import check_discord_configuration


class DiscordStatusTests(unittest.TestCase):
    def test_reports_invalid_token_without_exposing_it(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = SimpleNamespace(status_code=401)
        configured = patch.multiple(
            settings,
            discord_bot_token='"Bot fake-secret-token"',
            discord_channel_id='"123456789"',
        )
        with configured, patch("app.notifications.httpx.AsyncClient", return_value=client):
            result = asyncio.run(check_discord_configuration())

        self.assertEqual(result["reason"], "Discord rejected the bot token (HTTP 401)")
        self.assertNotIn("fake-secret-token", str(result))
        client.get.assert_awaited_once_with(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": "Bot fake-secret-token"},
        )

    def test_reports_valid_token_and_channel_access(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.side_effect = [
            SimpleNamespace(status_code=200),
            SimpleNamespace(status_code=200),
        ]
        configured = patch.multiple(
            settings,
            discord_bot_token="fake-secret-token",
            discord_channel_id="123456789",
        )
        with configured, patch("app.notifications.httpx.AsyncClient", return_value=client):
            result = asyncio.run(check_discord_configuration())

        self.assertTrue(result["valid"])
        self.assertTrue(result["channel_accessible"])
        self.assertIn("permission was not tested", result["reason"])
        self.assertEqual(client.get.await_count, 2)

    def test_reports_guild_mismatch_for_channel_in_wrong_server(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.side_effect = [
            SimpleNamespace(status_code=200),
            SimpleNamespace(status_code=200, json=lambda: {"guild_id": "999888777"}),
        ]
        configured = patch.multiple(
            settings,
            discord_bot_token="fake-secret-token",
            discord_channel_id="123456789",
            discord_guild_id="1564500402315984896",
        )
        with configured, patch("app.notifications.httpx.AsyncClient", return_value=client):
            result = asyncio.run(check_discord_configuration())

        self.assertTrue(result["valid"])
        self.assertFalse(result["channel_accessible"])
        self.assertIn("not in the configured server", result["reason"])

    def test_accepts_channel_inside_configured_server(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.side_effect = [
            SimpleNamespace(status_code=200),
            SimpleNamespace(
                status_code=200, json=lambda: {"guild_id": "1564500402315984896"}
            ),
        ]
        configured = patch.multiple(
            settings,
            discord_bot_token="fake-secret-token",
            discord_channel_id="1567960290404999321",
            discord_guild_id="1564500402315984896",
        )
        with configured, patch("app.notifications.httpx.AsyncClient", return_value=client):
            result = asyncio.run(check_discord_configuration())

        self.assertTrue(result["valid"])
        self.assertTrue(result["channel_accessible"])


if __name__ == "__main__":
    unittest.main()
