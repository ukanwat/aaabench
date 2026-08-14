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
    # THE COASTAL PLAIN. This is the landmass; everything below is hills on top
    # of it. Without it the island was defined by where two separate massifs
    # happened to end, and a subtractive valley cut can never pull two shores
    # together — so the harbour came out as an open strait between two islands
    # instead of a channel incised through joined land. A river needs a plain to
    # cut down into, so the plain has to exist first.
    dict(c=(  40,  -140), r=(2700, 1780), rot=-6,  peak= 33.0, shape=0.42, irr=0.30),

    # The two big masses also overlap across the valley line. If they do not,
    # the water between them is just the gap between two islands and the valley
    # is carving nothing — which is the difference between an enclosed harbour
    # and an open strait. The channel must be cut by the valley out of joined
    # land, not left over between separate land.
    #
    # North Point — the block north of the valley. Highest ground in the world.
    dict(c=(1150,  -980), r=(1440, 1180), rot=-8,  peak=118.0, shape=0.52, irr=0.34),
    # Sarn Head — the seaward shoulder. Rock, and steep to the ocean.
    dict(c=(1820, -1460), r=( 660,  560), rot=20,  peak= 92.0, shape=1.35, irr=0.30),
    # The Reach — the lower northern slope. Its south edge is the harbour's north shore.
    dict(c=( 300,  -800), r=( 980,  820), rot=-14, peak= 46.0, shape=0.45, irr=0.40),
    # Mainland core, south of the valley. Broad and low: the city's ground. Its
    # north edge is the harbour's south shore, so it reaches well over the line.
    dict(c=(-560,   560), r=(2020, 1120), rot=6,   peak= 66.0, shape=0.62, irr=0.38),
    # Kiln Rise — the stone for the seawall came out of its flank.
    dict(c=(-940,   740), r=( 640,  540), rot=-22, peak= 62.0, shape=1.15, irr=0.28),
    # Fenmoor rise, gentle, inland.
    dict(c=(-1820,  700), r=( 820,  740), rot=10,  peak= 40.0, shape=0.75, irr=0.45),
    # The south-east headland, between the harbour mouth and the lagoon.
    dict(c=(1020,   820), r=( 860,  620), rot=-18, peak= 44.0, shape=0.85, irr=0.46),
    # The Spine outcrop: a knob of hard rock on the south shore, and the reason
    # the towers stand here and nowhere else. Peaky, because that is what it is.
    dict(c=( 120,   100), r=( 360,  320), rot=0,   peak= 34.0, shape=1.5,  irr=0.14),
]

# Resistant rock. A band of it crossing the valley is why the Narrows are narrow:
# the river could only cut a gorge through it, not widen one.
# (cx, cz, rx, rz, rot°, extra height)
RESISTANT = [
    dict(c=(760, -400), r=(200, 950), rot=6, add=40.0),  # the Narrows bar
]

# Relief noise. Amplitude is what indents the coast; wavelength is what decides
# whether the result reads as inlets or as fuzz.
RELIEF = dict(
    major_wavelength=760.0, major_amp=13.5,     # bays, side valleys, ridges
    mid_wavelength=250.0,  mid_amp=5.5,         # coves and points
    fine_wavelength=70.0,  fine_amp=2.0,        # the ragged metre-scale edge
    warp=0.55,
)

# ---------------------------------------------------------------------------
# The valley. ONE continuous drowned river valley, from the inland head in the
# west, east through what is now the inner harbour, through the Narrows, and out
# to the ocean. Above water in the west it is still the River Ash; east of about
# x = −1000 it is under the sea and it is called the Sound.
# ---------------------------------------------------------------------------
VALLEY = [
    (-2500, 1120), (-2150,  980), (-1800,  820), (-1500,  640),
    (-1280,  420), (-1160,  160), (-1140, -120), (-1060, -330),
    ( -860, -440), ( -520, -480), ( -160, -480), (  200, -460),
    (  480, -430), (  640, -412), (  760, -400),          # THE NARROWS
    (  920, -370), ( 1200, -310), ( 1520, -230), ( 1860, -150),
    ( 2200,  -60), ( 2500,   20),
]

# Both tables are keyed on x normalised over the world width, t = (x + 2500)/5000,
# NOT on distance along the curve. Position-along-a-curve is discontinuous across
# the curve's medial axis and every quantity driven by it inherits the jump.
#     t 0.00 → x −2500   t 0.30 → x −1000   t 0.50 → x 0
#     t 0.65 → x  +750   t 0.80 → x +1500   t 1.00 → x +2500
VALLEY_FLOOR = [
    (0.00,  26.0), (0.12, 18.0), (0.22,  8.0), (0.30,  0.0),   # river becomes sea here
    (0.36,  -5.0), (0.44, -8.5), (0.52, -10.5), (0.59, -12.0),
    (0.65, -20.0), (0.68, -21.0),                              # the gorge at the Narrows
    (0.74, -24.0), (0.84, -28.0), (0.92, -32.0), (1.00, -36.0),
]

# Half-width of the valley FLOOR. The sides climb beyond this.
VALLEY_WIDTH = [
    (0.00,  22.0), (0.15,  45.0), (0.24, 120.0), (0.30, 205.0),
    (0.40, 230.0), (0.50, 255.0), (0.58, 205.0),
    (0.635, 150.0), (0.665, 148.0),                            # THE NARROWS ≈ 300 m across
    (0.72, 235.0), (0.80, 330.0), (0.92, 470.0), (1.00, 620.0),
]

# The two shores of a drowned valley are not alike, and the difference is the
# whole reason the city is laid out the way it is: the north side is the steep
# one, so the money built up it for the view; the south side is the gentle one,
# so the wharves, the rail and the streets went there.
VALLEY_SIDE_RUN_N = 400.0
VALLEY_SIDE_RUN_S = 640.0
VALLEY_SIDE_HEIGHT = 42.0     # how far the valley sides climb before meeting the upland

# Multiplier on the side run down the valley. Through the resistant band the
# sides are short and steep — that is a gorge, and it is why the Narrows narrow.
VALLEY_SIDE_RUN_SCALE = [
    (0.00, 1.00), (0.55, 1.00), (0.615, 0.30), (0.685, 0.30), (0.76, 1.00), (1.00, 1.00),
]

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
    # The line is DERIVED from the generated south coast, not written here.
    x_from=-500.0, x_to=2100.0,   # the stretch of open coast the drift runs along
    search_from_z=400.0,          # ignore the harbour; this is the ocean shore
    smooth=9.0,                   # drift cuts across coves rather than following them
    offshore=210.0,               # how far out the bar builds
    hook=26.0,                    # the recurve where the drift runs out
    crest=3.6, half_width=95.0, dune_amp=1.9,
)

# Behind the bar the water is cut off from the swell and silts up. The
# lagoon is shallow BECAUSE the bar is there, so it is derived from the
# bar rather than drawn as a polygon of its own.
LAGOON_DEPTH = -1.6

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
    dict(key='the_spine',   name='The Spine',    c=( 140,   140), r=420),
    dict(key='bellcross',   name='Bellcross',    c=( 150,   620), r=520),
    dict(key='ash_flats',   name='Ash Flats',    c=(-560,   -40), r=700),
    dict(key='kilnward',    name='Kilnward',     c=(-980,   720), r=520),
    dict(key='tern_bar',    name='Tern Bar',     c=(1000,  1640), r=900),
    dict(key='north_point', name='North Point',  c=(1200, -1200), r=900),
    dict(key='the_reach',   name='The Reach',    c=( 300,  -880), r=620),
    dict(key='cray_lagoon', name='Cray Lagoon',  c=( 400,  1320), r=760),
    dict(key='fenmoor',     name='Fenmoor',      c=(-1750,  800), r=800),
]
