"""Exercise public commands and the saved-state workflow."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from meffert.__main__ import main
from meffert.model import State, parse_moves


class CommandTests(unittest.TestCase):
    def run_command(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = main(args)
            except SystemExit as exc:
                code = exc.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_saved_state_can_be_loaded_solved_and_played_back(self):
        code, output, _ = self.run_command("apply", "U V W' X U V2", "--json")
        self.assertEqual(code, 0)
        state = State.from_dict(json.loads(output))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "puzzle.json"
            path.write_text(output)
            code, solution, error = self.run_command("solve", "--state", str(path), "--json")
            self.assertEqual(code, 0, error)
            result = json.loads(solution)
            self.assertEqual(state.apply(parse_moves(result["algorithm"])), State())
            self.assertTrue(result["optimal"])
            self.assertEqual(result["turns"], len(parse_moves(result["legacy"])))

    def test_solved_state_output(self):
        code, output, error = self.run_command("solve", "--scramble", "", "--json")
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["turns"], 0)

    def test_invalid_algorithm_has_useful_error(self):
        code, _, error = self.run_command("apply", "R U R'")
        self.assertEqual(code, 2)
        self.assertIn("Invalid move", error)
        self.assertNotIn("Traceback", error)

    def test_invalid_json_has_useful_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{broken")
            code, _, error = self.run_command("solve", "--state", str(path))
        self.assertEqual(code, 2)
        self.assertIn("error:", error)
        self.assertNotIn("Traceback", error)

    def test_invalid_permutation_is_rejected(self):
        data = State().to_dict()
        data["sides"]["Red"], data["sides"]["Orange"] = "Orange", "Red"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "impossible.json"
            path.write_text(json.dumps(data))
            code, _, error = self.run_command("solve", "--state", str(path))
        self.assertEqual(code, 2)
        self.assertIn("Unreachable", error)

    def test_seeded_scramble_is_reproducible(self):
        first = self.run_command("scramble", "--length", "30", "--seed", "42")
        self.assertEqual(first, self.run_command("scramble", "--length", "30", "--seed", "42"))
        moves = parse_moves(first[1])
        self.assertEqual(len(moves), 30)
        self.assertTrue(all(a % 4 != b % 4 for a, b in zip(moves, moves[1:])))

    def test_search_limit_is_explicit_in_json(self):
        code, output, _ = self.run_command("solve", "--scramble", "U V", "--max-nodes", "1", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["error"], "search_limit")

    def test_nonfinite_timeout_is_rejected(self):
        for timeout in ("nan", "inf", "-inf", "0"):
            code, _, error = self.run_command("solve", "--scramble", "U", f"--timeout={timeout}")
            self.assertEqual(code, 2)
            self.assertIn("finite positive", error)

    def test_maneuver_output_preserves_all_corners(self):
        code, output, error = self.run_command("maneuvers", "--limit", "2", "--json")
        self.assertEqual(code, 0, error)
        for result in json.loads(output):
            state = State().apply(parse_moves(result["algorithm"]))
            self.assertEqual(state.corners, State().corners)
            self.assertEqual(state.spokes, State().spokes)
            self.assertNotEqual(state.sides, State().sides)
            self.assertEqual(result["preserves"], "corners")


if __name__ == "__main__":
    unittest.main()
