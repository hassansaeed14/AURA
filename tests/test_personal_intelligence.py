import unittest
from unittest.mock import patch

import api.api_server as api_server
import brain.core_ai as core_ai
from memory import personalization
from memory.working_memory import WorkingMemoryState


class PersonalIntelligenceTests(unittest.TestCase):
    def test_personal_context_combines_identity_preferences_history_and_memory(self):
        working_state = WorkingMemoryState(
            active_topic="transformer notes",
            last_agent="summary_runtime",
            recent_references=["AI", "Rust", "transformers"],
        )

        with patch.object(
            personalization,
            "list_facts",
            return_value=[{"key": "user:hassan:user_preference", "value": "I prefer short technical answers"}],
        ), patch.object(
            personalization,
            "load_working_memory",
            return_value=working_state,
        ), patch.object(
            personalization,
            "search_memory",
            return_value=[
                {
                    "text": "User asked for transformer notes yesterday.",
                    "metadata": {"username": "hassan", "session_id": "session-1"},
                }
            ],
        ):
            context = personalization.build_personal_context(
                "explain transformers again",
                session_id="session-1",
                user_profile={"username": "hassan"},
                history=[
                    {"role": "user", "content": "make notes on transformers"},
                    {"role": "assistant", "content": "Done."},
                    {"role": "user", "content": "make slides from it"},
                ],
                intent="research",
            )

        self.assertEqual(context["display_name"], "Hassan")
        self.assertIn("I prefer short technical answers", context["preferences"])
        self.assertTrue(any("active topic" in line for line in context["working_memory"]))
        self.assertEqual(context["relevant_memories"], ["User asked for transformer notes yesterday."])
        self.assertIn("recent user flow", context["history_hint"])
        self.assertEqual(context["top_topics"], [])

    def test_personalized_system_prompt_is_quiet_and_bounded(self):
        prompt = personalization.build_personalized_system_prompt(
            "Base prompt.",
            {
                "display_name": "Hassan",
                "preferences": ["I prefer concise explanations"],
                "relevant_memories": ["Asked about Python vs Rust"],
            },
        )

        self.assertIn("PERSONAL CONTEXT", prompt)
        self.assertIn("user name: Hassan", prompt)
        self.assertIn("Use the user's name only when it feels natural", prompt)
        self.assertIn("Do not mention memory", prompt)

    def test_core_ai_passes_personal_context_to_runtime_and_result(self):
        captured = {}

        def fake_runtime(command, **kwargs):
            captured.update(kwargs)
            return {
                "intent": "general",
                "detected_intent": "general",
                "confidence": 0.91,
                "response": "AI is software that can learn patterns and support decisions.",
                "provider": "groq",
                "model": "test-model",
                "providers_tried": ["groq"],
                "used_agents": ["general"],
                "execution_mode": "assistant_llm",
                "decision": {},
                "orchestration": {},
                "permission_action": "general",
                "permission": {"success": True, "status": "approved", "permission": {"trust_level": "safe"}},
            }

        personal_context = {
            "display_name": "Hassan",
            "preferences": ["I prefer concise explanations"],
            "suggestion": "I can keep the next step focused.",
        }

        with patch.object(core_ai, "build_personal_context", return_value=personal_context), patch.object(
            core_ai,
            "_sync_context_into_response_engine",
        ), patch.object(
            core_ai.runtime_core_module,
            "process_command_detailed",
            side_effect=fake_runtime,
        ), patch.object(
            core_ai,
            "remember_profile_identity",
        ), patch.object(
            core_ai,
            "remember_explicit_personal_signals",
        ), patch.object(
            core_ai,
            "_record_exchange",
        ), patch.object(
            core_ai.agent_bus,
            "publish",
        ):
            result = core_ai.process_command_detailed(
                "what is AI",
                session_id="session-1",
                user_profile={"username": "Hassan"},
                security_context={"username": "Hassan"},
            )

        self.assertEqual(captured["security_context"]["personal_context"], personal_context)
        self.assertEqual(result["personal_context"]["display_name"], "Hassan")
        self.assertIn("Next,", result["response"])

    def test_public_casual_reply_does_not_leak_memory_name_without_profile(self):
        with patch.object(api_server, "get_personal_display_name", return_value=""):
            reply = api_server._build_casual_conversation_reply("hello", {})

        self.assertEqual(reply, "Hey. What can I help you with?")

    def test_public_context_ignores_legacy_global_names(self):
        personalization.clear_session_personal_context()

        with patch.object(personalization, "recall_fact", return_value={"value": "Jerry"}), patch.object(
            personalization,
            "get_user_name",
            create=True,
            return_value="Jerry",
        ):
            context = personalization.build_personal_context(
                "hello",
                session_id="public-a",
                user_profile={},
            )

        self.assertEqual(context["display_name"], "")
        self.assertEqual(context["preferences"], [])
        self.assertEqual(context["relevant_memories"], [])

    def test_public_session_name_is_temporary_and_isolated(self):
        personalization.clear_session_personal_context()
        personalization.remember_explicit_personal_signals("my name is Hassan", session_id="public-a")

        first = personalization.build_personal_context("hi", session_id="public-a", user_profile={})
        second = personalization.build_personal_context("hi", session_id="public-b", user_profile={})

        self.assertEqual(first["display_name"], "Hassan")
        self.assertEqual(second["display_name"], "")

    def test_name_overwrite_uses_latest_explicit_signal(self):
        personalization.clear_session_personal_context()
        personalization.remember_explicit_personal_signals("my name is Hassan", session_id="public-a")
        personalization.remember_explicit_personal_signals("call me Ali", session_id="public-a")

        context = personalization.build_personal_context("hi", session_id="public-a", user_profile={})

        self.assertEqual(context["display_name"], "Ali")

    def test_authenticated_scoped_memory_does_not_cross_users(self):
        facts = {
            "user:u1:user_name": {"key": "user:u1:user_name", "value": "Hassan"},
            "user:u2:user_name": {"key": "user:u2:user_name", "value": "Ali"},
            "user:hassan:user_name": {"key": "user:hassan:user_name", "value": "Captain"},
        }

        with patch.object(personalization, "recall_fact", side_effect=lambda key: facts.get(key)):
            user_a = personalization.get_personal_display_name({"id": "u1"}, session_id="session-a")
            user_b = personalization.get_personal_display_name({"id": "u2"}, session_id="session-b")
            username_with_alias = personalization.get_personal_display_name({"username": "hassan"}, session_id="session-c")
            public = personalization.get_personal_display_name({}, session_id="session-a")

        self.assertEqual(user_a, "Hassan")
        self.assertEqual(user_b, "Ali")
        self.assertEqual(username_with_alias, "Captain")
        self.assertEqual(public, "")

    def test_personal_prompt_does_not_claim_memory_when_empty(self):
        prompt = personalization.build_personalized_system_prompt("Base prompt.", {})

        self.assertEqual(prompt, "Base prompt.")
        self.assertNotIn("I remember", prompt)

    def test_clear_session_context_removes_short_term_identity(self):
        personalization.clear_session_personal_context()
        core_ai.SESSION_CONTEXT_HISTORY["public-a"] = [{"role": "user", "content": "my name is Hassan"}]
        personalization.remember_explicit_personal_signals("my name is Hassan", session_id="public-a")

        core_ai.clear_session_context("public-a")
        context = personalization.build_personal_context("hi", session_id="public-a", user_profile={})

        self.assertNotIn("public-a", core_ai.SESSION_CONTEXT_HISTORY)
        self.assertEqual(context["display_name"], "")


if __name__ == "__main__":
    unittest.main()
