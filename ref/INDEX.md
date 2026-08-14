# ref/ — reference photograph boards for Ashmouth

Nine district boards, one per district in `MAP_PLAN.md` §4. Every image was downloaded and
**looked at**; every `NOTES.md` was written after looking, not from memory. Every image has its
source URL recorded in its board's table.

Sources used, in order of value: **Mapillary** (street level, eye height, real light — the game
camera), **Wikimedia geosearch** (photographs taken at a coordinate), **Wikimedia Commons
keyword search** (named landmarks and one-off objects), **Openverse** (everyday subjects).
KartaView was checked at four anchors and returned nothing at any of them.

Where a board contains an image that is **not** from the anchor — because the anchor has no
photograph of the thing the district needs — the table row says so explicitly.

| district | board | images | the defining visual fact the photographs actually showed |
|---|---|---|---|
| **The Spine** | [the-spine/NOTES.md](the-spine/NOTES.md) | 12 | **Two-thirds of the street-level frames have scaffolding in them.** A permanent 4.5 m plywood ceiling over the pavement, lit by warm bulbs all day, is the real ground condition of a pre-war financial district — and there is no overhead wire anywhere. |
| **Bellcross** | [bellcross/NOTES.md](bellcross/NOTES.md) | 12 | **The fronts are painted and the backs are not.** Honey Bath-stone bay fronts in pastel pinks, blues and creams; plain red brick lean-tos and glass roofs behind. And the parked cars leave a running channel of 2.5–4 m — one vehicle wide. |
| **Ash Flats** | [ash-flats/NOTES.md](ash-flats/NOTES.md) | 13 | **The port ground is pale jointed concrete, not black asphalt**, with the old rail let flush into it at an angle — and most of the land is storing school buses, imported cars and empty trailer chassis rather than freight. |
| **Kilnward** | [kilnward/NOTES.md](kilnward/NOTES.md) | 13 | **Bottle kilns are squat, soot-black, iron-banded and jammed between buildings** — not tall red cones in open ground. And the mill roof feature is a clerestory monitor along the ridge, not a sawtooth. |
| **Tern Bar** | [tern-bar/NOTES.md](tern-bar/NOTES.md) | 12 | **The sign is taller than the building.** Freestanding neon pylon signs at the kerb, a boardwalk of diagonal herringbone panels bleached silver, warm pinkish-grey asphalt, and a water tower as the only landmark. |
| **North Point** | [north-point/NOTES.md](north-point/NOTES.md) | 15 | **No footway, no streetlight, no parked cars — except on the scenic switchback, which is bumper-to-bumper for hundreds of metres.** Dry-laid rounded fieldstone walls, a closed maple canopy, and sea fog as a normal daytime condition. |
| **The Reach** | [the-reach/NOTES.md](the-reach/NOTES.md) | 10 | **No centre line at all on the residential streets**, a kerb broken by a driveway apron every 15–20 m, and street trees pollarded into knuckled stubs to keep them off the wires. |
| **Cray Lagoon** | [cray-lagoon/NOTES.md](cray-lagoon/NOTES.md) | 11 | **Salt marsh does not stand up.** The high marsh is a laid mat swirled into 1–2 m cowlick whorls by the tide, gold and cinnamon all winter. Broken timber pile stubs stand in open water with nothing on them. |
| **Fenmoor** | [fenmoor/NOTES.md](fenmoor/NOTES.md) | 10 | **The reedbed stands all winter** as a 3 m wall of pale fawn canes — and the pylons read as many small grey shapes across the whole horizon, not a few big ones. At night: no streetlight, orange murk, a field of red obstruction lights. |

## Anchor problems found — for `MAP_PLAN.md` §4

Three of the sixteen anchor coordinates do not point at the thing they are labelled with.

1. **Ash Flats, (39.2664, −76.5836)** is **Fort McHenry National Monument**, not a container
   port. Geosearch there returns cannons and ramparts. The working terminals are
   **Seagirt ≈ (39.2540, −76.5480)** and **Dundalk ≈ (39.2480, −76.5310)**, with the port
   arterial around **(39.2590, −76.5379)**. Board gathered from those.
2. **North Point, (37.8590, −122.4850)** is **Wolf Ridge / Fort Cronkhite** — a WWII gun
   battery site. It has no switchbacks, no view of the city and no estates. The switchback
   pleasure road is **Conzelman Road, ≈ (37.8280, −122.4900)**; the lighthouse is
   **Point Bonita, ≈ (37.8158, −122.5295)**. Board gathered from those.
3. **Fenmoor, (40.8000, −74.0800)** is in the Meadowlands but its geosearch returns almost
   nothing except photographs of motorway signs taken from the motorway, and the adjacent
   nature reserve returns only bird portraits. The district is buildable from what is here but
   the anchor gives no ground-level access to the marsh at all. If Fenmoor is ever promoted
   above Tier 3 it needs a re-anchor somewhere with dense eye-height coverage of a
   reedbed–landfill–pylon landscape.

Two other coordinates are fine but are not the city the label implies: **Kilnward's
(42.6460, −71.3120) is Lowell, not Lawrence** (which is lucky — Lowell has the canal system the
district needs), and **Tern Bar's (42.0500, −70.1870) is Provincetown**, which has no Mapillary
coverage and whose geosearch is mostly night harbour shots.

## Street-level coverage, honestly

| district | Mapillary at eye height | notes |
|---|---|---|
| The Spine | **strong** (NYC) / **none** (Boston) | Lower Manhattan is densely covered 2014–2023. Downtown Boston returned an empty array at every bbox; that half is all Wikimedia. |
| Bellcross | **strong** (Baltimore) / **thin** (Bristol) | Totterdown has one 2025 sequence on Bath Road and a single 360-derived cluster. The famous steep painted streets have **no coverage** — filled from Geograph. |
| Ash Flats | **strong** | Both the Baltimore port arterial and Red Hook are well covered. |
| Kilnward | **strong** (Providence) / **thin** (Lowell) | Olneyville is dense, including under the viaduct. Lowell has five usable frames. |
| Tern Bar | **good** (Wildwood) / **none** (Provincetown) | One 2015 sequence covers the strip and the cross avenues. |
| North Point | **good** (Newport) / **thin but real** (Marin) | Conzelman Road *does* have coverage — see the caveat below. |
| The Reach | **good** | March 2026 phone sequence on the side streets, 2017–18 dashcam on the arterials. |
| Cray Lagoon | **good** (Chincoteague) / **none** (Barnegat) | The Barnegat anchor is in open water. |
| Fenmoor | **motorway only** | Coverage exists but every frame is shot from the Turnpike at speed. |

**Mapillary trap worth recording:** the API rejects a bounding box larger than roughly 0.02°
with `{"error":{"code":1,"message":"Please reduce the amount of data you're asking for"}}`. A
naive helper that reads `data` and ignores `error` reports this as *zero coverage*. I made that
mistake once (on the Marin Headlands) and it was wrong. **Always search in small tiles, and
always check for `error` in the response.**

**Wikimedia trap:** `upload.wikimedia.org` now returns HTTP 400 for arbitrary thumbnail widths
("Use thumbnail sizes listed on https://w.wiki/GHai"). 1600 px is *not* on the allowed list.
Ask the API for `iiurlwidth=1280` and download the `thumburl` it hands back — do not construct
thumbnail URLs by hand.
