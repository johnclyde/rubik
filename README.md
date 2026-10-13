# Rubik: Skewb Ultimate tools

A solver and algorithm explorer for **Meffert's 12-color Skewb Ultimate**:
the dodecahedron with four core-mounted corners, four free corners, and six
large pieces. Runs on **Python 3.14+**, with no third-party dependencies.

This models the whole puzzle, including large-piece orientation. It is not
a solver for a regular 3×3 cube, Pyraminx, Megaminx, or Gear Cube.

## Start here

Run these commands from the repository directory:

```sh
python3 -m meffert moves
python3 -m meffert apply "U V W' X"
python3 -m meffert solve --scramble "U V W' X"
python3 -m meffert scramble --length 15 --seed 42
```

The solver searches the puzzle state, rather than simply reversing a supplied
scramble. Results are shortest solutions where either a 120° turn or its
inverse costs one turn. Every solution is replayed on **all pieces** before
being printed.

## Know your moves

`U`, `V`, `W`, and `X` name the four original fixed-corner pieces. These are
the existing script's axes, **not** WCA Skewb notation or cube face names.
Follow the color cycles to establish each positive turn:

| Axis | Fixed corner colors / positive cycle | Old digit | Inverse |
| --- | --- | --- | --- |
| U | Red → Orange → Yellow → Red | 0 | U′ / 4 |
| V | Blue → Hot Pink → Dull Pink → Blue | 1 | V′ / 5 |
| W | Green → White → Purple → Green | 2 | W′ / 6 |
| X | Teal → Tan → Light Green → Teal | 3 | X′ / 7 |

Use an apostrophe for an inverse (`U'`). Two turns are also an inverse (`U2`).
Separate named moves with spaces; old digit strings like `0145` still work.
Axis labels stay attached to the original core-mounted pieces. The cycles
define the direction precisely, avoiding viewpoint-dependent “clockwise.”
Your physical puzzle must use the original color scheme, or you must
consistently rename its colors to match.

## Save, inspect, and solve a state

```sh
python3 -m meffert apply "U V W' X" --json > state.json
python3 -m meffert apply --state state.json
python3 -m meffert apply "U'" --state state.json --json > next-state.json
python3 -m meffert solve --state state.json
python3 -m meffert solve --state state.json --json
```

`--state -` reads JSON from standard input. A saved state is also a template
for manual entry from a physical puzzle; there is no camera recognition or
graphical sticker editor yet. The JSON contains three separate parts:

- `sides`: each large-piece sticker's original color → its current home-color
  position. The two pentagonal stickers identify the whole rigid large piece,
  including its orientation; its smaller rhombus stickers move with it.
- `spokes`: orientations of the four fixed corners: `0` is home, `1` is one
  positive axis turn, and `2` is its inverse.
- `corners`: each free-corner sticker's original color → its current home-color
  position. These labels are separate from the large-piece labels.

The maps describe **where a sticker went**, not the color currently visible
in a position. Every color must occur exactly once in each map. Impossible
piece arrangements are rejected before solving. See [the model guide](docs/model.md)
for the corner triples and physical reference layout.

## Find useful maneuvers

Find algorithms that change a few large-piece stickers while restoring every
corner:

```sh
python3 -m meffert maneuvers --limit 10
python3 -m meffert maneuvers --max-changed 4 --limit 3
```

To reproduce the original experiment, restore only the **four fixed spokes**:

```sh
python3 -m meffert maneuvers --preserve spokes --limit 175
```

Free corners may move in that mode. With the default maximum of six changed
side stickers, it finds all 175 nontrivial side transformations meeting that
constraint, with a shortest algorithm for each. The default full-corner mode
returns a sample in side/spoke projection-distance order; it does not promise
the globally shortest set across different targets.

## Search limits and performance

The model has 100,776,960 reachable states. The solver builds lookup tables
for corners and side/spoke projections, then uses their exact distances to
guide a bounded IDA* search. No downloaded database is needed. The original
Perl script examined up to `5 ** 12` candidate sequences.

Lookup preparation took about **0.8 seconds** on the development machine.
In a 100-scramble check, after preparation, all 30-turn random sequences were
solved in under 0.02 seconds each (8–12 solution turns). These are sample
measurements, not a guarantee for every machine or state.

```sh
python3 -m meffert solve --state state.json --timeout 30 --max-nodes 10000000
```

Defaults: 10 seconds, 2,000,000 search nodes, and 16 solution turns. Lookup
preparation counts toward elapsed time, but completes before the time limit
is checked; timeout is not a hard process deadline. Node budgets exclude
lookup construction. A bound failure exits with status 2 and says the search
is incomplete, rather than calling a state unsolvable. Increasing limits
retries from scratch. `--json` emits successful results and search-limit
errors as JSON; invalid input produces an ordinary error on stderr.
Random scrambles avoid consecutive moves on the same axis; they are not
uniform random states.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q meffert tests
```

Tests check legacy moves, piece integrity, impossible states, exact projection
sizes, shortest solutions against independent shallow breadth first search,
seeded longer scrambles, saved states, and search limits. CI runs on Python 3.14.

`meffert/solve_sides.pl` is retained as the historical color-mapping source;
prefer the new commands for actual use. The unrelated `calendar/` experiment
is preserved. Its package name shadows Python's standard-library `calendar`
when running from this directory; the puzzle tool does not use that module.

Puzzle geometry and sources: [model guide](docs/model.md).
