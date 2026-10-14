import json
import zipfile

from builders import build_pmd, build_pmx, build_vmd, vmd_bone
from mmd_bone_tools.cli import main
from mmd_bone_tools.model import load_model
from mmd_bone_tools.vmd import load_vmd


def write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_info_json(tmp_path, capsys):
    p = write(tmp_path, "m.pmx", build_pmx())
    assert main(["info", str(p), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["format"] == "PMX" and info["convention"] == "jp" and info["bones"] == 16
    v = write(tmp_path, "a.vmd", build_vmd([vmd_bone("左腕", 3)]))
    assert main(["info", str(v), "--bones"]) == 0
    assert "左腕" in capsys.readouterr().out


def test_translate_model_and_motion(tmp_path):
    p = write(tmp_path, "m.pmx", build_pmx())
    report = tmp_path / "r.json"
    assert main(["translate", str(p), "--rename", "--report", str(report), "-q"]) == 0
    m = load_model(tmp_path / "m_en.pmx")
    assert m.bones[6].name == "arm_L"
    assert json.loads(report.read_text(encoding="utf-8"))["renamed"]
    v = write(tmp_path, "a.vmd", build_vmd([vmd_bone("左腕", 0)], [("まばたき", 0, 1)]))
    out = tmp_path / "out.vmd"
    assert main(["translate", str(v), "-o", str(out), "--style", "blender", "-q"]) == 0
    mo = load_vmd(out)
    assert mo.bone_names() == ["arm.L"] and mo.morph_names() == ["blink"]


def test_convert_and_map(tmp_path, capsys):
    p = write(tmp_path, "m.pmd", build_pmd())
    assert main(["convert", str(p), "--to", "unity", "-q"]) == 0
    assert load_model(tmp_path / "m_unity.pmd").bones[6].name == "LeftUpperArm"
    assert main(["map", str(p), "--to", "mixamo", "--format", "csv"]) == 0
    assert "左腕,mixamorig:LeftArm" in capsys.readouterr().out


def test_retarget(tmp_path):
    target = write(tmp_path, "t.pmx", build_pmx())
    assert main(["convert", str(target), "--to", "en", "-o", str(tmp_path / "t_en.pmx"), "-q"]) == 0
    v = write(tmp_path, "a.vmd", build_vmd([vmd_bone("左腕", 0), vmd_bone("無い", 0)]))
    assert main(["retarget", str(v), "--model", str(tmp_path / "t_en.pmx"), "-o",
                 str(tmp_path / "o.vmd"), "-q"]) == 0
    assert load_vmd(tmp_path / "o.vmd").bone_names() == ["arm_L"]


def test_table_and_lookup(capsys):
    assert main(["table", "jp", "unity"]) == 0
    out = capsys.readouterr().out
    assert "arm.L,左腕,LeftUpperArm" in out and "thumb0.L,左親指０," in out
    assert main(["lookup", "mixamorig:LeftForeArm", "左髪１"]) == 0
    out = capsys.readouterr().out
    assert "jp=左ひじ" in out and "hair1_L" in out


def test_batch_with_zip(tmp_path):
    src = tmp_path / "downloads"
    src.mkdir()
    write(src, "m.pmx", build_pmx())
    with zipfile.ZipFile(src / "motion.zip", "w") as zf:
        zf.writestr("dance/a.vmd", build_vmd([vmd_bone("センター", 0)]))
    assert main(["batch", str(src), "-q"]) == 0
    out = tmp_path / "downloads_en"
    assert load_model(out / "m.pmx").bones[1].name_en == "center"
    assert load_vmd(out / "_unpacked" / "motion" / "dance" / "a.vmd").bone_names() == ["center"]


def test_bad_input_returns_error(tmp_path, capsys):
    p = write(tmp_path, "x.pmx", b"garbage")
    assert main(["info", str(p)]) == 2
    assert "error" in capsys.readouterr().err
