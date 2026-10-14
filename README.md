# mmd-bone-tools

Command line tools and a Python library for the boring parts of MMD rigging:
translating Japanese bone names, mapping bones between naming conventions and
making downloaded motions fit the model you want to use them on.

Works directly on the binary files (PMX 2.0/2.1, PMD, VMD). No Blender, MMD or
PMXEditor needed, no dependencies beyond Python 3.10+. Files are rewritten byte
for byte except for the names you change.

## Install

```sh
pip install -e .          # from a checkout; installs the `mmdbt` command
python -m mmd_bone_tools  # same thing without installing the script
```

## What it does

| Command | What for |
| --- | --- |
| `mmdbt info FILE` | Format, bone/morph counts, detected naming convention (`--bones` lists them, `--json` for scripts) |
| `mmdbt translate FILE` | Japanese to English bone, morph, material, frame, rigid body and joint names |
| `mmdbt convert FILE --to unity` | Rename bones to another convention: `jp`, `en`, `blender`, `unity`, `vrm`, `mixamo` |
| `mmdbt retarget MOTION.vmd --model MODEL.pmx` | Rename a motion's tracks so they drive this model's bones |
| `mmdbt map MODEL --to unity` | Export a bone map (JSON or CSV) for Unity, Blender or scripts |
| `mmdbt lookup NAME...` | Show one bone in every convention |
| `mmdbt table` | The whole standard bone table as CSV |
| `mmdbt unpack DL.zip` | Extract an MMD download with its Shift-JIS file names intact |
| `mmdbt batch FOLDER` | Translate every PMX/PMD/VMD in a folder, zips included |

### Translate a download

```sh
mmdbt unpack "ミク.zip" -d miku
mmdbt translate miku/ミク.pmx              # fills the English name fields, keeps JP names
mmdbt translate miku/ミク.pmx --rename     # replaces the JP names too
mmdbt translate dance.vmd                  # motion tracks -> English (dance_en.vmd)
mmdbt batch ~/Downloads/mmd -o ~/mmd_en    # everything at once
```

Two modes for models, because MMD matches motions to bones **by name**:

* default: the Japanese names stay, the English (universal) fields are filled.
  Japanese motions keep working and tools that read English names see English.
* `--rename`: the primary names become English. Use English motions with it,
  or run `retarget` on Japanese ones.

Standard bones use the MMD semi-standard English names (`arm_L`, `upper body2`,
`leg IK_R`, `thumb0_L`...). Other bones (hair, skirts, accessories, physics)
are translated word by word (`右スカート前２` -> `skirt_front2_R`), with kana
romanized as a fallback. Anything still containing Japanese is listed as
`untranslated` so you can fix it with a mapping file.

### Make a motion fit a model

```sh
mmdbt retarget dance.vmd --model unity_named.pmx
mmdbt retarget dance.vmd --model tpose.pmx --source-model original.pmx
```

Track matching tries, in order: your `--map` overrides, the exact name, the
standard bone table (so `左腕` finds `arm_L`, `arm.L` or `LeftUpperArm`), the
15-byte truncated form of long names, and finally the English translation.

With `--source-model` (the model the motion was made for) it also corrects
rotations for rest-pose differences, such as an A-pose motion on a T-pose
model, and scales translations by the leg length ratio. Each corrected key is
`q' = R_parent⁻¹ · q · R_bone`, where `R` takes the target's rest bone
direction onto the source's. Bones whose offset differs from their parent's
get a constant key even if the motion never touched them.

The report lists tracks with no matching bone and the model's core bones the
motion does not drive.

### Custom names

Any command that renames accepts `--map FILE`, either JSON
(`{"左髪１": "long_hair_L"}`) or a two-column CSV. Entries there win over
everything else.

## The 15-byte limit

VMD stores bone and morph names in 15-byte Shift-JIS fields. A model bone
whose name is longer can never be animated by a VMD. So:

* translated non-standard bone names are shortened to fit
  (`skirt_front_tip_L` -> `skirtFrontTip_L`), using the same rule for models
  and motions so they still match;
* `convert --to mixamo` / `unity` / `vrm` warns when the result is too long
  (`mixamorig:LeftForeArm`). Those conventions are for exporting to other
  software, not for playing VMDs in MMD;
* truncated names in existing VMDs are matched back to the full model names.

## Conventions

| key | convention | left upper arm |
| --- | --- | --- |
| `jp` | Japanese MMD | `左腕` |
| `en` | English MMD (semi-standard) | `arm_L` |
| `blender` | Blender, mirror-friendly | `arm.L` |
| `unity` | Unity Humanoid avatar slots | `LeftUpperArm` |
| `vrm` | VRM 1.0 humanoid | `leftUpperArm` |
| `mixamo` | Mixamo | `mixamorig:LeftArm` |

MMD-only bones (センター, グルーブ, IK bones, D bones, twist bones...) have no
Unity/VRM/Mixamo slot and are left out of those maps. MMD's 下半身 maps to
Hips and 上半身/上半身2/上半身3 to Spine/Chest/UpperChest. Watch out for
Mixamo's `LeftLeg`: it is the shin, while MMD's `leg_L` is the thigh. Name
lookups are convention-aware for that reason, and the convention is
auto-detected when you do not pass `--from`.

## Library

```python
from mmd_bone_tools import load_model, save_model, load_vmd, save_vmd, ops

model = load_model("miku.pmx")
report = ops.translate_model(model, rename=True)
save_model(model, "miku_en.pmx")

motion = load_vmd("dance.vmd")
ops.retarget(motion, model)
save_vmd(motion, "dance_for_miku_en.vmd")
```

## Development

```sh
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check src tests
```

Tests build PMX/PMD/VMD files byte by byte in `tests/builders.py` and check
that every codec round-trips exactly, plus forward kinematics checks for the
rest-pose retargeting. The codecs were also checked against the sample PMD
and VMD files that ship with three.js (byte-identical round trips).

## Sources and licensing

Everything here was written from the public format descriptions of PMX, PMD
and VMD and the published bone lists of Unity `HumanBodyBones`, VRM 1.0 and
Mixamo. No code or dictionaries were copied from other tools. MIT licensed.
Model and motion files you process keep their own licenses; check them before
redistributing anything you converted.
