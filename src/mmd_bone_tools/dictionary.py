"""Bone naming conventions and the canonical bone table.

Every standard humanoid bone has a canonical id (``"arm"`` with a side, for
example) and a name in each supported convention:

========  ==========================================  ======================
key       convention                                  example (left arm)
========  ==========================================  ======================
jp        Japanese MMD (PMX/PMD/VMD as shipped)       左腕
en        English MMD (semi-standard English names)   arm_L
blender   Blender style, mirror-friendly suffixes     arm.L
unity     Unity Humanoid avatar slots                 LeftUpperArm
vrm       VRM 1.0 humanoid bones                      leftUpperArm
mixamo    Mixamo rig                                  mixamorig:LeftArm
========  ==========================================  ======================

The table below was written for this project from public documentation of
each convention (Unity ``HumanBodyBones``, the VRM 1.0 humanoid spec, the
Mixamo skeleton and the MMD semi-standard bone set). It is not copied from
any other tool.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

CONVENTIONS = ("jp", "en", "blender", "unity", "vrm", "mixamo")

# Each row: canonical id, sided?, then one entry per convention. An entry is a
# primary name followed by optional aliases, separated by "|". Sided rows use
# placeholders: {J} 左/右, {s} L/R, {Side} Left/Right, {side} left/right.
# An empty entry means the convention has no such bone.
_ROWS: list[tuple[str, bool, str, str, str, str, str, str]] = [
    # id, sided, jp, en, blender, unity, vrm, mixamo
    ("master", False, "全ての親", "master|mother|root|all parent", "master|root", "", "", ""),
    ("center", False, "センター", "center|centre", "center", "", "", ""),
    ("groove", False, "グルーブ", "groove", "groove", "", "", ""),
    ("waist", False, "腰", "waist", "waist", "", "", ""),
    ("lower_body", False, "下半身", "lower body|lowerbody|lower_body", "lower_body", "Hips", "hips", "mixamorig:Hips"),
    ("upper_body", False, "上半身", "upper body|upperbody|upper_body", "upper_body", "Spine", "spine", "mixamorig:Spine"),
    ("upper_body2", False, "上半身2", "upper body2|upper body 2|upper_body2", "upper_body2", "Chest", "chest", "mixamorig:Spine1"),
    ("upper_body3", False, "上半身3", "upper body3|upper body 3|upper_body3", "upper_body3", "UpperChest", "upperChest", "mixamorig:Spine2"),
    ("neck", False, "首", "neck", "neck", "Neck", "neck", "mixamorig:Neck"),
    ("head", False, "頭", "head", "head", "Head", "head", "mixamorig:Head"),
    ("head_tip", False, "頭先", "head tip|head_tip", "head_tip", "", "", "mixamorig:HeadTop_End"),
    ("eyes", False, "両目", "eyes|both eyes", "eyes", "", "", ""),
    ("eye", True, "{J}目", "eye_{s}", "eye.{s}", "{Side}Eye", "{side}Eye", "mixamorig:{Side}Eye"),
    ("jaw", False, "あご|顎", "jaw", "jaw", "Jaw", "jaw", ""),
    ("tongue", False, "舌", "tongue", "tongue", "", "", ""),
    ("waist_cancel", True, "腰キャンセル{J}", "waist cancel_{s}|waistcancel_{s}", "waist_cancel.{s}", "", "", ""),
    ("shoulder_p", True, "{J}肩P", "shoulderP_{s}|shoulder p_{s}", "shoulderP.{s}", "", "", ""),
    ("shoulder", True, "{J}肩", "shoulder_{s}", "shoulder.{s}", "{Side}Shoulder", "{side}Shoulder", "mixamorig:{Side}Shoulder"),
    ("shoulder_c", True, "{J}肩C", "shoulderC_{s}|shoulder c_{s}", "shoulderC.{s}", "", "", ""),
    ("arm", True, "{J}腕", "arm_{s}", "arm.{s}", "{Side}UpperArm", "{side}UpperArm", "mixamorig:{Side}Arm"),
    ("arm_twist", True, "{J}腕捩", "arm twist_{s}|armtwist_{s}|arm_twist_{s}", "arm_twist.{s}", "", "", ""),
    ("arm_twist1", True, "{J}腕捩1", "arm twist1_{s}|armtwist1_{s}", "arm_twist1.{s}", "", "", ""),
    ("arm_twist2", True, "{J}腕捩2", "arm twist2_{s}|armtwist2_{s}", "arm_twist2.{s}", "", "", ""),
    ("arm_twist3", True, "{J}腕捩3", "arm twist3_{s}|armtwist3_{s}", "arm_twist3.{s}", "", "", ""),
    ("elbow", True, "{J}ひじ|{J}肘", "elbow_{s}", "elbow.{s}", "{Side}LowerArm", "{side}LowerArm", "mixamorig:{Side}ForeArm"),
    ("wrist_twist", True, "{J}手捩", "wrist twist_{s}|wristtwist_{s}|hand twist_{s}", "wrist_twist.{s}", "", "", ""),
    ("wrist_twist1", True, "{J}手捩1", "wrist twist1_{s}|wristtwist1_{s}", "wrist_twist1.{s}", "", "", ""),
    ("wrist_twist2", True, "{J}手捩2", "wrist twist2_{s}|wristtwist2_{s}", "wrist_twist2.{s}", "", "", ""),
    ("wrist_twist3", True, "{J}手捩3", "wrist twist3_{s}|wristtwist3_{s}", "wrist_twist3.{s}", "", "", ""),
    ("wrist", True, "{J}手首", "wrist_{s}|hand_{s}", "wrist.{s}", "{Side}Hand", "{side}Hand", "mixamorig:{Side}Hand"),
    ("hand_dummy", True, "{J}ダミー", "dummy_{s}", "dummy.{s}", "", "", ""),
    ("thumb0", True, "{J}親指0", "thumb0_{s}", "thumb0.{s}", "{Side}ThumbProximal", "{side}ThumbMetacarpal", "mixamorig:{Side}HandThumb1"),
    ("thumb1", True, "{J}親指1", "thumb1_{s}", "thumb1.{s}", "{Side}ThumbIntermediate", "{side}ThumbProximal", "mixamorig:{Side}HandThumb2"),
    ("thumb2", True, "{J}親指2", "thumb2_{s}", "thumb2.{s}", "{Side}ThumbDistal", "{side}ThumbDistal", "mixamorig:{Side}HandThumb3"),
    ("thumb_tip", True, "{J}親指先", "thumb tip_{s}|thumb3_{s}", "thumb_tip.{s}", "", "", "mixamorig:{Side}HandThumb4"),
    ("index1", True, "{J}人指1|{J}人差指1", "fore1_{s}|index1_{s}", "index1.{s}", "{Side}IndexProximal", "{side}IndexProximal", "mixamorig:{Side}HandIndex1"),
    ("index2", True, "{J}人指2|{J}人差指2", "fore2_{s}|index2_{s}", "index2.{s}", "{Side}IndexIntermediate", "{side}IndexIntermediate", "mixamorig:{Side}HandIndex2"),
    ("index3", True, "{J}人指3|{J}人差指3", "fore3_{s}|index3_{s}", "index3.{s}", "{Side}IndexDistal", "{side}IndexDistal", "mixamorig:{Side}HandIndex3"),
    ("index_tip", True, "{J}人指先|{J}人差指先", "fore tip_{s}|index tip_{s}|fore4_{s}", "index_tip.{s}", "", "", "mixamorig:{Side}HandIndex4"),
    ("middle1", True, "{J}中指1", "middle1_{s}", "middle1.{s}", "{Side}MiddleProximal", "{side}MiddleProximal", "mixamorig:{Side}HandMiddle1"),
    ("middle2", True, "{J}中指2", "middle2_{s}", "middle2.{s}", "{Side}MiddleIntermediate", "{side}MiddleIntermediate", "mixamorig:{Side}HandMiddle2"),
    ("middle3", True, "{J}中指3", "middle3_{s}", "middle3.{s}", "{Side}MiddleDistal", "{side}MiddleDistal", "mixamorig:{Side}HandMiddle3"),
    ("middle_tip", True, "{J}中指先", "middle tip_{s}|middle4_{s}", "middle_tip.{s}", "", "", "mixamorig:{Side}HandMiddle4"),
    ("ring1", True, "{J}薬指1", "third1_{s}|ring1_{s}", "ring1.{s}", "{Side}RingProximal", "{side}RingProximal", "mixamorig:{Side}HandRing1"),
    ("ring2", True, "{J}薬指2", "third2_{s}|ring2_{s}", "ring2.{s}", "{Side}RingIntermediate", "{side}RingIntermediate", "mixamorig:{Side}HandRing2"),
    ("ring3", True, "{J}薬指3", "third3_{s}|ring3_{s}", "ring3.{s}", "{Side}RingDistal", "{side}RingDistal", "mixamorig:{Side}HandRing3"),
    ("ring_tip", True, "{J}薬指先", "third tip_{s}|ring tip_{s}|third4_{s}", "ring_tip.{s}", "", "", "mixamorig:{Side}HandRing4"),
    ("little1", True, "{J}小指1", "little1_{s}|pinky1_{s}", "little1.{s}", "{Side}LittleProximal", "{side}LittleProximal", "mixamorig:{Side}HandPinky1"),
    ("little2", True, "{J}小指2", "little2_{s}|pinky2_{s}", "little2.{s}", "{Side}LittleIntermediate", "{side}LittleIntermediate", "mixamorig:{Side}HandPinky2"),
    ("little3", True, "{J}小指3", "little3_{s}|pinky3_{s}", "little3.{s}", "{Side}LittleDistal", "{side}LittleDistal", "mixamorig:{Side}HandPinky3"),
    ("little_tip", True, "{J}小指先", "little tip_{s}|pinky tip_{s}|little4_{s}", "little_tip.{s}", "", "", "mixamorig:{Side}HandPinky4"),
    ("leg", True, "{J}足", "leg_{s}", "leg.{s}", "{Side}UpperLeg", "{side}UpperLeg", "mixamorig:{Side}UpLeg"),
    ("knee", True, "{J}ひざ|{J}膝", "knee_{s}", "knee.{s}", "{Side}LowerLeg", "{side}LowerLeg", "mixamorig:{Side}Leg"),
    ("ankle", True, "{J}足首", "ankle_{s}", "ankle.{s}", "{Side}Foot", "{side}Foot", "mixamorig:{Side}Foot"),
    ("toe", True, "{J}つま先|{J}爪先", "toe_{s}", "toe.{s}", "", "", "mixamorig:{Side}Toe_End"),
    ("leg_ik_parent", True, "{J}足IK親", "leg IK parent_{s}|leg ik parent_{s}|legIKparent_{s}", "leg_IK_parent.{s}", "", "", ""),
    ("leg_ik", True, "{J}足IK", "leg IK_{s}|leg ik_{s}|legIK_{s}", "leg_IK.{s}", "", "", ""),
    ("toe_ik", True, "{J}つま先IK", "toe IK_{s}|toe ik_{s}|toeIK_{s}", "toe_IK.{s}", "", "", ""),
    ("leg_d", True, "{J}足D", "leg D_{s}|legD_{s}", "leg_D.{s}", "", "", ""),
    ("knee_d", True, "{J}ひざD", "knee D_{s}|kneeD_{s}", "knee_D.{s}", "", "", ""),
    ("ankle_d", True, "{J}足首D", "ankle D_{s}|ankleD_{s}", "ankle_D.{s}", "", "", ""),
    ("toe_ex", True, "{J}足先EX", "toe EX_{s}|toeEX_{s}|toe ex_{s}", "toe_EX.{s}", "{Side}Toes", "{side}Toes", "mixamorig:{Side}ToeBase"),
]

_SIDES = {
    "L": {"J": "左", "s": "L", "Side": "Left", "side": "left"},
    "R": {"J": "右", "s": "R", "Side": "Right", "side": "right"},
}


@dataclass(frozen=True)
class BoneEntry:
    id: str  # canonical id, e.g. "arm" or "arm.L"
    base: str  # id without side
    side: str  # "", "L" or "R"
    names: dict[str, tuple[str, ...]]  # convention -> (primary, *aliases)

    def name(self, convention: str) -> str | None:
        names = self.names.get(convention) or ()
        return names[0] if names else None


def _expand(template: str, side: str) -> tuple[str, ...]:
    if not template:
        return ()
    out = []
    for part in template.split("|"):
        if side:
            for k, v in _SIDES[side].items():
                part = part.replace("{" + k + "}", v)
        out.append(part)
    return tuple(out)


def _build() -> list[BoneEntry]:
    entries = []
    for row in _ROWS:
        base, sided, *cols = row
        for side in (("L", "R") if sided else ("",)):
            names = {conv: _expand(col, side) for conv, col in zip(CONVENTIONS, cols)}
            # MMD tools write full-width digits and "ＩＫ" as often as ASCII
            names["jp"] = names["jp"] + tuple(
                unicodedata.normalize("NFKC", n) for n in names["jp"]
            )
            entries.append(BoneEntry(f"{base}.{side}" if side else base, base, side, names))
    return entries


BONES: list[BoneEntry] = _build()
BY_ID: dict[str, BoneEntry] = {b.id: b for b in BONES}


def _fullwidth_digits(s: str) -> str:
    return s.translate({ord(c): ord(c) + 0xFEE0 for c in "0123456789"}).replace("IK", "ＩＫ")


def jp_display(name: str) -> str:
    """MMD's own standard bones use full-width digits and ＩＫ (e.g. 左親指０)."""
    return _fullwidth_digits(name)


# ---------------------------------------------------------------- matching

_SEP = " _.-"


def strip_namespace(name: str) -> str:
    """``mixamorig:LeftArm`` and ``Armature|mixamorig1:LeftArm`` -> ``LeftArm``."""
    for sep in (":", "|"):
        if sep in name:
            name = name.rsplit(sep, 1)[1]
    return name


def split_side(name: str) -> tuple[str, str]:
    """Return (core, side) with side in "", "L", "R"; core is normalized."""
    s = unicodedata.normalize("NFKC", strip_namespace(name)).strip()
    side = ""
    if s[:1] in ("左", "右"):
        side, s = ("L" if s[0] == "左" else "R"), s[1:]
    elif s[-1:] in ("左", "右") and len(s) > 1:
        side, s = ("L" if s[-1] == "左" else "R"), s[:-1]
    else:
        low = s.lower()
        for word, sd in (("left", "L"), ("right", "R")):
            if low.startswith(word):
                side, s = sd, s[len(word):]
                break
            if low.endswith(word) and len(low) > len(word) and low[-len(word) - 1] in _SEP:
                side, s = sd, s[:-len(word)]
                break
        else:
            if len(s) > 2 and s[1] in _SEP and s[0] in "lLrR":
                side, s = s[0].upper(), s[2:]
            elif len(s) > 2 and s[-2] in _SEP and s[-1] in "lLrR":
                side, s = s[-1].upper(), s[:-2]
    core = "".join(ch for ch in s.lower() if ch not in _SEP)
    return core, side


def _key(name: str) -> tuple[str, str]:
    return split_side(name)


_LOOKUP: dict[str, dict[tuple[str, str], BoneEntry]] = {c: {} for c in CONVENTIONS}
_EXACT: dict[str, dict[str, BoneEntry]] = {c: {} for c in CONVENTIONS}
for _b in BONES:
    for _conv, _names in _b.names.items():
        for _n in _names:
            _LOOKUP[_conv].setdefault(_key(_n), _b)
            _EXACT[_conv].setdefault(_n, _b)
            _EXACT[_conv].setdefault(unicodedata.normalize("NFKC", _n), _b)


def lookup(name: str, convention: str | None = None) -> BoneEntry | None:
    """Find the canonical bone for ``name``.

    With ``convention`` the name is only interpreted in that convention (this
    matters: Mixamo's ``LeftLeg`` is the shin, MMD's ``leg_L`` is the thigh).
    Without it, conventions are tried in order: jp, en, blender, unity, vrm,
    mixamo.
    """
    convs = (convention,) if convention else CONVENTIONS
    nk = unicodedata.normalize("NFKC", name)
    for conv in convs:
        hit = _EXACT[conv].get(name) or _EXACT[conv].get(nk)
        if hit:
            return hit
    key = _key(name)
    for conv in convs:
        hit = _LOOKUP[conv].get(key)
        if hit:
            return hit
    return None


def detect_convention(names) -> str:
    """Guess which convention a list of bone names follows."""
    names = list(names)
    best, best_score = "jp", -1
    for conv in CONVENTIONS:
        score = 0
        for n in names:
            nk = unicodedata.normalize("NFKC", n)
            if n in _EXACT[conv] or nk in _EXACT[conv]:
                score += 3
            elif _key(n) in _LOOKUP[conv]:
                score += 2
        if score > best_score:
            best, best_score = conv, score
    return best


def convert(name: str, dst: str, src: str | None = None) -> str | None:
    """Convert a standard bone name to another convention, or None."""
    entry = lookup(name, src)
    if entry is None:
        return None
    out = entry.name(dst)
    if out and dst == "jp":
        out = jp_display(out) if _uses_fullwidth(entry) else out
    return out


def _uses_fullwidth(entry: BoneEntry) -> bool:
    # MMD's standard names: fingers use full-width digits, IK bones use ＩＫ.
    # 上半身2 and 腕捩1.. are conventionally ASCII.
    return entry.base.startswith(("thumb", "index", "middle", "ring", "little")) or entry.base in ("leg_ik", "toe_ik")


# ------------------------------------------------------------------ morphs

MORPHS: list[tuple[str, str]] = [
    ("まばたき", "blink"), ("笑い", "smile"), ("ウィンク", "wink"), ("ウィンク右", "wink_R"),
    ("ウィンク２", "wink2"), ("ｳｨﾝｸ２右", "wink2_R"), ("ウィンク２右", "wink2_R"),
    ("はぅ", "close><"), ("なごみ", "calm"), ("びっくり", "surprised"), ("じと目", "doubt"),
    ("なぬ！", "nanu"), ("瞳小", "pupil_small"), ("瞳大", "pupil_big"), ("白目", "white_eye"),
    ("星目", "star_eye"), ("はちゅ目", "hachu_eye"), ("ハート", "heart_eye"),
    ("ハイライト消", "highlight_off"), ("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"),
    ("お", "o"), ("ワ", "wa"), ("∧", "mouth_^"), ("ω", "omega"), ("▲", "mouth_triangle"),
    ("□", "mouth_box"), ("にやり", "grin"), ("にっこり", "smile_mouth"), ("ぺろっ", "tongue_out"),
    ("口角上げ", "mouth_up"), ("口角下げ", "mouth_down"), ("口横広げ", "mouth_wide"),
    ("真面目", "serious"), ("困る", "troubled"), ("にこり", "cheerful"), ("怒り", "angry"),
    ("上", "brow_up"), ("下", "brow_down"), ("前", "brow_front"), ("照れ", "blush"),
    ("涙", "tears"), ("青ざめ", "pale"), ("がーん", "shock"), ("恐ろしい子！", "scary"),
]
MORPH_JP_EN = dict(MORPHS)
MORPH_EN_JP = {en: jp for jp, en in MORPHS}
