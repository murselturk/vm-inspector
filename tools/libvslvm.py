import logging
import os
import tempfile

from subprocess import run
from . import log, rmdir

__all__ = ["mount"]

L = logging.getLogger(__name__)


@log
def mount(path, offset):
    """Mount a Linux Logical Volume Manager (LVM) volume system using
    `libvslvm`.

    See also:
    https://github.com/libyal/libvslvm/wiki/Mounting

    Args:
        path (str): Path to the RAW image file containing LVM volume system.
        offset (str|int): Value in bytes where the LVM volume system starts.

    Returns:
        Path to the directory containing volumes as a virtual file named
        `lvm1`, `lvm2`, etc.
    """
    mp = tempfile.mkdtemp()
    cmd = ["vslvmmount", "-o", str(offset), path, mp]
    try:
        p = run(cmd, capture_output=True, check=False, text=True)
    except Exception as e:
        L.error("failed to execute command %s: %r", cmd, e)
        rmdir(mp)
        return ""

    out, err = p.stdout.strip(), p.stderr.strip()
    if p.returncode or not os.path.ismount(mp):
        L.error("retcode: %d, stdout: %s, stderr: %s", p.returncode, out, err)
        rmdir(mp)
        return ""

    return mp
