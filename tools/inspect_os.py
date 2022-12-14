import os
import logging
import re

from glob import iglob
from Registry import Registry  # type: ignore
from . import log

__all__ = ["get_linux_os_info", "get_windows_os_info"]

L = logging.getLogger(__name__)


@log
def get_linux_os_info(path):
    """Find and parse the os-release file.

    See also:
    https://www.freedesktop.org/software/systemd/man/os-release.html

    Args:
        path (str): Path to the mounted filesystem.

    Returns:
        Name and version of linux distribution as a dictionary. For example:
        {'name': 'CentOS Linux', 'version': '6.0 (Final)',
         'package_manager': 'rpm'}
    """
    release_files = {}
    for root, dirs, _ in os.walk(path):
        if "etc" in dirs:
            for f in iglob(f"{root}/etc/*release"):
                # Hack for immutable operating systems of Fedora.
                if not os.path.exists(f):
                    release_files.clear()
                    break
                if os.path.isfile(f):
                    release_files[os.path.basename(f)] = f
            else:
                if release_files:
                    break
            continue

    if not release_files:
        L.debug("no release file found")
        return {}

    L.debug("release files: %s", release_files)

    name = version = package_manager = ""
    if "centos-release" in release_files:
        L.debug("parsing %s", release_files["centos-release"])
        # CentOS 6.* doesn't have os-release, but centos-release.
        # For consistency, use always centos-release first.
        with open(release_files["centos-release"]) as f:
            # AlmaLinux 8.* and Rocky Linux 8.* also have centos-release.
            if m := re.match(r"^(.*)\srelease\s(.*)$", f.read()):
                name, version = m.groups()
                package_manager = "rpm"
    elif "gentoo-release" in release_files:
        # Gentoo now has a VERSION_ID tag in os-release, which did not exist
        # before. See also https://bugs.gentoo.org/788190. For consistency,
        # gentoo-release is parsed before os-release at this point.
        L.debug("parsing %s", release_files["gentoo-release"])
        with open(release_files["gentoo-release"]) as f:
            if m := re.match(r"^(Gentoo).*release\s(.*)$", f.read()):
                name, version = m.groups()
                package_manager = "portage"
    elif "os-release" in release_files:
        L.debug("parsing %s", release_files["os-release"])
        with open(release_files["os-release"]) as f:
            kv = {}
            for line in f:
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                kv[k] = v
            name = kv.get("NAME", "")
            version = kv.get("VERSION", kv.get("VERSION_ID", ""))
            # Arch-based distros have neither VERSION nor VERSION_ID.
            # These are using a rolling release model.
            if not version:
                version = kv.get("BUILD_ID", "")
            id_like = kv.get("ID_LIKE", kv.get("ID", ""))
            id_like = id_like.strip().strip("'\"").split()
            for i in id_like:
                if i == "alpine":
                    package_manager = "apk"
                elif i in ("debian", "ubuntu"):
                    package_manager = "dpkg"
                elif i == "arch":
                    package_manager = "pacman"
                elif i in ("centos", "fedora", "rhel"):
                    package_manager = "rpm"
                elif i in ("opensuse", "suse"):
                    package_manager = "rpm"
                elif i == "ol":  # Oracle Linux 6.10
                    package_manager = "rpm"
                else:
                    continue
                break
    elif "system-release" in release_files:
        # RedHat (RHEL) provides the redhat-release file. However, it does not
        # seem to be reliable for determining which operating system it is.
        # Therefore, for distributions such as Scientific Linux 6.* and
        # Oracle Linux 6.*, use system-release instead.
        L.debug("parsing %s", release_files["system-release"])
        with open(release_files["system-release"]) as f:
            if m := re.match(r"^(.*)\srelease\s(.*)$", f.read()):
                name, version = m.groups()
                package_manager = "rpm"

    if not name or not version:
        return {}

    name = name.strip().strip("'\"")
    version = version.strip().strip("'\"")

    return {
        "name": name,
        "version": version,
        "package_manager": package_manager
    }


@log
def get_windows_os_info(path):
    """Find and parse the software registry.

    Args:
        path (str): Path to the mounted filesystem.

    Returns:
        Name and version of windows distribution as a dictionary. For example:
        {'name': 'Microsoft Windows XP', 'version': '5.1',
         'package_manager': 'win'}
    """
    software = None

    locations = [
        "WINDOWS/system32/config/software",  # xp
        "Windows/System32/config/SOFTWARE",  # others
    ]

    for location in locations:
        software_path = os.path.join(path, location)
        if os.path.isfile(software_path):
            software = software_path
            break

    if not software:
        return {}

    try:
        registry = Registry.Registry(software)
    except Exception as e:
        L.error("failed to open registry file %s: %r", software, e)
        return {}

    hive_path = "Microsoft\\Windows NT\\CurrentVersion"
    try:
        key = registry.open(hive_path)
    except Exception as e:
        L.error("%s not found in %s: %r", hive_path, software, e)
        return {}

    name = version = ""
    for k in key.values():
        if k.name() == "ProductName":
            name = k.value()
        if k.name() == "CurrentVersion":
            version = k.value()

    if not name or not version:
        return {}

    return {"name": name, "version": version, "package_manager": "win"}
