"""Feed rendering — per-viewer audience + language applied AFTER the gate.

The pipeline produces one canonical, verified broadcast. Each SSE connection
then renders it for its viewer: language via the Translator client (a pure
rendering step on already-verified text) and audience via deterministic
transforms:

- ``fan`` (default)  — the broadcast as produced.
- ``analyst``        — same feed; insights already carry evidence ids,
                       confidence and the Verifier's per-check recount, so the
                       analyst register is structural, not cosmetic.
- ``kids``           — jargon-free: a lexicon rewrites analyst vocabulary into
                       plain language. Deterministic — the same line always
                       simplifies the same way.
- ``ad``             — audio description: commentary is replaced by lines
                       generated from event positions/outcomes
                       (``src/events/audio.py``) and insight frames are
                       suppressed — an AD track describes the action, not the
                       analytics.

None of this mutates session state: two viewers can watch the same match in
different languages and audiences simultaneously.
"""

from __future__ import annotations

import re
from collections import Counter

from src.events.audio import audio_line
from src.events.schema import Event

AUDIENCES = ("fan", "analyst", "kids", "ad")

# Analyst vocabulary → plain language. Applied token-wise, case-insensitive;
# keeps numbers intact (a "0.4 xG" line becomes "0.4 chance quality").
_KIDS_LEXICON = (
    ("expected goals", "chance quality"),
    ("xG", "chance quality"),
    ("PPDA", "pressing intensity"),
    ("pressing intensity", "how hard they're chasing the ball"),
    ("possession", "time on the ball"),
    ("formation", "the team's shape"),
    ("defensive third", "near their own goal"),
    ("final third", "near the other team's goal"),
    ("momentum", "who's on top"),
)


def _kidsify(text: str) -> str:
    out = text
    for term, plain in _KIDS_LEXICON:
        # preserve original casing pattern loosely: match any case, replace
        # with the plain phrase in lower case unless sentence-initial
        idx = out.lower().find(term.lower())
        while idx >= 0:
            replacement = plain.capitalize() if idx == 0 else plain
            out = out[:idx] + replacement + out[idx + len(term) :]
            idx = out.lower().find(term.lower())
    return out


def audience_payload(kind: str, payload: dict, audience: str) -> dict | None:
    """Reshape one frame for an audience. ``None`` suppresses the frame."""
    if audience == "ad":
        if kind in ("insight", "detection"):
            return None  # the AD track describes play, not analytics
        return payload
    if audience == "kids" and kind in ("commentary", "insight"):
        key = "text" if kind == "commentary" else "claim"
        if payload.get(key):
            return {**payload, key: _kidsify(payload[key]), "audience": "kids"}
    return payload


def audio_frames_for(
    frames: list[dict],
    events_by_id: dict[str, Event],
    home_team: str,
    away_team: str,
) -> list[dict]:
    """AD lines for a batch of flat event frames (from the SSE 'events' batch).

    The flat frame only carries ``xg``; the real ``Event`` rows keep
    ``body_part``, ``card``, ``set_piece_type``, ``player_in`` and
    ``formation`` — so lines are generated from the ledger, not the wire shape.
    """
    out = []
    for f in frames:
        e = events_by_id.get(str(f.get("id", "")))
        if e is None:
            continue
        line = audio_line(e, home_team, away_team)
        if line:
            out.append(line)
    return out


def translate_map(texts: list[str], lang: str, cache: dict[tuple[str, str], str]) -> dict[str, str]:
    """Translate unique texts through the cache. Returns text→translated map
    only for entries that changed; unchanged/missing entries keep originals."""
    from src.foundry.translate import get_translator  # noqa: PLC0415

    if lang == "en" or not texts:
        return {}
    todo = [t for t in dict.fromkeys(texts) if (lang, t) not in cache]
    if todo:
        translator = get_translator()
        out = translator.translate(todo, lang) if translator.available else None
        if out:
            for src, dst in zip(todo, out, strict=True):
                cache[(lang, src)] = dst
    return {t: cache[(lang, t)] for t in texts if (lang, t) in cache}


# ---- post-translation integrity (matchcut's verify_translation) -------------
#
# The gate verifies the canonical English line; this checks the translation
# didn't mangle it. Numbers must survive verbatim — including through
# non-Latin digit systems — and every name the source carried must still be
# there. A translation that breaks either falls back to the original text,
# honestly labelled.
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_PLAYER_TOKEN_RE = re.compile(r"\bP\d+\b")
_ENGLISH_ORDINAL_RE = re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.IGNORECASE)
_ORDINALS_OK = {"en", "en-NG", "pcm"}  # languages where English ordinals belong

# Arabic-Indic and Persian digits, and the Arabic decimal separator, read as
# Western digits so a localized ٤-٢ counts as the source's 4-2
_TRANSLATE_DIGITS = {
    **{0x0660 + i: str(i) for i in range(10)},
    **{0x06F0 + i: str(i) for i in range(10)},
    0x066B: ".",
}


def _numbers(text: str) -> list[str]:
    return _NUM_RE.findall(text.translate(_TRANSLATE_DIGITS))


def translation_intact(source: str, translated: str, lang: str) -> list[str]:
    """Problems with a translation, empty if the numbers/names survived."""
    problems = []
    if Counter(_numbers(source)) != Counter(_numbers(translated)):
        problems.append(f"numbers changed: {_numbers(source)} -> {_numbers(translated)}")
    lost = [n for n in _PLAYER_TOKEN_RE.findall(source) if n not in translated]
    if lost:
        problems.append(f"names lost: {lost}")
    if lang not in _ORDINALS_OK and _ENGLISH_ORDINAL_RE.search(translated):
        problems.append("English ordinals left in the translated line")
    return problems


def localized(
    payload: dict,
    key: str,
    lang: str,
    cache: dict[tuple[str, str], str],
) -> dict:
    """Apply translation to one text field, annotating provenance honestly."""
    text = payload.get(key)
    if not text or lang == "en":
        return {**payload, "lang": lang}
    translated = translate_map([text], lang, cache).get(text)
    if translated is None:
        return {**payload, "lang": lang, "translation": "original"}
    problems = translation_intact(text, translated, lang)
    if problems:
        # the translation mangled a fact — serve the verified original instead
        return {
            **payload,
            "lang": lang,
            "translation": "original",
            "translation_problem": problems[0],
        }
    return {**payload, key: translated, "lang": lang, "translation": "translator"}


def render_frame(
    kind: str,
    payload: dict,
    *,
    audience: str,
    lang: str,
    cache: dict[tuple[str, str], str],
    home_team: str = "Home",
    away_team: str = "Away",
    events_by_id: dict[str, Event] | None = None,
) -> list[tuple[str, dict]]:
    """The per-viewer pipeline: audience transform → localization.

    Returns zero or more (kind, payload) frames to emit on the SSE connection.
    """
    shaped = audience_payload(kind, payload, audience)
    if shaped is None:
        return []

    if kind == "events" and audience == "ad":
        # keep the raw batch (pitch viz still needs positions) and append
        # generated audio-description lines for describable events
        frames: list[tuple[str, dict]] = [(kind, payload)]
        for line in audio_frames_for(
            payload.get("batch", []), events_by_id or {}, home_team, away_team
        ):
            frames.append(("commentary", line))
        return frames

    if kind == "commentary":
        return [(kind, localized(shaped, "text", lang, cache))]
    if kind == "insight":
        return [(kind, localized(shaped, "claim", lang, cache))]
    return [(kind, shaped)]
