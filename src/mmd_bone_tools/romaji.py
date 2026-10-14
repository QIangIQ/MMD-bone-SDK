"""Minimal Hepburn romanization for kana, used as a last-resort fallback."""

from __future__ import annotations

_BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ゔ": "vu",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "ゎ": "wa",
}
_SMALL_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
_SMALL_V = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}


def _to_hiragana(text: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)


def is_kana(ch: str) -> bool:
    return "ぁ" <= ch <= "ゖ" or "ァ" <= ch <= "ヺ" or ch == "ー"


def romanize(text: str) -> str:
    h = _to_hiragana(text)
    out: list[str] = []
    i = 0
    while i < len(h):
        c = h[i]
        nxt = h[i + 1] if i + 1 < len(h) else ""
        if c == "っ":
            following = romanize(h[i + 1:i + 2]) if nxt else ""
            out.append(following[:1] if following and following[0] not in "aeiou" else "")
            i += 1
            continue
        if c == "ー":
            prev = "".join(out)
            out.append(prev[-1] if prev and prev[-1] in "aeiou" else "")
            i += 1
            continue
        base = _BASE.get(c)
        if base is None:
            out.append(c)
            i += 1
            continue
        if nxt in _SMALL_Y and base.endswith("i") and len(base) > 1:
            stem = base[:-1]
            if stem in ("sh", "ch", "j"):
                out.append(stem + _SMALL_Y[nxt])
            else:
                out.append(stem + "y" + _SMALL_Y[nxt])
            i += 2
            continue
        if nxt in _SMALL_V and len(base) > 1 and c not in _SMALL_V:
            stem = base[:-1] if base not in ("fu", "vu", "tsu") else base[:-1]
            out.append(stem + _SMALL_V[nxt])
            i += 2
            continue
        out.append(base)
        i += 1
    return "".join(out)
