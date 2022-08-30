import logging
import os
import tempfile

from . import log, subdirs

__all__ = [
    "list_applications_deb",
    "list_applications_rpm",
    "list_applications_windows"
]

L = logging.getLogger(__name__)

try:
    import rpm  # type: ignore
except ModuleNotFoundError:
    L.error(
        "You need to install the following package:\n"
        "sudo apt install python3-rpm"
        )
    raise

try:
    from Registry import Registry  # type: ignore
except ModuleNotFoundError:
    L.error(
        "You need to install the following package:\n"
        "pip3 install python-registry"
        )
    raise


@log
def list_applications_deb(path):
    """Find all packages installed on a debian-based linux distribution.

    See also:
    https://man7.org/linux/man-pages/man1/dpkg.1.html

    Args:
        path (str): Path to the mounted filesystem.

    Returns:
        List of packages. For example:
        [{'name': 'adduser', 'version': '3.118'}, ...]
    """
    dpkg_db = None

    locations = [
        "var/lib/dpkg/status",
        "lib/dpkg/status"  # separated /var partition
    ]

    for location in locations:
        db = os.path.join(path, location)
        if os.path.exists(db):
            dpkg_db = db
            break

    # Debian uses subvol=@rootfs for root filesystem for btrfs.
    # Therefore, under Debian 11.* looks like this: /@rootfs/var/lib/dpkg
    if dpkg_db is None:
        for dir in subdirs(path):
            new_path = os.path.join(path, dir)
            for location in locations:
                db = os.path.join(new_path, location)
                if os.path.exists(db):
                    dpkg_db = db
                    break
            if dpkg_db is not None:
                break

    if dpkg_db is None:
        L.debug("dpkg database not found")
        return []

    pkgs = []
    with open(dpkg_db) as f:
        name = version = ""
        installed = False
        for line in f:
            line = line.strip()
            if not line:
                if name and version and installed:
                    pkgs.append({
                        "name": name,
                        "version": version
                    })
                name = version = ""
                installed = False
            elif line.startswith("Package:"):
                name = line[9:]
            elif line.startswith("Status:"):
                installed = "installed" in line[8:].split()
            elif line.startswith("Version:"):
                version = line[9:]

    return pkgs


@log
def list_applications_rpm(path):
    """Find all packages installed on a rpm-based linux distribution.

    Args:
        path (str): Path to the mounted filesystem.

    Returns:
        List of packages. For example:
        [{'name': 'libgcc', 'version': '12.0.1'}, ...]
    """
    rpm_db = None
    for root, dirs, _ in os.walk(path):
        if "usr" in dirs:
            db = os.path.join(root, "usr/share/rpm")
            if os.path.exists(db):
                rpm_db = db
                break
            # https://fedoraproject.org/wiki/Changes/RelocateRPMToUsr
            db = os.path.join(root, "usr/lib/sysimage/rpm")
            if os.path.exists(db):
                rpm_db = db
                break
        if "var" in dirs:
            db = os.path.join(root, "var/lib/rpm")
            if os.path.exists(db):
                rpm_db = db
                break

    if rpm_db is None:
        L.debug("RPM database not found")
        return []

    log_file = tempfile.TemporaryFile()
    rpm.setLogFile(log_file)
    rpm.setVerbosity(rpm.RPMLOG_DEBUG)
    rpm.addMacro("_dbpath", rpm_db)
    ts = rpm.TransactionSet()

    try:
        dbMatch = ts.dbMatch()
    except Exception as e:
        L.error("failed to open RPM database: %r", e)
        return []

    pkgs = []
    for h in dbMatch:
        pkgs.append({
            "name": h["name"],
            "version": h["version"]
        })

    rpm.delMacro("_dbpath")

    return pkgs


@log
def list_applications_windows(path):
    """Find all applications installed on a windows distribution.

    Args:
        path (str): Path to the mounted filesystem.

    Returns:
        List of applications. For example:
        [{'name': 'Mozilla Firefox 43.0.1 (x86 de)', 'version': '43.0.1'}, ...]
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
        L.debug("software hive not found in %s", path)
        return []

    try:
        registry = Registry.Registry(software)
    except Exception as e:
        L.error("failed to open registry file %s: %r", software, e)
        return []

    apps = []

    # native applications
    hive_path = "Microsoft\\Windows\\CurrentVersion\\Uninstall"
    try:
        key = registry.open(hive_path)
    except Exception as e:
        L.error("%s not found in %s: %r", hive_path, software, e)
        return apps
    if apps_native := _list_applications_windows_from_key(key):
        apps.extend(apps_native)

    # 32-bit applications running on WOW64 emulator
    # see also: http://support.microsoft.com/kb/896459
    hive_path = "Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
    try:
        key = registry.open(hive_path)
    except Exception as e:
        L.error("%s not found in %s: %r", hive_path, software, e)
        return apps
    if apps_emulator := _list_applications_windows_from_key(key):
        apps.extend(apps_emulator)

    return apps


@log
def _list_applications_windows_from_key(key):
    """Parse applications from windows registry key.

    See also:
    https://docs.microsoft.com/en-us/windows/win32/msi/uninstall-registry-key

    Args:
        key (Registry.Key): Registry key.

    Returns:
        List of applications.
    """
    apps = []
    for k in key.subkeys():
        # name = k.name()
        # name does not say much, so take the display name
        name = version = ""
        for v in k.values():
            if v.name() == "DisplayName":
                name = v.value()
            if v.name() == "DisplayVersion":
                version = v.value()
        # ignore applications with no display name
        if name and version:
            apps.append({
                "name": name,
                "version": version
            })

    return apps
