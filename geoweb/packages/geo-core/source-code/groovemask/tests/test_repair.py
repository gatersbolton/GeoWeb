from __future__ import annotations

import numpy as np

from borehole_groove_cleaner.config import GrooveMaskConfig
from borehole_groove_cleaner.repair import rowwise_pchip_fill


def test_rowwise_fill_falls_back_when_context_is_missing() -> None:
    gray = np.tile(np.linspace(0.1, 0.9, 16, dtype=np.float32), (4, 1))
    mask = np.zeros_like(gray, dtype=np.uint8)
    mask[:, :3] = 1
    filled, stats = rowwise_pchip_fill(gray, mask, GrooveMaskConfig(mode="clean"))
    assert np.isfinite(filled).all()
    assert stats.linear_rows > 0 or stats.nearest_rows > 0
