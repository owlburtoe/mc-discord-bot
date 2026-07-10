# Crafty Discord Bot

A Discord slash-command bot for querying and controlling Minecraft servers managed by [Crafty Controller](https://gitlab.com/crafty-controller/crafty-4) on GitLab.

This bot supports multiple servers, role-based permissions, and runs cleanly in Docker.

This project is not affiliated with the Crafty Controller team; it simply uses their public API.

This is a personal project shared publicly. I may not respond to issues or feature requests.

---

## Features

- `/mc` slash command with action choices:
  - Status
  - Start
  - Stop
  - Restart
  - Update Executable
- **Auto-discovers servers from Crafty** — new servers appear in `/mc` automatically, no config edits or restarts
- Announces newly added / removed servers in the configured channel
- Supports multiple Minecraft servers
- Optionally restricts which Discord roles can control servers
- Works in a single Discord channel or globally
- Compatible with reverse proxies and containerized environments
- Optional HTTP health endpoint for container orchestration

---

## Requirements

- Discord Bot Token
- Discord bot permissions / scopes
  - OAuth2 scopes: bot, applications.commands
  - No privileged intents are required for basic slash-command usage
- Crafty Controller API Token
- Crafty Controller URL
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (recommended for local runs) or Docker

Crafty must have API access enabled.

---

# Installation

## Docker Compose

### Step 1 — Download the required files

Create a folder and go into it:

```bash
mkdir mc-discord-bot && cd mc-discord-bot
```

Download the Docker Compose file:

```bash
wget -O docker-compose.yml https://raw.githubusercontent.com/owlburtoe/mc-discord-bot/main/docker-compose.yml
```

and the environment template:

```bash
wget -O .env https://raw.githubusercontent.com/owlburtoe/mc-discord-bot/main/example.env
```

### Step 2 — Configure

Open `.env` in your editor and populate it with your values:

- `PUID`/`PGID` (_REQUIRED for Crafty to run properly!!_)
- Discord bot token
- Crafty URL and token

Download the servers template:

```bash
wget -O servers.json https://raw.githubusercontent.com/owlburtoe/mc-discord-bot/main/servers.json.example
```

Open `servers.json` in your editor and define your servers.

### Step 3 — Start the bot

The `docker-compose.yml` file is configured to automatically download the latest secure build directly from the **GitHub Container Registry (`ghcr.io`)**.

Bring it online:

```bash
docker compose up -d
```

_Note: If you are making modifications and prefer to build the bot locally from source rather than pulling the pre-built image, you can use `docker-compose-build.yml` instead._

_The bot won't fully start until all the required variables in `.env` are entered. Crafty will begin to run as long as PUID/PGID and TZ are provided._

To view logs:

```bash
docker compose logs -f
```

### Step 4 - Visit Crafty4

- Visit https://localhost:8443 to access the Controller and start your first server!

- Visit [Crafty Controller](https://gitlab.com/crafty-controller/crafty-4) on GitLab for instructions on starting your first server!

## Development

This project uses [ruff](https://docs.astral.sh/ruff/) for lightning-fast linting and formatting.

### 🧹 Linting

To check for issues and automatically fix what's possible:

```bash
uv run ruff check --fix .
```

### ✨ Formatting

To format the codebase:

```bash
uv run ruff format .
```

## License

- You do not edit the container image
- You update configuration only through .env
- Recreate the container when .env changes

# Configuration

The bot is configured entirely through environment variables.

See example.env for a complete template.

## Discord configuration

|      Variable      | Description                                            |
| :----------------: | :----------------------------------------------------- |
|   DISCORD_TOKEN    | Bot token from Discord Developer Portal                |
|      GUILD_ID      | Optional: Restrict slash commands to one guild         |
| ALLOWED_CHANNEL_ID | Optional: Channel ID where commands are allowed/wanted |
|      OWNER_ID      | Discord user ID with FULL permissions                  |
|    MOD_ROLE_ID     | Role allowed control actions                           |

## Crafty Controller configuration

|   Variable   | Description                        |
| :----------: | :--------------------------------- |
|  CRAFTY_URL  | Base URL of your Crafty Controller |
| CRAFTY_TOKEN | API token made in Crafty           |

## Servers (auto-discovery)

You do **not** need to define servers manually. The bot pulls the live server list
from Crafty (`GET /servers`) on startup and re-checks every `REFRESH_INTERVAL_MINUTES`
(default `5`). Any server you create in Crafty shows up in `/mc` on its own — Discord's
autocomplete is evaluated live, so no slash-command re-sync or container restart is
needed. Deleted servers drop off the list. New and removed servers are announced in
`ALLOWED_CHANNEL_ID` if it is set.

| Variable                   | Description                                                     |
| :------------------------: | :-------------------------------------------------------------- |
| REFRESH_INTERVAL_MINUTES   | How often (minutes) to re-pull the server list. Default: `5`.   |

If Crafty is briefly unreachable, the bot keeps serving the last-known list rather than
going empty.

### Optional offline fallback

`servers.json` (or `MC_SERVERS_JSON`, or the legacy `MC_SERVER_<N>_*` variables) is now
used **only as a seed** if Crafty is unreachable at startup. Once Crafty responds, its
live list takes over. Most setups can leave these unset.

```json
[
  {
    "key": "surv",
    "name": "Survival",
    "id": "00000000-0000-0000-0000-000000000001"
  }
]
```

## Slash Command Usage

###

In Discord: **/mc** <server> <action>

#### Actions:

- 📊 Status
- ▶️ Start
- ⏹️ Stop
- 🔁 Restart

Server names match what they are called in Crafty.

## Health Check Endpoint (optional)

### GET /health

Response example:

```json
{
  "status": "ok",
  "servers": 3,
  "last_refresh_ok": true
}
```

Enable by exposing port 8085 in Docker if needed by your orchestrator.

---

# Common Issues

## Commands not showing up

- Ensure the bot has application.commands scope
- If using GUILD_ID, the guild must match your server
- Wait a few minutes for global command propagation

## “Unknown server”

- Key/name mismatch between .env and command
- Incorrect server UUID

### 401 / Crafty API failure

- API token invalid
- Crafty URL incorrect
- HTTPS certificate issues if using self-signed certs
