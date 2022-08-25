import logging
import os
import tempfile

from subprocess import run
from . import log, rmdir

__all__ = ["mount"]

L = logging.getLogger(__name__)


@log
def mount(path):
    """Mount a VMware Virtual Machine Disk (VMDK) file as a RAW image in the
    local filesystem with read-only support using `libvmdk`.

    See also:
    https://github.com/libyal/libvmdk/wiki/Building
    https://github.com/libyal/libvmdk/wiki/Mounting

    Make sure you have downloaded the latest source distribution package from
    https://github.com/libyal/libvmdk/releases, e.g.
    libvmdk-alpha-20210807.tar.gz and built it as follows:
        $ sudo apt install build-essential libfuse-dev
        $ tar xfv libvmdk-alpha-20210807.tar.gz
        $ cd libvmdk-20210807/
        $ ./configure
        $ make
        $ sudo make install
        $ sudo ldconfig

    Args:
        path (str): Path to the VMDK file.

    Returns:
        Path to the directory containing a single virtual file named `vmdk1`.
    """
    mp = tempfile.mkdtemp()
    cmd = ["vmdkmount", path, mp]
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
