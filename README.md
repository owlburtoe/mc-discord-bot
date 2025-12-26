# Crafty Discord Bot

A Discord slash-command bot for querying and controlling Minecraft servers managed by **Crafty Controller**.

This bot supports multiple servers, role-based permissions, and runs cleanly in Docker.

---

## Features

- `/mc` slash command with action choices:
  - Status
  - Start
  - Stop
  - Restart
- Supports multiple Minecraft servers
- Optionally restricts which Discord roles can control servers
- Works in a single Discord channel or globally
- Compatible with reverse proxies and containerized environments
- Optional HTTP health endpoint for container orchestration

---

## Requirements

- Discord Bot Token
- Crafty Controller API Token
- Crafty Controller URL
- Python 3.11+ (for local runs) or Docker

Crafty must have API access enabled.

---

## Installation

### Option 1 — Docker Compose (recommended)

1. Clone this repository

   ```bash
   git clone <repo-url>
   cd crafty-discord-bot
   ```
2. Copy the example environment file
   cp example.env .env

3. Edit .env and fill in the values (see configuration section below)

4. Start the bot
   (sudo) docker compose up -d --build

# Configuration

The bot is configured entirely through environment variables.

See example.env for a complete template.

## Discord configuration

**Variable**		**Description**

DISCORD_TOKEN		Bot token from Discord Developer Portal

GUILD_ID		Optional: restrict slash commands to one guild

ALLOWED_CHANNEL_ID	Optional: channel ID where commands are allowed

OWNER_ID		Discord user ID with full permissions

MOD_ROLE_ID		Role allowed control actions
		
## Crafty Controller configuration

**Variable**		**Configuration**

CRAFTY_URL		Base URL of your Crafty Controller

CRAFTY_TOKEN		API token from Crafty


## Defining Minecraft servers

### Servers are mapped by index. Repeat the pattern for multiple servers.

MC_SERVER_<N>_KEY   = short keyword users type

MC_SERVER_<N>_NAME  = pretty name shown in Discord

MC_SERVER_<N>_ID    = server UUID from Crafty

### Example:

MC_SERVER_1_KEY=surv

MC_SERVER_1_NAME=Survival

MC_SERVER_1_ID=00000000-0000-0000-0000-000000000001

## Slash Command Usage

### /mc <server> <action>

Actions:
	•	📊 Status
	•	▶️ Start
	•	⏹️ Stop
	•	🔁 Restart

Server names match the values defined in your environment file.

## Health Check Endpoint (optional)

### GET /health

Response example:

{
  "status": "ok",
  "servers": 3
}

Enable by exposing port 8085 in Docker if needed by your orchestrator.


## Common Issues

Commands not showing up
	•	Ensure the bot has application.commands scope
	•	If using GUILD_ID, the guild must match your server
	•	Wait a few minutes for global command propagation

“Unknown server”
	•	Key/name mismatch between .env and command
	•	Incorrect server UUID

401 / Crafty API failure
	•	API token invalid
	•	Crafty URL incorrect
	•	HTTPS certificate issues if using self-signed certs

