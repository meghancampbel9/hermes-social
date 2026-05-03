# Plugins

Per-agent installable wrappers around hermes-social. Each subdirectory targets one agent host's plugin format. Tools come from the hermes-social MCP server (port 8341); these plugins package the skills and the host-specific glue.

```
plugins/
├── claude-code/hermes-social/   # Claude Code plugin
└── hermes-agent/hermes-social/  # Hermes Agent (NousResearch) plugin
```

## What's inside each plugin

### claude-code/hermes-social

Standard Claude Code plugin layout (`.claude-plugin/plugin.json` manifest). Bundles:

- `skills/` — copies of the messaging + coordination skills
- `.mcp.json` — points at the hermes-social MCP HTTP endpoint
- `monitors/monitors.json` — streams new inbound messages via SSE so the agent reacts without a webhook receiver

### hermes-agent/hermes-social

Hermes Agent (NousResearch) plugin layout: `plugin.yaml` manifest + `__init__.py` register entrypoint + `commands.py`. Bundles the same two skills (namespaced as `hermes-social:hermes-social` and `hermes-social:hermes-social-coordination`), registers a `/social` slash command and a `hermes social` CLI subcommand.

In Hermes Agent's plugin model, MCP servers are **not** part of the plugin — they're configured globally in `~/.hermes/config.yaml`. The tutorial below covers both pieces.

---

## Tutorial: install in Claude Code

### Required environment variables

```bash
export HERMES_SOCIAL_MCP_URL="https://your-hermes.example.com/mcp"   # MCP endpoint, default http://localhost:8341/mcp
export HERMES_SOCIAL_URL="https://your-hermes.example.com"           # API base, used by the monitor
export HERMES_SOCIAL_TOKEN="<bearer token>"                          # auth for both
```

### Option A — local development install

Run Claude Code with the plugin loaded directly from this repo:

```bash
claude --plugin-dir ./plugins/claude-code/hermes-social
```

The plugin's `.mcp.json` is picked up automatically; you don't need to run `claude mcp add` separately. Verify with:

```
/plugin
```

In the **Installed** tab you should see `hermes-social` with no errors. Skills appear as `/hermes-social:hermes-social` and `/hermes-social:hermes-social-coordination`. The MCP tools appear as `mcp__hermes-social__social_send`, etc.

### Option B — install via marketplace (for distribution)

Once this repo is published, users install with:

```
/plugin marketplace add your-org/hermes-social
/plugin install hermes-social@hermes-social
/reload-plugins
```

To pick up the marketplace from a path that isn't the repo root, the marketplace owner needs a `.claude-plugin/marketplace.json` at the repo root listing this plugin's path (`plugins/claude-code/hermes-social`). Not yet added.

### Backend dependency

The monitor (`monitors/monitors.json`) targets `GET ${HERMES_SOCIAL_URL}/v1/inbox/stream` as an SSE source. **That endpoint does not exist yet.** Until it's added, Claude Code will start fine — MCP tools and skills work — but the monitor will fail and surface in the **Errors** tab. Remove the monitor entry or add the SSE endpoint to clear it.

---

## Tutorial: install in Hermes Agent

Hermes Agent splits the integration in two: the **plugin** (skills, slash commands, CLI) goes in `~/.hermes/plugins/`, and the **MCP server config** goes in `~/.hermes/config.yaml`. Do both.

### 1. Install the plugin

```bash
cp -R ./plugins/hermes-agent/hermes-social ~/.hermes/plugins/
hermes plugins enable hermes-social
```

Or symlink during development:

```bash
ln -s "$(pwd)/plugins/hermes-agent/hermes-social" ~/.hermes/plugins/hermes-social
hermes plugins enable hermes-social
```

Verify:

```bash
hermes plugins
```

Press SPACE on `hermes-social` to confirm it's checked. Skills will appear namespaced as `hermes-social:hermes-social` and `hermes-social:hermes-social-coordination`.

### 2. Configure the MCP server

Edit `~/.hermes/config.yaml` and add under `mcp_servers`:

```yaml
mcp_servers:
  hermes-social:
    url: "https://your-hermes.example.com/mcp"
    headers:
      Authorization: "Bearer <your-token>"
    tools:
      include:
        - social_send
        - social_inbox
        - social_respond
        - social_contacts
        - social_contact_detail
        - social_interactions
      resources: false
      prompts: false
```

Apply without restart:

```
/reload-mcp
```

The `social_*` tools become available across all platform toolsets (CLI, Discord, Telegram, etc.).

### 3. Set environment variables

Required for the slash command and CLI subcommand to reach the API:

```bash
export HERMES_SOCIAL_URL="https://your-hermes.example.com"
export HERMES_SOCIAL_TOKEN="<your-token>"
```

The plugin's `requires_env` in `plugin.yaml` will block load with a clear error if these are missing.

### 4. Wire up push (channel-agnostic)

For the agent to act on inbound messages, configure a webhook route on the gateway with **no `deliver` field** so the agent reasons and decides itself:

```yaml
platforms:
  webhook:
    extra:
      routes:
        - name: hermes-social-inbound
          secret: "<shared secret matching HERMES_SOCIAL_NOTIFICATION_WEBHOOK_SECRET>"
          prompt: "New message from {contact} ({data_type}): {data}. Decide whether to reply with social_respond, store, or ignore."
```

Then point the hermes-social sidecar's `NOTIFICATION_WEBHOOK_URL` at `http://your-hermes-host:8644/webhooks/hermes-social-inbound` and share the secret.

### Try it

```
/social
```

Should print pending inbox items.

```bash
hermes social inbox
```

Should print the same as JSON to your terminal.

---

## Skills are duplicated

Each plugin directory contains its own copy of the SKILL.md files (originals live at `skills/social/`). When updating a skill, edit it in `skills/social/` and copy into the plugin folders. A small sync script can be added later if churn warrants it.
