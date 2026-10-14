import pytest

from builders import HUMANOID, build_pmd, build_pmx, build_vmd, vmd_bone
from mmd_bone_tools.binio import FormatError, decode_fixed, encode_fixed
from mmd_bone_tools.model import read_model, skeleton, write_model
from mmd_bone_tools.pmd import read_pmd, write_pmd
from mmd_bone_tools.pmx import read_pmx, write_pmx
from mmd_bone_tools.vmd import read_vmd, write_vmd


@pytest.mark.parametrize("utf8", [False, True])
@pytest.mark.parametrize("sizes", [(1, 1, 1, 1, 1, 1), (2, 2, 2, 2, 2, 2), (4, 4, 4, 4, 4, 4),
                                   (2, 1, 1, 2, 1, 1)])
def test_pmx_roundtrip_is_byte_identical(utf8, sizes):
    data = build_pmx(utf8=utf8, sizes=sizes)
    m = read_pmx(data)
    assert write_pmx(m) == data
    assert [b.name for b in m.bones] == [b[0] for b in HUMANOID]
    assert m.name == "テストモデル" and m.comment_en == "comment"
    assert [x.name for x in m.morphs] == ["まばたき", "あ", "骨", "UV", "照れ"]
    assert [x.name for x in m.materials] == ["肌", "髪"]
    assert m.rigid_bodies[0].name == "髪剛体" and m.joints[0].name == "髪ジョイント"
    assert m.display_frames[1].name_en == "Exp"


def test_pmx_bone_fields():
    m = read_pmx(build_pmx())
    ik = m.bones[13]
    assert ik.is_ik and ik.ik_target == 12 and [link.bone for link in ik.ik_links] == [11, 10]
    assert ik.ik_links[0].limits is not None and ik.ik_links[1].limits is None
    hair = m.bones[14]
    assert hair.inherit_parent == 4 and hair.inherit_weight == 0.5
    assert hair.fixed_axis == (1, 0, 0) and hair.external_key == 7
    assert m.bones[2].tail_bone == 3 and m.bones[4].tail_offset == (0, 1, 0)


def test_pmx_21_soft_body_tail_is_preserved():
    data = build_pmx(version=2.1, soft_body_tail=b"\x00\x00\x00\x00")
    assert write_pmx(read_pmx(data)) == data


def test_pmx_rename_changes_only_names():
    data = build_pmx()
    m = read_pmx(data)
    m.bones[6].name = "arm_L"
    m2 = read_pmx(write_pmx(m))
    assert m2.bones[6].name == "arm_L"
    assert m2.bones[6].position == m.bones[6].position
    assert len(m2.morphs) == 5 and m2.joints[0].name == "髪ジョイント"


def test_bad_files_raise():
    with pytest.raises(FormatError):
        read_pmx(b"nope")
    with pytest.raises(FormatError):
        read_pmx(build_pmx()[:200])
    with pytest.raises(FormatError):
        read_vmd(b"x" * 60)
    with pytest.raises(FormatError):
        read_model(b"hello")


@pytest.mark.parametrize("english,physics", [(True, True), (True, False), (False, False)])
def test_pmd_roundtrip(english, physics):
    data = build_pmd(english=english, physics=physics)
    m = read_pmd(data)
    assert write_pmd(m) == data
    assert m.bones[6].name == "左腕"
    assert m.has_english == english
    assert m.morphs[1].name == "まばたき"


def test_pmd_rename_and_enable_english():
    data = build_pmd(english=False, physics=False)
    m = read_pmd(data)
    from mmd_bone_tools.pmd import enable_english
    enable_english(m)
    m.bones[6].name_en = "arm_L"
    m2 = read_pmd(write_pmd(m))
    assert m2.has_english and m2.bones[6].name_en == "arm_L" and m2.bones[6].name == "左腕"


def test_vmd_roundtrip_with_mmd_padding_and_all_sections():
    bones = [vmd_bone("センター", 0, (1, 2, 3), garbage=True), vmd_bone("左腕", 10, garbage=True)]
    data = build_vmd(bones, [("まばたき", 5, 1.0)], camera=2, ik=[(0, [("左足ＩＫ", 1)])])
    m = read_vmd(data)
    assert write_vmd(m) == data
    assert m.bone_names() == ["センター", "左腕"] and m.bones[0].position == (1, 2, 3)
    assert m.ik[0].states[0].name == "左足ＩＫ"


@pytest.mark.parametrize("sections", ["bones", "morphs", "all"])
def test_vmd_truncated_files_roundtrip(sections):
    data = build_vmd([vmd_bone("頭", 0)], sections=sections)
    assert write_vmd(read_vmd(data)) == data


def test_vmd_long_names_are_truncated_without_splitting_characters():
    m = read_vmd(build_vmd([vmd_bone("頭", 0)]))
    m.bones[0].name = "左人差指先端調整ボーン"  # 22 bytes in Shift-JIS
    out = read_vmd(write_vmd(m))
    assert m.truncated == ["左人差指先端調整ボーン"]
    assert out.bones[0].name == "左人差指先端調"  # 14 bytes, no half character


def test_fixed_field_helpers():
    raw, cut = encode_fixed("あいうえおか", 11)
    assert cut and decode_fixed(raw) == "あいうえお"
    assert decode_fixed(b"\x8d\xb6\x00\xfd\xfd") == "左"


def test_skeleton_directions():
    sk = skeleton(read_model(build_pmx()))
    arm = sk.index("左腕")
    assert sk.direction(arm) == pytest.approx((2.5, -2.5, 0))
    assert sk.parents[arm] == sk.index("左肩")
    pmd_sk = skeleton(read_model(build_pmd()))
    assert pmd_sk.parents[0] == -1 and pmd_sk.names == sk.names


def test_write_model_dispatch():
    for data in (build_pmx(), build_pmd()):
        assert write_model(read_model(data)) == data
