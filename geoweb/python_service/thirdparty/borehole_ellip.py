from ..core.paths import ensure_borehole_path, borehole_project_dir  # side-effect: ensure path

ensure_borehole_path()

# 先尝试常规 import；失败则使用按路径加载，增强容器环境下的健壮性
try:
    from borehole_ellipticity import process_borehole_ellipticity  # type: ignore
    from vis_wrapper import (  # type: ignore
        generate_all_plots,
        generate_enhanced_plots,
        generate_orientation_histogram,
    )
    print("成功导入 borehole ellipticity 相关函数")
except ImportError as e:
    # 尝试按绝对路径加载模块
    import importlib.util
    import os

    proj_dir = borehole_project_dir()
    be_fp = os.path.join(proj_dir, "borehole_ellipticity.py")
    vw_fp = os.path.join(proj_dir, "vis_wrapper.py")

    try:
        spec_be = importlib.util.spec_from_file_location("borehole_ellipticity", be_fp)
        if spec_be is None or spec_be.loader is None:
            raise ImportError(f"无法创建 borehole_ellipticity 的加载器: {be_fp}")
        mod_be = importlib.util.module_from_spec(spec_be)
        spec_be.loader.exec_module(mod_be)  # type: ignore[attr-defined]
        process_borehole_ellipticity = getattr(mod_be, "process_borehole_ellipticity")

        spec_vw = importlib.util.spec_from_file_location("vis_wrapper", vw_fp)
        if spec_vw is None or spec_vw.loader is None:
            raise ImportError(f"无法创建 vis_wrapper 的加载器: {vw_fp}")
        mod_vw = importlib.util.module_from_spec(spec_vw)
        spec_vw.loader.exec_module(mod_vw)  # type: ignore[attr-defined]
        generate_all_plots = getattr(mod_vw, "generate_all_plots")
        generate_enhanced_plots = getattr(mod_vw, "generate_enhanced_plots")
        generate_orientation_histogram = getattr(mod_vw, "generate_orientation_histogram")

        print("按路径加载 borehole ellipticity 与 vis_wrapper 成功")
    except Exception as ee:
        print(f"导入科研函数失败: {e}")
        print(f"按路径加载科研函数失败: {ee}")
        print("请确认 python/Borehole ellipticity 下文件可用")
        raise
