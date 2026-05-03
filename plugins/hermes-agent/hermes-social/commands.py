import json
import os
import urllib.request


def _api_get(path: str) -> dict:
    base = os.environ["HERMES_SOCIAL_URL"].rstrip("/")
    token = os.environ["HERMES_SOCIAL_TOKEN"]
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def social_command(ctx, args: str) -> str:
    """In-session /social — show pending inbox.

    The agent should normally use the social_inbox MCP tool; this slash
    command is a quick human-driven peek at the inbox without prompting
    the LLM.
    """
    items = _api_get("/v1/inbox?status=received&limit=10")
    if not items:
        return "Inbox is empty."
    lines = [f"- {i['contact']}: {i['data_type']} ({i['id'][:8]})" for i in items]
    return "\n".join(lines)


def social_cli(args):
    """Terminal subcommand: `hermes social inbox`."""
    sub = (args[0] if args else "inbox").lower()
    if sub == "inbox":
        items = _api_get("/v1/inbox?limit=20")
        print(json.dumps(items, indent=2))
        return
    print(f"unknown subcommand: {sub}", flush=True)
