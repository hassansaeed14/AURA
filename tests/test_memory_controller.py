import unittest
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

import memory.episodic_memory as episodic_memory
import memory.memory_controller as memory_controller
import memory.semantic_memory as semantic_memory
import memory.working_memory as working_memory


class MemoryControllerTests(unittest.TestCase):
    def test_process_interaction_memory_routes_semantic_working_and_episodic_items(self):
        root = Path(mkdtemp(dir=r"D:\HeyGoku"))
        with patch.object(semantic_memory, "SEMANTIC_MEMORY_FILE", root / "semantic.json"), patch.object(
            episodic_memory,
            "EPISODIC_MEMORY_FILE",
            root / "episodic.json",
        ), patch.object(
            working_memory,
            "WORKING_MEMORY_FILE",
            root / "working.json",
        ), patch.object(memory_controller, "store_memory", lambda *args, **kwargs: None):
            stored = memory_controller.process_interaction_memory(
                "My name is Hassan and summarize Aura Report.docx",
                "Done",
                "research",
                0.92,
            )

            self.assertTrue(any(item["destination"] == "semantic" for item in stored))
            self.assertTrue(any(item["destination"] == "working" for item in stored))
            self.assertTrue(any(item["destination"] == "episodic" for item in stored))
            self.assertIsNotNone(semantic_memory.recall_fact("user_name"))
            self.assertEqual(working_memory.load_working_memory().active_file, "Aura Report.docx")


if __name__ == "__main__":
    unittest.main()
