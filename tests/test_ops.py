import math
import zipfile

import pytest

from builders import HUMANOID, build_pmd, build_pmx, build_vmd, vmd_bone
from mmd_bone_tools import ops, quat
from mmd_bone_tools.binio import encode_fixed
from mmd_bone_tools.model import read_model, skeleton, write_model
from mmd_bone_tools.vmd import read_vmd, write_vmd


def model(bones=HUMANOID):
    return read_model(build_pmx(bones))


def test_translate_model_fills_english_names_and_keeps_japanese():
    m = model()
    rep = ops.translate_model(m)
    assert [b.name for b in m.bones][:3] == ["全ての親", "センター", "上半身"]
    en = {b.name: b.name_en for b in m.bones}
    assert en["左腕"] == "arm_L" and en["左足ＩＫ"] == "leg IK_L" and en["左髪１"] == "hair1_L"
    assert m.morphs[0].name_en == "blink" and m.materials[0].name == "肌"
    assert rep.untranslated == []
    m2 = read_model(write_model(m))
    assert m2.bones[6].name_en == "arm_L"


def test_translate_model_rename_and_existing_english_kept():
    bones = list(HUMANOID)
    bones[6] = ("左腕", "LeftArmCustom", *bones[6][2:])
    m = model(bones)
    ops.translate_model(m, rename=True)
    assert m.bones[6].name == "arm_L" and m.bones[6].name_en == "LeftArmCustom"
    m = model(bones)
    ops.translate_model(m, overwrite=True)
    assert m.bones[6].name_en == "arm_L"


def test_translate_model_makes_duplicate_names_unique():
    bones = list(HUMANOID) + [("左髪1", "", (0, 0, 0), 4, (0, 1, 0))]  # ASCII digit twin
    m = model(bones)
    ops.translate_model(m, rename=True)
    names = [b.name for b in m.bones]
    assert "hair1_L" in names and "hair1_L_1" in names and len(set(names)) == len(names)


def test_translate_pmd_model_adds_english_block():
    m = read_model(build_pmd(english=False, physics=False))
    ops.translate_model(m)
    m2 = read_model(write_model(m))
    assert m2.has_english and m2.bones[6].name_en == "arm_L" and m2.morphs[1].name_en == "blink"


def test_custom_mapping_wins(tmp_path):
    p = tmp_path / "map.csv"
    p.write_text("左髪１,long_hair_L\n# comment,x\n", encoding="utf-8")
    m = model()
    ops.translate_model(m, custom=ops.load_mapping(p))
    assert m.bones[14].name_en == "long_hair_L"
    j = tmp_path / "map.json"
    j.write_text('{"左腕": "upperarm_l"}', encoding="utf-8")
    assert ops.load_mapping(j) == {"左腕": "upperarm_l"}


@pytest.mark.parametrize("dst,arm,hips", [
    ("unity", "LeftUpperArm", "Hips"), ("mixamo", "mixamorig:LeftArm", "mixamorig:Hips"),
    ("blender", "arm.L", "lower_body"), ("en", "arm_L", "lower body"),
])
def test_convert_model(dst, arm, hips):
    m = model()
    ops.convert_model(m, dst)
    names = [b.name for b in m.bones]
    assert names[6] == arm and names[9] == hips
    assert all(ord(c) < 128 for n in names for c in n)
    back = read_model(write_model(m))
    ops.convert_model(back, "jp")
    assert [b.name for b in back.bones][:14] == [b[0] for b in HUMANOID][:14]


def test_bone_map_export():
    mp = ops.bone_map(model(), "unity")
    assert mp["左腕"] == "LeftUpperArm" and mp["下半身"] == "Hips" and "左髪１" not in mp


def test_translate_and_convert_motion():
    data = build_vmd([vmd_bone("センター", 0), vmd_bone("左腕", 0), vmd_bone("左腕", 10)],
                     [("まばたき", 0, 1.0)], ik=[(0, [("左足ＩＫ", 1)])])
    mo = read_vmd(data)
    ops.translate_motion(mo)
    assert mo.bone_names() == ["center", "arm_L"] and mo.morph_names() == ["blink"]
    assert mo.ik[0].states[0].name == "leg IK_L"
    mo = read_vmd(write_vmd(mo))
    ops.convert_motion(mo, "jp")
    assert mo.bone_names() == ["センター", "左腕"] and mo.morph_names() == ["まばたき"]
    assert write_vmd(mo) == data


def test_motion_too_long_names_are_reported():
    mo = read_vmd(build_vmd([vmd_bone("左腕", 0)]))
    rep = ops.convert_motion(mo, "mixamo")
    assert rep.too_long == [("bones", "mixamorig:LeftArm")]


def test_match_tracks_handles_conventions_and_truncation():
    targets = ["center", "arm_L", "elbow_L", "mixamo_extra", "左人差指先端調整ボーン"]
    truncated = encode_fixed("左人差指先端調整ボーン", 15)[0].split(b"\x00")[0].decode("cp932")
    got = ops.match_tracks(["センター", "左腕", "左ひじ", truncated, "謎"], targets)
    assert got == {"センター": "center", "左腕": "arm_L", "左ひじ": "elbow_L",
                   truncated: "左人差指先端調整ボーン"}


def _fk(sk, rotations):
    """World rotation of every bone from local VMD rotations (frame 0)."""
    g = {}

    def world(i):
        if i < 0:
            return quat.IDENTITY
        if i not in g:
            g[i] = quat.mul(world(sk.parents[i]), rotations.get(sk.names[i], quat.IDENTITY))
        return g[i]

    return world


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


T_POSE = [list(b) for b in HUMANOID]
T_POSE[7][2] = (4.5, 14, 0)  # elbow level with the arm: T-pose
T_POSE[8][2] = (7.5, 14, 0)
T_POSE[8][4] = (1, 0, 0)
T_POSE = [tuple(b) for b in T_POSE]


def test_retarget_a_pose_motion_onto_t_pose_model():
    src = model()  # A-pose: arm points 45 degrees down
    dst = model(T_POSE)
    ops.convert_model(dst, "en")  # target uses English names
    q_upper = quat.from_axis_angle((0, 0, 1), 0.5)
    q_arm = quat.from_axis_angle((1, 0, 0), -0.4)
    q_elbow = quat.from_axis_angle((0, 1, 0), 0.7)
    data = build_vmd([vmd_bone("上半身", 0, rot=q_upper), vmd_bone("左腕", 0, rot=q_arm),
                      vmd_bone("左ひじ", 0, rot=q_elbow), vmd_bone("センター", 0, pos=(1, 2, 3)),
                      vmd_bone("存在しない", 0)])
    mo = read_vmd(data)
    src_rot = {f.name: f.rotation for f in mo.bones}
    rep = ops.retarget(mo, dst, src)
    assert rep.unmatched == ["存在しない"]
    mo = read_vmd(write_vmd(mo))
    dst_rot = {f.name: f.rotation for f in mo.bones}
    assert set(dst_rot) >= {"upper body", "arm_L", "elbow_L", "center"}
    ss, ts = skeleton(src), skeleton(dst)
    ws, wt = _fk(ss, src_rot), _fk(ts, dst_rot)
    for s_name, t_name in (("左腕", "arm_L"), ("左ひじ", "elbow_L"), ("上半身", "upper body")):
        si, ti = ss.index(s_name), ts.index(t_name)
        posed_src = _unit(quat.rotate(ws(si), ss.direction(si)))
        posed_dst = _unit(quat.rotate(wt(ti), ts.direction(ti)))
        assert posed_dst == pytest.approx(posed_src, abs=1e-5), t_name
    # same leg length, so translations are untouched
    assert next(f for f in mo.bones if f.name == "center").position == pytest.approx((1, 2, 3))


def test_retarget_rest_pose_adds_keys_for_unanimated_offset_bones():
    src, dst = model(), model(T_POSE)
    mo = read_vmd(build_vmd([vmd_bone("センター", 0)]))
    ops.retarget(mo, dst, src)
    names = mo.bone_names()
    assert "左腕" in names and "左ひじ" not in names  # elbow offset equals its parent's
    ss, ts = skeleton(src), skeleton(dst)
    wt = _fk(ts, {f.name: f.rotation for f in mo.bones})
    ti, si = ts.index("左ひじ"), ss.index("左ひじ")
    assert _unit(quat.rotate(wt(ti), ts.direction(ti))) == pytest.approx(_unit(ss.direction(si)), abs=1e-5)


def test_retarget_scales_translation_by_leg_length():
    small = [list(b) for b in HUMANOID]
    for b in small:
        b[2] = tuple(c * 0.5 for c in b[2])
    small = [tuple(b) for b in small]
    mo = read_vmd(build_vmd([vmd_bone("センター", 0, pos=(2, 4, 6))]))
    rep = ops.retarget(mo, model(small), model())
    assert mo.bones[0].position == pytest.approx((1, 2, 3))
    assert any("scaled by 0.5" in n for n in rep.notes)
    mo = read_vmd(build_vmd([vmd_bone("センター", 0, pos=(2, 4, 6))]))
    ops.retarget(mo, model(), scale=2.0)
    assert mo.bones[0].position == pytest.approx((4, 8, 12))


def test_retarget_warns_about_unaddressable_target_names():
    dst = model()
    ops.convert_model(dst, "mixamo")
    mo = read_vmd(build_vmd([vmd_bone("左腕", 0)]))
    rep = ops.retarget(mo, dst)
    assert ("bones", "mixamorig:LeftArm") in rep.too_long and rep.notes


def test_unpack_decodes_shift_jis_names(tmp_path):
    from mmd_bone_tools.archive import extract
    z = tmp_path / "dl.zip"
    sjis = "モデル/ミク.pmx".encode("cp932")
    placeholder = b"x" * len(sjis)
    with zipfile.ZipFile(z, "w") as zf:  # no UTF-8 flag, like Japanese Windows zips
        zf.writestr(placeholder.decode(), b"PMX ")
    z.write_bytes(z.read_bytes().replace(placeholder, sjis))
    files = extract(z, tmp_path / "out")
    assert [f.name for f in files] == ["ミク.pmx"] and files[0].parent.name == "モデル"


def test_unpack_rejects_path_traversal(tmp_path):
    from mmd_bone_tools.archive import extract
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../evil.txt", b"x")
    with pytest.raises(ValueError):
        extract(z, tmp_path / "out")
