import zipfile

from builders import build_pmx, build_vmd, vmd_bone
from mmd_bone_tools import jobs
from mmd_bone_tools.gui import run_translate
from mmd_bone_tools.model import load_model
from mmd_bone_tools.vmd import load_vmd


def test_run_translate_files_folders_and_zips(tmp_path):
    single = tmp_path / "one.pmx"
    single.write_bytes(build_pmx())
    folder = tmp_path / "pack"
    (folder / "sub").mkdir(parents=True)
    (folder / "sub" / "a.vmd").write_bytes(build_vmd([vmd_bone("左腕", 0)]))
    z = tmp_path / "dl.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("m/b.vmd", build_vmd([vmd_bone("センター", 0)]))
    lines = []
    n = run_translate([str(single), str(folder), str(z)], None, "en", True, lines.append)
    assert n == 3
    assert load_model(tmp_path / "one_en.pmx").bones[6].name == "arm_L"
    assert load_vmd(tmp_path / "pack_en" / "sub" / "a.vmd").bone_names() == ["arm_L"]
    assert load_vmd(tmp_path / "dl_en" / "_unpacked" / "dl" / "m" / "b.vmd").bone_names() == ["center"]
    assert lines[-1].startswith("done: 3")


def test_run_translate_into_output_folder_and_skips_bad_files(tmp_path):
    bad = tmp_path / "bad.pmx"
    bad.write_bytes(b"nope")
    good = tmp_path / "good.vmd"
    good.write_bytes(build_vmd([vmd_bone("頭", 0)]))
    out = tmp_path / "out"
    lines = []
    assert run_translate([str(bad), str(good)], str(out), "blender", False, lines.append) == 1
    assert load_vmd(out / "good_en.vmd").bone_names() == ["head"]
    assert any(line.startswith("skipped bad.pmx") for line in lines)


def test_default_out_and_kind(tmp_path):
    assert jobs.default_out("x/a.pmx", "en").name == "a_en.pmx"
    assert jobs.default_out("x/a.vmd", "unity", tmp_path) == tmp_path / "a_unity.vmd"
    assert jobs.kind("A.PMD") == "model"
