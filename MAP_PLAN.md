# MAP_PLAN — Ashmouth

**The game is `HARBOUR & ASH`. The city is Ashmouth**, on Ashmouth Sound, at the mouth of the
River Ash. The title is a street corner: where Harbour Street meets Ash Street is the middle of
downtown, and it is also the two halves of the place — the water and the industry.

This document is the index for the world. Story lives in [STORY_BIBLE.md](STORY_BIBLE.md).
District detail lives in `design/districts/*.md`, art direction in `design/art/*.md`, systems
values in `design/systems/*.md`, reference photography in `ref/<district>/`.

Units are metres, three.js convention (1 unit = 1 m, Y up). **North is −Z, east is +X.**
Origin `(0, 0)` is the crossroads of Harbour Street and Ash Street.

---

## 1. Why the city is here at all

Everything below is downstream of one fact, and nothing was placed because it looked good there.

> A river cut a valley through a low coastal range. Sea level rose and drowned it. What is left
> is a **ria** — a deep, sheltered channel with steep sides and deep water hard against the
> shore. That is a natural harbour that could take a big ship a century before anyone could
> dredge one, so a port grew at the first place the valley narrowed enough to ferry across.

From that single fact, in order:

- Deep water on the **south** side of the channel → the wharves went there, and the **rail** was
  laid to serve them, along the flattest ground.
- Rail and wharf need flat land, and there wasn't any, so the head of the harbour was **filled**
  — a century of tipping quarry spoil and ash into the shallows. That made ground is flat, it is
  soft, and it floods. → **Ash Flats**: heavy industry, freight, tank farm, nothing tall,
  nobody after seven.
- Workers walked to work, so their housing went up on the **slope directly above the wharves**,
  cheap and dense and downwind of the smell. → **Bellcross**.
- The money therefore built **across the water**, on the north shore: upwind, uphill, facing the
  afternoon sun, with the view back at the skyline it owned. → **Vantage Hill / North Point**.
- The banks that financed the shipping needed to be near the shipping but on ground that would
  hold a tower. The only solid rock at the head of the harbour is a small outcrop. → **The
  Spine**, a tall cluster with a hard edge where the rock stops and the fill begins. *That edge
  is why the skyline has a shape.*
- The river still arrives, and its floodplain is too wet to build and too flat to waste. → the
  park, the pitches, the allotments, the landfill. → **Fenmoor**.
- Longshore drift built a **sand spit** across the ocean side of the harbour mouth, and the
  lagoon behind it is too shallow and too brackish for anything but boats and birds. →
  **Tern Bar** and **Cray Lagoon**.
- The stone for the seawall came out of the hill behind Kilnward. → **the quarry**, now flooded.
- Containerisation happened in the eighties. The real freight left for a deepwater terminal down
  the coast. **Half the port is empty, and a half-empty port with rail, a customs shed and
  nobody watching is good for exactly one thing.** That is the story.

## 2. The silhouette

Bounds `x ∈ [−2500, +2500]`, `z ∈ [−2000, +2000]` — a 5.0 × 4.0 km world, ocean to every edge.
Three landmasses and a scatter of rocks.

```
                                   N  (−Z)
  −2500                                                              +2500
−2000 ┌──────────────────────────────────────────────────────────────────┐
      │  ~~~~ open ocean ~~~~        ╭─╮ cliffs                          │
      │                        ╭─────╯ ╰──╮        ☼ Sarn Head Light     │
      │           ~~~~    ╭────╯  VANTAGE  ╰───╮                         │
      │                 ╭─╯   ▲118m  HILL       ╰──╮   ~~~~~             │
−1000 │            ╭────╯    ╱ ╲  switchbacks      ╰───╮                 │
      │        ╭───╯    THE REACH   (postwar tract)     ╰──╮             │
      │      ╭─╯   ╭──────────────────────────────────────╮ ╰─╮          │
      │     ╱     ╱   NORTH POINT  ISLAND                  ╲   ╲         │
      │    │     ╱                                          ╲   │ ~~~~   │
 −400 │    │    ╰───────────╮        ╔═══╗ NARROWS BRIDGE ╭──╯   │       │
      │    │  ~~ ASH BASIN ~~╲       ║   ║                ╱      │       │
    0 │    ╰──╮  ▬▬▬▬▬▬▬▬  ▓▓▓▓▓ ◈   ║   ║   THE  SOUND  ╱  ~~~~~╯       │
      │  R.Ash │ ASH FLATS  THE SPINE╚═══╝ ~~~~~~~~~~~~~╱                │
      │   ╲    │ ▬cranes▬   ▓towers▓                   ╱     ~~~~~       │
      │    ╲   │══════════ BELLCROSS ═════╮           ╱                  │
 +600 │  FENMOOR  KILNWARD  (terraces)     ╰────╮    ╱      ~~~~~        │
      │   pitches  ▨mills▨   ▲62m Kiln Rise     ╲  ╱                     │
      │   landfill   quarry⬤          ╭─────────╯ ╱      ╭───────────╮   │
      │  ✈ Cray Field       ╭─────────╯          ╱      ╱  TERN  BAR  ╲  │
+1400 │      ╲     ╭────────╯   ~~ CRAY LAGOON ~~      ╱   beach/boardwalk│
      │       ╰────╯  ═══════ THE CAUSEWAY ═══════════╯  ▄▄▄▄▄▄▄▄▄▄▄▄▄  │
+2000 └──────────────────────────────────────────────────────────────────┘
                                   S  (+Z)
   ▓ towers  ▬ port/industry  ▨ mills  ▲ hill  ⬤ quarry  ✈ airfield  ☼ light  ◈ spawn
```

**The Sound** enters from the east, runs west-north-west, pinches to **the Narrows** at
`(760, −400)` where a band of resistant rock crosses the valley — which is why it is narrow, and
why the bridge and, for two hundred years before it, the ferry are there — then opens west into
**Ash Basin**, the inner harbour. Water is the boundary of the world on every side; there are no
invisible walls anywhere.

> **The generator corrected this plan, and the correction is kept.** The sketch called for North
> Point to be a separate island. What the terrain produced is a **peninsula**, joined to the
> mainland around the head of the harbour — because the valley floor climbs above sea level at
> the head, which is exactly where a drowned valley stops being drowned. That is better than the
> plan: the road round the harbour head is six kilometres, so the Narrows Bridge exists to save
> that drive, and before it was built the north shore was remote — which is *why* the money and
> the big houses went there. A bridge to an island with no other access explains nothing; a
> bridge that replaces a detour explains a district. **Tern Bar remains a genuinely separate
> landmass**, reached by the Causeway, so the map still has a real crossing to a real island.

**Measured: 6.75 km² of land** in a 20 km² world (generator output, session 1). The figure in
this plan is now a measurement, not an intention.

### How it is kept from being empty

Roughly a fifth of that land is *legitimately* not city — marsh, floodplain, cliff, quarry,
airfield apron, dune — and that is the point rather than an excuse: a real city is mostly not
buildings. The rule I am holding myself to is that **land gets a use before it gets a
building**, and every parcel answers *why is this here* with a cause. Density peaks on the
Spine and falls off in every direction at a rate set by ground conditions and land value, not
by a radius.

## 3. Landmarks — what you navigate by

Each is a one-off, hand-placed, with a silhouette readable at 500 m.

Positions are provisional until the road network is generated against the finished terrain —
a landmark whose coordinate predates the ground it stands on is a landmark in the sea.

| landmark | where | reads as |
|---|---|---|
| **Narrows Bridge** | `(760, −400)` | steel cantilever, 1936, 62 m clearance. The signature view; visible from most of the city. |
| **The Spine** | `(0, 0)` → `(300, −200)` | tall cluster on the rock outcrop. Tallest: **Halloway Tower**, 168 m, 1974, with a helipad. |
| **Sarn Head Light** | `(1750, −1500)` | white tower on the north-east cliff; the seaward marker. |
| **Ash Point power station** | `(−700, 200)` | two 90 m stacks on the basin, cooling-water intake. Visible from everywhere; the thing you steer by inland. |
| **Kilnward bottle kilns** | `(−900, 700)` | four brick kilns, preserved, dead. |
| **Grain elevator, Pier 9** | `(−200, 260)` | concrete silos, 46 m, painted-over company name. |
| **Cray Field control tower** | `(−1750, 1150)` | single-storey terminal, one 900 m runway. |
| **The Causeway** | `(−600, 1500)` → `(600, 1620)` | 1.9 km low crossing to Tern Bar with a lift span. |

## 4. Districts

Nine. Each names the real places it is anchored to and what was taken from each — the full
study, the reference board and the material/palette notes live in `design/districts/<name>.md`
and `ref/<name>/`.

| # | district | land | what a stranger notices in 3 seconds | tier |
|---|---|---|---|---|
| 1 | **The Spine** | rock outcrop, downtown | towers with 1920s setbacks jammed against 80s glass; streets too narrow for what's above them; granite plinths; sun only reaches the road at noon | 1 |
| 2 | **Bellcross** | slope above the port | stepped brick terraces climbing a hill, painted different colours by owner not by plan; marble stoops; wires; a corner shop every third block | **1 — hero** |
| 3 | **Ash Flats** | reclaimed fill, +2.5 m | gantry cranes, container stacks, tank farm, rail let into the road surface, chain link, nothing over three storeys | 2 |
| 4 | **Kilnward** | old industry on Kiln Rise | brick mills with sawtooth roofs and a rooftop water tank; a dead canal; the freight line cutting the district in half with one footbridge | 2 |
| 5 | **Tern Bar** | barrier spit, sand | mid-century motel signage, bleached timber boardwalk, dune fence, salt-stunted pines, everything one or two storeys and facing the sea | 2 |
| 6 | **North Point** | north shore hill, 118 m | switchbacks with a view, big houses on big lots, dry-stone walls, cliffs and a lighthouse; almost no shops | 3 |
| 7 | **The Reach** | lower north slope | postwar tract housing, carports, basketball hoops, one strip mall arterial, a water tower | 3 |
| 8 | **Cray Lagoon** | tidal marsh | phragmites to the horizon, stilted shacks on tidal creeks, a boardwalk and a bird hide, pylons marching across | 3 |
| 9 | **Fenmoor** | river floodplain | pitches, allotments, a capped landfill with vent flares, a flooded quarry, the airfield, scrub | 3 |

### Real-world anchors

One line each; the district document carries what was taken from each and why.

    The Spine     ← pre-war financial district      (40.7075, −74.0113) · (42.3564, −71.0553)
    Bellcross     ← steep painted terrace streets   (51.4400,  −2.5730) · (39.2764, −76.6100)
    Ash Flats     ← working container port          (39.2664, −76.5836) · (40.6743, −74.0146)
    Kilnward      ← 19th-c. mill district           (41.8180, −71.4380) · (42.6460, −71.3120)
    Tern Bar      ← mid-century motel beach strip   (38.9890, −74.8150) · (42.0500, −70.1870)
    North Point   ← headland switchbacks + estates  (37.8590, −122.4850) · (41.4600, −71.3400)
    The Reach     ← postwar tract suburbia          (40.7250, −73.5140)
    Cray Lagoon   ← barrier-island salt marsh       (39.7500, −74.1800) · (37.9330, −75.3790)
    Fenmoor       ← reedbed, landfill and pylons    (40.8000, −74.0800)

They are anchors, not copies: what is taken is block depth, storey height, setback rhythm, roof
clutter, material ageing, tree species, streetlight colour and what a corner shop looks like
there. No name, brand or trademark from any of them appears in Ashmouth.

## 5. Roads — the network answers to the ground

Not a grid stamp. The order the network was built in is the order it is generated in:

1. **The shore road** came first, because the wharves came first. `Harbour Street` follows the
   south side of Ash Basin, bending with every bay and quay, and it is not straight anywhere.
2. **The grid** is only on the Spine and the flat fill — a tight 90 × 70 m downtown grid on the
   outcrop, rotated 14° off north to sit square to the water rather than to the compass, which
   is why every street meeting it at the edge forks awkwardly.
3. **Bellcross climbs.** Streets run *across* the slope where they can and *straight up* it
   where the block demands, so a third of them are steps rather than road. Blocks are irregular
   because the coast cut them.
4. **The Ring (Route 9)** — elevated, 1961, driven through Kilnward on viaduct because that land
   was cheap and the people there could not stop it. It severs the district, casts a permanent
   shadow, and it is the fastest way across the map.
5. **Vantage Drive** — the pleasure road. Switchbacks up the north shore, no straight longer than
   180 m, camber and superelevation into every bend, the whole city on your right going up.
6. **The Causeway** — 1.9 km dead straight across the lagoon, because nothing was in the way.
7. Cul-de-sacs and loops in The Reach; a roundabout where the Ring meets Bar Road; two
   underpasses beneath the rail; one tunnel under Kiln Rise.

Gradients stay inside what a car can climb; carriageways stay wide enough for two vehicles;
every segment connects. Those are generator invariants, checked as data before anything is
built — the list lives in `design/systems/invariants.md`.

## 6. Spawn, and the first thing you see

**Spawn: `(120, 470)`, the top of Cutter Steps in Bellcross, facing north-east down the hill.**

One frame contains: the terrace street falling away in front of you, the cranes and container
stacks of Ash Flats below, the Spine's towers to the left, the Narrows Bridge and the water
behind them, and North Point's hill across the Sound. Skyline, industry, water, bridge and hill
in a single view, from a street — not a plaza, not a vista point, a street with bins on it.

## 7. Where missions happen

Act 1 in **Tern Bar** and **Kilnward** — small money, edges of the map, the player learns to
drive and to run. Act 2 moves to **Ash Flats** and **The Spine** — the port, the freight, the
tower. Act 3 returns to **Ash Basin** and the **Narrows Bridge**. The full list, one file per
mission, is `design/missions/`.

## 8. Quality tiers — the gradient, declared

The whole map exists in blockout before anything is dressed. Then, in this order:

- **Tier 1 — hero.** Bellcross, and the Harbour & Ash blocks of the Spine. Near-final: real
  materials, ground-floor storefronts with unique signage, wear where feet and tyres go,
  props at eye height, interior-implying detail, full night lighting.
- **Tier 2.** Ash Flats, Kilnward, Tern Bar. Correct silhouettes and correct materials, less
  dressing, storefronts and signage on the main frontages only.
- **Tier 3.** North Point, The Reach, Cray Lagoon, Fenmoor. Must read correctly from a normal
  playing camera and from the air, with full collision and no missing ground. Simpler is
  allowed; grey boxes and holes are not.

## 9. What is in, and what is deliberately out

**In:** boats (the harbour is the whole point) — dinghies to a coaster, a working ferry, the
marina · one helicopter with a helipad you can actually land on · freight rail with a working
yard, and the severance it causes · buses on real routes · the ground fleet · bridges,
viaducts, two underpasses, one tunnel, a multi-storey car park you can drive up · rooftops and
fire escapes · storm drains and a dead canal · quarry, landfill, construction sites · power
station · an airfield with light aircraft · beach, dunes, marsh, cliffs · enterable interiors,
a handful, done properly.

**Out, and why:** no international airport — a full one is 3 km² of tarmac and I would rather
spend that on city, so Cray Field is a single-runway regional strip. No subway — a city this
size would not have one; it has commuter rail, which also gives me the severance. No jets. No
gambling. Motorbikes and bicycles are in the fleet; jetskis are at the marina.

---

*Sketch, districts and landmark positions are the frozen macro layout. Micro — props, dressing,
detail — stays mutable. If this plan changes, this file changes with it.*
