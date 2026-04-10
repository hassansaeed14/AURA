import unittest

from config.master_spec import (
    ANTI_PATTERNS,
    AGENT_DESIGN_ORDER,
    ARCHITECTURE_RULES,
    BUILDER_FINAL_AUTHORITY,
    CAPABILITY_LABELS,
    CORE_PIPELINE,
    CURRENT_ISSUES,
    FEATURES_BUILT,
    HYBRID_IMPLEMENTATION_ORDER,
    IMPLEMENTATION_RULES,
    IMPLEMENTATION_PRIORITY,
    INTERFACE_SURFACES,
    NEXT_BUILDS,
    PROJECT_ROOT,
    SUPPORT_CHATS,
    SUPPORT_CHAT_GLOBAL_RULES,
    TRUST_MODEL,
    build_current_state_summary,
    build_master_spec_summary,
    build_support_chat_summary,
)


class MasterSpecTests(unittest.TestCase):
    def test_core_pipeline_matches_expected_flow(self):
        self.assertEqual(
            CORE_PIPELINE,
            ("perceive", "understand", "decide", "act", "reflect", "improve"),
        )

    def test_trust_model_covers_all_risk_levels(self):
        self.assertEqual(
            TRUST_MODEL,
            {
                "safe": "auto_allow",
                "private": "ask_confirmation",
                "sensitive": "session_approval",
                "critical": "pin_or_password",
            },
        )

    def test_summary_contains_interface_and_rules(self):
        summary = build_master_spec_summary()
        self.assertIn("autonomy", INTERFACE_SURFACES)
        self.assertIn("do_not_fake_capabilities", ARCHITECTURE_RULES)
        self.assertEqual(summary["trust_model"]["critical"], "pin_or_password")

    def test_implementation_doctrine_is_machine_readable(self):
        summary = build_master_spec_summary()
        self.assertEqual(CAPABILITY_LABELS, ("real", "hybrid", "placeholder"))
        self.assertEqual(IMPLEMENTATION_PRIORITY, CAPABILITY_LABELS)
        self.assertEqual(HYBRID_IMPLEMENTATION_ORDER[-1], "llm_enhancement_third")
        self.assertEqual(AGENT_DESIGN_ORDER[0], "detect_intent")
        self.assertIn("system_features_must_not_be_prompt_only", IMPLEMENTATION_RULES)
        self.assertIn("fake_system_status", ANTI_PATTERNS)
        self.assertIn("capability_labels", summary)

    def test_current_state_summary_includes_project_status(self):
        summary = build_current_state_summary()
        self.assertEqual(summary["project_root"], PROJECT_ROOT)
        self.assertIn("web_interface", FEATURES_BUILT)
        self.assertIn("purchase_flow_not_real_yet", CURRENT_ISSUES)
        self.assertIn("pin_system", NEXT_BUILDS)

    def test_support_chat_summary_matches_operating_model(self):
        summary = build_support_chat_summary()
        self.assertEqual(len(SUPPORT_CHATS), 5)
        self.assertIn("backend_builder", summary["support_chats"])
        self.assertIn("do_not_fake_features", SUPPORT_CHAT_GLOBAL_RULES)
        self.assertEqual(summary["builder_final_authority"], BUILDER_FINAL_AUTHORITY)


if __name__ == "__main__":
    unittest.main()
