import pytest

from mmd_bone_tools import dictionary as d
from mmd_bone_tools.translate import translate_bone, translate_morph


@pytest.mark.parametrize("jp,en,blender,unity,vrm,mixamo", [
    ("左腕", "arm_L", "arm.L", "LeftUpperArm", "leftUpperArm", "mixamorig:LeftArm"),
    ("右ひじ", "elbow_R", "elbow.R", "RightLowerArm", "rightLowerArm", "mixamorig:RightForeArm"),
    ("下半身", "lower body", "lower_body", "Hips", "hips", "mixamorig:Hips"),
    ("上半身2", "upper body2", "upper_body2", "Chest", "chest", "mixamorig:Spine1"),
    ("左足", "leg_L", "leg.L", "LeftUpperLeg", "leftUpperLeg", "mixamorig:LeftUpLeg"),
    ("左ひざ", "knee_L", "knee.L", "LeftLowerLeg", "leftLowerLeg", "mixamorig:LeftLeg"),
    ("右親指０", "thumb0_R", "thumb0.R", "RightThumbProximal", "rightThumbMetacarpal",
     "mixamorig:RightHandThumb1"),
    ("左人指３", "fore3_L", "index3.L", "LeftIndexDistal", "leftIndexDistal",
     "mixamorig:LeftHandIndex3"),
])
def test_convert_between_all_conventions(jp, en, blender, unity, vrm, mixamo):
    names = dict(jp=jp, en=en, blender=blender, unity=unity, vrm=vrm, mixamo=mixamo)
    for src, name in names.items():
        for dst, expected in names.items():
            got = d.convert(name, dst, src)
            assert got == expected, (src, name, dst)


def test_leg_means_different_bones_per_convention():
    assert d.lookup("LeftLeg", "mixamo").base == "knee"
    assert d.lookup("leg_L", "en").base == "leg"


@pytest.mark.parametrize("name,expected", [
    ("左足ＩＫ", "leg_ik.L"), ("左足IK", "leg_ik.L"), ("右つま先ＩＫ", "toe_ik.R"),
    ("腰キャンセル左", "waist_cancel.L"), ("左腕捩", "arm_twist.L"), ("右手捩2", "wrist_twist2.R"),
    ("Left Arm", "arm.L"), ("arm.L", "arm.L"), ("L_arm", "arm.L"), ("mixamorig1:RightHand", "wrist.R"),
    ("左ﾀﾞﾐｰ", "hand_dummy.L"), ("上半身２", "upper_body2"),
])
def test_lookup_variants(name, expected):
    assert d.lookup(name).id == expected


def test_jp_output_uses_mmd_standard_widths():
    assert d.convert("thumb1_L", "jp") == "左親指１"
    assert d.convert("leg IK_R", "jp") == "右足ＩＫ"
    assert d.convert("upper body2", "jp") == "上半身2"
    assert d.convert("arm twist1_L", "jp") == "左腕捩1"


def test_detect_convention():
    assert d.detect_convention(["センター", "左腕", "右腕", "髪"]) == "jp"
    assert d.detect_convention(["center", "arm_L", "arm_R", "hair"]) == "en"
    assert d.detect_convention(["arm.L", "arm.R", "elbow.L"]) == "blender"
    assert d.detect_convention(["mixamorig:Hips", "mixamorig:LeftArm"]) == "mixamo"
    assert d.detect_convention(["Hips", "LeftUpperArm", "LeftThumbProximal"]) == "unity"
    assert d.detect_convention(["hips", "leftUpperArm", "leftThumbMetacarpal"]) == "vrm"


def test_table_ids_are_unique_and_both_sides_exist():
    ids = [b.id for b in d.BONES]
    assert len(ids) == len(set(ids))
    for b in d.BONES:
        if b.side == "L":
            assert b.base + ".R" in d.BY_ID


@pytest.mark.parametrize("jp,en", [
    ("左髪１", "hair1_L"), ("右スカート前２", "skirt_front2_R"), ("前髪1", "bangs1"),
    ("ツインテール左3", "twintail3_L"), ("髪の毛先", "hair_tip"), ("ネクタイ1", "necktie1"),
    ("左袖2", "sleeve2_L"), ("尻尾1", "tail1"), ("リボン_右", "ribbon_R"),
    ("センター", "center"), ("左足ＩＫ", "leg IK_L"), ("hair_01", "hair_01"),
])
def test_translate_bone(jp, en):
    t = translate_bone(jp)
    assert t.result == en and t.complete


def test_translate_bone_blender_style_and_fallbacks():
    assert translate_bone("左腕", "blender").result == "arm.L"
    assert translate_bone("左髪１", "blender").result == "hair1.L"
    assert translate_bone("ふわふわ").result == "fuwafuwa"
    t = translate_bone("謎骨")
    assert not t.complete and t.result.endswith("_bone")


def test_translate_morph():
    assert translate_morph("まばたき").result == "blink"
    assert translate_morph("ウィンク２右").result == "wink2_R"
    assert translate_morph("あ").result == "a"
