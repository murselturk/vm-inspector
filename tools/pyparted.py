import logging

from . import log

__all__ = ["list_partitions"]

L = logging.getLogger(__name__)

try:
    import parted  # type: ignore
except ModuleNotFoundError:
    L.error(
        "You need to install the following packages:\n"
        "sudo apt install python3-dev libparted-dev pkg-config\n"
        "pip3 install pyparted"
        )
    raise

SUPPORTED_FS_TYPES = ["ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "ntfs"]


@log
def list_partitions(path):
    """Find all partitions with a filesystem or a LVM volume system in a RAW
    image file using `pyparted`.

    See also:
    https://github.com/dcantrell/pyparted

    Args:
        path (str): Path to the RAW image file.

    Returns:
        List of partitions. For example:
        [{'nr': 1, 'type': 'ext4', 'offset': 1048576, 'size': 1073741824},
         {'nr': 2, 'type': 'btrfs', 'offset': 1074790400, 'size': 20400046080}]
    """
    try:
        device = parted.getDevice(path)
    except Exception as e:
        L.error("failed to get device from %s: %r", path, e)
        return []

    try:
        disk = parted.Disk(device)
    except Exception as e:
        L.error("failed to read disk from %s: %r", path, e)
        return []

    ret = []
    for part in disk.partitions:
        if part.fileSystem and part.fileSystem.type in SUPPORTED_FS_TYPES:
            part_type = part.fileSystem.type
        elif part.getFlag(parted.PARTITION_LVM):
            part_type = "lvm"
        else:
            continue

        ret.append({
            "nr": part.number,
            "type": part_type,
            "offset": part.geometry.start * device.sectorSize,  # in bytes
            "size": part.geometry.length * device.sectorSize  # in bytes
        })

    return ret
