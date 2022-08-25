import logging
import os
import tempfile

from subprocess import Popen, PIPE
from time import sleep
from . import log, rmdir

__all__ = ["mount"]

L = logging.getLogger(__name__)


@log
def mount(path, fs_type, part_nr=None):
    """Mount a RAW image file containing an ext2/ext3/ext4/xfs/btrfs/vfat/ntfs
    filesystem with read-only support using `lklfuse`.

    Make sure you have built `LKL` from the source code:
        $ sudo apt install build-essential flex bison bc libfuse-dev \
            libarchive-dev xfsprogs python git
        $ git clone https://github.com/lkl/linux.git
        $ cd linux
        $ echo "CONFIG_NTFS_FS=y" >> arch/lkl/configs/defconfig
        $ make -C tools/lkl
        $ sudo cp tools/lkl/lklfuse /usr/local/bin

    Args:
        path (str): Path to the RAW image file.
        fs_type (str): Filesystem type.
        part_nr (int|str): Partition number.

    Returns:
        Path to the mount point.
    """
    mp = tempfile.mkdtemp()

    opts = f"ro,type={fs_type}"
    if part_nr is not None:
        opts += f",part={part_nr}"
    if fs_type == "xfs":
        # filesystem will be mounted without running log recovery.
        # otherwise, the mount will fail.
        # see also: https://man7.org/linux/man-pages/man5/xfs.5.html
        opts += ",opts=norecovery"
    elif fs_type == "ext3" or fs_type == "ext4":
        # allow mounting dirty ext3 and ext4 filesystems
        # see also: https://man7.org/linux/man-pages/man5/ext3.5.html
        # example error message that occurs e.g. when mounting Fedora 26:
        # JBD2: recovery failed
        # EXT4-fs (vda): error loading journal
        opts += ",opts=noload"

    cmd = ["lklfuse", path, mp, "-f", "-o", opts]

    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True)
    except Exception as e:
        L.error("failed to execute command %s: %r", cmd, e)
        rmdir(mp)
        return None

    while p.poll() is None:
        if os.path.ismount(mp):
            return mp
        sleep(1)

    ret = p.poll()
    out, err = p.communicate()
    out, err = out.strip(), err.strip()
    L.error("retcode: %d, stdout: %s, stderr: %s", ret, out, err)

    rmdir(mp)

    return None
