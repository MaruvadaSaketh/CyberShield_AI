import unittest
from unittest.mock import patch

import api_client


class ApiClientTests(unittest.TestCase):
    def test_run_agent_workflow_posts_to_recovery_endpoint(self):
        payload = {
            "incident_id": "SYNTHETIC-1",
            "incident_type": "Synthetic test",
            "severity": "LOW",
            "risk_score": 5,
            "summary": "Synthetic incident only",
        }

        with patch.object(api_client, "_request", return_value={}) as request:
            result = api_client.run_agent_workflow_api(payload)

        self.assertEqual(result, {})
        request.assert_called_once_with(
            "POST",
            "/api/agent-workflow/run",
            json=payload,
        )

    def test_chat_api_posts_to_chat_endpoint(self):
        messages = [
            {"role": "user", "content": "Is my transaction risky?"},
            {"role": "assistant", "content": "Share more details."},
            {"role": "user", "content": "It was flagged for an unusual location."},
        ]

        with patch.object(api_client, "_request", return_value={"reply": "ok"}) as request:
            result = api_client.chat_api(messages)

        self.assertEqual(result, {"reply": "ok"})
        request.assert_called_once_with(
            "POST",
            "/api/chat",
            json={"messages": messages},
        )


if __name__ == "__main__":
    unittest.main()
