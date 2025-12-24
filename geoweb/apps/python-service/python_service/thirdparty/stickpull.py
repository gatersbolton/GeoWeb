from ..core.paths import ensure_stick_pull_path, stick_pull_dir  # side-effect: ensure path

ensure_stick_pull_path()

# 先尝试常规 import；失败则使用按路径加载
try:
    from fix_stick_pull import fix_stick_pull  # type: ignore
    print("成功导入 stick-and-pull 去伪影函数")
except ImportError as e:
    import importlib.util
    import os

    mod_fp = os.path.join(stick_pull_dir(), "fix_stick_pull.py")

    try:
        spec = importlib.util.spec_from_file_location("fix_stick_pull", mod_fp)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法创建 fix_stick_pull 的加载器: {mod_fp}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        fix_stick_pull = getattr(mod, "fix_stick_pull")
        print("按路径加载 stick-and-pull 模块成功")
    except Exception as ee:
        print(f"导入 stick-and-pull 模块失败: {e}")
        print(f"按路径加载 stick-and-pull 模块失败: {ee}")
        print("请确认 packages/geo-core/artifacts/stick-and-pull 下文件可用")
        raise
