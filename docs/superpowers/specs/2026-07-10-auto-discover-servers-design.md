# Auto-Discover Crafty Servers — Design

**Date:** 2026-07-10
**Status:** Approved (pending spec review)

## Problem

Servers are hand-maintained in `servers.json` (`key`/`name`/`id`). Whenever a new
Minecraft server is created in Crafty Controller, someone must manually add its UUID
to `servers.json` and recreate the container before the `/mc` command can see it.

We want the bot to **auto-recognize** servers directly from Crafty so they can be
queried, started, stopped, restarted, and updated with no manual config upkeep.

## Key insight

`/mc` already uses **autocomplete** for the `server` argument, which Discord evaluates
live on every keystroke. New servers therefore appear in the picker **without any
slash-command re-sync**. The only thing that must change is *where the list of servers
comes from*: a live, cached view of Crafty instead of a static file.

## Decisions (from brainstorming)

- **Source of truth:** fully automatic from Crafty's `GET /servers`. `servers.json` is
  demoted to an optional offline seed.
- **Refresh model:** cache + periodic background refresh (not live-per-keystroke).
- **Interval:** env-configurable via `REFRESH_INTERVAL_MINUTES` (default `5`).
- **On API failure:** keep the last-known cache (never go empty on a transient error).
- **Announce new servers:** yes — post to the allowed channel.
- **Announce removed servers:** yes — post to the allowed channel.
- **Manual refresh command:** no (the timer covers it).

## Architecture

Introduce a `ServerRegistry` that owns the cached server list. All read sites
(autocomplete, command lookup, `/health`) read from the registry. A background task
refreshes it on a timer and announces diffs.

```
Crafty GET /servers
        │
        ▼
CraftyClient.list_servers()  ──►  ServerRegistry.refresh()  ──►  cache: {id: {name, id}}
        (normalize)                (diff + swap, keep on fail)          │
                                          │                             ├─► autocomplete
                                     ServerDiff(added, removed)         ├─► command lookup
                                          │                             └─► /health count
                                          ▼
                              background loop announces
                              🆕 added / ➖ removed  → ALLOWED_CHANNEL_ID
```

## Components

### 1. `CraftyClient.list_servers()` — new method in `crafty_api.py`

- `GET {url}/servers`, `timeout=10`, `raise_for_status()`.
- Crafty returns `{"status": "ok", "data": [ {server_id, server_name, ...}, ... ]}`.
- Normalize each entry to `{"id": <server_id>, "name": <server_name>}`.
- Entries missing `server_id` are skipped (logged); missing `server_name` falls back to
  the id string.
- Raises on non-200 / network error (bubbles up to `refresh()`), matching the existing
  `get_stats` style.

### 2. `server_registry.py` — new module

State:
- `_servers: dict[str, dict[str, str]]` keyed by Crafty UUID (`{id: {"name", "id"}}`).
  Keyed by UUID because it is unique; server names can collide.
- `last_refresh_ok: bool`, `last_refresh_error: str | None` (for `/health`).

API:
- `servers -> dict[str, dict[str, str]]` — read accessor for the current cache.
- `async refresh() -> ServerDiff` — calls `client.list_servers()`, builds the new dict,
  diffs against the current cache, atomically swaps it in, returns
  `ServerDiff(added: list[entry], removed: list[entry])`.
  - On success: updates cache, sets `last_refresh_ok = True`.
  - On failure (`list_servers` raised): logs, **keeps existing cache**, sets
    `last_refresh_ok = False` + `last_refresh_error`, returns an **empty** diff.
- `seed(entries: dict)` — populate the cache from a fallback source (used once at startup
  if the first refresh fails); does not emit a diff / announcements.

`ServerDiff` is a small dataclass (`added`, `removed`), each a list of
`{"name", "id"}` entries. `has_changes` convenience property.

### 3. Background refresh loop — in `cogs/minecraft.py`

- `discord.ext.tasks.loop(minutes=settings.refresh_interval_minutes)` decorated method.
- Started in the cog's `cog_load` / `__init__` after an **initial refresh**.
- Each tick: `diff = await registry.refresh()`; if `diff.has_changes`, announce.
- **Announcements** go to `settings.allowed_channel_id`:
  - Added → `🆕 New server detected: **{name}**`
  - Removed → `➖ Server removed: **{name}**`
  - If `allowed_channel_id` is unset or the channel can't be fetched, log and skip
    (never crash the loop). Wrap the announce in try/except.
- The **initial** startup refresh does **not** announce (everything would look "new").

### 4. Startup wiring — `bot.py` / cog load

- Instantiate `ServerRegistry(self.crafty)` and attach it (e.g. `self.registry`).
- Initial refresh:
  1. `diff = await registry.refresh()`.
  2. If it failed **and** the cache is empty **and** `settings.servers` (servers.json /
     `MC_SERVERS_JSON`) has entries → `registry.seed(settings.servers)` as an offline
     fallback, and let the loop retry.
- `/health` reports `registry` count + `last_refresh_ok` instead of
  `len(settings.servers)`:
  ```json
  { "status": "ok", "servers": 3, "last_refresh_ok": true }
  ```

### 5. Config — `config.py`

- Add `refresh_interval_minutes: int = Field(5, alias="REFRESH_INTERVAL_MINUTES")`.
- Keep the existing `servers` property (now used only as the offline seed).

## Changes to existing code

| File | Change |
|------|--------|
| `crafty_api.py` | Add `list_servers()`. |
| `server_registry.py` | New module: `ServerRegistry`, `ServerDiff`. |
| `cogs/minecraft.py` | Read servers from `registry` (autocomplete + lookup); add the `tasks.loop` refresher + announcements; accept `registry` in `__init__`. |
| `bot.py` | Build `ServerRegistry`, run initial refresh + offline-seed fallback, pass it to the cog, update `/health`. |
| `config.py` | Add `REFRESH_INTERVAL_MINUTES`. |
| `example.env` / `README.md` | Document `REFRESH_INTERVAL_MINUTES` and the new auto-discovery behavior; note `servers.json` is now an optional fallback. |

`servers.json` and the legacy `MC_SERVER_N_*` parsing stay in place purely as an
offline seed — no runtime dependency on them.

## Error handling

- `list_servers` raises on API/network error → `refresh()` catches, logs, keeps cache,
  flags `last_refresh_ok = False`.
- Malformed server entry → skipped + logged, refresh continues with the rest.
- Announcement failure (no channel, missing perms, fetch error) → caught + logged; the
  loop keeps running.
- Command lookup against an empty registry → existing "❌ Unknown server" path already
  handles it.

## Testing

- **`list_servers`** (`tests/test_crafty_api.py`, mirrors existing mocked-session style):
  - parses a mocked `data[]` into normalized `{"id","name"}`;
  - skips an entry missing `server_id`;
  - raises `ClientError` on failure.
- **`ServerRegistry`** (`tests/test_server_registry.py`, new):
  - first `refresh()` populates cache and returns all as `added`;
  - a second `refresh()` with one server added / one removed returns exactly that diff;
  - `refresh()` when `list_servers` raises keeps the previous cache, returns an empty
    diff, sets `last_refresh_ok = False`;
  - `seed()` populates without producing a diff.
- Existing `test_config.py` / cog behavior remain green (registry is additive).

## Out of scope

- Manual `/mc refresh` action.
- Editing display names / short keys per server (Crafty's name is used verbatim).
- Reacting to Crafty webhooks / push events (polling only).
```
