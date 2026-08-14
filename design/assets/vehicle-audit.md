# Vehicle palette — sourcing and vetting audit

**51 accepted, 44 rejected** — 12 as ripped game assets, 14 as real trademarked marques or
real-world liveries, 18 on quality. 64 models were downloaded and inspected; the rest were
rejected from their listing, uploader and description before spending the bandwidth. 869 MB of
source geometry and texture in, 101 MB shipped.

Every accepted file was looked at on a turntable under one neutral light before it was kept, and
four were held against real photographs afterwards. A high rejection rate is the point: on
Sketchfab, roughly one candidate in three that *looks* right in a search result is either
extracted from a commercial game, a badged real car, or untextured.

Files: `workspace/assets/vehicles/*.glb` + `manifest.json`
Sensor: `tools/vehicle_contact_sheet.py`
Captures: `shots/vehicles/`
Provenance and licences: `ASSETS.md`
Reference photographs: `ref/vehicles/`

---

## 1. The normalisation contract

Every accepted asset conforms to all of this. It is also machine-readable in
`manifest.json` under `contract`.

| | |
|---|---|
| **Units** | metres. Bounding box measured, compared against a real-world reference for the class, recorded in `manifest.json` as `dimensions_m` alongside `class_reference_m` and `deviation_pct`. |
| **Up** | +Y. Two sources were Z-up (both shipping containers) and were rotated on the way in, not at runtime. |
| **Forward** | −Z. Every Sketchfab vehicle arrived facing **+X**; all 40 were yawed 90°. |
| **Origin** | centre of the wheelbase, on the ground plane. `min.y == 0` is asserted by the contact sheet on every load and printed as a `!!` if it is off by more than 20 mm. All 51 pass. |
| **Wheels** | `wheel_fl` / `wheel_fr` / `wheel_rl` / `wheel_rr`, pivot at the hub centre. |
| **Materials** | metallic-roughness. 40 of 51 carry `KHR_materials_clearcoat` on the body paint from the source, so clearcoat is already wired and only needs its strength driven. |
| **Textures** | KTX2 — UASTC for normal maps, ETC1S for everything else, 1024 px cap. |
| **Geometry** | `EXT_meshopt_compression`. |

**Two things a consumer must know.**

1. **meshopt quantises POSITION.** The accessor `min`/`max` in the shipped files are in integer
   quantisation space, not metres. Read dimensions from `manifest.json`, or from a `Box3` after
   `GLTFLoader` has applied the dequantisation. I measured the wrong thing once and got a sedan
   147 km long before the browser-side box caught it.
2. **The loader needs both decoders**: `KTX2Loader` with the transcoder at
   `vendor/three/jsm/libs/basis/`, and `MeshoptDecoder`. Without them the files fail at load,
   not at build.

### Scale was measured, not assumed

The 1.75 m human figure in `--mode scale` is what makes a scale error visible; on its own an
asset 20% too large looks fine. `shots/vehicles/review-scale-front.png` is that pass over the
whole fleet.

It caught one real error: `bus_citytransit` came out **3.17 m wide**, 24% over the 2.55 m legal
maximum for a road vehicle anywhere. I had scaled it to a 12 m length. Rescaled to legal width
it is a **9.65 m midibus**, which is what the proportions were always describing. Everything
else landed within ±20% of its class reference; the residual +10–18% on width is mirrors, which
my reference figures exclude.

Two assets are still outside tolerance and are kept with the deviation recorded:
`motorcycle_cruiser` (+38% width, +47% height — a chopper with tall bars) and `bicycle_cruiser`
(+69% width). Both are flagged in `manifest.json`.

### Wheel naming is derived from geometry, not from the source label

Several sources name the rear pair from the driver's seat and the front pair from outside, so
`RL` ends up on the right-hand side. After normalisation the answer is unambiguous — forward is
−Z, right is +X — so the tags are reassigned from position. `sedan_fairheaven80` had its rear
pair swapped and would have mirrored any per-corner suspension.

- **37 of 51** have all four wheels as separate nodes with the pivot at the hub — drivable.
- **3** (`van_shvan92`, `sedan_riverside88`, `boxtruck_lct3000_07`) have the **rear axle as one
  welded mesh**. Front wheels steer, rear wheels cannot spin independently. Fine as traffic, not
  as the player's car.
- **11** are single welded meshes with no wheel nodes: both bicycles, the bus, both containers,
  the forklift, the trailer, the junker, and the three powered two-wheelers. Traffic-only.

### What is *not* done, and should be said plainly

- **AO.** None of the accepted assets ship an occlusion texture. Contact shadow under the arches
  and in the door shuts is coming entirely from the renderer.
- **Baked lighting in albedo.** `junker_pirozhok` is a retopologised photogrammetry scan and has
  the capture day's light baked into its base colour. It will glow slightly wrong at dusk. The
  other 50 are artist-authored and clean.
- **LODs.** Not generated. Every asset is one level.

---

## 2. Compression, and the arithmetic that should worry the next person

Pipeline per asset: `dedup` → `prune` → `resize 1024` → `uastc` (normal maps only) → `etc1s`
(everything else) → `meshopt`.

**869.0 MB → 101.4 MB across 51 files**, a mean of 2.0 MB each. Per-file before/after is in
`manifest.json` (`bytes_before`, `bytes`). The largest single win was
`container_20ft_rusted.glb`, 98.4 MB → 4.1 MB: it shipped 4096 px maps for 11k triangles.

**The 1024 px cap was decided by looking, not by rule.** I built the same two vehicles at 512,
1024 and 2048 and rendered them at 3 m — `shots/vehicles/texcmp-close.png`. At 2048 the chrome
window surround and the door-handle recess are a touch crisper. At 1024 the difference is
marginal at 3 m and gone by 6 m. At 512 the chrome trim visibly softens and the door crease
smears. 1024 costs 2.6 MB per vehicle against 6.2 MB for 2048. A uniform cap is also part of
normalisation in its own right: mixing a 2048 body with 1024 neighbours produces exactly the
texel-density mismatch that makes a library look assembled.

**KTX-Software was not installed**, so `gltf-transform etc1s`/`uastc` failed with a bare
`Command failed: command -v ktx`. It is not in Homebrew. I extracted the official
`KTX-Software-4.4.2-Darwin-arm64.pkg` with `pkgutil --expand-full`, copied `bin/ktx` and
`libktx*.dylib` into one directory (the binary looks for the dylib via `@rpath`, so they must
sit **side by side**, not in a `lib/` subdirectory), and put that on `PATH`. **Anyone
re-running this pipeline has to do the same or every texture silently stays as PNG/JPEG** —
which costs nothing at build time and everything in GPU memory.

### The memory number nobody will like

Bytes on disk are not GPU cost. At 1024 px, ETC1S with a mip chain is ≈0.7 MB resident per
texture. Each vehicle carries ~12 images. **51 × 12 × 0.7 MB ≈ 430 MB resident if all are
loaded at once** — against a stated budget of a few hundred MB for the entire city.

The fleet cannot all be resident. Two levers, in order of value:

1. **The shared-atlas extraction, and this is the big one.** The 40 Zhabotinsky vehicles share
   a common material set — `UCB_BOTTOM`, `UCB_Interiors`, `UCB_Lights_and_Glass`, the tyre set,
   the number-plate sheet and the badge sheet. Roughly **8 of each vehicle's 12 textures are
   byte-identical across the whole fleet**, and each `.glb` currently embeds its own copy. Emit
   them once as external `.ktx2` and have every vehicle reference them by URI, with a shared
   texture cache in the loader, and vehicle texture memory drops to *4 unique body maps per
   vehicle plus one shared set* — roughly 120 MB instead of 430 MB. I did not do this because it
   needs a loader-side cache to actually pay off, and the loader is another lane's code.
2. **Stream by distance** and keep ~10 bodies resident.

### Draw calls

**1,137 primitives across 51 vehicles, a mean of 22 each.** Thirty vehicles visible is ~670
draw calls before a single building. This is inherent to how the source is authored — the body,
hood, each door, each pane of glass, the interior and the suspension are separate meshes, which
is exactly what makes them useful (openable doors, per-pane glass, spinnable wheels).

I deliberately **did not run `gltf-transform join`.** It saved about 1% of bytes and around four
draw calls, and it **flattened the node hierarchy and destroyed every `wheel_*` node**. The
contact sheet caught this — the whole palette suddenly reported `0/4 wheels` — after I had
already shipped one build with it. Instancing at runtime is the right answer here, not joining
at build time.

---

## 3. Where I looked, and what each source was actually worth

| source | verdict |
|---|---|
| **Sketchfab** | The only source that mattered. 51 of 51 accepted files came from here. Search is open, download works with `$SKETCHFAB_API_TOKEN`, and the `license=` filter is per-request so CC0 and CC-BY need two queries. It is also, exactly as warned, full of ripped game assets — see the rejection list. |
| **Poly Haven** | **A wall for vehicles.** All 521 models enumerated; the entire road-vehicle inventory is `covered_car` (a car under a tarp), `old_tyre`, and two rusted wheel rims. The three ships are 17th-century sailing vessels. Superb CC0 authoring, nothing drivable. Do not spend time here again for vehicles — it remains the best source for props. |
| **Google Scanned Objects** | **A wall.** All 1,033 names pulled and grepped. The only hits are `Vtech_Cruise_Learn_Car_25_Years`, `Sonny_School_Bus` and `SORTING_BUS` — children's toys, scanned faithfully. Genuinely the right source for household props later. |
| **ABO** | Not pursued past the bucket listing. It is Amazon's *furniture and household* product catalogue; there is no road vehicle in it and enumerating 8,000 entries to prove that was not a good use of the time. |
| **Objaverse** | Not used. It aggregates Sketchfab, so it inherits the same provenance risk with *less* metadata to vet against — no uploader description, no like count, no clean licence field. Searching Sketchfab directly is strictly better for this job. |
| **NASA / Smithsonian** | Not pursued. Aircraft, spacecraft and museum artefacts. |
| **Openverse** | Worked, keyless, for reference photography. Its relevance ranking is weak on short queries: "taxi cab" returned a **Lego model** as the top CC-BY result, and "panel van" returned an estate car. Look at what comes back before trusting it. |

### The find that made this work

**Daniel Zhabotinsky** (`sketchfab.com/DanielZhabotinsky`) has ~130 downloadable vehicles under
CC-BY, all **invented marques** — Fairheaven, Shvan, Kiri, Illinois, Lightbody, LCT 3000,
Bokaroo, Phoenix, Tiara GT. Descriptions say "inspired by" a real class rather than reproducing
a car, and each carries an explicit blanket grant on top of CC-BY. Forty of them are here.

They arrive **already in metres at real scale** with four separately named wheel nodes, a
clearcoat-enabled body material, separate glass panes, an interior, and a shared material
library. That is not what "low poly model" in the title suggests, and I nearly filtered them out
on the word.

**The honest caveat: the fleet is 40/51 from one author.** That buys coherence — a real city's
traffic does share a design language — but it also means one person's proportional habits run
through 80% of what the player will see. If a later session finds the fleet reads uniform, that
is why, and the fix is to source 5–10 bodies from different authors at the same bar rather than
to add more Zhabotinsky.

### Badges and plates — the rule-2 check

Every Zhabotinsky vehicle shares one 2048 px badge atlas. I extracted and looked at it. It is
entirely **fictional marques** — Muzda, Sieger, Fida, Toya, Bursan, Legioner, Moreburg, Lord
Savage, Boff — drawn as deliberate pastiche. No real trademark is reproduced. Two are close
visual parodies: a blue-and-white quartered roundel, and an Italian-tricolour shield. If the
project wants to be maximally conservative those two cells of the atlas can be painted out;
they are in the lower-right quadrant of `Carbadges_misc_U_baseColor.png`.

The shared number-plate atlas carries **real US state names** — Michigan, Texas, California —
alongside generic ones and a fictional "Steelheaven". Not a trademark issue, but for a fictional
city they should be replaced when the livery generator runs.

---

## 4. What is in the palette

51 vehicles. `shots/vehicles/palette-fit-front.png` is the whole thing in one frame.

| tier | count | classes |
|---|---|---|
| Ordinary traffic | 26 | microcar 1, citycar 1, hatchback 6, compact 1, sedan 7, estate 2, SUV 1, pickup 4, van 1, minibus 1, utility 1 |
| Working | 9 | box truck 2, flatbed 1, tow truck 1, bus 1, forklift 1, trailer 1, container 2 |
| Character | 11 | muscle 1, coupe 1, sports 4, roadster 1, taxi 2, police 1, junker 1 |
| Two-wheelers | 5 | motorcycle 1, moped 1, scooter 1, bicycle 2 |

Wear distribution: 12 clean, 33 used, 5 worn, 1 wrecked. That skew is deliberate — a pristine
object reads as a render, and 26 ordinary-traffic bodies with factory paint would read as a
showroom.

**The weakest asset I kept is `motorcycle_cruiser`.** Its proportions are wrong (+38% width,
+47% height against a real cruiser), the teal paint is flat and toy-like next to the
photoscanned junker, and the chrome has no wear at all. I kept it because it is the **only
textured motorcycle** I could find at any acceptable licence — the alternative, a 565k-triangle
naked sport bike with genuinely good geometry, shipped with **zero textures**. An unbranded
motorcycle at this bar is a real hole and it should be re-hunted.

---

## 5. Rejections — 44, with reasons

Written down so a later session does not walk back into them.

### Rejected under rule 1 — extracted from a commercial game

These were all uploaded to Sketchfab under CC-BY. None of them is the uploader's work. Shipping
one would be the single most damaging thing available here.

| model | uploader | what it actually is |
|---|---|---|
| Call of Duty: Black Ops 4 Blackout — T.E.D.D. | `4130ff15fe394c239cc064b5286c43` | Activision asset |
| Call of Duty BO2 — Tranzit Bus | `4130ff15fe394c239cc064b5286c43` | Activision asset |
| Left 4 Dead Box Truck | `CoolGuywhodosevehicles` | Valve asset |
| tow truck (burnout 1) | `amogusstrikesback2` | Criterion/EA asset |
| longnose cab (burnout 3) | `amogusstrikesback2` | Criterion/EA asset |
| burnout 3 garage / burnout legends ds / asphalt 6 garage | `amogusstrikesback2` | EA / Gameloft assets |
| Tow Truck — Construction Sim 2017 | `vj32621` | ripped from a commercial sim |
| Mater | `Car2022` | Pixar character |
| Helluva Boss IMP City Transit Bus | `t.flores` | ripped from an animated series |
| 1974 Smokey And The Bandit Kenworth W900A | `mcvehiclessketchfab` | film-licensed, real marque |

The pattern is reliable enough to filter on: a title naming a game or film, an uploader whose
whole portfolio is one franchise, and an empty description.

### Rejected under rule 2 — real marque or real-world livery baked in

| model | reason |
|---|---|
| **MAN TGX 2010 V8 semi-truck** (`DevPoly3D`) | The **MAN wordmark is textured onto the front bumper**. Otherwise the best articulated tractor I found — 37.7k tri, 1024 px, correct proportions. Rejecting it leaves a hole (below). Also could not satisfy myself about provenance: a "high-detail" branded truck given away free is the exact shape of a converted commercial asset. |
| **London double-decker "look-alike"** (`robinmikart`) | Carries a **"B.O.A.C. LONDON" advertising panel** — a real airline brand painted into the albedo — and is unmistakably a specific real city's bus. |
| Harley-Davidson Police, Harley-Davidson Seventy-Two, Honda CB750, Honda Civic Type R, Suzuki SX4, VW Polo, VW Transporter T1, Toyota Hiace, BMW M3, Mercedes W123, Kia Granbird, Hyundai Aero | Real trademarked marques with badges modelled and textured. Not worth de-badging when unbranded equivalents exist. |

### Rejected on quality

| model | reason |
|---|---|
| **Three Cylinder Naked Street Bike** (`jamie3d`) | 565k triangles, 574 draw calls, and **zero texture images** — flat per-material colours only. Beautiful geometry, unusable material authoring. This is the one I most wanted to keep. |
| **Autocar McNeilus refuse truck** | Bounding box spans **286 m** on one axis from detached geometry; 83 materials over 108 primitives. Broken layout, not worth the repair. |
| **Semi Trailer Low poly Animated** (`Artbor`) | **2,193 primitives** for 26k triangles — 12 triangles per draw call. `join` only got it to 1,767. An exploded model. |
| **Maintenance vehicles** (`ondrasaur`) | Six municipal trucks in one scene, ~5k triangles each, no wheel separation, no surface detail. Would need splitting, and each piece would still be below the bar at 2 m. |
| **Forklift** (`alban`) | Genuine wear, but the bounding box is nearly cubic — 3.7 × 3.17 × 3.18 m. A real counterbalance forklift is 1.2 m wide. The proportions do not reconcile with any real machine and I could not establish what inflates the box. |
| **Abandoned Euro Car raw scan** (`kryik1023`) | The best rust-bucket available anywhere and I could not use it: 916k triangles across **10 overlapping raw scan chunks**, a single 8192 px atlas, bounding box dominated by scan debris, and the capture lighting baked into albedo. `simplify` gets it to 59k triangles cleanly — the geometry is salvageable — but the chunk cleanup is Blender work I did not have time for. **Worth returning to.** |
| **1940s City Coach** (`robinmikart`) | Period-inconsistent with a contemporary port city, and 153 draw calls across 24 materials at 4096 px. |
| **Sqarebird '70** (`DanielZhabotinsky`) | Not a street vehicle. It is a Can-Am/Group-C style **race prototype** — 0.97 m tall, full-width rear wing, exposed chassis. Out of scope for city traffic. |
| Low-poly kits — `Free Low Poly Vehicles Pack` (rgsdev), `Low Poly cars pack` (matisosanimation), `Low poly sedans 11-car pack` (vladek27), `PSX Sedan Car` (174 tri), `Generic Lowpoly Sedan` (2,160 tri), `containers estilo ps1/ps2`, `Low Poly Cargo Container` (12 tri), `Shipping containers` (48 tri), `Stylized Bus` | Deliberately stylised or flat-shaded. Cheap is not a virtue. |
| `Lowpoly Ford F100 - No Textures` (barbo-autos) | States in the title that it has no textures. |

### Repaired rather than rejected

| model | fault | fix |
|---|---|---|
| **`hatchback_sigil07`** | Bounding box 4.11 m tall; the car floated. One mesh, `Sigil08_Body_Badges`, exported broken — its vertices span 1.3 m below the road and 1.4 m above the roof. | Dropped that node. The badges it carried were a fictional-marque decal sheet. The car underneath is a clean modern 3-door hatch, 4.33 × 1.78 × 1.38 m. |
| **`sedan_riverside88`** | Yaw came out at 61°, not 90° — its rear axle is one welded mesh offset from centre, so the front/rear vector was wrong. | Forward direction given explicitly. |
| **`bus_citytransit`** | 3.17 m wide, over the legal maximum. | Rescaled by width; it is a 9.65 m midibus. |
| **`motorcycle_cruiser`** | Sank 33 mm below the ground after `simplify`. | Root translation; `min.y == 0`. |
| **`sedan_fairheaven80`** | Rear wheel nodes named left/right the wrong way round. | Tags reassigned from geometry across the whole fleet. |

---

## 6. Held against reference photographs — naming the gap

`shots/vehicles/ref-compare.png`, mine on the left, real on the right.

**`van_shvan92` vs a street-parked estate** (`ref/vehicles/real_panel_van.jpg`)
The real one has a black rubber weatherstrip around every pane and a chrome drip rail along the
roof gutter; mine has glass meeting bodywork in one continuous surface with a dark line painted
where the seal should be. The real paint has vertical wash streaks and a dirt gradient that gets
heavier toward the sills, and the clearcoat is visibly flattened on the horizontal panels where
the sun has hit it; mine is uniformly glossy top to bottom, so it reads as freshly detailed no
matter what the wear tag says. The real tyre flattens against the kerb and its sidewall carries
raised lettering; mine is a clean torus with a smooth sidewall and no contact patch.

**`boxtruck_lct3000_95` vs a New York box truck** (`ref/vehicles/real_box_truck.jpg`)
The real box body is built from riveted panels with seam battens every metre, aluminium corner
extrusions, and a scuffed rub rail along the bottom edge; mine has a faint embossed pattern
across an otherwise continuous surface with no seams and no corner hardware. The real one is
covered in graffiti and road film with rust blooming on the rear frame and mud flaps hanging
behind the rear axle; mine has the step but no flaps, no plates, no rust. The real steel wheels
show individual lug nuts and grease around the hub; mine has smooth painted hubs.

**`police_murphy97` vs a police estate** (`ref/vehicles/real_police_car.jpg`)
The real markings are applied retroreflective vinyl: they sit proud of the paint with a visible
cut edge, and they have a completely different specular response — under a headlight they blaze
while the paint stays dark. Mine are painted into the base colour with **identical roughness on
both sides of the boundary**, so at night the decal and the paint will bloom the same way. That
is the single clearest tell in the whole palette, and it is a roughness-map problem, not a
geometry one.

**`taxi_canyon75` vs the same reference**
This one is closer than I expected — it already has a checker band, a printed fare table, dents
pressed into the door skin and chipped paint along the sill, which is more honest wear than most
paid assets carry. The same vinyl-versus-paint problem applies: the checker band is albedo-only.

**The gap common to all of them: glass has no thickness and no interior depth.** Look into the
box truck's cab window and the interior is a flat dark plane. Real automotive glass is 4–6 mm
with a visible green edge, a slight double reflection, and a cabin behind it that occludes.

---

## 7. What I would hunt next, in order

1. **An unbranded articulated tractor unit.** The single biggest hole. I have two semi-trailers
   and nothing to pull them with, in a port city. Every candidate was either a real marque with
   the wordmark modelled (MAN TGX) or an exploded mesh. Zhabotinsky's catalogue has no
   heavy-haul tractor; try `comrade1280`'s "Generic civil service vehicles pack" (92k tri,
   CC-BY, invented liveries) which I did not have time to unpack, and search "cabover" and
   "day cab" rather than "semi truck".
2. **A refuse truck and a street sweeper.** Both were on the brief and both failed — the only
   refuse trucks on Sketchfab under a usable licence are real branded chassis or broken.
3. **A better motorcycle**, per the weakest-asset note above.
4. **Clean up the `kryik1023` raw scans.** Three genuinely photogrammetric wrecked cars, CC-BY,
   already downloaded. `simplify --ratio 0.04` takes the Euro Car from 916k to 59k triangles
   with no visible loss. What is needed is a Blender pass to delete the scan-debris chunks and
   crop the atlas. That would give the palette two or three more real junkers, which is the
   category where photogrammetry beats artist work most decisively.
5. **The shared-atlas extraction** in §2. It is worth more than any additional vehicle.
6. **A harbour tug or workboat.** Not attempted. Poly Haven's only boats are 17th-century
   sailing ships; Sketchfab's "tugboat" query is dominated by an asset-pack author of the same
   name. Try "workboat", "pilot boat", "harbour tug" and expect to look at real hull photos.

---

## 8. The sensor

`tools/vehicle_contact_sheet.py` renders every `.glb` in a directory on a turntable against one
neutral studio setup and stitches a labelled contact sheet.

```bash
~/imagegen/bin/python tools/vehicle_contact_sheet.py                        # fit, front-quarter
~/imagegen/bin/python tools/vehicle_contact_sheet.py --mode scale           # true relative size
~/imagegen/bin/python tools/vehicle_contact_sheet.py --angles 0,90,180,270  # a sheet per angle
~/imagegen/bin/python tools/vehicle_contact_sheet.py --only van_shvan92 --tile 1200x900 \
    --mode scale --scale-dist 3.2                                           # close inspection
```

Two modes because they catch different lies. `fit` frames each vehicle to fill its tile, so what
you judge is surface — shutlines, glass, tyre sidewalls, and texel density against neighbours.
`scale` gives every tile one world framing with a 1 m grid and a 1.75 m human, so proportion and
units are judged instead. Each tile prints measured L×W×H, triangles, draw calls, materials,
largest texture, wheel-node count and file size, and flags `min.y` if the asset floats or sinks.

**Three things it cost me to learn, recorded so they are not paid for twice.**

- `WebGPURenderer.setViewport` uses a **top-left** origin, not GL's bottom-left. Getting it
  backwards flips the sheet vertically, and every label then confidently names the wrong
  vehicle — a very convincing way to be wrong.
- Enabling shadow maps **breaks accumulate-into-one-canvas via viewport/scissor**: the
  shadow pass resets the colour attachment, so the sheet ends up containing only the last
  vehicle. The tool now renders each tile separately and stitches with PIL. Slower, correct.
- It carries the Metal/WebGPU launch flags and **asserts on the backend string**. A headless
  Chromium on default flags renders through SwiftShader, and a screenshot from a CPU rasterizer
  looks exactly like a screenshot.

### Captures

| file | what |
|---|---|
| `palette-fit-front.png` | the shipped 51, front three-quarter |
| `review-fit-000.png` / `review-fit-front.png` | the 41-candidate pass, rear and front |
| `review-scale-front.png` | the scale/proportion pass with the human figure |
| `reviewx-fit.png` | the 20 non-Zhabotinsky candidates, most of which were rejected |
| `closeup-suspects.png` | the two broken Zhabotinsky assets and four good ones at 640×480 |
| `closeup-x.png` | the gap-filler calls, including the B.O.A.C. bus and the MAN badge |
| `texcmp.png` / `texcmp-close.png` | 512 vs 1024 vs 2048, whole-vehicle and at 3 m |
| `ref-compare.png` | four accepted vehicles beside real photographs |
