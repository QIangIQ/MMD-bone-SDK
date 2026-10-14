# Changelog

## 1.0.0 - 2026-10-14

First stable release.

- **Desktop app** (`MMDBoneTools.exe` on Windows, `mmdbt-gui` or `mmdbt gui` elsewhere)
  with English and Japanese labels: translate files, folders and zip downloads,
  convert bone naming, retarget motions and look up bone names.
- **Standalone Windows executables**, no Python needed.
- **Translate** Japanese bone, morph, material, display frame, rigid body and joint
  names to English in PMX/PMD models and VMD motions. Standard bones use MMD's
  semi-standard English names (`左腕` → `arm_L`); other bones are translated word by
  word with kana romanization as a fallback, and shortened to fit VMD's 15-byte names.
- **Convert** bone names between Japanese MMD, English MMD, Blender (`arm.L`),
  Unity Humanoid, VRM 1.0 and Mixamo (110 standard bones).
- **Retarget** VMD motions onto any model by name, with optional rest-pose
  correction (A-pose to T-pose) and translation scaling from a source model.
- **Unpack** Japanese zip downloads with correct Shift-JIS file names, and
  **batch** translate whole folders.
- Byte-exact PMX 2.0/2.1, PMD and VMD readers and writers; no dependencies.
