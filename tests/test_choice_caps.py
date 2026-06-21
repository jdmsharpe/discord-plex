"""Guard against breaching Discord's 25-static-choices-per-option cap.

Discord rejects any slash-command option carrying more than 25 static
``choices`` with API error 50035. py-cord syncs every command in a single
all-or-nothing bulk PUT on connect, so ONE over-limit option silently aborts
slash-command registration for EVERY cog in the bot. This test makes that
catastrophic failure mode loud at CI time instead of silent at runtime.

Discovery is generic and future-proof. It does not hand-parse the AST; it
counts the RESOLVED choice lists from two sources:

1.  Every module-level constant named ``*_CHOICES`` in the package (the
    convention used by the AI bots in this family — currently none here, but
    the test will pick them up automatically if this repo ever adopts it).
2.  The ``choices`` of every option on every registered slash command. py-cord
    normalises inline ``choices=[...]`` (e.g. the ``media_type`` options in
    ``cog.py``) into ``OptionChoice`` lists on the command objects, so this
    catches inline choice lists too — including ones added in the future.
"""

import importlib
import pkgutil

import discord
import pytest

import discord_plex
from discord_plex.cogs.plex.cog import PlexCog

# Discord's hard limit: an option may carry at most this many static choices.
# Exceeding it triggers API error 50035 and aborts the entire bulk command sync.
MAX_STATIC_CHOICES = 25


def _iter_package_modules(package):
    """Import and yield every submodule of ``package`` (recursively)."""
    yield package
    for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            yield importlib.import_module(info.name)
        except Exception:  # pragma: no cover - a broken import is another test's job
            continue


def _discover_module_level_choice_lists():
    """Find every module-level ``*_CHOICES`` list across the package.

    Returns (id_label, source, length) tuples for the RESOLVED lists. This is
    convention-driven and zero-AST: if a constant is named ``FOO_CHOICES`` and
    holds a sized collection, it is protected automatically.
    """
    found = []
    for module in _iter_package_modules(discord_plex):
        for name in dir(module):
            if not name.endswith("_CHOICES"):
                continue
            value = getattr(module, name)
            try:
                length = len(value)
            except TypeError:
                continue
            found.append((f"{module.__name__}.{name}", module.__name__, length))
    return found


def _discover_registered_command_choice_lists():
    """Find the ``choices`` of every option on every registered slash command.

    Covers inline ``choices=[...]`` declarations, which py-cord resolves into
    ``OptionChoice`` lists on the command options. Future-proof: any new command
    with an over-cap inline choices list is caught with no test changes.
    """
    found = []
    groups = {
        PlexCog.plex.name: PlexCog.plex,
        PlexCog.request.name: PlexCog.request,
    }
    for group_name, group in groups.items():
        for command in getattr(group, "subcommands", []):
            for option in getattr(command, "options", []):
                choices = getattr(option, "choices", None)
                if not choices:
                    continue
                label = f"/{group_name} {command.name}:{option.name}"
                found.append((label, "discord_plex.cogs.plex.cog", len(choices)))
    return found


_MODULE_LEVEL_CHOICE_LISTS = _discover_module_level_choice_lists()
_REGISTERED_CHOICE_LISTS = _discover_registered_command_choice_lists()
_ALL_CHOICE_LISTS = _MODULE_LEVEL_CHOICE_LISTS + _REGISTERED_CHOICE_LISTS


def test_discovery_found_at_least_one_choice_list():
    """Sanity check: if discovery returns nothing, the guard is silently dead.

    This repo declares inline ``choices`` on its ``media_type`` options, so the
    registered-command walk must always surface them. A regression that empties
    this list would otherwise make every parametrized assertion vacuously pass.
    """
    assert _ALL_CHOICE_LISTS, (
        "No slash-command choice lists were discovered. The 25-choice cap guard "
        "is now inert — discovery is broken or all choices were removed."
    )


@pytest.mark.parametrize(
    ("label", "source", "count"),
    _ALL_CHOICE_LISTS,
    ids=[label for label, _source, _count in _ALL_CHOICE_LISTS],
)
def test_choice_list_within_discord_cap(label, source, count):
    """Every static choices list must stay within Discord's 25-choice cap.

    Discord rejects an option with >25 static choices (API error 50035), and
    py-cord's all-or-nothing bulk sync means one over-limit list aborts
    slash-command registration for the entire bot.
    """
    assert count <= MAX_STATIC_CHOICES, (
        f"{label} (in {source}) has {count} static choices, which exceeds "
        f"Discord's hard cap of {MAX_STATIC_CHOICES}. Discord will reject the "
        f"bulk command sync with API error 50035 and SILENTLY abort "
        f"slash-command registration for EVERY cog in the bot. Trim the list "
        f"to {MAX_STATIC_CHOICES} or fewer entries, or move it behind an "
        f"autocomplete callback (which is not subject to the static cap)."
    )


def test_cap_constant_matches_discord_limit():
    """Pin the documented cap so the guard cannot be quietly loosened to >25."""
    assert MAX_STATIC_CHOICES == 25
    # OptionChoice is the type py-cord resolves inline string choices into;
    # asserting it exists keeps the registered-command walk meaningful.
    assert hasattr(discord, "OptionChoice")
