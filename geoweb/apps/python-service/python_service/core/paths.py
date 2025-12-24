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

