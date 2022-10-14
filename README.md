# vm-inspector

A sample tool for inspecting a disk image file, e.g. vmdk, vdi, qcow, etc., to determine which operating system and applications it contains.

## Usage

To inspect a disk image file:

```sh
python3 inspect.py foo.vmdk
```

or

```sh
./inspect.py foo.vmdk
```

## CLI options

```sh
./inspect.py --help
```

```
usage: inspect.py [-h] [-b {libvmdk,nbdfuse}] [-v] image

Tool for inspecting a disk image file to determine which operating
system and applications it contains.

positional arguments:
  image                 disk image file to inspect

optional arguments:
  -h, --help            show this help message and exit
  -b {libvmdk,nbdfuse}, --backend {libvmdk,nbdfuse}
                        used backend for mounting disk image files in
                        the local filesystem (default: nbdfuse)
  -v, --verbose         print debug messages
```

## Requirements

- Python >= 3.9

- Debian 11 Bullseye (recommended)

- [lklfuse](https://github.com/lkl/linux)

  ```sh
  $ sudo apt install build-essential flex bison bc libfuse-dev libarchive-dev xfsprogs python git
  $ git clone https://github.com/lkl/linux.git
  $ cd linux
  $ echo "CONFIG_NTFS_FS=y" >> arch/lkl/configs/defconfig
  $ make -C tools/lkl
  $ sudo cp tools/lkl/lklfuse /usr/local/bin
  ```

- [nbdfuse](https://libguestfs.org/nbdfuse.1.html) + [qemu-nbd](https://www.qemu.org/docs/master/tools/qemu-nbd.html) (qcow2, vdi, vmdk, etc.) or [libvmdk](https://github.com/libyal/libvmdk) >= 20210807 (vmdk only)

  ```sh
  $ sudo apt install qemu-utils nbdfuse
  ```

  ```sh
  $ sudo apt install build-essential libfuse-dev
  $ wget https://github.com/libyal/libvmdk/releases/download/20210807/libvmdk-alpha-20210807.tar.gz
  $ tar xfv libvmdk-alpha-20210807.tar.gz
  $ cd libvmdk-20210807/
  $ ./configure
  $ make
  $ sudo make install
  $ sudo ldconfig
  ```

- [libvslvm](https://github.com/libyal/libvslvm) >= 20210807

  ```sh
  $ sudo apt install build-essential libfuse-dev
  $ wget https://github.com/libyal/libvslvm/releases/download/20210807/libvslvm-experimental-20210807.tar.gz
  $ tar xfv libvslvm-experimental-20210807.tar.gz
  $ cd libvslvm-20210807/
  $ ./configure
  $ make
  $ sudo make install
  $ sudo ldconfig
  ```

- [pyparted](https://github.com/dcantrell/pyparted)

  ```sh
  $ sudo apt install python3 python3-pip python3-dev libparted-dev pkg-config
  $ pip3 install pyparted
  ```

- [python-registry](https://github.com/williballenthin/python-registry)

  ```sh
  $ sudo apt install python3 python3-pip
  $ pip3 install python-registry
  ```

- [python3-rpm](https://github.com/rpm-software-management/rpm) >= 4.16.1.3

  ```sh
  $ sudo apt install build-essential python3 python3-dev python3-pip zlib1g-dev libgcrypt20-dev libmagic-dev libpopt-dev libsqlite3-dev libarchive-dev
  $ wget https://ftp.osuosl.org/pub/rpm/releases/rpm-4.16.x/rpm-4.16.1.3.tar.bz2
  $ tar xfv rpm-4.16.1.3.tar.bz2
  $ cd rpm-4.16.1.3/
  $ ./autogen.sh --enable-python --enable-bdb=no --enable-bdb-ro --enable-sqlite=yes --enable-ndb --without-lua --disable-plugins
  $ make
  $ sudo make install
  $ sudo ldconfig
  $ cd python && sudo python3 setup.py install
  ```
