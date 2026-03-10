import os
import sys


def repo_root() -> str:
    """Return repository root based on current file location."""
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def borehole_project_dir() -> str:
    """Return path to 'packages/compute/borehole-ellipticity' project."""
    return os.path.join(repo_root(), 'packages', 'compute', 'borehole-ellipticity')


def borehole_data_dir() -> str:
    """Return path to 'packages/compute/borehole-ellipticity/data' directory."""
    return os.path.join(borehole_project_dir(), 'data')


def ensure_borehole_path() -> None:
    """Ensure the borehole project dir is in sys.path."""
    target = borehole_project_dir()
    target = os.path.normpath(target)
    if target not in sys.path:
        sys.path.append(target)


# Ensure path immediately on import
ensure_borehole_path()


def stressinv_root_dir() -> str:
    """Return path to 'packages/compute/stress-inversion/V1.0' project root."""
    return os.path.join(repo_root(), 'packages', 'compute', 'stress-inversion', 'V1.0')


def stressinv_module_dir() -> str:
    """Return path to 'packages/compute/stress-inversion/V1.0/stressinv' for Python imports."""
    return os.path.join(stressinv_root_dir(), 'stressinv')


def stressinv_data_dir() -> str:
    """Return path to 'packages/compute/stress-inversion/V1.0/data' directory."""
    return os.path.join(stressinv_root_dir(), 'data')


def ensure_stressinv_path() -> None:
    """Ensure the stress inversion project module dir is in sys.path."""
    target = os.path.normpath(stressinv_module_dir())
    if target not in sys.path:
        sys.path.append(target)


def geo_core_artifacts_dir() -> str:
    """Return path to legacy geo-core source-code directory."""
    return os.path.join(repo_root(), 'packages', 'geo-core', 'source-code')


def stick_pull_dir() -> str:
    """Return path to legacy 'stick-and-pull' source implementation directory."""
    return os.path.join(geo_core_artifacts_dir(), 'stick-and-pull')


def stick_pull_demo_image() -> str:
    """Return path to default stick-and-pull demo image."""
    return os.path.join(stick_pull_dir(), 'stick_pull.png')


def ensure_stick_pull_path() -> None:
    """Ensure the stick-and-pull artifact dir is in sys.path for imports."""
    target = os.path.normpath(stick_pull_dir())
    if target not in sys.path:
        sys.path.append(target)


# Ensure path immediately on import for stick-and-pull helpers
ensure_stick_pull_path()


def geo_core_package_dir() -> str:
    """Return path to 'packages/geo-core' package root."""
    return os.path.join(repo_root(), 'packages', 'geo-core')


def ensure_geo_core_path() -> None:
    """Ensure geo-core package root is in sys.path so 'algorithms' can be imported."""
    target = os.path.normpath(geo_core_package_dir())
    if target not in sys.path:
        sys.path.append(target)


# Ensure path immediately on import for geo-core algorithm framework.
ensure_geo_core_path()


def geo_core_dlis_dir() -> str:
    """Return path to legacy DLIS sample source directory."""
    return os.path.join(geo_core_artifacts_dir(), 'dlis')


def dlis_demo_dir() -> str:
    """Return path to bundled DLIS demo raw directory."""
    return os.path.join(geo_core_dlis_dir(), 'raw')


def dlis_demo_file() -> str:
    """Return path to the first bundled DLIS demo file."""
    directory = dlis_demo_dir()
    if not os.path.isdir(directory):
        return os.path.join(directory, 'demo.dlis')
    files = [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.lower().endswith('.dlis')
    ]
    if files:
        return files[0]
    return os.path.join(directory, 'demo.dlis')


def groovemask_dir() -> str:
    """Return path to the GrooveMask source implementation directory."""
    return os.path.join(geo_core_artifacts_dir(), 'groovemask')


def groovemask_demo_image() -> str:
    """Return path to the bundled GrooveMask demo image."""
    return os.path.join(groovemask_dir(), 'tests', 'groovemask_test.png')

