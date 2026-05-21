import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class StructuredGenerationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
