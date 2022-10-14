import logging
import os
import tempfile

from subprocess import Popen, PIPE
from time import sleep
from . import log, rmdir

__all__ = ["mount"]

L = logging.getLogger(__name__)


@log
def mount(path):
    """Mount a disk image file as a RAW image file in the local filesystem with
    read-only support using `qemu-nbd` + `nbdfuse`.

    See also:
    https://manpages.debian.org/bullseye/qemu-utils/qemu-nbd.8.en.html
    https://manpages.debian.org/bullseye/libnbd-bin/nbdfuse.1.en.html

    Args:
        path (str): Path to the disk image file.

    Returns:
        Path to the directory containing a single virtual file named `nbd`.
    """
    mp = tempfile.mkdtemp()
    cmd = [
        "nbdfuse",
        "--readonly",
        mp,
        "--socket-activation",
        "qemu-nbd",
        "--read-only",
        path
    ]

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True)
    except Exception as e:
        L.error("failed to execute command %s: %r", cmd, e)
        rmdir(mp)
        return ""

    while p.poll() is None:
        if os.path.ismount(mp):
            return mp
        sleep(1)

    ret = p.poll()
    out, err = p.communicate()
    out, err = out.strip(), err.strip()
    L.error("retcode: %d, stdout: %s, stderr: %s", ret, out, err)

    rmdir(mp)

    return ""
