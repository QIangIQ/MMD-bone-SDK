"""Japanese -> English name translation for bones and morphs.

Standard bones come from :mod:`dictionary`. Anything else (hair, skirt,
accessory and physics bones) goes through a word dictionary with longest-match
tokenization, then kana romanization as a fallback. Results that still contain
untranslated kanji are reported so they can be fixed by hand or with a custom
mapping file.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from . import dictionary as d
from .romaji import is_kana, romanize

# Longest match wins, so compound words are listed alongside their parts.
WORDS: dict[str, str] = {
    # body
    "全ての親": "master", "センター": "center", "グルーブ": "groove", "上半身": "upper_body",
    "下半身": "lower_body", "頭": "head", "首": "neck", "顔": "face", "目": "eye", "両目": "eyes",
    "瞳": "pupil", "眉": "brow", "まゆ": "brow", "まつ毛": "eyelash", "睫毛": "eyelash", "舌": "tongue",
    "歯": "teeth", "口": "mouth", "唇": "lip", "あご": "jaw", "顎": "jaw", "頬": "cheek", "鼻": "nose",
    "耳": "ear", "肩": "shoulder", "腕": "arm", "ひじ": "elbow", "肘": "elbow", "手首": "wrist",
    "手": "hand", "指": "finger", "親指": "thumb", "人指": "index", "人差指": "index", "中指": "middle",
    "薬指": "ring", "小指": "little", "胸": "breast", "乳": "breast", "おっぱい": "breast",
    "腹": "belly", "お腹": "belly", "へそ": "navel", "腰": "waist", "尻": "butt", "お尻": "butt",
    "足": "leg", "脚": "leg", "もも": "thigh", "太もも": "thigh", "太腿": "thigh", "ひざ": "knee",
    "膝": "knee", "すね": "shin", "足首": "ankle", "つま先": "toe", "爪先": "toe", "かかと": "heel",
    "踵": "heel", "足先": "toe", "捩": "twist", "捩り": "twist", "ねじり": "twist",
    # hair
    "髪": "hair", "髪の毛": "hair", "前髪": "bangs", "後髪": "back_hair", "後ろ髪": "back_hair",
    "横髪": "side_hair", "サイド": "side", "もみあげ": "sideburn", "アホ毛": "ahoge", "あほ毛": "ahoge",
    "ツインテール": "twintail", "ツインテ": "twintail", "ポニーテール": "ponytail", "ポニテ": "ponytail",
    "おさげ": "braid", "三つ編み": "braid", "みつあみ": "braid", "お団子": "bun", "団子": "bun",
    "毛": "hair",
    # clothing and accessories
    "スカート": "skirt", "服": "clothes", "袖": "sleeve", "そで": "sleeve", "襟": "collar",
    "えり": "collar", "裾": "hem", "すそ": "hem", "ネクタイ": "necktie", "タイ": "tie",
    "リボン": "ribbon", "帽子": "hat", "ぼうし": "hat", "フード": "hood", "マント": "cape",
    "コート": "coat", "ジャケット": "jacket", "ベルト": "belt", "ポケット": "pocket", "ボタン": "button",
    "フリル": "frill", "レース": "lace", "紐": "string", "ひも": "string", "帯": "sash",
    "飾り": "ornament", "アクセ": "accessory", "アクセサリー": "accessory", "ペンダント": "pendant",
    "ネックレス": "necklace", "イヤリング": "earring", "ピアス": "piercing", "鎖": "chain",
    "チェーン": "chain", "鈴": "bell", "花": "flower", "羽": "wing", "翼": "wing", "尻尾": "tail",
    "しっぽ": "tail", "尾": "tail", "ケモミミ": "kemomimi", "猫耳": "cat_ear", "ネコミミ": "cat_ear",
    "うさ耳": "bunny_ear", "ヘッドホン": "headphones", "ヘッドフォン": "headphones", "眼鏡": "glasses",
    "メガネ": "glasses", "めがね": "glasses", "マフラー": "scarf", "スカーフ": "scarf", "手袋": "glove",
    "靴": "shoe", "ブーツ": "boots", "靴下": "sock", "ソックス": "socks", "ニーソ": "knee_socks",
    "パーカー": "parka", "ワンピース": "dress", "ドレス": "dress", "エプロン": "apron",
    "パンツ": "pants", "ズボン": "trousers", "ブラ": "bra", "胸当て": "breastplate",
    # props
    "武器": "weapon", "剣": "sword", "刀": "katana", "鞘": "scabbard", "銃": "gun", "杖": "staff",
    "傘": "umbrella", "旗": "flag", "本": "book", "マイク": "mic", "ギター": "guitar", "ネギ": "leek",
    # positions and modifiers
    "前": "front", "後": "back", "後ろ": "back", "横": "side", "上": "upper", "下": "lower",
    "中": "mid", "内": "inner", "外": "outer", "表": "front", "裏": "back", "先": "tip", "先端": "tip",
    "根元": "root", "根本": "root", "元": "base", "中心": "center", "大": "big", "小": "small",
    "長": "long", "短": "short", "親": "parent", "子": "child", "ダミー": "dummy", "調整": "adjust",
    "補助": "helper", "操作": "control", "制御": "control", "回転": "rotate", "移動": "move",
    "位置": "position", "連動": "link", "追従": "follow", "物理": "physics", "揺れ": "sway",
    "ゆれ": "sway", "光": "light", "ハイライト": "highlight", "目線": "gaze", "視線": "gaze",
    "表情": "expression", "キャンセル": "cancel", "全体": "all", "基準": "base", "ルート": "root",
    # materials, physics and colors
    "肌": "skin", "体": "body", "白目": "eye_white", "口内": "mouth_inner", "影": "shadow",
    "透過": "transparent", "剛体": "rigid", "ジョイント": "joint", "白": "white", "黒": "black",
    "赤": "red", "青": "blue", "緑": "green", "黄": "yellow", "金": "gold", "銀": "silver",
    "骨": "bone", "ボーン": "bone", "の": "",
}

_MAX_WORD = max(map(len, WORDS))
BONE_NAME_LIMIT = 15
_KANJI = re.compile(r"[㐀-鿿豈-﫿]")


@dataclass
class Translation:
    source: str
    result: str
    method: str  # "standard", "words", "unchanged"
    complete: bool  # False when Japanese characters remain


def _has_japanese(s: str) -> bool:
    return bool(_KANJI.search(s)) or any(is_kana(c) for c in s)


def _side_suffix(side: str, style: str) -> str:
    if not side:
        return ""
    return ("." if style == "blender" else "_") + side


def _word_at(s: str, i: int) -> bool:
    return any(s[i:i + n] in WORDS for n in range(1, _MAX_WORD + 1))


def _tokens(s: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        for n in range(min(_MAX_WORD, len(s) - i), 0, -1):
            w = s[i:i + n]
            if w in WORDS:
                if WORDS[w]:
                    out.append(WORDS[w])
                i += n
                break
        else:
            if is_kana(c):
                j = i + 1
                while j < len(s) and is_kana(s[j]) and not _word_at(s, j):
                    j += 1
                out.append(romanize(s[i:j]))
                i = j
            elif c.isascii() and (c.isalnum()):
                j = i
                while j < len(s) and s[j].isascii() and s[j].isalnum():
                    j += 1
                out.append(s[i:j])
                i = j
            elif c in " _.-・":
                i += 1
            else:
                j = i + 1
                while (j < len(s) and not is_kana(s[j]) and not s[j].isascii()
                       and s[j] not in "・" and not _word_at(s, j)):
                    j += 1
                out.append(s[i:j])
                i = j
    return out


def _join(tokens: list[str]) -> str:
    out = ""
    for t in tokens:
        if not out:
            out = t
        elif t.isdigit():
            out += t
        else:
            out += "_" + t
    return out


def translate_words(name: str, style: str = "en") -> Translation:
    s = unicodedata.normalize("NFKC", name).strip()
    side = ""
    if len(s) > 1:
        for i, ch in enumerate(s):
            if ch in ("左", "右"):
                side = "L" if ch == "左" else "R"
                s = s[:i] + s[i + 1:]
                break
    result = _join(_tokens(s)) + _side_suffix(side, style)
    return Translation(name, result, "words", not _has_japanese(result))


ABBREVIATIONS = {
    "accessory": "acc", "ornament": "orn", "front": "fr", "back": "bk", "upper": "up",
    "lower": "lo", "inner": "in", "outer": "out", "middle": "mid", "twist": "tw",
    "adjust": "adj", "control": "ctrl", "position": "pos", "rotate": "rot", "helper": "hlp",
    "physics": "phys", "sleeve": "slv", "ribbon": "rbn", "shoulder": "sh", "twintail": "twin",
    "ponytail": "pony", "necktie": "tie", "highlight": "hl", "expression": "exp",
    "parent": "par", "child": "ch", "center": "ctr", "skirt": "skt", "hair": "hr",
}


def fit_name(name: str, limit: int = BONE_NAME_LIMIT) -> str:
    """Shorten a translated bone name to fit VMD's 15-byte field.

    The same rule is used for models and motions, so a shortened model bone
    and the matching shortened motion track always agree.
    """
    if len(name.encode("cp932", errors="replace")) <= limit:
        return name
    suffix = ""
    m = re.search(r"[._][LR]$", name)
    if m:
        name, suffix = name[:-2], name[-2:]
    words = re.split(r"[ _]", name)
    budget = limit - len(suffix)
    # 1) camelCase instead of separators
    def camel(ws):
        return ws[0] + "".join(w[:1].upper() + w[1:] for w in ws[1:])
    out = camel(words)
    # 2) abbreviate the longest words first
    order = sorted(range(len(words)), key=lambda i: -len(words[i]))
    for i in order:
        if len(out) <= budget:
            break
        base = re.match(r"([a-zA-Z]+)(\d*)$", words[i])
        if base and base.group(1).lower() in ABBREVIATIONS:
            words[i] = ABBREVIATIONS[base.group(1).lower()] + base.group(2)
            out = camel(words)
    if len(out.encode("cp932", errors="replace")) > budget:
        out = out.encode("cp932", errors="replace")[:budget].decode("cp932", errors="ignore")
    return out + suffix


def translate_bone(name: str, style: str = "en", fit: bool = True) -> Translation:
    """Translate one bone name. ``style`` is ``"en"`` or ``"blender"``.

    With ``fit`` (the default) non-standard names are shortened to VMD's
    15-byte limit so motions can still address them.
    """
    if not _has_japanese(name):
        return Translation(name, name, "unchanged", True)
    entry = d.lookup(name, "jp")
    if entry is not None:
        out = entry.name(style)
        if out:
            return Translation(name, out, "standard", True)
    t = translate_words(name, style)
    if fit:
        t.result = fit_name(t.result)
    return t


def translate_morph(name: str) -> Translation:
    if not _has_japanese(name):
        return Translation(name, name, "unchanged", True)
    for key in (name, unicodedata.normalize("NFKC", name)):
        if key in d.MORPH_JP_EN:
            return Translation(name, d.MORPH_JP_EN[key], "standard", True)
    return translate_words(name)


def translate_text(name: str) -> Translation:
    """Generic translation for material, frame, rigid body and joint names."""
    if not _has_japanese(name):
        return Translation(name, name, "unchanged", True)
    return translate_words(name)
