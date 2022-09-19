#!/usr/bin/env python3

import logging
import os
import re
import sys

from tools import libvslvm, lklfuse, nbdfuse, subfiles, unmount, rmdir
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

fmt = "{asctime}, {name}:{lineno}:{funcName}(), {levelname}, {message}"
logging.basicConfig(level=logging.DEBUG, format=fmt, style="{")

APK = re.compile(r"^(Alpine).*$")
DPKG = re.compile(r"^(Debian|Ubuntu|Linux\sMint|LMDE).*$")
PACMAN = re.compile(r"^(Arch|Manjaro).*$")
PORTAGE = re.compile(r"^(Gentoo).*$")
RPM = re.compile(r"^(CentOS|AlmaLinux|Scientific|Rocky|Oracle|openSUSE|Fedora).*$") # noqa
WIN = re.compile(r"^(Microsoft|Windows).*$")


def main(vmdk_path):
    nbd_mp = nbdfuse.mount(vmdk_path)
    if not nbd_mp:
        sys.exit()

    nbd = os.path.join(nbd_mp, "nbd")
    parts = list_partitions(nbd)
    if not parts:
        unmount(nbd_mp)
        rmdir(nbd_mp)
        sys.exit()

    lvm_mp = ""
    fs_mps = []
    for part in parts:
        if part["type"] == "lvm":
            lvm_mp = libvslvm.mount(nbd, part["offset"])
            if not lvm_mp:
                continue
            for vol in subfiles(lvm_mp):
                vol_path = os.path.join(lvm_mp, vol)
                vol_parts = list_partitions(vol_path)
                if not vol_parts:
                    continue
                if mp := lklfuse.mount(vol_path, vol_parts[0]["type"]):
                    fs_mps.append((mp, parts[0]["type"]))
        else:
            if mp := lklfuse.mount(nbd, part["type"], part["nr"]):
                fs_mps.append((mp, part["type"]))

    os_info = {}
    apps = {}
    for fspath, fstype in fs_mps:
        if fstype == "ntfs":
            os_info = get_windows_os_info(fspath)
        else:
            os_info = get_linux_os_info(fspath)
        if os_info:
            break

    os_name = os_info.get("name", "")
    for fspath, _ in fs_mps:
        if APK.match(os_name):
            apps = list_applications_apk(fspath)
        elif DPKG.match(os_name):
            apps = list_applications_dpkg(fspath)
        elif PACMAN.match(os_name):
            apps = list_applications_pacman(fspath)
        elif PORTAGE.match(os_name):
            apps = list_applications_portage(fspath)
        elif RPM.match(os_name):
            apps = list_applications_rpm(fspath)
        elif WIN.match(os_name):
            apps = list_applications_windows(fspath)
        if apps:
            break

    for fspath, _ in fs_mps:
        unmount(fspath)
        rmdir(fspath)

    if lvm_mp:
        unmount(lvm_mp)
        rmdir(lvm_mp)

    unmount(nbd_mp)
    rmdir(nbd_mp)


if __name__ == "__main__":
    path = sys.argv[1]
    main(path)
