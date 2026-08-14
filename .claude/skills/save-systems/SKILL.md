---
name: save-systems
description: >
  Design save/load for game state — choosing what to serialize, file formats,
  save slots, atomic crash-safe writes, schema versioning and migration, and
  autosave. Engine-neutral. Use when the user mentions save system, save/load,
  game state persistence, save slots, autosave, save file corruption, or
  migrating old saves to a new version.
license: Apache-2.0
compatibility: Platform-neutral. In a browser the store is localStorage, IndexedDB or the File System Access API.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Save systems

A save file is a **serialized snapshot of game state** that survives restarts.
The hard parts aren't writing bytes — they're choosing *what* to save, writing it
so a crash mid-save can't corrupt it, and reading *old* saves after you ship a
patch. Get those three right and the rest is plumbing.

## When to use

- Use to persist progress: player stats, inventory, world flags, settings,
  positions — across sessions and game updates.
- Use to design save slots, quicksave/autosave, and crash-safe writes.
- Use when old save files break after a content/code change (versioning &
  migration).

**When *not* to use:** for the storage API itself. In a browser the options are
`localStorage` (small, synchronous, string-only), IndexedDB (large, asynchronous,
structured-clone) and the File System Access API, and "atomic write" means something
different in each — read their documentation while
applying the patterns here.

## Core workflow

1. **Decide what state is authoritative.** Save the *data* (hp, position, seed,
   unlocked flags), not engine objects or scene nodes. You will reconstruct
   objects from data on load — never serialize live node references.
2. **Define a versioned schema.** Every save embeds a `version` integer. This is
   the single most important field for a game you intend to patch.
3. **Pick a format.** JSON/text for readability and debuggability; a binary
   format for size/speed or mild tamper-resistance. Start with JSON.
4. **Write atomically.** Serialize to a temp file, flush, then rename over the
   real file. A crash leaves either the old save or the new one — never a
   half-written one.
5. **Load defensively.** Read version → migrate up to current → validate →
   instantiate. Keep a backup of the last good save and fall back on parse error.
6. **Autosave on safe boundaries** (level change, checkpoint), throttled, and to a
   separate slot so it can't clobber a manual save.
7. **Verify**: save, fully quit, relaunch, load — and confirm by inspection that
   state matches. Test loading a save from the previous version.

## Patterns

### 1. Serialize state as plain data (not engine objects)

```js
// Build a plain-data object. Each savable thing reports its own state.
function captureState() {
  return {
    version: SAVE_VERSION,                       // ALWAYS stamp the schema version
    player: { hp: player.hp, pos: [player.position.x, player.position.y, player.position.z] },
    inventory: player.inventory.toArray(),       // ids + counts, not live objects
    flags: world.flags,                          // e.g. { met_guard: true }
    seed: world.seed,                            // regenerate procedural content
  };
}

// On load, RECONSTRUCT from the data — do not expect live references back.
function applyState(data) {
  player.hp = data.player.hp;
  player.position.set(...data.player.pos);
  player.inventory.fromArray(data.inventory);
  world.flags = data.flags;
}
// Serialize plain numbers and arrays, never engine objects. A vector class survives
// JSON.stringify as {x,y,z} and comes back as a bare object with no methods, which
// fails later and far from here.
```

### 2. Atomic, crash-safe write (temp + rename)

```js
// There is no atomic rename in a browser. The temp-file-then-rename trick does not
// exist, so crash safety has to come from the storage API you pick.
//
// localStorage: synchronous, string-only, a few MB. A single setItem is effectively
// atomic — but "write two keys and stay consistent" is not, so keep a save in ONE key.
localStorage.setItem("save.slot0", JSON.stringify(data));

// IndexedDB: asynchronous, large, and genuinely transactional — the whole
// transaction commits or none of it does. This is the one to use for real saves.
const tx = db.transaction("saves", "readwrite");
tx.objectStore("saves").put({ id: "slot0", data });
await tx.done;                                   // commits atomically, or aborts

// WRONG: writing a save across several localStorage keys. A tab closed mid-write
// leaves a half-updated save that loads without error and is quietly corrupt.
```

Rename-over-target is atomic on POSIX (same volume); on Windows a replace-by-rename
isn't guaranteed atomic, so keep the previous file as `path + ".bak"` before the
rename — that backup is what actually guarantees you can recover from a bad write.

### 3. Versioned load with migration

```python
SAVE_VERSION = 3

def load_save(raw_bytes):
    data = parse(raw_bytes)                  # JSON/binary -> dict
    v = data.get("version", 0)
    if v > SAVE_VERSION:
        raise NewerSaveError(v)              # save is from a newer build; refuse
    while v < SAVE_VERSION:                   # apply migrations in order, v -> v+1
        data = MIGRATIONS[v](data)
        v += 1
        data["version"] = v
    validate(data)                            # check required keys / ranges
    return data

# Each migration is a pure function from one version's shape to the next.
def migrate_1_to_2(d):
    d["flags"] = {k: True for k in d.pop("completed_quests", [])}  # list -> set-map
    return d
MIGRATIONS = {1: migrate_1_to_2, 2: migrate_2_to_3}
```

### 4. Save slots + throttled autosave

```js
const SLOT_KEY = i => `save.slot${i}`;
const AUTOSAVE_KEY = "save.autosave";            // separate: never clobbers a slot
let autosaveCooldown = 0;

function autosaveIfDue(dt) {
  autosaveCooldown -= dt;
  if (autosaveCooldown > 0) return;
  saveTo(AUTOSAVE_KEY, captureState());
  autosaveCooldown = 60;                         // throttle: at most once a minute
}
// Trigger an immediate autosave on checkpoints and transitions, not mid-combat.
// And save on `visibilitychange` -> hidden, not on `beforeunload`: a mobile tab is
// often killed without ever firing unload, and that is where saves get lost.
```

## Pitfalls

- **Serializing engine objects/node paths** ties saves to scene structure;
  renaming a node breaks every old save. Save data, rebuild objects on load.
- **No version field.** The day you ship a patch, every existing save is a
  guessing game. Stamp `version` from version 1.
- **In-place writes** corrupt saves on crash/power loss. Always temp-write then
  rename; keep a `.bak`.
- **Trusting the file blindly.** Saves get truncated, hand-edited, or
  cloud-synced stale. Validate on load and fall back to backup on failure.
- **Floats and locale.** Text serializers can drop precision or use comma
  decimal separators in some locales. Use a locale-invariant serializer.
- **Autosave clobbering manual saves**, or firing mid-action and saving an
  inconsistent state. Use a dedicated autosave slot and save on safe boundaries.
- **Storing secrets or trusting client saves in multiplayer.** A local save is
  player-controlled; never treat it as authoritative for online state. In a browser it is
  also *erasable* — storage can be cleared by the user or evicted under pressure, so a save
  that only exists in the tab is a save you will lose.

## References

- `references/versioning-and-migration.md` — schema evolution strategies, the
  migration chain, backups/rollback, format trade-offs (JSON vs binary), and a
  load-time validation checklist.

## Related skills

- `procedural-gen` — store the seed to regenerate worlds instead of saving them.