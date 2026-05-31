import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class StructuredGenerationTests(unittest.TestCase):
    def test_code_files_are_read_without_losing_indentation(self):
        from modules.pdf_reader import read_file, get_page_count, get_page_label

        source = "def greet(name):\n    return f'Hi {name}'\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(source)
            path = handle.name
        try:
            self.assertEqual(read_file(path), source.rstrip())
            self.assertEqual(get_page_label(path), "est. pages")
            self.assertGreaterEqual(get_page_count(path), 1)
        finally:
            os.unlink(path)

    def test_library_snapshot_preserves_code_text(self):
        import modules.doc_library as doc_library

        original_path = doc_library.LIBRARY_SNAPSHOT_PATH
        with tempfile.TemporaryDirectory() as tmp:
            doc_library.LIBRARY_SNAPSHOT_PATH = os.path.join(tmp, "library.json")
            try:
                doc_library.save_library_snapshot({
                    "abc": {
                        "id": "abc",
                        "filename": "example.py",
                        "chunks": ["def x(): pass"],
                        "pages": 1,
                        "unit_label": "est. pages",
                        "words": 3,
                        "code_text": "def x():\n    pass",
                    }
                }, "abc")
                library, active = doc_library.load_library_snapshot()
            finally:
                doc_library.LIBRARY_SNAPSHOT_PATH = original_path

        self.assertEqual(active, "abc")
        self.assertEqual(library["abc"]["code_text"], "def x():\n    pass")

    def test_mindmap_builds_tree_from_unordered_concepts(self):
        from modules.mindmap import build_mindmap_tree

        payload = {
            "topic": "Python Project",
            "concepts": [
                {"name": "File Handling", "summary": "Reads and writes files.", "keywords": ["files"], "related": ["paths"], "importance": "medium"},
                {"name": "Main Function", "summary": "Starts the program.", "keywords": ["entry"], "related": ["control flow"], "importance": "high"},
                {"name": "Error Handling", "summary": "Handles invalid input.", "keywords": ["exceptions"], "related": ["validation"], "importance": "medium"},
                {"name": "Data Validation", "summary": "Checks user input.", "keywords": ["validation"], "related": ["Error Handling"], "importance": "high"},
                {"name": "Output Formatting", "summary": "Formats final results.", "keywords": ["display"], "related": ["results"], "importance": "low"},
                {"name": "Loop Control", "summary": "Repeats program steps.", "keywords": ["control flow"], "related": ["Main Function"], "importance": "medium"},
            ],
        }

        tree = build_mindmap_tree(payload)

        self.assertEqual(tree["root"], "Python Project")
        self.assertGreaterEqual(len(tree["branches"]), 4)
        self.assertTrue(all(branch["children"] for branch in tree["branches"]))

    def test_mindmap_uses_legacy_markdown_fallback(self):
        import modules.mindmap as mindmap

        original = mindmap.ask_lmstudio
        calls = []

        def fake_ask(prompt, context="", temperature=0.2, system_prompt=""):
            calls.append(prompt)
            if "Extract study concepts" in prompt:
                return "not json"
            return "# Legacy Topic\n## Branch One\nSummary: fallback branch\n### Fallback child"

        mindmap.ask_lmstudio = fake_ask
        try:
            result = mindmap.generate_mindmap_tree_result(chunks=["fallback content"])
        finally:
            mindmap.ask_lmstudio = original

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "legacy_fallback")
        self.assertEqual(result["data"]["tree"]["root"], "Legacy Topic")

    def test_quiz_requests_replacements_after_duplicates(self):
        import modules.quiz as quiz

        original = quiz.ask_lmstudio
        prompts = []

        def q(text, answer):
            return {
                "question": text,
                "topic": "Basics",
                "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
                "answer": answer,
                "explanation": "Because the document says so.",
            }

        def fake_ask(prompt, context="", temperature=0.2, system_prompt=""):
            prompts.append(prompt)
            if "exactly 3" in prompt:
                return json.dumps({"questions": [q("What is alpha?", "A"), q("What is alpha?", "A"), q("What is beta?", "B")]})
            return json.dumps({"questions": [q("What is gamma?", "C")]})

        quiz.ask_lmstudio = fake_ask
        try:
            result = quiz.generate_quiz_result(chunks=["alpha beta gamma"], num_questions=3)
        finally:
            quiz.ask_lmstudio = original

        questions = result["data"]["questions"]
        self.assertEqual(len(questions), 3)
        self.assertEqual(len({item["question"] for item in questions}), 3)
        self.assertIn("Already accepted", prompts[-1])
        self.assertEqual(result["status"], "repaired")

    def test_flashcards_requests_replacements_after_duplicates(self):
        import modules.flashcards as flashcards

        original = flashcards.ask_lmstudio
        prompts = []

        def card(question, answer):
            return {"question": question, "answer": answer, "topic": "Basics"}

        def fake_ask(prompt, context="", temperature=0.2, system_prompt=""):
            prompts.append(prompt)
            if "exactly 3" in prompt:
                return json.dumps({"cards": [card("Define alpha", "Alpha"), card("Define alpha", "Alpha"), card("Define beta", "Beta")]})
            return json.dumps({"cards": [card("Define gamma", "Gamma")]})

        flashcards.ask_lmstudio = fake_ask
        try:
            result = flashcards.generate_flashcards_result(chunks=["alpha beta gamma"], num_cards=3)
        finally:
            flashcards.ask_lmstudio = original

        cards = result["data"]["cards"]
        self.assertEqual(len(cards), 3)
        self.assertEqual(len({item["question"] for item in cards}), 3)
        self.assertIn("Already accepted", prompts[-1])
        self.assertEqual(result["status"], "repaired")


    def test_audio_overview_repairs_speaker_routing(self):
        from modules.audio_overview import validate_script

        raw = {
            "metadata": {"title": "Energy Notes", "estimated_minutes": 6},
            "turns": [
                {"speaker": "host_a", "text": "Welcome in. Today we are unpacking energy transfer from the notes. [music]"},
                {"speaker": "host_a", "text": "Right, and the key idea is that energy changes form while total energy is conserved."},
                {"speaker": "host_b", "text": "So the useful question is where the energy goes during each process."},
                {"speaker": "host_b", "text": "Exactly, and examples help keep that from becoming too abstract."},
            ],
        }
        script, repaired = validate_script(raw, source_title="Energy Notes", preset={"min_turns": 4, "max_turns": 8, "target_turns": 4})

        self.assertTrue(repaired)
        self.assertIsNotNone(script)
        speakers = [turn["speaker"] for turn in script["turns"]]
        self.assertEqual(speakers, ["HOST_A", "HOST_B", "HOST_A", "HOST_B"])
        self.assertNotIn("[music]", script["turns"][0]["text"])

    def test_audio_overview_assembles_wav_segments(self):
        import wave
        from pathlib import Path
        from modules.audio_overview import assemble_wav_segments

        def write_wav(path):
            with wave.open(str(path), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(8000)
                out.writeframes(b"\x00\x00" * 800)

        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.wav"
            second = Path(tmp) / "second.wav"
            combined = Path(tmp) / "combined.wav"
            write_wav(first)
            write_wav(second)

            assemble_wav_segments([first, second], combined, pause_ms=100)

            self.assertTrue(combined.exists())
            with wave.open(str(combined), "rb") as result:
                self.assertGreater(result.getnframes(), 1600)



if __name__ == "__main__":
    unittest.main()
