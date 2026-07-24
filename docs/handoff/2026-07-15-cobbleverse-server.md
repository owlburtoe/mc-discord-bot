# Handoff — Cobbleverse (Cobblemon) server on Crafty

Date: 2026-07-15
Status: **Planning only, paused by user ("deal with it later"). No code changed, nothing created on Crafty.**

## Goal
Create a new Minecraft server on the live Crafty instance and install the Cobbleverse
(Cobblemon / Pokémon) modpack. User authorized **API creation** (not web UI).

## Key facts established this session
- **Live Crafty instance = `.env2`** → `https://crafty.owlburtoe.dev/api/v2` (its token returns HTTP 200).
  - `.env` → `crafty.hernandezfamily.us` is **DEAD** (404 on every path). Ignore it.
- **Cobbleverse is a modpack, not a mod.** Loader = **Fabric**, MC = **1.21.1**.
  - Latest release: **1.7.40** (file ID `8415719`, ~214 MB), uploaded 2026-07-12.
  - CurseForge page: https://www.curseforge.com/minecraft/modpacks/cobbleverse-cobblemon
  - **No dedicated server pack** is published — the CF download is the *client* zip
    (manifest.json of mod IDs + `overrides/`). Real mod jars are CF-gated (API often
    returns `downloadUrl: null`), so server files must be assembled first.
- **The bot in this repo only does status/start/stop/restart/update** (`/mc`). It has
  no create-server or install-mod capability. Server creation is a raw Crafty API job.
- Crafty API import shape (from docs): upload archive, then
  `POST /api/v2/servers` with `create_type: "minecraft_java"` →
  `minecraft_java_create_data.create_type: "import_server"` →
  `import_server_create_data { archive_name, archive_internal_path, jarfile, mem_min, mem_max, server_properties_port }`.

## The blocker that stopped us: RAM
- Machine has **8 GB total**. Cobbleverse wants **6 GB+** comfortably.
- Can't give JVM all 8 (OS + Crafty need ~3 GB headroom). Max safe heap ≈ **5 GB**.
- User balked at buying RAM (DDR prices ~$15+/GB right now). **Decision deferred.**

## Two paths forward (user to pick)
1. **Full pack, lean (5 GB).** User builds server files with **ServerPackCreator**
   (point it at a CurseForge-app / Prism install of Cobbleverse 1.7.40 → produces
   Fabric 1.21.1 server + start.sh + zip). Hand the zip path to Claude → Claude uploads
   to Crafty, `POST import_server`, sets Java 21 / min 3G / max 5G / EULA / start cmd,
   adds to `servers.json`. Risk: tight, may OOM with >1–2 players.
2. **Lean custom Cobblemon server (RECOMMENDED for 8 GB).** Skip the mega-pack. Fabric
   1.21.1 + Cobblemon + a few QoL/world mods, **all from Modrinth (scriptable, no CF
   gating, no ServerPackCreator)**. Runs in 3–4 GB. Claude can fully automate this.

## Exact next step
Ask user: path #1 (test full pack at 5 GB) or #2 (build lean Cobblemon server)?
- If #2: assemble Fabric 1.21.1 + Cobblemon mod set from Modrinth, create server via
  Crafty API on `crafty.owlburtoe.dev`, Java 21, max 5G (or 4G), add to `servers.json`.
- If #1: wait for user's `server-pack.zip` path, then upload + import via API.

## Settings agreed
- Heap: min 3 GB / max **5 GB** (hard ceiling on this box).
- Java **21** (required for MC 1.21.1).
- Server name: **not finalized** (proposed "Cobbleverse"). `servers.json` key TBD.

## Notes / gotchas
- Auto-mode safety classifier blocked DNS/port probing and multi-token API scanning.
  Stick to the single `.env2` token against `crafty.owlburtoe.dev` for one clear purpose.
- `.env2` contains a real Crafty token — do NOT commit it.
