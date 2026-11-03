"""Run: python3 evals/test_how_i_prompt.py (from the skill folder)."""
import importlib.util, unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("hip", HERE.parent / "scripts" / "how_i_prompt.py")
hip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hip)


class Extract(unittest.TestCase):
    data = hip.extract(HERE / "session.jsonl")
    turns = data["turns"]

    def test_keeps_only_human_turns_in_order(self):
        self.assertEqual([t["kind"] for t in self.turns],
                         ["prompt", "commande", "réponse QCM", "en cours de tour", "refus avec consigne", "réponse QCM partielle"])

    def test_prompts_are_verbatim_except_masking(self):
        p = [t["prompt"] for t in self.turns]
        self.assertEqual(p[0], "fais le récap, écris à «email» avec token=«secret» depuis ~/proj")
        self.assertEqual(p[1:], ["/second-pass sur le diff", "Langue ? → Français", "et ajoute un test",
                                 "fais plutôt une copie", "Stack ? → grain"])

    def test_records_what_the_agent_did(self):
        first = self.turns[0]
        self.assertEqual((first["tools"], first["files"], first["reply_excerpt"]),
                         ({"Edit": 2}, ["~/proj/a.py"], "Récap écrit."))
        self.assertEqual(self.data["project"], "~/proj")

    def test_render_shows_prompt_and_summary(self):
        self.turns[0]["resume"] = "Écrit le récap."
        md = hip.render(self.data)
        self.assertIn("> fais le récap", md)
        self.assertIn("→ Écrit le récap.", md)
        self.assertNotIn("bob", md)


if __name__ == "__main__":
    unittest.main()
