# A script to dump the memory of Runner.Worker process

import ctypes
import re
import os
import sys

def find_process_pid(process_name):
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/comm", "r") as f:
                    name = f.read().strip()
                if name == process_name:
                    return int(pid)
            except (FileNotFoundError, PermissionError):
                continue
    return None

ulseek = ctypes.cdll['libc.so.6'].lseek
ulseek.restype = ctypes.c_uint64
ulseek.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_int]

def seek_set(fd, pos):
    # lseek casting to 64-bit unsigned
    ctypes.set_errno(0)
    ret = ulseek(fd, pos, os.SEEK_SET)
    if ctypes.get_errno() != 0:
        raise OSError(ctypes.get_errno())

def dump(pid, out):
    # Adapted from http://unix.stackexchange.com/a/6302/39407
    maps_file = open("/proc/%d/maps" % pid, 'r')
    mem_file = os.open("/proc/%d/mem" % pid, os.O_RDONLY)

    for line in maps_file.readlines():  # for each mapped region
        m = re.match(r'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([-r])', line)
        if m.group(3) == 'r': # if this is a readable region
            start = int(m.group(1), 16)
            end = int(m.group(2), 16)

            # seek to region start
            seek_set(mem_file, start)
            # read region contents
            try:
                chunk = os.read(mem_file, end - start)
            except OSError as e:
                continue
            # dump contents to standard output
            out.write(chunk)

    maps_file.close()
    os.close(mem_file)

if __name__ == "__main__":
    process_name = "Runner.Worker"
    pid = find_process_pid(process_name)
    if pid is None:
        print(f"Process {process_name} not found", file=sys.stderr)
        sys.exit(1)
    print(f"Found process: {process_name} (pid {pid})")
    if sys.stdout.isatty():
        print("Refusing to dump memory to a tty. Use a pipe.", file=sys.stderr)
        sys.exit(1)

    if sys.version_info >= (3, ):
        stdout = sys.stdout.buffer
    else:
        stdout = sys.stdout

    dump(pid, stdout)