"""Exact sticker permutations for the twelve-color Skewb Ultimate.

Permutations map each sticker's home position to its current position. The
side moves are the original solve_sides.pl model. Corner moves follow the
same rotations on the Skewb's inscribed cube; see docs/model.md.
"""

from array import array
from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Any, Sequence

COLORS = (
    "Red", "Orange", "Yellow", "Blue", "Hot Pink", "Dull Pink",
    "Green", "White", "Purple", "Teal", "Tan", "Light Green",
)
AXES = ("U", "V", "W", "X")
MOVE_NAMES = AXES + tuple(axis + "'" for axis in AXES)
IDENTITY = tuple(range(12))
FIXED_VECTORS = ((1, 1, 1), (-1, -1, 1), (1, -1, -1), (-1, 1, -1))
FREE_VECTORS = tuple(tuple(-value for value in vector) for vector in FIXED_VECTORS)
SIDE_PAIRS = (("Red", "Purple"), ("Orange", "Light Green"),
              ("Yellow", "Blue"), ("Hot Pink", "Tan"),
              ("Dull Pink", "Green"), ("White", "Teal"))
SIDE_CYCLES = (
    (("Red", "Orange", "Yellow"), ("Purple", "Light Green", "Blue")),
    (("Blue", "Hot Pink", "Dull Pink"), ("Yellow", "Tan", "Green")),
    (("Green", "White", "Purple"), ("Dull Pink", "Teal", "Red")),
    (("Teal", "Tan", "Light Green"), ("Orange", "White", "Hot Pink")),
)


def _cycles_permutation(cycles: Sequence[Sequence[str]]) -> tuple[int, ...]:
    result = list(IDENTITY)
    for cycle in cycles:
        for source, destination in zip(cycle, (*cycle[1:], cycle[0])):
            result[COLORS.index(source)] = COLORS.index(destination)
    return tuple(result)


def compose(state: Sequence[int], move: Sequence[int]) -> tuple[int, ...]:
    return tuple(move[position] for position in state)


def _with_inverses(moves: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return moves + tuple(compose(move, move) for move in moves)


SIDE_MOVES = _with_inverses(tuple(_cycles_permutation(cycles) for cycles in SIDE_CYCLES))


def rotate(vector: Sequence[int], axis: Sequence[int]) -> tuple[int, int, int]:
    """Right-handed 120-degree rotation about a tetrahedral diagonal."""
    x, y, z = vector
    a, b, c = axis
    return a * c * z, b * a * x, c * b * y


def _free_move(axis: tuple[int, ...]) -> tuple[int, ...]:
    result = list(IDENTITY)
    for corner, vector in enumerate(FREE_VECTORS):
        if sum(a * b for a, b in zip(vector, axis)) < 0:
            continue
        destination = FREE_VECTORS.index(rotate(vector, axis))
        for normal_axis in range(3):
            normal = tuple(vector[i] if i == normal_axis else 0 for i in range(3))
            rotated = rotate(normal, axis)
            new_axis = next(i for i, value in enumerate(rotated) if value)
            result[corner * 3 + normal_axis] = destination * 3 + new_axis
    return tuple(result)


# Slots are free corners opposite U/V/W/X, with x/y/z sticker normals.
FREE_MOVES = _with_inverses(tuple(_free_move(axis) for axis in FIXED_VECTORS))
FREE_SLOTS = ("Hot Pink", "Green", "Teal", "Red", "Light Green", "White",
              "Tan", "Orange", "Blue", "Purple", "Dull Pink", "Yellow")


def parse_moves(algorithm: str) -> tuple[int, ...]:
    """Accept U V W X, prime/2 suffixes, and legacy digits 0..7.

    Two 120-degree turns equal an inverse. Compact digit strings retain the
    old script's notation. Named moves must be separated by whitespace.
    """
    if not isinstance(algorithm, str):
        raise ValueError("An algorithm must be text.")
    tokens = algorithm.replace("\u2019", "'").split()
    result: list[int] = []
    for token in tokens:
        if re.fullmatch(r"[0-7]+", token):
            result.extend(int(digit) for digit in token)
            continue
        match = re.fullmatch(r"([UVWXuvwx])(['2]?)", token)
        if not match:
            raise ValueError(f"Invalid move {token!r}; use U V W X, primes, or digits 0..7.")
        result.append(AXES.index(match[1].upper()) + (4 if match[2] else 0))
    return tuple(result)


def format_moves(moves: Sequence[int], *, legacy: bool = False) -> str:
    return "".join(str(move) for move in moves) if legacy else " ".join(MOVE_NAMES[move] for move in moves)


def inverse(moves: Sequence[int]) -> tuple[int, ...]:
    return tuple((move + 4) % 8 for move in reversed(moves))


@dataclass(frozen=True)
class State:
    sides: tuple[int, ...] = IDENTITY
    spokes: tuple[int, ...] = (0, 0, 0, 0)
    corners: tuple[int, ...] = IDENTITY

    def turn(self, move: int) -> "State":
        if type(move) is not int or not 0 <= move < 8:
            raise ValueError("Move must be an integer from 0 through 7.")
        spokes = list(self.spokes)
        spokes[move % 4] = (spokes[move % 4] + (1 if move < 4 else 2)) % 3
        return State(compose(self.sides, SIDE_MOVES[move]), tuple(spokes),
                     compose(self.corners, FREE_MOVES[move]))

    def apply(self, moves: Sequence[int]) -> "State":
        state = self
        for move in moves:
            state = state.turn(move)
        return state

    def to_dict(self) -> dict[str, Any]:
        return {
            "puzzle": "skewb-ultimate", "version": 1,
            "sides": {color: COLORS[self.sides[i]] for i, color in enumerate(COLORS)},
            "spokes": dict(zip(AXES, self.spokes)),
            "corners": {slot: FREE_SLOTS[self.corners[i]] for i, slot in enumerate(FREE_SLOTS)},
        }

    @classmethod
    def from_dict(cls, value: Any) -> "State":
        if not isinstance(value, dict) or value.get("puzzle") != "skewb-ultimate":
            raise ValueError("Expected a Skewb Ultimate state object.")
        if type(value.get("version")) is not int or value["version"] != 1:
            raise ValueError("Unsupported state version; expected 1.")
        if set(value) != {"puzzle", "version", "sides", "spokes", "corners"}:
            raise ValueError("State must contain puzzle, version, sides, spokes, and corners only.")

        def permutation(field: str, names: tuple[str, ...]) -> tuple[int, ...]:
            data = value[field]
            if (not isinstance(data, dict) or set(data) != set(names)
                    or any(not isinstance(item, str) for item in data.values())
                    or set(data.values()) != set(names)):
                raise ValueError(f"{field} must map every named sticker to a unique named position.")
            return tuple(names.index(data[name]) for name in names)

        spokes = value["spokes"]
        if (not isinstance(spokes, dict) or set(spokes) != set(AXES)
                or any(type(v) is not int or v not in (0, 1, 2) for v in spokes.values())):
            raise ValueError("spokes must give U, V, W, X orientations as integers 0, 1, or 2.")
        return cls(permutation("sides", COLORS), tuple(spokes[axis] for axis in AXES),
                   permutation("corners", FREE_SLOTS))


@dataclass
class Coordinates:
    side_states: list[bytes]
    side_ids: dict[bytes, int]
    side_transitions: array
    corner_states: list[bytes]
    corner_ids: dict[bytes, int]
    corner_transitions: array
    corner_spokes: array

    def encode(self, state: State) -> tuple[int, int]:
        try:
            side = self.side_ids[bytes(state.sides)]
            corner = self.corner_ids[bytes((*state.spokes, *state.corners))]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Unreachable state: a piece is split, flipped, or twisted illegally.") from exc
        return side, corner


@lru_cache(maxsize=1)
def build_coordinates() -> Coordinates:
    """Enumerate independent side and corner orbits, never the full puzzle."""
    side_states = [bytes(IDENTITY)]
    side_ids = {side_states[0]: 0}
    side_transitions = array("I")
    for state in side_states:
        for move in SIDE_MOVES:
            child = bytes(move[position] for position in state)
            if child not in side_ids:
                side_ids[child] = len(side_states)
                side_states.append(child)
            side_transitions.append(side_ids[child])

    corner_states = [bytes((0, 0, 0, 0, *IDENTITY))]
    corner_ids = {corner_states[0]: 0}
    corner_transitions = array("I")
    corner_spokes = array("B")
    for state in corner_states:
        corner_spokes.append(sum(state[i] * 3 ** i for i in range(4)))
        for move in range(8):
            spokes = list(state[:4])
            spokes[move % 4] = (spokes[move % 4] + (1 if move < 4 else 2)) % 3
            child = bytes((*spokes, *(FREE_MOVES[move][position] for position in state[4:])))
            if child not in corner_ids:
                corner_ids[child] = len(corner_states)
                corner_states.append(child)
            corner_transitions.append(corner_ids[child])
    return Coordinates(side_states, side_ids, side_transitions, corner_states,
                       corner_ids, corner_transitions, corner_spokes)
