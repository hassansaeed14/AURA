import unittest
from unittest.mock import patch

import api.api_server as api_server
import brain.core_ai as core_ai
from memory import personalization
from memory.working_memory import WorkingMemoryState


class PersonalIntelligenceTests(unittest.TestCase):
    def test_personal_context_combines_identity_preferences_history_and_memory(self):
        learning_snapshot = {
            "user_profile": {"preferences": {"answer_style": "concise"}},
            "learned_facts": ["I usually prefer bullet points"],
            "topic_frequency": {"code": 4, "research": 2},
            "behavior_stats": {"short_queries": 6, "medium_queries": 2, "long_queries": 1},
        }
        working_state = WorkingMemoryState(
            active_topic="transformer notes",
            last_agent="summary_runtime",
            recent_references=["AI", "Rust", "transformers"],
        )

        with patch.object(personalization.learning_agent, "load_data", return_value=learning_snapshot), patch.object(
            personalization,
            "list_facts",
            return_value=[{"key": "user_preference", "value": "I prefer short technical answers"}],
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
                    "metadata": {"session_id": "session-1"},
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
        self.assertEqual(context["top_topics"][0], "code (4)")

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


if __name__ == "__main__":
    unittest.main()
