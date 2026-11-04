import unittest

from fraud_detection import analyze_transaction
from phishing_detection import analyze_message


class FraudDetectionTests(unittest.TestCase):
    def test_high_risk_synthetic_case(self):
        result = analyze_transaction(
            amount=25000,
            usual_amount=3000,
            unusual_time=True,
            unusual_location=False,
            rapid_transactions=True,
            reported_phishing=True,
        )
        self.assertEqual(result["score"], 80)
        self.assertEqual(result["severity"], "HIGH")

    def test_no_indicators(self):
        result = analyze_transaction(amount=1000, usual_amount=2000)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["severity"], "LOW")

    def test_suspicious_message_flags_indicators(self):
        result = analyze_message(
            "URGENT: Your KYC will expire today. "
            "Click http://example.invalid/kyc to update immediately."
        )
        self.assertGreater(result["score"], 0)
        self.assertTrue(result["indicators"])


if __name__ == "__main__":
    unittest.main()
