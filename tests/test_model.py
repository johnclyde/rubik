"""Model contracts, including compatibility with the original Perl maps."""

from copy import deepcopy
from pathlib import Path
import random
import re
import unittest

from meffert.model import (
    AXES,
    COLORS,
    FREE_MOVES,
    FREE_SLOTS,
    IDENTITY,
    SIDE_MOVES,
    State,
    build_coordinates,
    format_moves,
    inverse,
    parse_moves,
)


class MoveTests(unittest.TestCase):
    def test_legacy_perl_side_maps_are_preserved(self):
        source = (Path(__file__).resolve().parents[1] / "meffert" / "solve_sides.pl").read_text()
        for move, axis in enumerate("uvwx"):
            with self.subTest(axis=axis):
                literal = re.search(r"my \$" + axis + r" = \{(.*?)\};", source, re.DOTALL)
                self.assertIsNotNone(literal)
                pairs = re.findall(r"'([^']+)'\s*=>\s*'([^']+)'", literal.group(1))
                self.assertEqual(len(pairs), 12)
                original = dict(pairs)
                self.assertEqual(set(original), set(COLORS))
                actual = State().turn(move).to_dict()["sides"]
                self.assertEqual(actual, original)
                reverse = {destination: start for start, destination in original.items()}
                self.assertEqual(State().turn(move + 4).to_dict()["sides"], reverse)

    def test_each_move_has_order_three_and_an_inverse(self):
        start = State().apply((0, 1, 2, 7, 0, 6, 3, 5, 2))
        for move in range(8):
            with self.subTest(move=move):
                self.assertNotEqual(start.turn(move), start)
                self.assertEqual(start.apply((move,) * 3), start)
                self.assertEqual(start.turn(move).turn((move + 4) % 8), start)
                self.assertEqual(start.turn(move).turn(move), start.turn((move + 4) % 8))

    def test_mixed_sequence_inversion(self):
        rng = random.Random(20261012)
        for length in (0, 1, 2, 10, 50, 200):
            moves = tuple(rng.randrange(8) for _ in range(length))
            with self.subTest(length=length):
                self.assertEqual(State().apply(moves).apply(inverse(moves)), State())
                self.assertEqual(inverse(inverse(moves)), moves)

    def test_free_corner_geometry(self):
        # Corners are opposite U/V/W/X; sticker normals are x/y/z.
        # A positive 120-degree turn cycles x -> y -> z. These corner
        # paths follow the four tetrahedral diagonals of the inscribed cube.
        paths = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))
        for move, path in enumerate(paths):
            expected = list(IDENTITY)
            for source, destination in zip(path, path[1:] + path[:1]):
                for normal in range(3):
                    expected[3 * source + normal] = 3 * destination + (normal + 1) % 3
            with self.subTest(axis=AXES[move]):
                self.assertEqual(FREE_MOVES[move], tuple(expected))
                self.assertEqual(State().turn(move).spokes,
                                 tuple(int(index == move) for index in range(4)))

    def test_all_sticker_moves_are_permutations(self):
        for kind, moves in (("sides", SIDE_MOVES), ("corners", FREE_MOVES)):
            for index, move in enumerate(moves):
                with self.subTest(kind=kind, move=index):
                    self.assertEqual(tuple(sorted(move)), IDENTITY)

    def test_notation_and_legacy_digits(self):
        self.assertEqual(parse_moves("u V w x U' V2 W’ x2"), tuple(range(8)))
        self.assertEqual(parse_moves("0123 4567"), tuple(range(8)))
        self.assertEqual(parse_moves(" U\nV\tW  X "), (0, 1, 2, 3))
        self.assertEqual(parse_moves(""), ())
        self.assertEqual(format_moves(tuple(range(8))), "U V W X U' V' W' X'")
        self.assertEqual(format_moves(tuple(range(8)), legacy=True), "01234567")
        self.assertEqual(parse_moves(format_moves((7, 2, 5, 0))), (7, 2, 5, 0))

    def test_invalid_notation_and_moves_are_rejected(self):
        for text in (None, [], 0, "8", "-1", "UV", "U3", "R", "U''", "V2'", "1.0"):
            with self.subTest(algorithm=text), self.assertRaises(ValueError):
                parse_moves(text)
        for move in (-1, 8, True, False, 1.0, "0", None):
            with self.subTest(move=move), self.assertRaises(ValueError):
                State().turn(move)


class StateSerializationTests(unittest.TestCase):
    def test_round_trip(self):
        for state in (State(), State().apply((0, 5, 2, 7, 1, 0, 6))):
            with self.subTest(state=state):
                self.assertEqual(State.from_dict(state.to_dict()), state)
        self.assertEqual(set(State().to_dict()["corners"]), set(FREE_SLOTS))

    def test_top_level_schema_is_strict(self):
        valid = State().to_dict()
        invalid = [None, [], "{}", 1, True, {}]
        for field in valid:
            missing = deepcopy(valid)
            del missing[field]
            invalid.append(missing)
        extra = deepcopy(valid)
        extra["extra"] = 1
        invalid.append(extra)
        for puzzle in (None, "megaminx", [], 1):
            invalid.append(dict(valid, puzzle=puzzle))
        for version in (None, True, False, "1", 1.0, 0, 2, [], {}):
            invalid.append(dict(valid, version=version))
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                State.from_dict(payload)

    def test_sticker_permutations_are_strict(self):
        for field, names in (("sides", COLORS), ("corners", FREE_SLOTS)):
            mapping = dict(zip(names, names))
            missing = dict(mapping)
            del missing[names[0]]
            duplicate = dict(mapping)
            duplicate[names[0]] = names[1]
            extra = dict(mapping, unknown=names[0])
            wrong_key = dict(missing, unknown=names[0])
            invalid = [None, [], names, "not a map", missing, duplicate, extra, wrong_key]
            for bad_value in (None, [], {}, 0, True, "unknown"):
                replacement = dict(mapping)
                replacement[names[0]] = bad_value
                invalid.append(replacement)
            for bad_mapping in invalid:
                payload = State().to_dict()
                payload[field] = bad_mapping
                with self.subTest(field=field, mapping=bad_mapping), self.assertRaises(ValueError):
                    State.from_dict(payload)

    def test_spoke_orientations_are_strict(self):
        invalid = [None, [], "0000", {}, {"U": 0, "V": 0, "W": 0},
                   {"U": 0, "V": 0, "W": 0, "X": 0, "Y": 0}]
        for value in (-1, 3, True, False, 0.0, "0", None, [], {}):
            invalid.append({"U": value, "V": 0, "W": 0, "X": 0})
        for spokes in invalid:
            payload = State().to_dict()
            payload["spokes"] = spokes
            with self.subTest(spokes=spokes), self.assertRaises(ValueError):
                State.from_dict(payload)


class CoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coordinates = build_coordinates()

    def test_exact_orbit_sizes(self):
        coordinates = self.coordinates
        self.assertEqual(len(coordinates.side_states), 11520)
        self.assertEqual(len(coordinates.side_ids), 11520)
        self.assertEqual(len(coordinates.side_transitions), 11520 * 8)
        self.assertEqual(len(coordinates.corner_states), 8748)
        self.assertEqual(len(coordinates.corner_ids), 8748)
        self.assertEqual(len(coordinates.corner_transitions), 8748 * 8)
        self.assertEqual(len(coordinates.corner_spokes), 8748)
        self.assertEqual(coordinates.encode(State()), (0, 0))

    def test_generated_transitions_match_reachable_state_turns(self):
        coordinates = self.coordinates
        rng = random.Random(625)
        state = State()
        for sample in range(160):
            side, corner = coordinates.encode(state)
            self.assertEqual(coordinates.side_states[side], bytes(state.sides))
            self.assertEqual(coordinates.corner_states[corner], bytes((*state.spokes, *state.corners)))
            expected_spokes = sum(orientation * (3 ** index)
                                  for index, orientation in enumerate(state.spokes))
            self.assertEqual(coordinates.corner_spokes[corner], expected_spokes)
            for move in range(8):
                with self.subTest(sample=sample, move=move):
                    expected = coordinates.encode(state.turn(move))
                    actual = (coordinates.side_transitions[side * 8 + move],
                              coordinates.corner_transitions[corner * 8 + move])
                    self.assertEqual(actual, expected)
            state = state.turn(rng.randrange(8))

    def test_split_or_flipped_side_pieces_are_unreachable(self):
        split = list(IDENTITY)
        # Red and Orange belong to different two-sticker side pieces.
        split[COLORS.index("Red")], split[COLORS.index("Orange")] = (
            split[COLORS.index("Orange")], split[COLORS.index("Red")])
        flipped = list(IDENTITY)
        # Red/Purple is one intact piece; flipping just that piece is illegal.
        flipped[COLORS.index("Red")], flipped[COLORS.index("Purple")] = (
            flipped[COLORS.index("Purple")], flipped[COLORS.index("Red")])
        for sides in (split, flipped):
            with self.subTest(sides=sides), self.assertRaisesRegex(ValueError, "Unreachable"):
                self.coordinates.encode(State(sides=tuple(sides)))

    def test_impossible_corner_configurations_are_unreachable(self):
        split = list(IDENTITY)
        split[0], split[3] = split[3], split[0]
        mirrored = list(IDENTITY)
        mirrored[0], mirrored[1] = mirrored[1], mirrored[0]
        twisted = (1, 2, 0, *range(3, 12))
        swapped = (*range(3, 6), *range(3), *range(6, 12))
        invalid = [State(corners=tuple(corners)) for corners in (split, mirrored, twisted, swapped)]
        invalid.append(State(spokes=(1, 0, 0, 0)))
        for state in invalid:
            # The JSON shape is valid; coordinate lookup must reject the
            # impossible physical state after its structural validation.
            restored = State.from_dict(state.to_dict())
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, "Unreachable"):
                self.coordinates.encode(restored)


if __name__ == "__main__":
    unittest.main()
