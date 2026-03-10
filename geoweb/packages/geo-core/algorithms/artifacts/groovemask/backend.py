from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


def _source_root() -> Path:
    return Path(__file__).resolve().parents[3] / "source-code" / "groovemask" / "src"


def ensure_groovemask_path() -> None:
    target = str(_source_root())
    if target not in sys.path:
        sys.path.append(target)


@lru_cache(maxsize=1)
def load_backend() -> dict[str, Any]:
    ensure_groovemask_path()

    from borehole_groove_cleaner import GrooveMaskConfig, clean_grooves
    from borehole_groove_cleaner.io import auto_crop_bbox, save_result_bundle

    return {
        "GrooveMaskConfig": GrooveMaskConfig,
        "clean_grooves": clean_grooves,
        "auto_crop_bbox": auto_crop_bbox,
        "save_result_bundle": save_result_bundle,
    }
