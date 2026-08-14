"""Ashmouth — world constants and the hand-authored control geometry.

Everything here is metres, three.js convention: X east, Z south (so north is −Z),
Y up. Origin (0, 0) is the crossroads of Harbour Street and Ash Street.

The landmass outlines below are *deliberate*. They are hand-placed control points
that get splined and then roughened by noise — the brief's two honest routes to a
coastline, used together: draw the bays, points and channels on purpose, let noise
supply the fractal detail no one would hand-place.
"""

SEED = 20260814

# ---------------------------------------------------------------------------
# World extent
# ---------------------------------------------------------------------------
WORLD_MIN_X, WORLD_MAX_X = -2500.0, 2500.0
WORLD_MIN_Z, WORLD_MAX_Z = -2000.0, 2000.0
WORLD_W = WORLD_MAX_X - WORLD_MIN_X       # 5000 m
WORLD_H = WORLD_MAX_Z - WORLD_MIN_Z       # 4000 m

# Master heightfield resolution. 2 m is fine for terrain: roads, kerbs and
# building pads are vector geometry laid on top, not raster.
CELL = 2.0
GRID_W = int(WORLD_W / CELL)              # 2500
GRID_H = int(WORLD_H / CELL)              # 2000

# Erosion runs on a coarser grid — a Python-side flow routing over 5M cells is
# not worth the wall clock, and drainage is a large-scale process anyway. Fine
# detail is added back after upsampling.
EROSION_CELL = 8.0
EROSION_W = int(WORLD_W / EROSION_CELL)   # 625
EROSION_H = int(WORLD_H / EROSION_CELL)   # 500

SEA_LEVEL = 0.0
# Mean tide range. The quays were built for it, which is why the ladder rungs
# and the tide line exist at all.
TIDE_RANGE = 2.4

# ---------------------------------------------------------------------------
# Landmasses — hand-drawn control polygons, clockwise, in metres.
# ---------------------------------------------------------------------------
# The main island. Its east side is the south bank of the Sound, so the outline
# runs: south coast (ocean) → west coast → north-west shore of Ash Basin →
# along the south side of the Sound out to the harbour mouth → back down.
MAINLAND = [
    (-2180,  260), (-2240,  620), (-2120,  980), (-1960, 1180),
    (-1700, 1300), (-1380, 1330), (-1120, 1250), (-980,  1360),   # Fenmoor shore, river mouth bight
    (-760,  1520), (-520,  1600), (-240,  1580), (  60,  1500),   # lagoon-side, Causeway root
    ( 360,  1420), ( 620,  1300), ( 840,  1120), ( 980,   900),   # south-east headland
    (1120,   700), (1240,   520), (1420,   400), (1660,   330),   # harbour mouth, south side
    (1900,   300), (2060,   240),                                  # Sarn Point south — open ocean
    (1780,   150), (1500,   110), (1240,   120), (1020,    60),   # north edge: the Sound, south bank
    ( 860,   -20), ( 700,   -60), ( 560,   -30), ( 420,    40),   # THE NARROWS  (~300 m wide here)
    ( 260,    90), (  80,   110), ( -120,   90), ( -340,  120),   # Ash Basin south shore — the wharves
    ( -560,   60), ( -760,   90), ( -940,   40), ( -1120,  90),
    (-1340,   40), (-1560,  110), (-1780,   60), (-1980,  140),
]

# North Point. A separate island: the Sound cuts clean through, so the bridge is
# the only road on. Cliffs on the ocean side, a hill down the spine.
NORTH_POINT = [
    ( -260,  -180), ( -60,  -240), ( 200,  -220), ( 460,  -280),   # south shore, facing the basin
    ( 700,  -240), ( 940,  -300), (1180,  -260), (1420,  -320),
    (1660,  -280), (1880,  -360), (2060,  -520),                    # the harbour mouth, north side
    (2140,  -800), (2100, -1080), (1980, -1340), (1760, -1540),     # Sarn Head — cliffs, the light
    (1460, -1660), (1120, -1700), ( 780, -1660), ( 460, -1560),     # north coast, open ocean
    ( 180, -1420), ( -60, -1240), ( -220, -1000), ( -300,  -720),
    ( -320,  -440),
]

# Tern Bar — the barrier spit. Longshore drift built it; it is low, sandy and
# almost straight, with a hooked recurved end where the drift runs out.
TERN_BAR = [
    ( 380, 1560), ( 700, 1520), (1020, 1500), (1340, 1520),
    (1620, 1580), (1840, 1680), (1960, 1820), (1900, 1900),
    (1700, 1840), (1420, 1760), (1100, 1700), ( 780, 1690),
    ( 460, 1700), ( 300, 1660),
]

# Small stuff. A city's water is never empty.
ISLETS = [
    # (cx, cz, radius, height) — rocks and one built-on islet in the basin
    (1180,  -60,  70, 6.5),    # Cutwater Rock, mid-channel, has a beacon
    (1560,   40,  38, 3.2),
    (-380,  -60,  95, 4.0),    # Gull Bank — spoil heap turned island
    (2160, -1180, 46, 9.0),
]

LANDMASSES = {
    'mainland':    dict(poly=MAINLAND,   rough=1.0, seed=11),
    'north_point': dict(poly=NORTH_POINT, rough=1.25, seed=23),  # rockier, more indented
    'tern_bar':    dict(poly=TERN_BAR,   rough=0.35, seed=37),   # sand smooths a coast out
}

# ---------------------------------------------------------------------------
# Relief — hand-placed masses. Erosion and noise do the rest.
# ---------------------------------------------------------------------------
# (cx, cz, radius, peak height, falloff exponent)
HILLS = [
    ( 980, -1080,  900, 118.0, 2.1),   # Vantage Hill — the north shore high ground
    (1620, -1420,  520,  74.0, 1.9),   # Sarn Head, the cliff shoulder
    ( 340,  -900,  600,  52.0, 2.4),   # The Reach, lower north slope
    (-900,   760,  520,  62.0, 2.2),   # Kiln Rise — the stone came out of its flank
    (-1560,  420,  460,  34.0, 2.6),   # Fenmoor rise, gentle
    ( 120,   -60,  260,  22.0, 3.0),   # the Spine outcrop: small, solid, why the towers are here
]

# Made ground and cut platforms. These are flat because people made them flat.
# (x0, z0, x1, z1, height, edge_softness, name)
PLATFORMS = [
    (-1150, -40,  600, 400,  2.5,  22, 'ash_flats'),      # a century of tipping into the shallows
    (-2050, 900, -1350, 1400, 4.0,  40, 'cray_field'),    # airfield apron, graded flat
    (-1180, 480,  -700, 900, 14.0,  30, 'kilnward_yard'), # mill floor, cut into the rise
]

# The quarry: a cut into Kiln Rise's flank, now flooded.
QUARRY = dict(cx=-1210, cz=690, r=210, floor=-16.0, rim=44.0)

# The river. It still arrives; its floodplain is why Fenmoor is a park.
# Control points from the inland edge down to the basin.
RIVER_ASH = [
    (-2380, 940), (-2100, 860), (-1820, 800), (-1560, 720),
    (-1330, 640), (-1150, 520), (-1040, 380), (-1010, 220), (-1020, 60),
]
RIVER_WIDTH_MOUTH = 90.0
RIVER_WIDTH_HEAD = 26.0

# ---------------------------------------------------------------------------
# Bathymetry — depth matters, because deep water at the shore is why the city
# is here. The Sound is a drowned valley: steep sides, deep middle.
# ---------------------------------------------------------------------------
SOUND_CHANNEL = [   # thalweg — the deep line of the drowned valley
    (2400, 400), (2000, 320), (1700, 230), (1400, 170),
    (1100,  60), (860, -10), (700, -60), (540, -40),
    (300,  10), (0,   40), (-320, 30), (-640, 20), (-900, 10),
]
SOUND_DEPTH_MOUTH = -26.0     # a bulk carrier can come in on any tide
SOUND_DEPTH_HEAD = -9.5       # silting up at the head; dredged for the wharves
SOUND_HALF_WIDTH = 190.0      # the deep trough is narrow; the sides are steep

OCEAN_SHELF_DEPTH = -38.0     # beyond the harbour mouth
LAGOON_DEPTH = -1.8           # Cray Lagoon: too shallow to be useful for anything

# The water behind the spit. Tidal at both ends, but it never gets deep — which
# is why nothing was ever built there and why the birds have it.
LAGOON_POLY = [
    (-820, 1420), (-300, 1500), ( 300, 1560), ( 900, 1560),
    (1500, 1600), (1980, 1760), (2060, 1960), (1400, 1900),
    ( 700, 1800), (   0, 1740), (-560, 1660), (-880, 1560),
]

# Erosion. Stream-power incision plus hillslope creep — the two processes that
# actually shape a landscape. Tuned by looking at the hillshade, not by theory.
EROSION_ITERS = 28
EROSION_K = 0.00042        # fluvial incision coefficient
EROSION_M = 0.5            # drainage-area exponent
EROSION_N = 1.0            # slope exponent
EROSION_DIFFUSE = 0.28     # hillslope creep per iteration

# ---------------------------------------------------------------------------
# Districts — centre, radius of influence, and what the land IS there.
# Used to drive land use before anything is built on it.
# ---------------------------------------------------------------------------
DISTRICTS = [
    dict(key='the_spine',   name='The Spine',    c=( 120,  -30), r=420),
    dict(key='bellcross',   name='Bellcross',    c=( 120,  520), r=520),
    dict(key='ash_flats',   name='Ash Flats',    c=(-480,  200), r=700),
    dict(key='kilnward',    name='Kilnward',     c=(-950,  700), r=520),
    dict(key='tern_bar',    name='Tern Bar',     c=(1100, 1640), r=900),
    dict(key='north_point', name='North Point',  c=(1200,-1080), r=900),
    dict(key='the_reach',   name='The Reach',    c=( 360, -720), r=620),
    dict(key='cray_lagoon', name='Cray Lagoon',  c=( 300, 1300), r=760),
    dict(key='fenmoor',     name='Fenmoor',      c=(-1650, 800), r=800),
]
