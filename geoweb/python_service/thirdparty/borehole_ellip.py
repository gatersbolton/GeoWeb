from ..core.paths import ensure_borehole_path  # side-effect: ensure path

ensure_borehole_path()

try:
    from borehole_ellipticity import process_borehole_ellipticity  # type: ignore
    from vis_wrapper import (  # type: ignore
        generate_all_plots,
        generate_enhanced_plots,
        generate_orientation_histogram,
    )
    print("成功导入 borehole ellipticity 相关函数")
except ImportError as e:
    print(f"导入科研函数失败: {e}")
    print("请确认 python/Borehole ellipticity 下文件可用")
    raise


