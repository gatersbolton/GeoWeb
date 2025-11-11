from ..core.paths import ensure_stressinv_path  # side-effect: ensure path

ensure_stressinv_path()

try:
    # Import Python implementations converted from MATLAB
    from stressinv_ellipticity import invert_global  # type: ignore
    from stressinv_ellipticity_depthwise import invert_depthwise  # type: ignore
    print("成功导入地应力反演相关函数")
except ImportError as e:
    print(f"导入地应力反演函数失败: {e}")
    print("请确认 python/BoreholeEllipStressInv/V1.0/stressinv 目录可用")
    raise


