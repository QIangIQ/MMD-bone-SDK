"""Tools for translating, mapping and retargeting MMD bones."""

from .dictionary import BONES, CONVENTIONS, convert, detect_convention, lookup
from .model import load_model, save_model, skeleton
from .ops import (
                  bone_map,
                  convert_model,
                  convert_motion,
                  match_tracks,
                  retarget,
                  translate_model,
                  translate_motion,
)
from .translate import translate_bone, translate_morph
from .vmd import load_vmd, save_vmd

__version__ = "1.0.0"

__all__ = [
    "BONES", "CONVENTIONS", "convert", "detect_convention", "lookup", "load_model",
    "save_model", "skeleton", "bone_map", "convert_model", "convert_motion", "match_tracks",
    "retarget", "translate_model", "translate_motion", "translate_bone", "translate_morph",
    "load_vmd", "save_vmd",
]
