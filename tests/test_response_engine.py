import unittest
from unittest.mock import patch

import brain.response_engine as response_engine


class ResponseEngineTests(unittest.TestCase):
    def test_generate_web_search_response_payload_returns_search_backed_answer(self):
        search_result = {
            "success": True,
            "source": "duckduckgo_instant_answer",
            "live_data": True,
            "data": {
                "query": "latest groq api pricing",
                "heading": "Groq API pricing",
                "abstract": "Groq currently prices usage by model and token volume.",
                "related_topics": [
                    "Pricing can change over time.",
                    "Check the provider status page for the latest details.",
                ],
            },
        }

        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "Groq currently prices usage by model and token volume. The exact rates can change, so check their latest pricing page for the current numbers.",
                "attempts": ["groq"],
                "routing_order": ["groq"],
                "latency_ms": 25.0,
            },
        ):
            payload = response_engine.generate_web_search_response_payload(
                "What is the latest Groq API pricing?",
                search_result,
            )

        self.assertTrue(payload["success"])
        self.assertTrue(payload["web_used"])
        self.assertEqual(payload["provider"], "groq")
        self.assertEqual(payload["explanation_mode"], "direct")
        self.assertIn("current numbers", payload["content"])

    def test_generate_response_payload_uses_degraded_reply_when_all_providers_fail(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": False,
                "reason": "No healthy AI provider completed the request.",
                "attempts": [
                    {"provider": "gemini", "status": "unavailable", "reason": "Gemini unavailable"},
                    {"provider": "openai", "status": "rate_limited", "reason": "OpenAI rate limited"},
                    {"provider": "groq", "status": "auth_failed", "reason": "Groq auth failed"},
                ],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("What is wrong with my setup?")

        self.assertFalse(payload["success"])
        self.assertIn("live ai providers", payload["degraded_reply"].lower())
        self.assertIn("gemini", payload["degraded_reply"].lower())

    def test_generate_response_payload_strips_canned_filler_for_questions(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "text": "Certainly, sir. Quantum computing uses qubits.",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("What is quantum computing?")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["content"], "Quantum computing uses qubits.")

    def test_generate_response_payload_strips_stale_memory_filler_for_non_history_question(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "We've discussed this before. Quantum computing uses qubits to represent probabilities.",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("What is quantum computing?")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["content"], "Quantum computing uses qubits to represent probabilities.")

    def test_generate_response_payload_strips_false_repeat_claims(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "I've answered this question for you multiple times before. Elon Musk is a business magnate and entrepreneur.",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("Who is Elon Musk?")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["content"], "Elon Musk is a business magnate and entrepreneur.")

    def test_generate_response_payload_strips_recap_wrappers(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "I've noticed that you've asked about stress multiple times before. To recap, some common strategies include deep breathing and a short walk.",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("What should I do if I am feeling stressed?")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["content"], "Some common strategies include deep breathing and a short walk.")

    def test_generate_response_payload_strips_repeat_claim_sentences(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "You've asked this question before, multiple times. I'd be happy to explain it again. Quantum computing uses qubits and quantum effects to process information.",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("What is quantum computing?")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["content"], "Quantum computing uses qubits and quantum effects to process information.")

    def test_generate_response_payload_applies_cleanup_to_direct_requests(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "It seems like you've asked this before. I'll provide the answer again. Here's a Python function:\ndef reverse_string(s):\n    return s[::-1]",
                "attempts": [],
                "routing_order": ["gemini", "openai", "groq"],
            },
        ):
            payload = response_engine.generate_response_payload("Write me a Python function to reverse a string")

        self.assertTrue(payload["success"])
        self.assertTrue(payload["content"].startswith("Here's a Python function:"))

    def test_generate_response_payload_sets_comparison_explanation_mode(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": True,
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "text": "Python is simpler to learn, while Rust gives tighter control over memory and performance.",
                "attempts": [],
                "routing_order": ["groq"],
            },
        ):
            payload = response_engine.generate_response_payload("Compare Python vs Rust")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["explanation_mode"], "comparison")

    def test_generate_response_payload_uses_primary_provider_only_for_normal_answers(self):
        with patch.object(
            response_engine,
            "generate_with_best_provider",
            return_value={
                "success": False,
                "reason": "No healthy AI provider completed the request.",
                "attempts": [
                    {"provider": "groq", "status": "auth_failed", "reason": "Groq auth failed"},
                ],
                "routing_order": ["groq"],
            },
        ) as provider_mock:
            response_engine.generate_response_payload("What is quantum computing?")

        self.assertTrue(provider_mock.called)
        self.assertTrue(provider_mock.call_args.kwargs["preferred_only"])
        self.assertEqual(provider_mock.call_args.kwargs["preferred"], response_engine.DEFAULT_REASONING_PROVIDER)

    def test_local_assignment_content_expands_for_large_page_targets(self):
        content = response_engine._build_local_assignment_content("transformers", page_target=10)

        self.assertIn("Historical Development", content)
        self.assertIn("Ethical and Social Impact", content)
        self.assertIn("Comparative Perspective", content)
        self.assertIn("Architecture and Mechanism", content)
        self.assertIn("This section should stay centered on practical use and visible outcomes", content)

    def test_assignment_depth_profile_scales_by_page_band(self):
        compact = response_engine._build_assignment_depth_profile(4)
        expanded = response_engine._build_assignment_depth_profile(7)
        extended = response_engine._build_assignment_depth_profile(10)

        self.assertEqual(compact["band"], "compact")
        self.assertEqual(compact["base_paragraph_target"], 2)
        self.assertEqual(compact["paragraph_ceiling"], 2)
        self.assertEqual(compact["max_tokens"], 480)

        self.assertEqual(expanded["band"], "expanded")
        self.assertEqual(expanded["base_paragraph_target"], 2)
        self.assertEqual(expanded["paragraph_ceiling"], 3)
        self.assertEqual(expanded["max_tokens"], 620)

        self.assertEqual(extended["band"], "extended")
        self.assertEqual(extended["base_paragraph_target"], 3)
        self.assertEqual(extended["paragraph_ceiling"], 4)
        self.assertEqual(extended["max_tokens"], 760)

    def test_assignment_section_weighting_makes_intro_lighter_than_core(self):
        intro = response_engine._resolve_assignment_section_depth("Introduction", 10)
        core = response_engine._resolve_assignment_section_depth("Core Concepts", 10)
        conclusion = response_engine._resolve_assignment_section_depth("Conclusion", 10)

        self.assertEqual(intro["weight_label"], "light")
        self.assertEqual(core["weight_label"], "high")
        self.assertLess(intro["paragraph_target"], core["paragraph_target"])
        self.assertLess(intro["token_budget"], core["token_budget"])
        self.assertLess(conclusion["token_budget"], core["token_budget"])

    def test_assignment_section_weighting_scales_core_depth_in_extended_mode(self):
        compact_core = response_engine._resolve_assignment_section_depth("Core Concepts", 4)
        extended_core = response_engine._resolve_assignment_section_depth("Core Concepts", 10)

        self.assertLess(compact_core["paragraph_target"], extended_core["paragraph_target"])
        self.assertLess(compact_core["token_budget"], extended_core["token_budget"])

    def test_assignment_section_plan_uses_technical_style_variants_for_technical_topics(self):
        plan = response_engine._build_assignment_section_plan("transformers", 10)
        titles = [section["title"] for section in plan]
        kinds = [section["kind"] for section in plan]
        purposes = {section["title"]: section["purpose"] for section in plan}

        self.assertIn("Architecture and Mechanism", titles)
        self.assertIn("Applications and Use Cases", titles)
        self.assertIn("implementation considerations", kinds)
        self.assertLess(titles.index("Architecture and Mechanism"), titles.index("Applications and Use Cases"))
        self.assertIn("without moving into full definitions or mechanism detail", purposes["Technical Background and Context"])
        self.assertIn("without re-explaining the mechanism in full", purposes["Applications and Use Cases"])

    def test_assignment_section_plan_uses_comparative_style_for_comparison_topics(self):
        plan = response_engine._build_assignment_section_plan("python vs rust", 7)
        titles = [section["title"] for section in plan]
        kinds = [section["kind"] for section in plan]

        self.assertIn("Comparison Context", titles)
        self.assertIn("Comparative Analysis", titles)
        self.assertIn("Best-Fit Use Cases", titles)
        self.assertIn("Tradeoffs and Limitations", titles)
        self.assertIn("comparative perspective", kinds)
        self.assertNotIn("How It Works", titles)

    def test_assignment_domain_guidance_uses_topic_sensitive_terminology(self):
        technical = response_engine._build_assignment_domain_guidance("transformers", "how it works", "technical")
        social = response_engine._build_assignment_domain_guidance("climate change", "background and context", "standard")
        comparative = response_engine._build_assignment_domain_guidance("python vs rust", "comparative perspective", "comparative")

        self.assertEqual(technical["domain"], "technical")
        self.assertIn("system components", technical["prompt_terminology"])
        self.assertIn("data flow", technical["prompt_examples"])

        self.assertEqual(social["domain"], "social")
        self.assertIn("institutions, communities, policy", social["prompt_terminology"])
        self.assertIn("policy environments", social["prompt_examples"])

        self.assertEqual(comparative["domain"], "comparative")
        self.assertIn("criteria, tradeoffs, alternatives", comparative["prompt_terminology"])
        self.assertIn("side-by-side scenarios", comparative["prompt_examples"])

    def test_assignment_section_prompt_reflects_page_band_depth(self):
        compact_prompt = response_engine._build_assignment_section_prompt(
            "transformers",
            "core concepts",
            "Core Concepts",
            "Define the main ideas clearly.",
            4,
        )
        extended_prompt = response_engine._build_assignment_section_prompt(
            "transformers",
            "core concepts",
            "Core Concepts",
            "Define the main ideas clearly.",
            10,
        )
        intro_prompt = response_engine._build_assignment_section_prompt(
            "transformers",
            "introduction",
            "Introduction",
            "Introduce the topic.",
            10,
        )

        self.assertIn("Section weight: high.", compact_prompt)
        self.assertIn("2 coherent paragraphs", compact_prompt)
        self.assertIn("Keep the section concise and focused", compact_prompt)
        self.assertIn("Focus on the main concepts, principles, definitions, and relationships", compact_prompt)
        self.assertIn("Do not repeat background history, a full mechanism walkthrough, or use-case examples", compact_prompt)
        self.assertIn("system components, architecture, data flow", compact_prompt)
        self.assertIn("4 coherent paragraphs", extended_prompt)
        self.assertIn("Section weight: high.", extended_prompt)
        self.assertIn("Use fuller academic depth", extended_prompt)
        self.assertIn("2 coherent paragraphs", intro_prompt)
        self.assertIn("Section weight: light.", intro_prompt)
        self.assertIn("Keep this section brief", intro_prompt)

    def test_assignment_section_prompt_uses_social_domain_terminology_for_social_topics(self):
        social_prompt = response_engine._build_assignment_section_prompt(
            "climate change",
            "background and context",
            "Background and Context",
            "Explain the wider context around the topic.",
            7,
        )

        self.assertIn("institutions, communities, policy", social_prompt)
        self.assertIn("policy environments", social_prompt)

    def test_generate_document_content_payload_uses_chunked_sections_for_large_assignments(self):
        captured_calls = []

        def fake_generate(prompt, system_override=None, max_tokens=0, temperature=0.0):
            heading = prompt.split("Write only the '", 1)[1].split("'", 1)[0]
            captured_calls.append(
                {
                    "heading": heading,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            return {
                "success": True,
                "content": f"{heading}\nThis is the {heading.lower()} section.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "providers_tried": ["groq"],
            }

        with patch.object(response_engine, "generate_response_payload", side_effect=fake_generate) as payload_mock:
            payload = response_engine.generate_document_content_payload(
                "assignment",
                "artificial intelligence",
                page_target=10,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["source"], "provider_chunked")
        self.assertEqual(payload["provider"], "groq")
        self.assertIn("Historical Development", payload["content"])
        self.assertIn("Implementation Considerations", payload["content"])
        self.assertIn("Comparative Perspective", payload["content"])
        self.assertGreaterEqual(payload_mock.call_count, 10)
        intro_call = next(call for call in captured_calls if call["heading"] == "Introduction")
        core_call = next(call for call in captured_calls if call["heading"] == "Core Concepts")
        comparison_call = next(call for call in captured_calls if call["heading"] == "Comparative Perspective")
        self.assertEqual(intro_call["max_tokens"], 418)
        self.assertEqual(core_call["max_tokens"], 760)
        self.assertEqual(comparison_call["max_tokens"], 745)
        self.assertLess(intro_call["max_tokens"], core_call["max_tokens"])
        self.assertTrue(all(call["temperature"] == 0.35 for call in captured_calls))

    def test_generate_document_content_payload_uses_lighter_chunk_depth_for_mid_size_assignments(self):
        captured_calls = []

        def fake_generate(prompt, system_override=None, max_tokens=0, temperature=0.0):
            heading = prompt.split("Write only the '", 1)[1].split("'", 1)[0]
            captured_calls.append(
                {
                    "heading": heading,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            return {
                "success": True,
                "content": f"{heading}\nThis is the {heading.lower()} section.",
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "providers_tried": ["groq"],
            }

        with patch.object(response_engine, "generate_response_payload", side_effect=fake_generate) as payload_mock:
            payload = response_engine.generate_document_content_payload(
                "assignment",
                "artificial intelligence",
                page_target=4,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["source"], "provider_chunked")
        self.assertGreaterEqual(payload_mock.call_count, 8)
        intro_call = next(call for call in captured_calls if call["heading"] == "Introduction")
        core_call = next(call for call in captured_calls if call["heading"] == "Core Concepts")
        self.assertEqual(intro_call["max_tokens"], 264)
        self.assertEqual(core_call["max_tokens"], 480)
        self.assertLess(intro_call["max_tokens"], core_call["max_tokens"])
        self.assertTrue(all(call["temperature"] == 0.33 for call in captured_calls))
        self.assertTrue(any("2 coherent paragraphs" in call["prompt"] for call in captured_calls))

    def test_local_assignment_section_body_respects_weighting(self):
        intro_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "introduction",
            page_target=10,
            display_title="Introduction",
        )
        core_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "core concepts",
            page_target=10,
            display_title="Core Concepts",
        )

        intro_paragraphs = intro_body.split("\n\n")
        core_paragraphs = core_body.split("\n\n")

        self.assertEqual(len(intro_paragraphs), 2)
        self.assertEqual(len(core_paragraphs), 4)
        self.assertLess(len(intro_paragraphs), len(core_paragraphs))

    def test_local_assignment_section_body_adds_distinctness_guidance_for_adjacent_sections(self):
        background_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "background and context",
            page_target=10,
            display_title="Technical Background and Context",
        )
        mechanism_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "how it works",
            page_target=10,
            display_title="Architecture and Mechanism",
        )
        applications_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "applications",
            page_target=10,
            display_title="Applications and Use Cases",
        )

        self.assertIn("rather than define every technical idea or explain the full internal workflow", background_body)
        self.assertIn("understanding the mechanism in motion", mechanism_body)
        self.assertIn("practical use and visible outcomes", applications_body)

    def test_local_assignment_section_body_uses_topic_sensitive_domain_support(self):
        technical_body = response_engine._build_local_assignment_section_body(
            "transformers",
            "how it works",
            page_target=10,
            display_title="Architecture and Mechanism",
        )
        social_body = response_engine._build_local_assignment_section_body(
            "climate change",
            "background and context",
            page_target=10,
            display_title="Background and Context",
        )
        comparative_body = response_engine._build_local_assignment_section_body(
            "python vs rust",
            "comparative perspective",
            page_target=10,
            display_title="Comparative Analysis",
        )

        self.assertIn("data flow, processing stages, architectural roles", technical_body)
        self.assertIn("institutions, communities, policy environments", social_body)
        self.assertIn("alternatives, suitability, tradeoffs", comparative_body)

    def test_local_assignment_content_uses_style_variant_titles(self):
        technical_content = response_engine._build_local_assignment_content("transformers", page_target=10)
        comparative_content = response_engine._build_local_assignment_content("python vs rust", page_target=7)

        self.assertIn("Architecture and Mechanism", technical_content)
        self.assertIn("Applications and Use Cases", technical_content)
        self.assertIn("Comparison Context", comparative_content)
        self.assertIn("Comparative Analysis", comparative_content)

    def test_infer_explanation_mode_prefers_simple_when_user_says_simply(self):
        mode = response_engine.infer_explanation_mode("Explain artificial intelligence simply")
        self.assertEqual(mode, "simple")

    def test_polish_assistant_reply_strips_personalized_and_formal_wrappers(self):
        raw = (
            "Hello Hassan from Mansehra, I'd be happy to help you compare Python and Rust. "
            "Python is easier to learn, while Rust gives you tighter performance control."
        )
        cleaned = response_engine.polish_assistant_reply(raw, user_input="compare python vs rust")
        self.assertNotIn("Hassan", cleaned)
        self.assertNotIn("Mansehra", cleaned)
        self.assertTrue(cleaned.startswith("I'd be happy to help you compare Python and Rust.") or cleaned.startswith("Python is easier"))

    def test_polish_assistant_reply_trims_overlong_direct_answers(self):
        raw = (
            "Quantum computing is a computing model that uses qubits and quantum effects. "
            "Unlike classical bits, qubits can represent multiple possibilities at once. "
            "That can make some specialized problems much faster to solve. "
            "It may help in cryptography, optimization, chemistry, and simulation."
        )
        cleaned = response_engine.polish_assistant_reply(raw, user_input="what is quantum computing")
        self.assertLessEqual(len(cleaned), 420)
        self.assertIn("Quantum computing", cleaned)


if __name__ == "__main__":
    unittest.main()
