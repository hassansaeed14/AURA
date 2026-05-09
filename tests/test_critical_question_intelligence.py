import unittest
from unittest.mock import patch

import brain.response_engine as response_engine


def _critical_answer(topic: str = "provider routing") -> str:
    return (
        "Direct verdict: Use the safer staged option, not a rushed migration, because reliability depends on measured failure behavior.\n\n"
        f"Reasoning: For {topic}, the decision should compare runtime stability, fallback behavior, latency, rate limits, and operational recovery. "
        "A single primary path can be simpler and faster, but it creates more pressure on one provider when quotas or network errors appear. "
        "A fallback architecture adds complexity, but it gives the assistant a controlled way to keep answering when the preferred provider fails.\n\n"
        "Assumptions / uncertainty: I am assuming this is for a local AURA deployment and that current provider health can change. "
        "Without live telemetry, exact reliability cannot be verified.\n\n"
        "Risks: The main risks are stale provider health, overconfident status labels, slow retries, and degraded answers that look normal.\n\n"
        "Recommendation: Keep one clean primary provider path, preserve a verified fallback chain with cooldowns and truthful degraded replies, and have a qualified expert review the risky parts.\n\n"
        "Next step: Measure real request failures for a short prompt sweep, then tune the provider cooldown and retry thresholds."
    )


class CriticalQuestionIntelligenceTests(unittest.TestCase):
    def test_simple_question_stays_normal_mode(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "Hi. I am here.",
                "attempts": [{"provider": "groq", "status": "success"}],
                "routing_order": ["groq"],
            },
        ):
            payload = response_engine.generate_response_payload("hi")

        self.assertTrue(payload["success"])
        self.assertFalse(payload["critical_question"])
        self.assertNotEqual(payload["explanation_mode"], "critical_reasoning")

    def test_architecture_question_uses_critical_mode(self):
        prompt = "Should AURA keep one Groq primary path or a multi-provider fallback architecture for production reliability?"
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": _critical_answer("AURA provider routing"),
                "attempts": [{"provider": "groq", "status": "success"}],
                "routing_order": ["groq"],
            },
        ) as provider_mock:
            payload = response_engine.generate_response_payload(prompt)

        self.assertTrue(payload["success"])
        self.assertTrue(payload["critical_question"])
        self.assertEqual(payload["explanation_mode"], "critical_reasoning")
        self.assertIn("architecture", payload["critical_profile"]["domains"])
        self.assertTrue(payload["critical_verification"]["ok"])
        system_message = provider_mock.call_args.args[0][0]["content"]
        self.assertIn("CRITICAL QUESTION MODE", system_message)

    def test_medical_question_uses_cautious_safe_domain_mode(self):
        prompt = "Should I change my blood pressure medication dosage?"
        medical_answer = (
            "Direct verdict: Do not change the dosage on your own.\n\n"
            "Reasoning: Blood pressure medication affects circulation, heart workload, kidney function, and possible side effects. "
            "Changing dose without a clinician can make pressure too high or too low and can interact with other medicines.\n\n"
            "Assumptions / uncertainty: I do not know your prescription, readings, medical history, or other medications, so this is general safety guidance only.\n\n"
            "Risks: The risks include dizziness, fainting, rebound high blood pressure, drug interactions, and delayed treatment of a serious condition.\n\n"
            "Recommendation: Contact your doctor, pharmacist, or qualified professional before changing anything. If you have severe symptoms, seek urgent medical care.\n\n"
            "Next step: Record recent blood pressure readings, current dose, symptoms, and timing, then share them with your clinician."
        )
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": medical_answer,
                "attempts": [{"provider": "groq", "status": "success"}],
                "routing_order": ["groq"],
            },
        ):
            payload = response_engine.generate_response_payload(prompt)

        self.assertTrue(payload["success"])
        self.assertTrue(payload["critical_question"])
        self.assertEqual(payload["critical_profile"]["risk_level"], "high")
        self.assertIn("medical", payload["critical_profile"]["domains"])
        self.assertIn("doctor", payload["content"].lower())
        self.assertTrue(payload["critical_verification"]["ok"])

    def test_weak_critical_answer_is_rejected_and_regenerated(self):
        prompt = "Should we migrate AURA authentication storage for better security and reliability?"
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            side_effect=[
                {
                    "success": True,
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "text": "Do it. It will definitely be better.",
                    "attempts": [{"provider": "groq", "status": "success"}],
                    "routing_order": ["groq"],
                },
                {
                    "success": True,
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "text": _critical_answer("authentication storage"),
                    "attempts": [{"provider": "groq", "status": "success"}],
                    "routing_order": ["groq"],
                },
            ],
        ) as provider_mock:
            payload = response_engine.generate_response_payload(prompt)

        self.assertTrue(payload["success"])
        self.assertEqual(provider_mock.call_count, 2)
        self.assertNotIn("Do it", payload["content"])
        self.assertTrue(payload["critical_verification"]["ok"])
        self.assertIn("critical_retry", payload["response_stage"])

    def test_external_fact_question_requires_uncertainty_or_source_caveat(self):
        profile = response_engine.classify_critical_question("What is OpenAI's current API status?")
        answer = (
            "Direct verdict: It is fine.\n\n"
            "Reasoning: The API works.\n\n"
            "Risks: There are none.\n\n"
            "Recommendation: Keep using it.\n\n"
            "Next step: Continue."
        )
        verification = response_engine.verify_critical_answer(answer, profile)

        self.assertTrue(profile["is_critical"])
        self.assertTrue(profile["needs_external_facts"])
        self.assertIn("missing_uncertainty", verification["issues"])
        self.assertIn("missing_source_caveat", verification["issues"])

    def test_critical_provider_failure_returns_limited_structured_fallback(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": False,
                "reason": "No healthy provider.",
                "attempts": [{"provider": "groq", "status": "rate_limited"}],
                "routing_order": ["groq"],
            },
        ):
            payload = response_engine.generate_response_payload(
                "Should we change AURA security architecture before the demo?"
            )

        self.assertFalse(payload["success"])
        self.assertTrue(payload["critical_question"])
        self.assertIn("Direct verdict", payload["degraded_reply"])
        self.assertIn("verified live-model answer", payload["degraded_reply"])


if __name__ == "__main__":
    unittest.main()
