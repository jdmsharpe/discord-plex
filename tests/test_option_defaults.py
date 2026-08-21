"""Guard against an option description advertising a default the code no longer uses.

Discord renders an option's description verbatim in the slash-command UI, so a
``(default: X)`` clause is a promise made directly to users. When a "promote the
default" commit changes the option's actual default value and forgets the
description, that promise silently becomes a lie: nothing crashes, nothing logs,
nothing lints, and every user of the command is told the wrong thing until
somebody notices by hand. Four such drifts were found across this bot family in a
single audit, each traceable to exactly that kind of commit. This test makes that
class of drift impossible to merge.

THIS REPO IS THE HONEST-ZERO CASE, AND THE DOCSTRING SAYS SO RATHER THAN HIDING IT.
This repo has exactly two choice-backed options: ``media_type`` on ``/plex search``
(choices ``movie``/``show``/``artist``) and ``media_type`` on ``/request search``
(choices ``movie``/``tv``). **Both default to the empty string** — a "not set"
sentinel that is deliberately absent from their own choice lists, since ``""`` is
none of those values. A default that matches no choice has no canonical display
name, so there is nothing for its ``(default: not set)`` clause to be checked
against, and inventing a name is how false positives get in. That, and nothing
else, is why **no option in this repo is assertable today**: the count is a real
zero, not a discovery failure. Until one of those defaults is promoted to a real
choice, the matcher tests below are what carry the guarantee — they exercise the
acceptance rule directly, against a fixed case table, so the rule is always under
test no matter what discovery finds. Nothing in this file is skipped: the
per-option test is simply not parametrized while the assertable set is empty, and
the empty set is asserted directly instead.

Discovery is generic and future-proof. It does not hand-enumerate commands; it
walks ``vars(PlexCog)`` for every ``discord.SlashCommandGroup``, then every
subcommand of each group, then every option of each subcommand. A group, command
or option added later is covered automatically, with no edits here.

SCOPE IS DELIBERATELY NARROW. An option is asserted over only when it has ALL
FOUR of:

1.  static ``choices`` — so the advertised default has a canonical display name
    to be checked against;
2.  a non-``None`` ``default`` — so there is a real value to resolve;
3.  a ``(default: ...)`` clause in its description — so a claim was actually
    made; and
4.  a default that resolves to one of its OWN choices — so the claim has
    something to be checked against.

An option that clears the first three bars but fails the fourth is UNASSERTABLE.
Unassertable options are counted and named by
``test_unassertable_options_are_named_not_silently_dropped`` — both of this
repo's options land there today — so a reader always sees WHICH options are out
of reach and why, instead of a silent pass. Options with no choices, or with no
default, are out of scope ON PURPOSE. Their effective default is very often
applied downstream — in the command body, in a client wrapper, in a config
object — where introspection cannot see it, and asserting over them produced
roughly 35 false positives when this rule was trialled across the family. A
guard that cries wolf gets muted, which is strictly worse than no guard at all.
Do not widen this rule.

A claim is accepted on exactly four conditions, and nothing else:

*   the lowercased display name appears in the claimed text;
*   the claimed text equals the display name's STEM (the name with any trailing
    parenthetical removed, so ``Foo 1.5 (Preview)`` is matched by ``Foo 1.5``);
*   the claimed text starts with that stem (descriptions sometimes append prose
    after the name, e.g. ``Deep Research; Max for best reports``); or
*   the raw default value is NON-EMPTY and appears in the claimed text
    (descriptions often say ``1:1`` where the display name is ``Square (1:1)``).

EVERY ONE of those matches is anchored by ``NOT_EXTENDED``, and that anchor is
the whole point of this revision. Three unsound acceptances that earlier
revisions of this guard allowed are gone, each because review showed it waved
through exactly the drift this guard exists to catch:

*   ``display_name.startswith(claimed)`` is REMOVED. It accepted a stale claim of
    ``"Foo 1"`` on an option promoted to ``"Foo 1.5"``, because the new name is a
    prefix-superset of the old one.
*   plain substring containment is REMOVED in favour of the anchored search. Bare
    containment accepted a claim that EXTENDS the real name: ``"Claude Opus 5"``
    matches inside a claim of ``"Claude Opus 5.1"``, so promoting 5 to 5.1 and
    leaving the description stale still passed. ``NOT_EXTENDED`` rejects a
    continuation into a longer identifier — a word character, a hyphen, or a dot
    followed by a digit — while still allowing ordinary sentence punctuation,
    because real descriptions write things like
    ``"(default: Claude Opus 5. warning: Opus is expensive!)"``.
*   the raw-value acceptance is GUARDED against an empty value. ``"" in claimed``
    is always ``True``, so an option whose default value was the empty string
    accepted arbitrary wrong text — which is precisely the shape of both options
    in this repo.

All three are pinned as cases in ``_MATCHER_CASES`` so they cannot come back.
"""

import re

import discord
import pytest

from discord_plex.cogs.plex.cog import PlexCog

# The clause this family uses to tell users, in the Discord UI, what happens
# when they omit an option: "Filter by type. (default: not set)".
_DEFAULT_CLAUSE_RE = re.compile(r"\(default:\s*([^)]+)\)", re.IGNORECASE)

# Strips a trailing parenthetical from a choice's display name so that
# "Foo 1.5 (Preview)" can still be matched by a description that says "Foo 1.5".
_PARENTHETICAL_RE = re.compile(r"\s*\(.*")

# Anchor appended to EVERY match below. It rejects a match that the claim
# continues into a longer identifier (a word character, a hyphen, or a dot
# followed by a digit), which is how "Claude Opus 5" used to be accepted by a
# claim of "Claude Opus 5.1". It deliberately still allows ordinary sentence
# punctuation — ". warning:", ";", ",", end-of-string — because real
# descriptions use it. Do not relax this to plain containment.
NOT_EXTENDED = r"(?![\w-])(?!\.\d)(?!\s+\w)"


def _claim_matches(display_name: str, raw_value: object, claimed: str) -> bool:
    """Is ``claimed`` a legitimate spelling of the option's real default?

    Accepts on exactly four conditions — see the module docstring for why each
    one exists, and which three former acceptances were removed as unsound.
    """
    name = (display_name or "").strip().lower()
    value = str(raw_value or "").strip().lower()
    claim = (claimed or "").strip().lower()
    if not name or not claim:
        return False
    stem = _PARENTHETICAL_RE.sub("", name).strip()
    # The display name is quoted somewhere in the claim, and the claim does not
    # extend it into a longer identifier.
    if re.search(re.escape(name) + NOT_EXTENDED, claim):
        return True
    # The claim is the name with its trailing parenthetical trimmed off.
    if stem and claim == stem:
        return True
    # The claim opens with that stem and then adds prose.
    if stem and re.match(re.escape(stem) + NOT_EXTENDED, claim):
        return True
    # The claim uses the raw value's spelling. An empty value must never match,
    # because `""` is contained in every string.
    return bool(value and re.search(re.escape(value) + NOT_EXTENDED, claim))


# Proven matcher cases, shared verbatim across every repo in this family. Each
# row is (display name, raw value, claimed text, expected acceptance, why).
# These run regardless of what discovery finds, which is what keeps this guard
# from ever going vacuous: the RULE is always under test even when no option in
# the repo happens to be assertable — the situation in this repo today.
_MATCHER_CASES = [
    (
        "Gemini 3.7 Flash",
        "gemini-3.7-flash",
        "Gemini 3.7 Flash Pro",
        False,
        "space-extended superset drift: the claim names a longer, different model",
    ),
    ("GPT Image 2", "gpt-image-2", "GPT Image 1.5", False, "real drift"),
    ("GPT Image 1.5", "gpt-image-1.5", "GPT Image 1", False, "prefix-superset drift (v3 hole)"),
    ("Claude Opus 5", "claude-opus-5", "Claude Opus 5.1", False, "SUPERSET drift (v4 hole)"),
    (
        "Claude Opus 5",
        "claude-opus-5",
        "Claude Opus 5. warning: Opus is expensive!",
        True,
        "sentence punctuation after name",
    ),
    (
        "Grok Imagine Video 1.5 (Preview)",
        "grok-imagine-video-1.5-preview",
        "Grok Imagine Video 1.5",
        True,
        "trailing parenthetical trimmed",
    ),
    (
        "Deep Research (Apr 2026)",
        "deep-research-preview-04-2026",
        "Deep Research; Max for best reports",
        True,
        "prose after the stem",
    ),
    ("Square (1:1)", "1:1", "1:1", True, "description uses the raw value"),
    ("Kore (Firm)", "Kore", "Kore", True, "value spelling"),
    ("Gemini 3.7 Flash", "gemini-3.7-flash", "Gemini 3.6 Flash", False, "real drift"),
    ("Anything", "", "total nonsense", False, "empty value must not vacuously accept"),
    (
        "Gemini 3.1 Flash Preview TTS",
        "gemini-3.1-flash-tts-preview",
        "Gemini 2.5 Flash Preview TTS",
        False,
        "real drift",
    ),
]


def _discover_default_claiming_options():
    """Find every choice-backed option whose description advertises a default.

    Walks the cog's slash-command groups generically instead of naming them, so
    future commands and options are protected without touching this test.

    Returns ``(assertable, unassertable)``. Both hold ``(label, claimed, actual,
    resolved_name)`` tuples; ``claimed`` is the text inside the
    ``(default: ...)`` clause and ``actual`` is the option's real default value.
    In ``assertable``, ``resolved_name`` is the display name of the choice whose
    value equals that default. In ``unassertable``, no choice matched the default
    and ``resolved_name`` is ``None``, so there is nothing to check the claim
    against.
    """
    assertable = []
    unassertable = []
    for group in vars(PlexCog).values():
        if not isinstance(group, discord.SlashCommandGroup):
            continue
        for command in getattr(group, "subcommands", []):
            for option in getattr(command, "options", []):
                choices = getattr(option, "choices", None) or []
                actual = getattr(option, "default", None)
                if not choices or actual is None:
                    continue
                match = _DEFAULT_CLAUSE_RE.search(getattr(option, "description", "") or "")
                if match is None:
                    continue
                resolved_name = next((c.name for c in choices if c.value == actual), None)
                label = f"/{group.name} {command.name}:{option.name}"
                entry = (label, match.group(1).strip(), actual, resolved_name)
                if resolved_name is None:
                    unassertable.append(entry)
                else:
                    assertable.append(entry)
    return assertable, unassertable


_ASSERTABLE, _UNASSERTABLE = _discover_default_claiming_options()

# Recorded discovery counts. These are EXACT, not floors.
#
# A ">= N" floor in a repo whose real count IS N is behaviourally identical to a
# non-emptiness check, and it cannot catch a PARTIAL discovery collapse (say a
# py-cord upgrade that moves options off subcommands and halves what the walk
# finds). Written as ">= 0" it can never fail at all. So these are equalities.
#
# UPDATE THESE NUMBERS DELIBERATELY when you add or remove a choice-backed
# option that states a default, or when you promote one of the two `media_type`
# defaults from "" to a real choice (which moves it from unassertable to
# assertable). A mismatch means either a real change to the commands or a
# regression in discovery — and both of those deserve a human look, which is
# exactly why this fails loudly instead of adapting.
EXPECTED_ASSERTABLE = 0
EXPECTED_UNASSERTABLE = 2


def _describe(entries) -> str:
    """Render discovered options for an assertion message, one per line."""
    if not entries:
        return "    (none)"
    return "\n".join(
        f"    {label} claims '(default: {claimed})', real default {actual!r}, "
        f"resolved choice name {resolved!r}"
        for label, claimed, actual, resolved in entries
    )


@pytest.mark.parametrize(
    ("display_name", "raw_value", "claimed", "expected", "why"),
    _MATCHER_CASES,
    ids=[
        f"{name}|{claimed}|{'accept' if expected else 'reject'}"
        for name, _v, claimed, expected, _w in _MATCHER_CASES
    ],
)
def test_claim_matcher_accepts_only_legitimate_spellings(
    display_name, raw_value, claimed, expected, why
):
    """The acceptance rule itself, exercised directly against known-good verdicts.

    This is the guard's backbone, and in this repo it is the ONLY thing carrying
    the guarantee, because no option is assertable yet. It runs whether or not
    discovery finds anything, so the rule can never rot into a no-op. Three rows
    pin defects that earlier revisions shipped: a prefix-superset promotion
    ("Foo 1" -> "Foo 1.5") must be REJECTED, a superset promotion
    ("Claude Opus 5" -> "Claude Opus 5.1") must be REJECTED, and an empty raw
    default value must never vacuously accept arbitrary text. A fourth row pins
    the flip side of the anchor: ordinary sentence punctuation after the name
    must still be ACCEPTED, or the guard starts failing honest descriptions.
    """
    assert _claim_matches(display_name, raw_value, claimed) is expected, (
        f"Matcher regression ({why}): a description claiming '(default: {claimed})' "
        f"on an option whose real default is {raw_value!r} — the choice named "
        f"{display_name!r} — should have been "
        f"{'ACCEPTED' if expected else 'REJECTED'}, but was not. Changing this "
        f"verdict changes what drift the guard lets through; if you meant to, "
        f"update the module docstring's acceptance list too."
    )


def test_discovery_finds_exactly_the_recorded_option_counts():
    """Discovery must find exactly the options this file records, no more and no fewer.

    See ``EXPECTED_ASSERTABLE`` / ``EXPECTED_UNASSERTABLE`` above for why these
    are exact counts rather than a floor, and why a mismatch is meant to stop a
    human rather than be auto-adjusted.
    """
    found = (len(_ASSERTABLE), len(_UNASSERTABLE))
    expected = (EXPECTED_ASSERTABLE, EXPECTED_UNASSERTABLE)
    assert found == expected, (
        f"Discovery found {len(_ASSERTABLE)} assertable and {len(_UNASSERTABLE)} "
        f"unassertable choice-backed option(s) with a '(default: ...)' clause, but "
        f"this file records {EXPECTED_ASSERTABLE} and {EXPECTED_UNASSERTABLE}.\n"
        f"  assertable:\n{_describe(_ASSERTABLE)}\n"
        f"  unassertable:\n{_describe(_UNASSERTABLE)}\n"
        f"Either the commands really changed — in which case update "
        f"EXPECTED_ASSERTABLE / EXPECTED_UNASSERTABLE in the same commit — or the "
        f"cog walk regressed and this guard has quietly lost coverage. Do not "
        f"'fix' this by relaxing it back into a floor."
    )


def test_unassertable_options_are_named_not_silently_dropped():
    """Options out of the guard's reach are counted and named, never silently passed.

    Both of this repo's choice-backed options default to ``""``, which is not one
    of their own choices, so neither resolves to a display name and neither can
    have its ``(default: not set)`` clause checked. That is a real, explainable
    zero — but it is only honest if the options are reported rather than dropped
    on the floor, so the exact count is asserted here and the offenders are named
    in the failure message. Promote either default to a real choice and this
    count drops while ``EXPECTED_ASSERTABLE`` rises.
    """
    assert len(_UNASSERTABLE) == EXPECTED_UNASSERTABLE, (
        f"Expected exactly {EXPECTED_UNASSERTABLE} unassertable choice-backed "
        f"option(s) — the two `media_type` options, whose '' default matches none "
        f"of their own choices — but found {len(_UNASSERTABLE)}:\n"
        f"{_describe(_UNASSERTABLE)}\n"
        f"An option lands here when it states a default in its description but its "
        f"real default resolves to no choice of its own, so there is no display "
        f"name to check the claim against. If one was promoted to a real choice, "
        f"move the count to EXPECTED_ASSERTABLE; if one vanished from discovery "
        f"entirely, the walk is broken."
    )


if _ASSERTABLE:

    @pytest.mark.parametrize(
        ("label", "claimed", "actual", "resolved_name"),
        _ASSERTABLE,
        ids=[label for label, _claimed, _actual, _resolved in _ASSERTABLE],
    )
    def test_option_description_names_its_actual_default(label, claimed, actual, resolved_name):
        """A '(default: X)' clause must name the choice the option actually defaults to.

        Discord shows this text to users verbatim, so a stale clause is wrong
        information in the product, not just a stale comment.
        """
        assert _claim_matches(resolved_name, actual, claimed), (
            f"{label} advertises '(default: {claimed})', but the option actually "
            f"defaults to {actual!r} — the choice named {resolved_name!r}. Discord "
            f"renders that description verbatim, so every user of this command is "
            f"being shown the wrong default. Update the description to name "
            f"{resolved_name!r}, or restore the default to the value the "
            f"description claims."
        )

else:

    def test_no_option_is_assertable_in_this_repo_yet():
        """The zero is asserted directly, so this file never emits a skipped test.

        Parametrizing the per-option test over an empty list would produce a
        SKIPPED result, which reads as "unknown" in CI. Instead the per-option
        test is only defined when there is something to run, and the empty case
        is asserted here as the fact it actually is: this repo's two
        choice-backed options both default to ``""``, which resolves to no
        choice, so nothing is assertable. The matcher tests above hold the line
        until that changes.
        """
        assert not _ASSERTABLE, (
            f"Discovery found {len(_ASSERTABLE)} assertable option(s) where this "
            f"file expects none:\n{_describe(_ASSERTABLE)}\n"
            f"A default was promoted to a real choice — good. Delete this test, "
            f"let the parametrized per-option test take over, and update "
            f"EXPECTED_ASSERTABLE / EXPECTED_UNASSERTABLE to match."
        )
