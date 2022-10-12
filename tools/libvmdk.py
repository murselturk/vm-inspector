import io
import logging
import os
import struct
import tempfile

from collections import namedtuple
from subprocess import run
from . import log, rm, rmdir

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
    # See also: https://github.com/libyal/libvmdk/issues/7
    # libvmdk currently can't mount VMDK files with type "monolithicSparse"
    # if they've been renamed. There is already a created issue that has been
    # marked as solved and closed. Since libvmdk still can't handle renamed
    # single "monolithicSparse" images, extract name manually from descriptor,
    # create a symlink in case of mismatch and try to mount image through
    # this symlink.
    name = _extract_name_from_descriptor(path)
    if renamed := (name and name != os.path.basename(path)):
        L.debug("%s has been renamed", path)
        tempdir = tempfile.mkdtemp()
        symlink = os.path.join(tempdir, name)
        os.symlink(path, symlink)
        L.debug("created symlink with original name: %s", symlink)
        path = symlink

    mp = tempfile.mkdtemp()
    cmd = ["vmdkmount", path, mp]
    try:
        p = run(cmd, capture_output=True, check=False, text=True)
    except Exception as e:
        L.error("failed to execute command %s: %r", cmd, e)
        rmdir(mp)
        if renamed:
            rm(symlink)
            rmdir(tempdir)
        return None

    if renamed:
        rm(symlink)
        rmdir(tempdir)

    if os.path.ismount(mp):
        return mp

    out, err = p.stdout.strip(), p.stderr.strip()
    L.error("retcode: %d, stdout: %s, stderr: %s", p.returncode, out, err)
    rmdir(mp)

    return None


@log
def _extract_name_from_descriptor(path):
    """
    VMware Virtual Disks Virtual Disk Format 1.1
    https://www.vmware.com/app/vmdk/?src=vmdk

    typedef uint64  SectorType;
    typedef uint8   Bool;

    typedef struct SparseExtentHeader {
        uint32      magicNumber;
        uint32      version;
        uint32      flags;
        SectorType  capacity;
        SectorType  grainSize;
        SectorType  descriptorOffset;
        SectorType  descriptorSize;
        uint32      numGTEsPerGT;
        SectorType  rgdOffset;
        SectorType  gdOffset;
        SectorType  overHead;
        Bool        uncleanShutdown;
        char        singleEndLineChar;
        char        nonEndLineChar;
        char        doubleEndLineChar1;
        char        doubleEndLineChar2;
        uint16      compressAlgorithm;
        uint8       pad[433];
    } SparseExtentHeader;

    #define SPARSE_MAGICNUMBER 0x564d444b /* 'V' 'M' 'D' 'K' */
    """
    with open(path, "rb") as fh:
        name = ""
        if not (magic := fh.read(4)) or magic != b"KDMV":
            return None

        fh.seek(-4, io.SEEK_CUR)

        fmt = "<IIIQQQQIQQQ?ccccHB"
        size = struct.calcsize(fmt)
        data = fh.read(size)

        Header = namedtuple(
            "Header",
            "magic version flags capacity grain_size desc_offset desc_size "
            "num_gtes_per_gt rgd_offset gd_offset overhead is_dirty "
            "single_end_line_char non_end_line_char first_dbl_end_line_char "
            "second_dbl_end_line_char compress_algorithm pad"
        )
        header = Header._make(struct.unpack_from(fmt, data))

        # check if the descriptor is embedded
        if not (header.desc_offset > 0):
            return None

        # extract disc descriptor file
        fh.seek(header.desc_offset * 512)
        data = fh.read(header.desc_size * 512)
        descriptor = data.split(b"\x00", 1)[0].decode()

        for line in descriptor.splitlines():
            if not (line := line.strip()) or line.startswith("#"):
                continue

            if line.startswith("createType"):
                if line[11:].strip('"') != "monolithicSparse":
                    break
                else:
                    continue

            if line.startswith("RW "):
                extent = line.split(" ", 3)
                name = extent[3].strip('"')
                break

        return name
