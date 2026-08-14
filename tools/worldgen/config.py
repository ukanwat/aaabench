"""Ashmouth — world constants and the hand-authored structure.

Metres throughout, three.js convention: X east, Z south (north is −Z), Y up.
Origin (0, 0) is the crossroads of Harbour Street and Ash Street.

**Nothing here is a coastline.** The coast is not authored; it is where the
finished terrain crosses zero. What is authored is the *structure* — where the
high ground is, where the valley runs, where the resistant rock is — because
that is what actually decides the shape of a drowned coast. Getting this the
right way round is the difference between a map and two potatoes.

The sequence the world is built in, and why:

    uplift → relief noise → the valley → EROSION against a sea level 40 m
    lower than today → flood to zero → deposition → what people built

The erosion runs against a base level of −40 m because that is where the sea
was during the last glacial. The valleys were cut then. Drowning them now is
what produces a ria: a deep sheltered channel with steep sides, side bays that
are drowned tributaries, headlands that are the ridges between them, and islands
that are hills the water went round. Every one of those is a consequence here
rather than a thing someone drew.
"""

SEED = 20260814

# ---------------------------------------------------------------------------
# World extent
# ---------------------------------------------------------------------------
WORLD_MIN_X, WORLD_MAX_X = -2500.0, 2500.0
WORLD_MIN_Z, WORLD_MAX_Z = -2000.0, 2000.0
WORLD_W = WORLD_MAX_X - WORLD_MIN_X       # 5000 m
WORLD_H = WORLD_MAX_Z - WORLD_MIN_Z       # 4000 m

CELL = 2.0
GRID_W = int(WORLD_W / CELL)              # 2500
GRID_H = int(WORLD_H / CELL)              # 2000

EROSION_CELL = 8.0
EROSION_W = int(WORLD_W / EROSION_CELL)   # 625
EROSION_H = int(WORLD_H / EROSION_CELL)   # 500

SEA_LEVEL = 0.0
GLACIAL_SEA_LEVEL = -40.0                 # where the sea was when the valleys were cut
TIDE_RANGE = 2.4

# ---------------------------------------------------------------------------
# Uplift — the structural high ground.
# (cx, cz, rx, rz, rotation°, peak, edge_flatness, irregularity)
#
# `edge_flatness` > 1 makes the massif's rim shallow. That matters more than the
# peak height: a shallow rim means the relief noise moves the waterline hundreds
# of metres, which is where an indented coast comes from. A steep rim gives a
# smooth coast however much noise is on it.
# ---------------------------------------------------------------------------
MASSIFS = [
    # North Point — the block north of the valley. Highest ground in the world.
    dict(c=(1050, -1010), r=(1320,  830), rot=-8,  peak=132.0, flat=1.9, irr=0.34),
    # Sarn Head — the seaward shoulder, rock, steep to the ocean.
    dict(c=(1780, -1420), r=( 620,  520), rot=20,  peak= 86.0, flat=1.2, irr=0.30),
    # The Reach — lower northern slope running down to the water.
    dict(c=( 220,  -820), r=( 820,  560), rot=-14, peak= 54.0, flat=2.4, irr=0.42),
    # Mainland core, south of the valley. Broad and low: this is the city's ground.
    dict(c=(-620,   740), r=(1900,  880), rot=6,   peak= 74.0, flat=2.6, irr=0.40),
    # Kiln Rise — the stone came out of its flank.
    dict(c=(-940,   700), r=( 620,  520), rot=-22, peak= 64.0, flat=1.6, irr=0.28),
    # Fenmoor rise, gentle, inland.
    dict(c=(-1780,  640), r=( 780,  700), rot=10,  peak= 42.0, flat=2.8, irr=0.45),
    # The south-east headland, between the harbour mouth and the lagoon.
    dict(c=( 900,   860), r=( 780,  520), rot=-18, peak= 46.0, flat=2.2, irr=0.46),
    # The Spine outcrop: small, hard, and the reason the towers are where they are.
    dict(c=( 140,   -40), r=( 300,  240), rot=0,   peak= 26.0, flat=1.1, irr=0.16),
]

# Resistant rock. A band of it crossing the valley is why the Narrows are narrow:
# the river could only cut a gorge through it, not widen one.
# (cx, cz, rx, rz, rot°, extra height)
RESISTANT = [
    dict(c=(700, -60), r=(190, 900), rot=6, add=38.0),   # the Narrows bar
]

# Relief noise. Amplitude is what indents the coast; wavelength is what decides
# whether the result reads as inlets or as fuzz.
RELIEF = dict(
    major_wavelength=760.0, major_amp=26.0,     # bays, side valleys, ridges
    mid_wavelength=250.0,  mid_amp=9.5,         # coves and points
    fine_wavelength=70.0,  fine_amp=2.6,        # the ragged metre-scale edge
    warp=0.55,
)

# ---------------------------------------------------------------------------
# The valley. ONE continuous drowned river valley, from the inland head in the
# west, east through what is now the inner harbour, through the Narrows, and out
# to the ocean. Above water in the west it is still the River Ash; east of about
# x = −1000 it is under the sea and it is called the Sound.
# ---------------------------------------------------------------------------
VALLEY = [
    (-2500, 1120), (-2180, 1000), (-1860,  860), (-1560,  700),
    (-1300,  540), (-1120,  380), (-1020,  200), ( -980,   40),
    ( -760,  -10), ( -420,   20), (  -60,   50), ( 320,   20),
    ( 560,   -40), ( 700,   -62), ( 880,   -30), (1140,    50),
    (1440,   140), (1760,   220), (2120,   320), (2500,   430),
]

# Floor elevation down the valley, as (t along valley 0→1, height m).
# It crosses zero at about t = 0.30, which is where the river becomes the sea.
VALLEY_FLOOR = [
    (0.00,  26.0), (0.12, 17.0), (0.22,  7.5), (0.30,  0.0),
    (0.38, -6.5), (0.46, -9.5), (0.54, -11.0), (0.62, -13.0),
    (0.68, -21.0),                                   # the gorge at the Narrows
    (0.74, -24.0), (0.84, -28.0), (1.00, -34.0),
]

# Half-width of the valley floor down its length. Wide where the rock is soft,
# pinched to almost nothing through the resistant band.
VALLEY_WIDTH = [
    (0.00,  70.0), (0.16, 130.0), (0.26, 260.0), (0.36, 520.0),
    (0.48, 620.0), (0.58, 430.0),
    (0.66, 150.0), (0.70, 145.0),                    # THE NARROWS
    (0.76, 340.0), (0.86, 620.0), (1.00, 900.0),
]
VALLEY_SIDE_HEIGHT = 96.0     # how far the valley sides climb before meeting the upland

# ---------------------------------------------------------------------------
# Erosion — stream-power incision plus hillslope creep.
# ---------------------------------------------------------------------------
EROSION_ITERS = 45
EROSION_K = 0.00055
EROSION_M = 0.5
EROSION_N = 1.0
EROSION_DIFFUSE = 0.30

# ---------------------------------------------------------------------------
# Deposition. The spit is not erosional — longshore drift built it — so it is
# added after the flood, as a sand ridge in shallow water running along the
# drift direction, hooked at the far end where the drift runs out of energy.
# ---------------------------------------------------------------------------
SPIT = dict(
    line=[(-120, 1560), (300, 1600), (760, 1610), (1200, 1620),
          (1560, 1680), (1830, 1790), (1930, 1930)],
    crest=3.6, half_width=95.0, dune_amp=1.9,
)

# Silt where the river drops its load, and the flats that go under at high tide.
DELTA = dict(c=(-1010, 180), r=420.0, amount=3.2)

# ---------------------------------------------------------------------------
# What people did to it.
# ---------------------------------------------------------------------------
# Reclaimed land: a century of tipping quarry spoil and ash into the shallows
# to make wharf frontage. Flat, soft, and it floods. Bounded by a seawall, so
# the edge is a hard vertical line where it meets the water — that wall is the
# most characteristic thing about a made-ground waterfront.
RECLAIM = [
    dict(poly=[(-1120, 60), (-980, -40), (-620, -30), (-240, 10), (60, 40),
               (330, 10), (470, 60), (430, 210), (120, 300), (-260, 330),
               (-620, 320), (-980, 300), (-1160, 220)],
         height=2.9, name='ash_flats'),
    dict(poly=[(-1180, 470), (-820, 430), (-700, 560), (-740, 880), (-1060, 930),
               (-1210, 800)],
         height=15.5, name='kilnward_yard'),
    dict(poly=[(-2130, 900), (-1420, 830), (-1360, 1290), (-2070, 1360)],
         height=5.2, name='cray_field'),
]

# The quarry. Not a circle — a quarry is a bite taken out of a hillside from the
# side that was easiest to get a road to, with benches down to a flooded floor.
QUARRY = dict(
    poly=[(-1330, 560), (-1120, 520), (-990, 620), (-1010, 800), (-1180, 870),
          (-1340, 790), (-1390, 660)],
    floor=-14.0, bench_h=8.0, bench_w=24.0,
)

# ---------------------------------------------------------------------------
# Districts — centre and radius of influence.
# ---------------------------------------------------------------------------
DISTRICTS = [
    dict(key='the_spine',   name='The Spine',    c=( 140,  -40), r=420),
    dict(key='bellcross',   name='Bellcross',    c=( 140,  520), r=520),
    dict(key='ash_flats',   name='Ash Flats',    c=(-480,  180), r=700),
    dict(key='kilnward',    name='Kilnward',     c=(-950,  700), r=520),
    dict(key='tern_bar',    name='Tern Bar',     c=(1000, 1640), r=900),
    dict(key='north_point', name='North Point',  c=(1150,-1050), r=900),
    dict(key='the_reach',   name='The Reach',    c=( 260,  -760), r=620),
    dict(key='cray_lagoon', name='Cray Lagoon',  c=( 400, 1300), r=760),
    dict(key='fenmoor',     name='Fenmoor',      c=(-1700, 780), r=800),
]
