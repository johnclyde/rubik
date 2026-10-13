"""Exact projection tables and a bounded, shortest-path puzzle search.

Every move costs one turn, including the inverse of a 120-degree turn.  Moves
0..3 turn the four axes clockwise; moves 4..7 are their respective inverses.
The coordinate tables, and therefore the physical model, live outside this
module.  This module uses only the Python standard library.
"""

from array import array
from dataclasses import dataclass, field
from math import isfinite
from time import monotonic
from typing import Sequence


UNKNOWN = 255
NO_PARENT = 0xFFFFFFFF
SPOKE_COUNT = 81
MOVE_COUNT = 8


def _spoke_moves() -> tuple[tuple[int, ...], ...]:
    rows = []
    for orientation in range(SPOKE_COUNT):
        row = []
        for direction in (1, -1):
            for axis in range(4):
                place = 3 ** axis
                old = orientation // place % 3
                row.append(orientation + ((old + direction) % 3 - old) * place)
        rows.append(tuple(row))
    return tuple(rows)


SPOKE_MOVES = _spoke_moves()


@dataclass
class SearchTables:
    """Flat transition tables with the solved state at coordinate zero.

    ``corner_spokes[corner_id]`` encodes the four fixed-corner orientations in
    base three, with axis zero as the least significant digit.  Projection
    distances are computed once and retained for subsequent searches.
    """

    side_transitions: Sequence[int]
    corner_transitions: Sequence[int]
    corner_spokes: Sequence[int]
    side_spoke_distances: bytearray | None = field(default=None, init=False)
    corner_distances: bytearray | None = field(default=None, init=False)
    side_spoke_parents: array | None = field(default=None, init=False)
    side_spoke_moves: bytearray | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not self.side_transitions or len(self.side_transitions) % MOVE_COUNT:
            raise ValueError("side transitions must contain eight moves per state")
        if not self.corner_transitions or len(self.corner_transitions) % MOVE_COUNT:
            raise ValueError("corner transitions must contain eight moves per state")
        if len(self.corner_spokes) != self.corner_count:
            raise ValueError("one spoke orientation is required per corner state")
        if self.corner_spokes[0] != 0:
            raise ValueError("corner coordinate zero must have solved spokes")
        if any(not 0 <= x < self.side_count for x in self.side_transitions):
            raise ValueError("invalid side transition coordinate")
        if any(not 0 <= x < self.corner_count for x in self.corner_transitions):
            raise ValueError("invalid corner transition coordinate")
        if any(not 0 <= x < SPOKE_COUNT for x in self.corner_spokes):
            raise ValueError("invalid spoke orientation coordinate")
        for corner, spoke in enumerate(self.corner_spokes):
            for move in range(MOVE_COUNT):
                next_corner = self.corner_transitions[corner * MOVE_COUNT + move]
                if self.corner_spokes[next_corner] != SPOKE_MOVES[spoke][move]:
                    raise ValueError("corner transitions disagree with spoke orientations")

    @property
    def side_count(self) -> int:
        return len(self.side_transitions) // MOVE_COUNT

    @property
    def corner_count(self) -> int:
        return len(self.corner_transitions) // MOVE_COUNT

    def prepare(self, *, paths: bool = False) -> None:
        """Compute admissible distances, optionally retaining projection paths."""
        if self.side_spoke_distances is None or (
            paths and self.side_spoke_parents is None
        ):
            self._build_side_spoke(paths=paths)
        if self.corner_distances is None:
            distances = bytearray([UNKNOWN]) * self.corner_count
            distances[0] = 0
            queue = array("I", [0])
            transitions = self.corner_transitions
            for state in queue:
                following_depth = distances[state] + 1
                offset = state * MOVE_COUNT
                for move in range(MOVE_COUNT):
                    following = transitions[offset + move]
                    if distances[following] == UNKNOWN:
                        distances[following] = following_depth
                        queue.append(following)
            self.corner_distances = distances

    def _build_side_spoke(self, *, paths: bool) -> None:
        count = self.side_count * SPOKE_COUNT
        distances = bytearray([UNKNOWN]) * count
        distances[0] = 0
        parents = array("I", [NO_PARENT]) * count if paths else None
        moves = bytearray(count) if paths else None
        if parents is not None:
            parents[0] = 0
        queue = array("I", [0])
        transitions = self.side_transitions
        for state in queue:
            side, spoke = divmod(state, SPOKE_COUNT)
            offset = side * MOVE_COUNT
            following_depth = distances[state] + 1
            for move, next_spoke in enumerate(SPOKE_MOVES[spoke]):
                following = transitions[offset + move] * SPOKE_COUNT + next_spoke
                if distances[following] == UNKNOWN:
                    distances[following] = following_depth
                    queue.append(following)
                    if parents is not None and moves is not None:
                        parents[following] = state
                        moves[following] = move
        self.side_spoke_distances = distances
        self.side_spoke_parents = parents
        self.side_spoke_moves = moves

    def projection_path(self, side: int, spoke: int = 0) -> tuple[int, ...]:
        """Return a shortest path from solved to this side/spoke projection."""
        if not 0 <= side < self.side_count or not 0 <= spoke < SPOKE_COUNT:
            raise ValueError("projection coordinate is out of range")
        self.prepare(paths=True)
        assert self.side_spoke_parents is not None
        assert self.side_spoke_moves is not None
        state = side * SPOKE_COUNT + spoke
        if self.side_spoke_parents[state] == NO_PARENT:
            raise ValueError("side/spoke projection is unreachable")
        result = []
        while state:
            result.append(self.side_spoke_moves[state])
            state = self.side_spoke_parents[state]
        return tuple(reversed(result))


@dataclass(frozen=True)
class SearchResult:
    moves: tuple[int, ...]
    nodes: int
    elapsed: float


class SearchLimitError(RuntimeError):
    """A bound stopped an incomplete search; it is not proof of impossibility."""

    def __init__(self, reason: str, *, nodes: int, elapsed: float, lower_bound: int):
        self.reason = reason
        self.nodes = nodes
        self.elapsed = elapsed
        self.lower_bound = lower_bound
        super().__init__(
            f"{reason}; searched {nodes:,} nodes in {elapsed:.2f}s "
            f"(solution needs at least {lower_bound} turns)"
        )


def invert(moves: Sequence[int]) -> tuple[int, ...]:
    return tuple((move + 4) % MOVE_COUNT for move in reversed(moves))


def solve(
    tables: SearchTables,
    side: int,
    corner: int,
    *,
    max_depth: int = 16,
    max_nodes: int = 2_000_000,
    timeout: float = 10.0,
) -> SearchResult:
    """Find a shortest solution with IDA*, or explicitly report a search limit.

    The maximum of two exact projection distances is an admissible heuristic.
    Consecutive turns about one axis are redundant in a shortest solution.
    Transposition entries include the preceding axis so that this pruning does
    not accidentally discard a path with different allowed next moves.
    """
    if not 0 <= side < tables.side_count or not 0 <= corner < tables.corner_count:
        raise ValueError("puzzle coordinate is out of range")
    if max_depth < 0 or max_nodes < 1 or not isfinite(timeout) or timeout <= 0:
        raise ValueError("depth must be nonnegative; node and time limits must be positive")
    started = monotonic()
    if side == 0 and corner == 0:
        return SearchResult((), 0, monotonic() - started)
    tables.prepare()
    side_distance = tables.side_spoke_distances
    corner_distance = tables.corner_distances
    assert side_distance is not None and corner_distance is not None
    spokes = tables.corner_spokes
    side_moves = tables.side_transitions
    corner_moves = tables.corner_transitions
    corner_count = tables.corner_count
    initial_bound = max(
        side_distance[side * SPOKE_COUNT + spokes[corner]], corner_distance[corner]
    )
    if initial_bound == UNKNOWN:
        raise ValueError("puzzle has an unreachable projection")
    nodes = 0
    bound = initial_bound
    path: list[int] = []
    seen: dict[int, int] = {}
    found = -1
    infinity = 10 ** 9

    def limited(reason: str) -> SearchLimitError:
        return SearchLimitError(
            reason, nodes=nodes, elapsed=monotonic() - started, lower_bound=bound
        )

    def visit(current_side: int, current_corner: int, depth: int, last_axis: int) -> int:
        nonlocal nodes
        if nodes >= max_nodes:
            raise limited("node limit reached")
        nodes += 1
        if nodes == 1 or nodes % 1024 == 0:
            if monotonic() - started >= timeout:
                raise limited("time limit reached")
        heuristic = max(
            side_distance[current_side * SPOKE_COUNT + spokes[current_corner]],
            corner_distance[current_corner],
        )
        estimate = depth + heuristic
        if estimate > bound:
            return estimate
        if current_side == 0 and current_corner == 0:
            return found
        key = (current_side * corner_count + current_corner) * 5 + last_axis + 1
        remaining = bound - depth
        if seen.get(key, -1) >= remaining:
            return infinity
        # Keep search memory bounded; dropping old entries only costs speed.
        if len(seen) < 500_000:
            seen[key] = remaining
        minimum = infinity
        side_offset = current_side * MOVE_COUNT
        corner_offset = current_corner * MOVE_COUNT
        for move in range(MOVE_COUNT):
            axis = move % 4
            if axis == last_axis:
                continue
            path.append(move)
            result = visit(
                side_moves[side_offset + move],
                corner_moves[corner_offset + move],
                depth + 1,
                axis,
            )
            if result == found:
                return found
            path.pop()
            minimum = min(minimum, result)
        return minimum

    while bound <= max_depth:
        seen.clear()
        following_bound = visit(side, corner, 0, -1)
        if following_bound == found:
            return SearchResult(tuple(path), nodes, monotonic() - started)
        if following_bound == infinity:
            raise ValueError("puzzle coordinates do not describe a reachable state")
        bound = following_bound
    raise limited(f"depth limit of {max_depth} reached")


@dataclass(frozen=True)
class Maneuver:
    side: int
    moves: tuple[int, ...]
    changed_colors: int
    preserves_all_corners: bool


def find_maneuvers(
    tables: SearchTables,
    side_changes: Sequence[int],
    *,
    max_changed: int = 6,
    preserve_all_corners: bool = True,
    limit: int = 10,
    max_depth: int = 16,
    max_nodes: int = 2_000_000,
    timeout: float = 10.0,
) -> tuple[Maneuver, ...]:
    """Find shortest algorithms for selected small side permutations.

    Fixed-spoke mode exhaustively considers the historical script's targets.
    Full-corner mode searches those targets in projection-distance order under
    a shared time/node budget.  A limit raises ``SearchLimitError`` rather than
    presenting an incomplete enumeration as a complete one.  The returned
    sample is not claimed to be the globally shortest set across targets.
    """
    if len(side_changes) != tables.side_count:
        raise ValueError("one change count is required per side coordinate")
    if max_changed < 1 or limit < 1:
        raise ValueError("change and result limits must be positive")
    if max_depth < 0 or max_nodes < 1 or not isfinite(timeout) or timeout <= 0:
        raise ValueError("depth must be nonnegative; node and time limits must be positive")
    started = monotonic()
    tables.prepare(paths=not preserve_all_corners)
    assert tables.side_spoke_distances is not None
    distances = tables.side_spoke_distances
    candidates = sorted(
        (side for side, changed in enumerate(side_changes)
         if 0 < changed <= max_changed and distances[side * SPOKE_COUNT] != UNKNOWN),
        key=lambda side: (distances[side * SPOKE_COUNT], side),
    )
    results = []
    nodes = 0
    for side in candidates:
        remaining_time = timeout - (monotonic() - started)
        if remaining_time <= 0 or nodes >= max_nodes:
            raise SearchLimitError(
                "maneuver search budget reached", nodes=nodes,
                elapsed=monotonic() - started,
                lower_bound=distances[side * SPOKE_COUNT],
            )
        if preserve_all_corners:
            try:
                result = solve(
                    tables, side, 0, max_depth=max_depth,
                    max_nodes=max_nodes - nodes, timeout=remaining_time,
                )
            except SearchLimitError as error:
                raise SearchLimitError(
                    error.reason, nodes=nodes + error.nodes,
                    elapsed=monotonic() - started, lower_bound=error.lower_bound,
                ) from error
            nodes += result.nodes
            moves = invert(result.moves)
        else:
            distance = distances[side * SPOKE_COUNT]
            if distance > max_depth:
                raise SearchLimitError(
                    f"depth limit of {max_depth} reached", nodes=nodes,
                    elapsed=monotonic() - started, lower_bound=distance,
                )
            # A cached projection path visits exactly distance + 1 nodes.
            # As in solve(), the node budget excludes building shared tables.
            if nodes + distance + 1 > max_nodes:
                raise SearchLimitError(
                    "node limit reached", nodes=nodes,
                    elapsed=monotonic() - started, lower_bound=distance,
                )
            moves = tables.projection_path(side)
            nodes += distance + 1
        results.append(Maneuver(side, moves, side_changes[side], preserve_all_corners))
        if len(results) >= limit:
            break
    return tuple(results)
