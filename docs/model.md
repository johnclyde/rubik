# Skewb Ultimate model

The puzzle described in `meffert/solve_sides.pl` is the **twelve-color Skewb
Ultimate**: a dodecahedron with four corners attached to a tetrahedral core,
four free corners, and six large four-color pieces. The original script calls
the attached corners “spokes” and the large pieces “sides.” We retain those
terms to keep its algorithms and color scheme recognizable.

The four attached corners can turn in place. The four free corners move
between the remaining corner positions and can also change orientation. They
are the pieces sometimes described informally as “false centers.” Each large
piece has two large pentagonal stickers and two smaller rhombic stickers.
Tracking its two pentagonal stickers determines its position and orientation;
the rhombic stickers move with that same rigid piece.

This is the Skewb mechanism extended into a dodecahedron. Unlike an ordinary
Skewb, the orientations of the six large pieces are visible and must be solved.
The model therefore cannot discard those orientations or use an ordinary
Skewb solved-state check.

## State and move conventions

All sticker permutations map **a sticker's home position to its current
position**. A serialized entry such as `"Red": "Orange"` means that the
sticker which belongs in the Red position is currently in the Orange
position. It does not mean that Orange is the sticker currently occupying
the Red position.

There are three state components:

- `sides`: the twelve pentagonal stickers, using the original script's colors.
- `spokes`: four orientation counters, `U`, `V`, `W`, and `X`, modulo three.
- `corners`: the twelve stickers on the four free corners, again using their
  solved color names as position labels.

The same color appears in multiple components. A Red side sticker and a Red
free-corner sticker are distinct stickers and occupy distinct positions.

`U V W X` correspond exactly to the original script's `u v w x`, or legacy
digits `0 1 2 3`. Their inverses are `U' V' W' X'`, or `4 5 6 7`. Two turns
about the same axis equal its inverse, so `U2` means `U'`. Three equal turns
are the identity.

The original script calls the base turns “clockwise.” In the coordinates
below they are right-handed **positive 120-degree rotations about the outward
axis**. Apparent clockwise direction depends on which end of that axis the
viewer looks from. In particular, looking toward the center from the outward
end makes a positive turn appear counterclockwise. The color cycles, not that
informal viewing label, define compatibility with the old script.

These `U V W X` names identify this repository's four colored spokes. They are
not an assertion of the World Cube Association's ordinary Skewb notation.

## An inscribed cube fixes the geometry

Embed a cube in the dodecahedron. Its eight vertices are the eight corner
positions. Use these vectors for the core-attached corners:

| Spoke | Vector | Solved colors, in base-turn order |
| --- | --- | --- |
| U | `(1, 1, 1)` | Red → Orange → Yellow |
| V | `(-1, -1, 1)` | Blue → Hot Pink → Dull Pink |
| W | `(1, -1, -1)` | Green → White → Purple |
| X | `(-1, 1, -1)` | Light Green → Teal → Tan |

The free corners occupy the negatives of these four vectors. The large pieces
occupy the six face centers of the inscribed cube:

| Cube face | The two pentagonal stickers on one large piece |
| --- | --- |
| `+x` | Red / Purple |
| `+y` | Orange / Light Green |
| `+z` | Yellow / Blue |
| `-x` | Hot Pink / Tan |
| `-y` | Dull Pink / Green |
| `-z` | White / Teal |

These pairs are also recoverable directly from the original twelve-sticker
permutations: every move carries each pair to another complete pair.

For a turn around outward axis `a`, rotate positions in the half-space
`dot(a, position) > 0`. This turns the attached corner on that axis, three
free corners, and three large pieces. The other attached corners and the
free corner opposite the axis remain in place. Rotate sticker normals along
with their positions.

For these four axes, write `a = (a, b, c)`. The positive 120-degree rotation
has this exact integer formula:

```text
rotate((x, y, z), (a, b, c)) = (a*c*z, b*a*x, c*b*y)
```

It is Rodrigues' rotation formula specialized to the four unit-sign vectors
with `a*b*c = 1`. It applies to both position vectors and normals. There is
no rounding step or floating-point state in the model.

## Deriving the free-corner colors

The free-corner colors are derived from the same dodecahedral geometry,
rather than assigned arbitrarily. Let `φ = (1 + sqrt(5)) / 2`. The face normals
below give the unique color scheme consistent with the chosen embedding and
the original spoke and side labels:

| Color | Dodecahedron face normal |
| --- | --- |
| Red | `(φ, 1, 0)` |
| Orange | `(0, φ, 1)` |
| Yellow | `(1, 0, φ)` |
| Blue | `(-1, 0, φ)` |
| Hot Pink | `(-φ, -1, 0)` |
| Dull Pink | `(0, -φ, 1)` |
| Green | `(0, -φ, -1)` |
| White | `(1, 0, -φ)` |
| Purple | `(φ, -1, 0)` |
| Teal | `(-1, 0, -φ)` |
| Tan | `(-φ, 1, 0)` |
| Light Green | `(0, φ, -1)` |

A face meets cube corner `p` exactly when `dot(normal, p) = φ + 1`. Applying
that rule to the fixed vectors produces the original spoke triples; applying
it to their negatives gives the free corners:

| Free position | Vector | x-normal slot | y-normal slot | z-normal slot |
| --- | --- | --- | --- | --- |
| Opposite U | `(-1, -1, -1)` | Hot Pink | Green | Teal |
| Opposite V | `(1, 1, -1)` | Red | Light Green | White |
| Opposite W | `(-1, 1, 1)` | Tan | Orange | Blue |
| Opposite X | `(1, -1, 1)` | Purple | Dull Pink | Yellow |

The slot columns refer to the corresponding inscribed-cube sticker normals,
with their sign taken from the corner vector. For example, Hot Pink at
opposite U uses `(-1, 0, 0)`. A dodecahedral normal has the same dominant
coordinate as its cube sticker normal. The signed-coordinate rotation above
permutes these normal axes exactly, so the cube model produces the same
sticker transitions without storing `φ`.

`FREE_SLOTS` uses row order from this table, with x, y, z within each row.
This order is an indexing convention, not a universal corner-twist convention.
Do not reinterpret arbitrary changes to a corner's three indices as legal
rotations: cyclic orientation, piece integrity, and reachability all matter.
Other six-color or twelve-color commercial sticker schemes may require an
explicit relabeling before importing a physical puzzle state.

## Reproducible free-sticker transitions

Each parenthesized triple is a cycle from source position to destination
position. For example, `(Red Orange Yellow)` sends Red to Orange, Orange to
Yellow, and Yellow to Red. Colors omitted from a move remain fixed.

```text
U: (Red Orange Yellow)
   (White Tan Dull Pink)
   (Light Green Blue Purple)

V: (Hot Pink Dull Pink Blue)
   (Green Yellow Tan)
   (Teal Purple Orange)

W: (Hot Pink Light Green Yellow)
   (Green White Purple)
   (Teal Red Dull Pink)

X: (Hot Pink Orange White)
   (Green Blue Red)
   (Teal Tan Light Green)
```

Rotate the full dodecahedron normals above at each affected free-corner
position to recover these cycles independently. The free position opposite
the turning axis stays fixed; the other three positions cycle. A move also
increments only its own spoke counter modulo three. The side transitions are
the original Perl tables without modification.

## Reachability and independent validation

The complete generated state space contains **100,776,960 states**:

| Projection | Reachable states |
| --- | ---: |
| Six oriented large pieces | 11,520 |
| Four spoke orientations plus four oriented free corners | 8,748 |
| Complete puzzle | 100,776,960 |

The side count is `6!/2 × 2^5`: the piece permutation is even and the number
of flipped pieces is even. The combined corner count is `4!/2 × 3^6`.
Corner constraints couple the fixed and free pieces, so counting their
permutations and orientations independently would overcount.

The full count equals `11,520 × 8,748`. There is no further compatibility
constraint between these two projections. Checking membership in both
generated orbits therefore validates a complete state, including piece
integrity, parity, and orientation constraints. This statement concerns the
combined corner projection; the four spoke counters and free corners are
not independent of one another.

The implementation was cross-checked using an independent construction:

1. Apply Rodrigues' formula at 120 degrees to the golden-ratio face normals.
   All four geometric side moves reproduce both cycles in each original Perl
   move table. The free moves reproduce the cycles listed above.
2. Represent the fixed corners as twelve explicit stickers instead of four
   counters. Combine these with twelve free stickers, and enumerate the
   generated corner orbit by breadth-first search: 8,748 permutations.
3. Enumerate the twelve-side-sticker orbit separately: 11,520 permutations.
4. Place fixed, free, and side permutations on three disjoint blocks of twelve
   labels. A SymPy `PermutationGroup` order calculation on the four resulting
   generators gives 100,776,960, independently confirming the product and
   matching the published Skewb Ultimate count.

This verification does not require a physical puzzle or enumerating all
100 million combined states. Useful regression checks include each move
cubed being identity, move/inverse cancellation, preservation of complete
pieces, the published orbit sizes, the independent free-sticker cycles, and
replay of every returned solution against the entire state.

## What the original script did and did not model

`solve_sides.pl` describes the correct large-piece projection. Its search
requires each spoke turn to occur a multiple of three times, restoring the
four attached corners. That condition does **not** restore the four free
corners: they can remain moved or twisted. A useful side maneuver can
therefore still disturb part of the real puzzle.

The original output was a bounded collection of side maneuvers, not a full
puzzle solver or a proof of shortest solutions. Its twelve-base-turn search
bound and subsequent notation shortening did not search all algorithms of a
given final length. The full model adds the omitted free-corner state while
preserving the original side mappings and legacy move notation.

## Sources

- [Meffert's original Skewb Ultimate solution booklet, archived by James
  Storer](https://www.cs.brandeis.edu/~storer/JimPuzzles/RUBIK/SkewbUltimate/SkewbUltimateSolutionMeffert.pdf):
  manufacturer identification, piece types, four axes, and 120-degree turns.
  The booklet's six-color examples are not the repository's twelve-color
  sticker scheme.
- [Jaap Scherphuis: Ultimate Skewb / Puzzleball](https://www.jaapsch.net/puzzles/ultimate.htm):
  cube-in-dodecahedron construction, fixed/free corner distinction, visible
  orientations, legal-state constraints, and the 100,776,960-state count.
  Scherphuis is also a coauthor of the manufacturer's solution booklet.
- [Jaap Scherphuis: Ideas for further puzzles](https://www.jaapsch.net/puzzles/ideas.htm):
  the four-armed Skewb mechanism and its dodecahedral Ultimate Skewb variant.
- [Meffert's current manufacturer site](https://www.mefferts.com/): identifies
  a Skewb Ultimate twelve-color product.

The coordinate assignments, color-normal correspondence, and independently
computed transitions above are a derivation from the original repository's
move tables and that geometry. They are not a claim that the manufacturer
publishes this particular coordinate convention.
