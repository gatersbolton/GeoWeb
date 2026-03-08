from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
import sys
from typing import Any


@dataclass(frozen=True)
class RealESRGANModelSpec:
    model_name: str
    netscale: int
    default_weight_name: str


_MODEL_SPECS: dict[str, RealESRGANModelSpec] = {
    "RealESRGAN_x4plus": RealESRGANModelSpec(
        model_name="RealESRGAN_x4plus",
        netscale=4,
        default_weight_name="RealESRGAN_x4plus.pth",
    ),
    "RealESRGAN_x4plus_anime_6B": RealESRGANModelSpec(
        model_name="RealESRGAN_x4plus_anime_6B",
        netscale=4,
        default_weight_name="RealESRGAN_x4plus_anime_6B.pth",
    ),
    "RealESRGAN_x2plus": RealESRGANModelSpec(
        model_name="RealESRGAN_x2plus",
        netscale=2,
        default_weight_name="RealESRGAN_x2plus.pth",
    ),
    "realesr-general-x4v3": RealESRGANModelSpec(
        model_name="realesr-general-x4v3",
        netscale=4,
        default_weight_name="realesr-general-x4v3.pth",
    ),
}

SUPPORTED_MODEL_NAMES = tuple(sorted(_MODEL_SPECS.keys()))

_GEO_CORE_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SOURCE_ROOT = _GEO_CORE_ROOT / "source-code" / "Real-ESRGAN"
_WEIGHTS_ROOT = _SOURCE_ROOT / "weights"


def source_root() -> Path:
    return _SOURCE_ROOT


def resolve_model_spec(model_name: str) -> RealESRGANModelSpec:
    spec = _MODEL_SPECS.get(model_name)
    if spec is None:
        supported = ", ".join(SUPPORTED_MODEL_NAMES)
        raise ValueError(f"Unsupported Real-ESRGAN model '{model_name}'. Supported: {supported}.")
    return spec


def resolve_model_path(model_name: str, override_path: str | None = None) -> Path:
    resolve_model_spec(model_name)
    if override_path:
        path = Path(override_path)
        if not path.is_absolute():
            path = (_REPO_ROOT / path).resolve()
    else:
        spec = resolve_model_spec(model_name)
        path = _WEIGHTS_ROOT / spec.default_weight_name
    if not path.exists():
        raise FileNotFoundError(f"Real-ESRGAN weight file not found: {path}")
    return path


def _ensure_source_path() -> None:
    target = str(_SOURCE_ROOT)
    if target not in sys.path:
        sys.path.insert(0, target)


def _build_network(model_name: str) -> tuple[Any, int]:
    spec = resolve_model_spec(model_name)
    _ensure_source_path()

    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan.archs.srvgg_arch import SRVGGNetCompact

    if spec.model_name == "RealESRGAN_x4plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    elif spec.model_name == "RealESRGAN_x4plus_anime_6B":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
    elif spec.model_name == "RealESRGAN_x2plus":
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
    elif spec.model_name == "realesr-general-x4v3":
        model = SRVGGNetCompact(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_conv=32,
            upscale=4,
            act_type="prelu",
        )
    else:  # pragma: no cover - guarded by resolve_model_spec
        raise ValueError(f"Unsupported Real-ESRGAN model '{model_name}'.")
    return model, spec.netscale


def _resolve_device(prefer_device: str, gpu_id: int | None) -> tuple[Any, str]:
    _ensure_source_path()
    import torch

    preferred = (prefer_device or "auto").lower()
    if preferred == "cpu":
        return torch.device("cpu"), "cpu"
    if preferred == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("prefer_device=cuda but CUDA is not available.")
        if gpu_id is not None:
            return torch.device(f"cuda:{gpu_id}"), f"cuda:{gpu_id}"
        return torch.device("cuda"), "cuda"

    if torch.cuda.is_available():
        if gpu_id is not None:
            return torch.device(f"cuda:{gpu_id}"), f"cuda:{gpu_id}"
        return torch.device("cuda"), "cuda"
    return torch.device("cpu"), "cpu"


class RealESRGANRunner:
    def __init__(self, upsampler: Any, *, model_name: str, device_label: str) -> None:
        self._upsampler = upsampler
        self.model_name = model_name
        self.device_label = device_label
        self._lock = Lock()

    def enhance(
        self,
        image: Any,
        *,
        outscale: float,
        alpha_upsampler: str,
    ) -> Any:
        with self._lock:
            output, _ = self._upsampler.enhance(
                image,
                outscale=outscale,
                alpha_upsampler=alpha_upsampler,
            )
        return output


@lru_cache(maxsize=8)
def get_realesrgan_runner(
    *,
    model_name: str,
    model_path: str,
    tile: int,
    tile_pad: int,
    pre_pad: int,
    prefer_device: str,
    gpu_id: int | None,
    use_fp32: bool,
) -> RealESRGANRunner:
    _ensure_source_path()

    from realesrgan import RealESRGANer

    model, netscale = _build_network(model_name)
    device, device_label = _resolve_device(prefer_device, gpu_id)
    half = device_label.startswith("cuda") and not use_fp32

    upsampler = RealESRGANer(
        scale=netscale,
        model_path=model_path,
        model=model,
        tile=tile,
        tile_pad=tile_pad,
        pre_pad=pre_pad,
        half=half,
        device=device,
    )
    return RealESRGANRunner(upsampler, model_name=model_name, device_label=device_label)
