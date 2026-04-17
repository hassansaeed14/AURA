import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import api.api_server as api_server
import brain.runtime_core as runtime_core
from security.trust_engine import build_permission_response
import tools.document_generator as document_generator


class DocumentGeneratorTests(unittest.TestCase):
    def test_detect_document_request_parses_notes_assignment_and_format(self):
        notes_request = document_generator.detect_document_request("make notes on transformers in pdf")
        assignment_request = document_generator.detect_document_request("write 5 page assignment on machine learning in docx")
        prefix_notes_request = document_generator.detect_document_request("give me docx notes on ai")
        inline_format_notes_request = document_generator.detect_document_request("make notes in pdf on transformers")
        inferred_assignment_request = document_generator.detect_document_request("make me a 10 page pdf on transformers")
        inline_assignment_request = document_generator.detect_document_request("write assignment in pdf on artificial intelligence")

        self.assertIsNotNone(notes_request)
        self.assertEqual(notes_request.document_type, "notes")
        self.assertEqual(notes_request.topic, "transformers")
        self.assertEqual(notes_request.export_format, "pdf")

        self.assertIsNotNone(assignment_request)
        self.assertEqual(assignment_request.document_type, "assignment")
        self.assertEqual(assignment_request.topic, "machine learning")
        self.assertEqual(assignment_request.export_format, "docx")
        self.assertEqual(assignment_request.page_target, 5)

        self.assertIsNotNone(prefix_notes_request)
        self.assertEqual(prefix_notes_request.document_type, "notes")
        self.assertEqual(prefix_notes_request.topic, "ai")
        self.assertEqual(prefix_notes_request.export_format, "docx")

        self.assertIsNotNone(inline_format_notes_request)
        self.assertEqual(inline_format_notes_request.document_type, "notes")
        self.assertEqual(inline_format_notes_request.topic, "transformers")
        self.assertEqual(inline_format_notes_request.export_format, "pdf")

        self.assertIsNotNone(inferred_assignment_request)
        self.assertEqual(inferred_assignment_request.document_type, "assignment")
        self.assertEqual(inferred_assignment_request.topic, "transformers")
        self.assertEqual(inferred_assignment_request.export_format, "pdf")
        self.assertEqual(inferred_assignment_request.page_target, 10)

        self.assertIsNotNone(inline_assignment_request)
        self.assertEqual(inline_assignment_request.document_type, "assignment")
        self.assertEqual(inline_assignment_request.topic, "artificial intelligence")
        self.assertEqual(inline_assignment_request.export_format, "pdf")

    def test_generate_document_writes_requested_export_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            document_generator,
            "GENERATED_DIR",
            Path(tmp_dir),
        ), patch.object(
            document_generator,
            "generate_document_content_payload",
            return_value={
                "success": True,
                "content": "Introduction\nThis is a generated assignment.",
                "provider": "local",
                "model": "template",
                "source": "local_template",
                "degraded": True,
                "providers_tried": [],
            },
        ):
            txt_result = document_generator.generate_document("notes", "artificial intelligence", "txt")
            pdf_result = document_generator.generate_document("assignment", "machine learning", "pdf")
            docx_result = document_generator.generate_document("assignment", "deep learning", "docx", page_target=6)

            self.assertTrue(Path(txt_result["file_path"]).exists())
            self.assertTrue(Path(pdf_result["file_path"]).exists())
            self.assertTrue(Path(docx_result["file_path"]).exists())
            self.assertTrue(txt_result["download_url"].startswith("/downloads/"))
            self.assertEqual(Path(pdf_result["file_path"]).suffix.lower(), ".pdf")
            self.assertEqual(Path(docx_result["file_path"]).suffix.lower(), ".docx")
            self.assertEqual(docx_result["page_target"], 6)


class RuntimeDocumentRoutingTests(unittest.TestCase):
    def test_document_generation_permission_is_safe(self):
        permission = build_permission_response("document_generation")

        self.assertTrue(permission["success"])
        self.assertEqual(permission["permission"]["trust_level"], "safe")

    def test_runtime_routes_document_request_directly(self):
        with patch.object(
            runtime_core,
            "handle_document_generation",
            return_value={
                "success": True,
                "message": "I created the notes on transformers. You can download them here: /downloads/notes-transformers.txt",
                "download_url": "/downloads/notes-transformers.txt",
                "file_name": "notes-transformers.txt",
                "file_path": "D:/HeyGoku/generated/notes-transformers.txt",
                "document_type": "notes",
                "format": "txt",
                "page_target": 4,
                "topic": "transformers",
                "source": "local_template",
                "provider": "local",
                "model": "template",
                "providers_tried": [],
            },
        ), patch.object(runtime_core, "respond_in_language", side_effect=lambda response, language: response), patch.object(
            runtime_core,
            "store_and_learn",
        ):
            result = runtime_core.process_single_command_detailed("make notes on transformers")

        self.assertEqual(result["execution_mode"], "document_generation")
        self.assertEqual(result["download_url"], "/downloads/notes-transformers.txt")
        self.assertEqual(result["document_type"], "notes")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["permission_action"], "document_generation")
        self.assertTrue(result["permission"]["success"])
        self.assertEqual(result["page_target"], 4)


class ApiDocumentEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api_server.app)

    def test_prepare_chat_context_marks_document_request_safe(self):
        with patch.object(api_server, "load_user_profile", return_value={}), patch.object(
            api_server,
            "detect_intent_with_confidence",
            return_value=("content", 0.91),
        ):
            context = api_server._prepare_chat_context(
                "write assignment on artificial intelligence",
                "hybrid",
                user=None,
            )

        self.assertEqual(context["detected_intent"], "document")
        self.assertTrue(context["permission"]["success"])
        self.assertEqual(context["permission"]["permission"]["trust_level"], "safe")

    def test_generate_document_endpoint_returns_download_url(self):
        with patch.object(api_server, "requires_first_run_setup", return_value=False), patch.object(
            api_server,
            "generate_document",
            return_value={
                "success": True,
                "download_url": "/downloads/notes-ai.txt",
                "file_name": "notes-ai.txt",
                "document_type": "notes",
                "format": "txt",
                "page_target": 3,
                "topic": "artificial intelligence",
                "provider": "local",
                "source": "local_template",
            },
        ) as generate_mock:
            response = self.client.post(
                "/api/generate/document",
                json={"type": "notes", "topic": "artificial intelligence", "format": "txt", "page_target": 3},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["download_url"], "/downloads/notes-ai.txt")
        self.assertEqual(payload["page_target"], 3)
        self.assertEqual(generate_mock.call_args.kwargs["page_target"], 3)

    def test_api_chat_document_request_bypasses_permission_block(self):
        with patch.object(api_server, "requires_first_run_setup", return_value=False), patch.object(
            api_server,
            "_current_user",
            return_value=None,
        ), patch.object(
            api_server,
            "load_user_profile",
            return_value={},
        ), patch.object(
            api_server,
            "detect_intent_with_confidence",
            return_value=("content", 0.91),
        ), patch.object(
            api_server,
            "process_command_detailed",
            return_value={
                "intent": "document",
                "detected_intent": "document",
                "confidence": 1.0,
                "response": "I created the assignment on artificial intelligence. You can download it here: /downloads/assignment-ai.txt",
                "used_agents": ["document_generator"],
                "agent_capabilities": [],
                "execution_mode": "document_generation",
                "decision": {"intent": "document"},
                "orchestration": {"primary_agent": "document_generator"},
                "permission_action": "document_generation",
                "permission": build_permission_response("document_generation"),
                "provider": "local",
                "model": "template",
                "providers_tried": [],
                "download_url": "/downloads/assignment-ai.txt",
                "file_name": "assignment-ai.txt",
                "document_type": "assignment",
                "document_format": "txt",
                "page_target": 5,
                "document_topic": "artificial intelligence",
                "document_source": "local_template",
                "degraded": False,
            },
        ), patch.object(
            api_server,
            "_attempt_persist_chat_turn",
            return_value={"saved": True},
        ):
            response = self.client.post(
                "/api/chat",
                json={"message": "write assignment on artificial intelligence", "mode": "hybrid"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["execution_mode"], "document_generation")
        self.assertEqual(payload["download_url"], "/downloads/assignment-ai.txt")
        self.assertEqual(payload["page_target"], 5)
        self.assertNotIn("Approval is required", payload["reply"])


if __name__ == "__main__":
    unittest.main()
