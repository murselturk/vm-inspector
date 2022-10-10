#!/usr/bin/env python3

import argparse
import logging
import os
import sys

from tools import libvmdk, libvslvm, lklfuse, nbdfuse, subfiles, unmount, rmdir
from tools.inspect_apps import (
    list_applications_apk,
    list_applications_dpkg,
    list_applications_pacman,
    list_applications_portage,
    list_applications_rpm,
    list_applications_windows
)
from tools.inspect_os import get_linux_os_info, get_windows_os_info
from tools.pyparted import list_partitions

parser = argparse.ArgumentParser()
parser.description = "Tool for inspecting a disk image file to determine "\
                     "which operating system and applications it contains."
parser.add_argument("image", type=str, help="disk image file to inspect")
parser.add_argument("-b", "--backend", type=str, default="nbdfuse",
                    choices=("libvmdk", "nbdfuse"),
                    help="used backend for mounting disk image files in the " +
                         "local filesystem (default: nbdfuse)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="print debug messages")

args = parser.parse_args()

if args.verbose:
    fmt = "{asctime}, {name}:{lineno}:{funcName}(), {levelname}, {message}"
    logging.basicConfig(level=logging.DEBUG, format=fmt, style="{")
else:
    logging.basicConfig(level=logging.CRITICAL)

if args.backend == "libvmdk":
    image_mp = libvmdk.mount(args.image)
else:
    image_mp = nbdfuse.mount(args.image)

if not image_mp:
    print(f"{args.backend} could not mount {args.image}", file=sys.stderr)
    sys.exit(1)

if args.backend == "libvmdk":
    raw = os.path.join(image_mp, "vmdk1")
else:
    raw = os.path.join(image_mp, "nbd")

parts = list_partitions(raw)
if not parts:
    unmount(image_mp)
    rmdir(image_mp)
    print("could not find any partitions", file=sys.stderr)
    sys.exit(1)

fs_mps = []
lvm = [part for part in parts if part["type"] == "lvm"]
lvm_mp = None

if not lvm:
    for part in parts:
        if fs_mp := lklfuse.mount(raw, part["type"], part["nr"]):
            fs_mps.append((fs_mp, part["type"]))
elif lvm_mp := libvslvm.mount(raw, lvm[0]["offset"]):
    for vol in subfiles(lvm_mp):
        vol_path = os.path.join(lvm_mp, vol)
        vol_part = list_partitions(vol_path)
        if not vol_part:
            continue
        if fs_mp := lklfuse.mount(vol_path, vol_part[0]["type"]):
            fs_mps.append((fs_mp, vol_part[0]["type"]))

os_info = {}
for k, v in fs_mps:
    if v == "ntfs":
        os_info = get_windows_os_info(k)
    else:
        os_info = get_linux_os_info(k)
    if os_info:
        break

apps = []
package_manager = os_info.get("package_manager", "")
for k, _ in fs_mps:
    if package_manager == "apk":
        apps = list_applications_apk(k)
    elif package_manager == "dpkg":
        apps = list_applications_dpkg(k)
    elif package_manager == "pacman":
        apps = list_applications_pacman(k)
    elif package_manager == "portage":
        apps = list_applications_portage(k)
    elif package_manager == "rpm":
        apps = list_applications_rpm(k)
    elif package_manager == "win":
        apps = list_applications_windows(k)
    else:
        break
    if apps:
        break

for k, _ in fs_mps:
    unmount(k)
    rmdir(k)

if lvm_mp:
    unmount(lvm_mp)
    rmdir(lvm_mp)

unmount(image_mp)
rmdir(image_mp)

print({
    "name": os_info.get("name", ""),
    "version": os_info.get("version", ""),
    "apps": apps
})
