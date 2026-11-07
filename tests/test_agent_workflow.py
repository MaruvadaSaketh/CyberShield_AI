import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.genai import errors

from app import agent_workflow
from app.main import app as fastapi_app
from app.config import settings
from app.schemas import IncidentReport


class AgentWorkflowTests(unittest.TestCase):
    def setUp(self):
        agent_workflow._agent_client = None
        self.settings = patch.multiple(
            settings,
            google_api_key="google-test-key",
            agent_name="fraud-detection",
            gemini_model="gemini-3.8-flash",
        )
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.addCleanup(setattr, agent_workflow, "_agent_client", None)

    def test_creates_direct_gemini_client_without_gateway(self):
        client = SimpleNamespace(models=SimpleNamespace())
        with patch.object(agent_workflow.genai, "Client", return_value=client) as create:
            result = agent_workflow.get_agent_client()

        self.assertIs(result, client)
        create.assert_called_once_with(api_key="google-test-key")

    def test_workflow_requires_only_google_api_key(self):
        self.assertTrue(agent_workflow.is_agent_workflow_configured())
        with patch.object(settings, "google_api_key", ""):
            self.assertFalse(agent_workflow.is_agent_workflow_configured())

    def test_analysis_redacts_sensitive_summary_and_uses_gemini(self):
        generate_content = Mock(
            return_value=SimpleNamespace(text="Contact your bank directly.")
        )
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
        report = IncidentReport(
            incident_id="incident-1",
            incident_type="fraud",
            risk_score=80,
            severity="HIGH",
            summary=(
                "Contact user@example.com about account 123456789012; "
                "PASSWORD=secret123"
            ),
        )

        with patch.object(agent_workflow, "get_agent_client", return_value=client):
            result = agent_workflow.analyze_incident_with_agent(report)

        call = generate_content.call_args.kwargs
        incident = json.loads(call["contents"])
        self.assertNotIn("user@example.com", incident["summary"])
        self.assertNotIn("123456789012", incident["summary"])
        self.assertNotIn("secret123", incident["summary"])
        self.assertEqual(call["model"], "gemini-3.8-flash")
        self.assertEqual(result["analysis"], "Contact your bank directly.")
        self.assertTrue(result["human_review_required"])

    def test_unavailable_gemini_model_returns_local_triage(self):
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=Mock(
                    side_effect=errors.ClientError(404, {"message": "model not found"})
                )
            )
        )
        report = IncidentReport(
            incident_id="incident-1",
            incident_type="fraud",
            risk_score=80,
            severity="HIGH",
            summary="Review synthetic transaction.",
        )

        with patch.object(agent_workflow, "get_agent_client", return_value=client):
            result = agent_workflow.analyze_incident_with_agent(report)

        self.assertEqual(result["analysis_source"], "local_rule_based_fallback")
        self.assertIn("not an AI-generated assessment", result["analysis"])
        self.assertNotIn("configured Gemini model is unavailable", result["analysis"])
        self.assertTrue(result["human_review_required"])

    def test_maps_gemini_authentication_rejection(self):
        generate_content = Mock(
            side_effect=errors.ClientError(401, {"message": "unauthorized"})
        )
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
        report = IncidentReport(
            incident_id="incident-1",
            incident_type="fraud",
            risk_score=80,
            severity="HIGH",
            summary="Review transaction.",
        )

        with (
            patch.object(agent_workflow, "get_agent_client", return_value=client),
            self.assertRaises(HTTPException) as raised,
        ):
            agent_workflow.analyze_incident_with_agent(report)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("rejected credentials", raised.exception.detail)

    def test_workflow_posts_review_to_discord_without_calling_gemini(self):
        payload = {
            "incident_id": "synthetic-incident",
            "incident_type": "fraud",
            "risk_score": 80,
            "severity": "HIGH",
            "summary": "Review synthetic transaction.",
        }

        with (
            patch.object(agent_workflow, "analyze_incident_with_agent") as analyze,
            patch(
                "app.main.send_discord_alert",
                new_callable=AsyncMock,
                return_value={"sent": True, "message_id": "discord-message-1"},
            ) as send_discord,
        ):
            response = TestClient(fastapi_app).post(
                "/api/agent-workflow/run", json=payload
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["agent_name"], "Discord account recovery review")
        self.assertEqual(result["analysis_source"], "discord")
        self.assertIn("sent to Discord", result["analysis"])
        self.assertTrue(result["human_review_required"])
        self.assertTrue(result["discord"]["sent"])
        analyze.assert_not_called()
        message = send_discord.await_args.args[0]
        self.assertIn("CyberShield Account Recovery Review", message)
        self.assertIn("synthetic-incident", message)
    def test_hides_unexpected_provider_error_details(self):
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=Mock(
                    side_effect=RuntimeError("private provider response")
                )
            )
        )
        report = IncidentReport(
            incident_id="incident-1",
            incident_type="fraud",
            risk_score=80,
            severity="HIGH",
            summary="Review transaction.",
        )

        with (
            patch.object(agent_workflow, "get_agent_client", return_value=client),
            self.assertRaises(HTTPException) as raised,
        ):
            agent_workflow.analyze_incident_with_agent(report)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("Check the backend logs", raised.exception.detail)
        self.assertNotIn("private provider response", raised.exception.detail)

    def test_rejects_empty_gemini_response(self):
        client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=Mock(return_value=SimpleNamespace(text=None))
            )
        )
        report = IncidentReport(
            incident_id="incident-1",
            incident_type="fraud",
            risk_score=80,
            severity="HIGH",
            summary="Review transaction.",
        )

        with (
            patch.object(agent_workflow, "get_agent_client", return_value=client),
            self.assertRaises(HTTPException) as raised,
        ):
            agent_workflow.analyze_incident_with_agent(report)

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("empty response", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()