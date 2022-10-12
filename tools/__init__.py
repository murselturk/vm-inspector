import logging
import os

from functools import wraps
from subprocess import run

__all__ = [
    "unmount",
    "rmdir",
    "subdirs",
    "subfiles"
]

L = logging.getLogger(__name__)


def log(func):
    """Simple decorator for logging function calls."""
    @wraps(func)
    def _log(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        params = ", ".join(args_repr + kwargs_repr)
        file_name = os.path.basename(func.__code__.co_filename)
        file_name = os.path.splitext(file_name)[0]
        func_name = func.__name__ if file_name == "__init__" \
            else f"{file_name}.{func.__name__}"
        L.debug("%s called with %s", func_name, params)
        try:
            result = func(*args, **kwargs)
            L.debug("%s returned %s", func_name, result)
            return result
        except Exception as e:
            L.error("%s raised %r", func_name, e)
            raise e
    return _log


@log
def unmount(path):
    """Unmount a FUSE filesystem using fusermount.

    See also:
    https://manpages.debian.org/bullseye/fuse/fusermount.1.en.html

    Args:
        path (str): Path to the mounted FUSE filesystem.

    Returns:
        True if the command was successful, False otherwise.
    """
    cmd = ["fusermount", "-u", path]
    try:
        p = run(cmd, capture_output=True, check=False, text=True)
    except Exception as e:
        L.error("failed to execute command %s: %r", cmd, e)
        return False

    return not p.returncode


@log
def rm(path):
    """Remove a file.

    Args:
        path (str): Path to file.

    Returns:
        True if the command was successful, False otherwise.
    """
    try:
        os.remove(path)
    except OSError as e:
        L.error("failed to remove file %s: %r", path, e)
        return False

    return True


@log
def rmdir(path):
    """Remove a directory.

    Args:
        path (str): Path to directory.

    Returns:
        True if the command was successful, False otherwise.
    """
    try:
        os.rmdir(path)
    except OSError as e:
        L.error("failed to remove directory %s: %r", path, e)
        return False

    return True


def subdirs(path):
    """Yield directory names under given path using os.scandir.

    See also:
    https://docs.python.org/3/library/os.html#os.scandir
    """
    with os.scandir(path) as it:
        for entry in it:
            if not entry.name.startswith(".") and entry.is_dir():
                yield entry.name


def subfiles(path):
    """Yield file names under given path using os.scandir.

    See also:
    https://docs.python.org/3/library/os.html#os.scandir
    """
    with os.scandir(path) as it:
        for entry in it:
            if not entry.name.startswith(".") and entry.is_file():
                yield entry.name
