from pathlib import Path

PLUGIN_DIR = Path(__file__).parent


def register(ctx):
    ctx.register_skill("hermes-social", PLUGIN_DIR / "skills" / "hermes-social")
    ctx.register_skill(
        "hermes-social-coordination",
        PLUGIN_DIR / "skills" / "hermes-social-coordination",
    )

    from . import commands

    ctx.register_command("social", commands.social_command)
    ctx.register_cli_command("social", commands.social_cli)
