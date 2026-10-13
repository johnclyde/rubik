"""Command-line interface; run with python3 -m meffert."""

import argparse
import json
import math
from pathlib import Path
import random
import sys
from typing import Sequence

from .model import (
    AXES, COLORS, FREE_SLOTS, IDENTITY, SIDE_CYCLES, State, build_coordinates,
    format_moves, parse_moves,
)
from .search import SearchLimitError, SearchTables, find_maneuvers, solve


def _positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def _positive_time(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return result


def _limits(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-depth", type=_positive_int, default=16,
                        help="maximum solution length (default: 16)")
    parser.add_argument("--max-nodes", type=_positive_int, default=2_000_000,
                        help="search node budget (default: 2000000)")
    parser.add_argument("--timeout", type=_positive_time, default=10.0,
                        help="time budget in seconds (default: 10)")


def _input(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--scramble", help="algorithm applied to the solved puzzle")
    group.add_argument("--state", type=Path, help="saved JSON state; use - for stdin")


def _state(args: argparse.Namespace) -> State:
    if getattr(args, "state", None) is not None:
        contents = sys.stdin.read() if str(args.state) == "-" else args.state.read_text(encoding="utf-8")
        return State.from_dict(json.loads(contents))
    return State().apply(parse_moves(getattr(args, "scramble", "") or ""))


def _print_state(state: State) -> None:
    print("Skewb Ultimate — solved" if state == State() else "Skewb Ultimate — unsolved")
    print("Fixed corners: " + ", ".join(f"{axis}={twist}" for axis, twist in zip(AXES, state.spokes)))
    for title, labels, positions in (("Large pieces", COLORS, state.sides),
                                      ("Free corners", FREE_SLOTS, state.corners)):
        changes = [f"{label} → {labels[positions[i]]}" for i, label in enumerate(labels) if positions[i] != i]
        print(f"{title}: " + ("; ".join(changes) if changes else "solved"))


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m meffert",
        description="Model and solve the twelve-color Meffert's Skewb Ultimate.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("moves", help="show the four axes and move notation")

    apply_parser = commands.add_parser("apply", help="apply moves and inspect or save a state")
    apply_parser.add_argument("algorithm", nargs="?", default="", help="e.g. \"U V W' X\" or 0127")
    apply_parser.add_argument("--state", type=Path, help="start from saved JSON (or - for stdin)")
    apply_parser.add_argument("--json", action="store_true", help="emit a reusable JSON state")

    solve_parser = commands.add_parser("solve", help="find a shortest solution for all pieces")
    _input(solve_parser, required=True)
    _limits(solve_parser)
    solve_parser.add_argument("--json", action="store_true", help="emit a JSON result")

    scramble_parser = commands.add_parser("scramble", help="generate a random move sequence")
    scramble_parser.add_argument("--length", type=_positive_int, default=15)
    scramble_parser.add_argument("--seed", type=int, help="reproduce a sequence")

    maneuver_parser = commands.add_parser("maneuvers", help="find algorithms moving a few large-piece stickers")
    maneuver_parser.add_argument("--preserve", choices=("corners", "spokes"), default="corners",
                                 help="preserve all corners, or just the four fixed spokes")
    maneuver_parser.add_argument("--max-changed", type=int, choices=range(1, 13), default=6,
                                 help="maximum changed large-piece stickers (default: 6)")
    maneuver_parser.add_argument("--limit", type=_positive_int, default=10)
    maneuver_parser.add_argument("--json", action="store_true")
    _limits(maneuver_parser)

    args = parser.parse_args(argv)
    try:
        if args.command == "moves":
            print("Skewb Ultimate: four axes, 120° per turn.")
            print("Track the original fixed corner pieces; axis names travel with the core.")
            for i, (axis, cycles) in enumerate(zip(AXES, SIDE_CYCLES)):
                print(f"  {axis} ({i}): " + " → ".join((*cycles[0], cycles[0][0])))
            print("A prime reverses a turn: U' = U2 = 4; V'=5, W'=6, X'=7.")
            print("Named moves need spaces. Legacy digit strings such as 0145 also work.")
            print("Directions follow these color cycles; avoid relying on a viewpoint's 'clockwise'.")
            return 0

        if args.command == "scramble":
            rng = random.Random(args.seed)
            moves: list[int] = []
            for _ in range(args.length):
                candidates = [move for move in range(8) if not moves or move % 4 != moves[-1] % 4]
                moves.append(rng.choice(candidates))
            print(format_moves(moves))
            return 0

        if args.command == "apply":
            state = _state(args).apply(parse_moves(args.algorithm))
            build_coordinates().encode(state)
            _json(state.to_dict()) if args.json else _print_state(state)
            return 0

        coordinates = build_coordinates()
        tables = SearchTables(coordinates.side_transitions, coordinates.corner_transitions,
                              coordinates.corner_spokes)
        limits = {"max_depth": args.max_depth, "max_nodes": args.max_nodes, "timeout": args.timeout}
        if args.command == "solve":
            state = _state(args)
            result = solve(tables, *coordinates.encode(state), **limits)
            if state.apply(result.moves) != State():
                raise RuntimeError("Internal error: solution failed playback verification.")
            if args.json:
                _json({"algorithm": format_moves(result.moves), "legacy": format_moves(result.moves, legacy=True),
                       "turns": len(result.moves), "optimal": True, "nodes": result.nodes,
                       "elapsed_seconds": round(result.elapsed, 4)})
            else:
                print(format_moves(result.moves) if result.moves else "Already solved.")
                print(f"{len(result.moves)} turns · shortest solution · all pieces verified")
            return 0

        changes = [sum(home != destination for home, destination in enumerate(state))
                   for state in coordinates.side_states]
        maneuvers = find_maneuvers(tables, changes, max_changed=args.max_changed,
                                  preserve_all_corners=args.preserve == "corners",
                                  limit=args.limit, **limits)
        records = []
        for maneuver in maneuvers:
            state = State().apply(maneuver.moves)
            if (state.spokes != (0, 0, 0, 0)
                    or (args.preserve == "corners" and state.corners != IDENTITY)):
                raise RuntimeError("Internal error: maneuver failed playback verification.")
            records.append({"algorithm": format_moves(maneuver.moves),
                            "legacy": format_moves(maneuver.moves, legacy=True),
                            "turns": len(maneuver.moves), "preserves": args.preserve,
                            "changes": {COLORS[i]: COLORS[position] for i, position in enumerate(state.sides)
                                        if i != position}})
        if args.json:
            _json(records)
        else:
            print("Preserves all eight corners." if args.preserve == "corners"
                  else "Preserves the four fixed spokes; free corners may move.")
            for record in records:
                print(f"{record['algorithm']} ({record['turns']} turns)")
                print("  " + "; ".join(f"{source} → {destination}" for source, destination in record["changes"].items()))
            if not records:
                print("No nontrivial maneuvers match the requested sticker count.")
        return 0
    except SearchLimitError as exc:
        if getattr(args, "json", False):
            _json({"error": "search_limit", "reason": exc.reason, "nodes": exc.nodes,
                   "lower_bound": exc.lower_bound, "elapsed_seconds": round(exc.elapsed, 4)})
        else:
            print(f"Search incomplete: {exc}. Increase the search limits to continue.", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
