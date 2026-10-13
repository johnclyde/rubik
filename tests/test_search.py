"""Search tests use a tiny independent coordinate model with known distances."""

import unittest
import random

from meffert.model import IDENTITY, State, build_coordinates, parse_moves

from meffert.search import (
    SPOKE_MOVES,
    SearchLimitError,
    SearchTables,
    find_maneuvers,
    invert,
    solve,
)


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Four independent three-position dials, with no movable side pieces.
        # The exact shortest distance is the number of nonzero base-3 digits.
        cls.tables = SearchTables(
            [0] * 8,
            [next_state for row in SPOKE_MOVES for next_state in row],
            list(range(81)),
        )

    def test_all_dial_states_have_shortest_solutions(self):
        for state in range(81):
            with self.subTest(state=state):
                expected = sum(state // 3 ** axis % 3 != 0 for axis in range(4))
                result = solve(self.tables, 0, state)
                self.assertEqual(len(result.moves), expected)
                following = state
                for move in result.moves:
                    following = SPOKE_MOVES[following][move]
                self.assertEqual(following, 0)

    def test_projection_paths_and_inverse(self):
        for state in range(81):
            moves = self.tables.projection_path(0, state)
            following = 0
            for move in moves:
                following = SPOKE_MOVES[following][move]
            self.assertEqual(following, state)
            for move in invert(moves):
                following = SPOKE_MOVES[following][move]
            self.assertEqual(following, 0)

    def test_depth_limit_reports_admissible_lower_bound(self):
        with self.assertRaises(SearchLimitError) as caught:
            solve(self.tables, 0, 40, max_depth=3)
        self.assertEqual(caught.exception.lower_bound, 4)
        self.assertIn("depth limit", caught.exception.reason)

    def test_node_limit(self):
        with self.assertRaises(SearchLimitError) as caught:
            solve(self.tables, 0, 40, max_nodes=1)
        self.assertEqual(caught.exception.nodes, 1)
        self.assertIn("node limit", caught.exception.reason)

    def test_time_limit(self):
        with self.assertRaises(SearchLimitError) as caught:
            solve(self.tables, 0, 40, timeout=1e-12)
        self.assertIn("time limit", caught.exception.reason)

    def test_solved_state_needs_no_search(self):
        result = solve(self.tables, 0, 0, max_depth=0, max_nodes=1)
        self.assertEqual(result.moves, ())
        self.assertEqual(result.nodes, 0)

    def test_invalid_limits_and_coordinates(self):
        for kwargs in ({"timeout": 0}, {"timeout": float("nan")},
                       {"timeout": float("inf")}, {"max_nodes": 0}, {"max_depth": -1}):
            with self.assertRaises(ValueError):
                solve(self.tables, 0, 1, **kwargs)
        with self.assertRaises(ValueError):
            solve(self.tables, 1, 1)
        with self.assertRaises(ValueError):
            self.tables.projection_path(0, 81)

    def test_model_orientation_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "disagree"):
            SearchTables([0] * 8, [0] * 8, [0])

    def test_empty_maneuver_set(self):
        self.assertEqual(find_maneuvers(self.tables, [0]), ())


class FullPuzzleSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coordinates = build_coordinates()
        c = cls.coordinates
        cls.tables = SearchTables(c.side_transitions, c.corner_transitions, c.corner_spokes)
        cls.tables.prepare(paths=True)
        cls.changes = [sum(a != b for a, b in enumerate(state)) for state in c.side_states]

    def test_projection_sizes_and_diameters(self):
        self.assertEqual(self.tables.side_count, 11_520)
        self.assertEqual(self.tables.corner_count, 8_748)
        self.assertEqual(len(self.tables.side_spoke_distances), 933_120)
        self.assertNotIn(255, self.tables.side_spoke_distances)
        self.assertNotIn(255, self.tables.corner_distances)
        self.assertEqual(max(self.tables.side_spoke_distances), 11)
        self.assertEqual(max(self.tables.corner_distances), 7)

    def test_shortest_paths_match_independent_shallow_breadth_first_search(self):
        distances = {(0, 0): 0}
        queue = [(0, 0)]
        c = self.coordinates
        for side, corner in queue:
            depth = distances[side, corner]
            result = solve(self.tables, side, corner)
            self.assertEqual(len(result.moves), depth)
            following_side, following_corner = side, corner
            for move in result.moves:
                following_side = c.side_transitions[following_side * 8 + move]
                following_corner = c.corner_transitions[following_corner * 8 + move]
            self.assertEqual((following_side, following_corner), (0, 0))
            if depth >= 4:
                continue
            for move in range(8):
                following = (c.side_transitions[side * 8 + move],
                             c.corner_transitions[corner * 8 + move])
                if following not in distances:
                    distances[following] = depth + 1
                    queue.append(following)
        self.assertEqual(len(distances), 2073)

    def test_scrambled_full_states_solve_and_replay(self):
        randomizer = random.Random(100)
        for _ in range(20):
            state = State().apply([randomizer.randrange(8) for _ in range(30)])
            result = solve(self.tables, *self.coordinates.encode(state))
            self.assertEqual(state.apply(result.moves), State())

    def test_floating_corners_are_included_in_solution(self):
        state = State().apply(parse_moves("0145"))
        self.assertEqual(state.spokes, (0, 0, 0, 0))
        self.assertNotEqual(state.corners, IDENTITY)
        result = solve(self.tables, *self.coordinates.encode(state))
        self.assertEqual(state.apply(result.moves), State())
        self.assertEqual(len(result.moves), 4)

    def test_all_fixed_spoke_maneuvers(self):
        maneuvers = find_maneuvers(
            self.tables, self.changes, preserve_all_corners=False, limit=1000
        )
        self.assertEqual(len(maneuvers), 175)
        self.assertEqual(sum(m.changed_colors == 4 for m in maneuvers), 15)
        self.assertEqual(sum(m.changed_colors == 6 for m in maneuvers), 160)
        for maneuver in maneuvers:
            state = State().apply(maneuver.moves)
            self.assertEqual(state.spokes, (0, 0, 0, 0))
            self.assertEqual(self.coordinates.encode(state)[0], maneuver.side)
            self.assertFalse(maneuver.preserves_all_corners)
            self.assertEqual(len(maneuver.moves),
                             self.tables.side_spoke_distances[maneuver.side * 81])

    def test_full_corner_maneuvers(self):
        maneuvers = find_maneuvers(self.tables, self.changes, limit=10)
        self.assertEqual(len(maneuvers), 10)
        for maneuver in maneuvers:
            state = State().apply(maneuver.moves)
            self.assertEqual(state.spokes, (0, 0, 0, 0))
            self.assertEqual(state.corners, IDENTITY)
            self.assertEqual(self.coordinates.encode(state)[0], maneuver.side)
            self.assertTrue(maneuver.preserves_all_corners)

    def test_maneuver_limit_is_explicit(self):
        with self.assertRaises(SearchLimitError):
            find_maneuvers(self.tables, self.changes, max_nodes=1)

    def test_fixed_spoke_maneuver_limits_are_explicit(self):
        for limits in ({"max_nodes": 1}, {"timeout": 1e-12}, {"max_depth": 3}):
            with self.subTest(limits=limits), self.assertRaises(SearchLimitError):
                find_maneuvers(self.tables, self.changes,
                               preserve_all_corners=False, **limits)

    def test_maneuver_time_limit_must_be_finite(self):
        for timeout in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                find_maneuvers(self.tables, self.changes, timeout=timeout)


if __name__ == "__main__":
    unittest.main()
