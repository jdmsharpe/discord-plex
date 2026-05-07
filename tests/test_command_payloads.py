import json

from discord_plex.cogs.plex.cog import PlexCog


def _serialize_command_group_payload(group):
    return {
        "name": group.name,
        "description": group.description,
        "options": [
            {
                "name": command.name,
                "description": command.description,
                "options": [
                    option.to_dict()
                    for option in command.options
                    if option.input_type is not None
                ],
                "type": 1,
                "nsfw": False,
            }
            for command in group.subcommands
        ],
        "nsfw": False,
    }


def test_registered_command_groups_fit_discord_size_limit():
    """Discord rejects any single top-level command payload over 8000 bytes."""

    groups_by_name = {
        PlexCog.plex.name: PlexCog.plex,
        PlexCog.request.name: PlexCog.request,
    }

    assert set(groups_by_name) == {"plex", "request"}
    assert [command.name for command in groups_by_name["plex"].subcommands] == [
        "search",
        "playing",
        "recent",
        "stats",
    ]
    assert [command.name for command in groups_by_name["request"].subcommands] == [
        "search",
        "status",
        "queue",
        "approve",
        "deny",
    ]

    payload_sizes = {
        name: len(
            json.dumps(
                _serialize_command_group_payload(group),
                separators=(",", ":"),
            ).encode("utf-8")
        )
        for name, group in groups_by_name.items()
    }

    assert payload_sizes["plex"] < 8000
    assert payload_sizes["request"] < 8000
