import argparse
import os
import sys
import time

import serial


class RawRepl:
    def __init__(self, port, baud=115200, timeout=2):
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout, write_timeout=timeout)
        time.sleep(0.2)

    def close(self):
        self.ser.close()

    def read_until(self, marker, timeout=5):
        end = time.time() + timeout
        data = b""
        while time.time() < end:
            b = self.ser.read(1)
            if b:
                data += b
                if marker in data:
                    return data
            else:
                time.sleep(0.01)
        raise RuntimeError("timeout waiting for %r, got %r" % (marker, data[-200:]))

    def enter(self):
        self.ser.write(b"\r\x03\x03")
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\x01")
        self.read_until(b">", 5)

    def exit(self):
        self.ser.write(b"\x02")

    def exec(self, code, timeout=10):
        if isinstance(code, str):
            code = code.encode()
        self.ser.write(code)
        self.ser.write(b"\x04")
        self.read_until(b"OK", timeout)
        out = self.read_until(b"\x04", timeout)[:-1]
        err = self.read_until(b"\x04", timeout)[:-1]
        if err:
            raise RuntimeError(err.decode(errors="replace"))
        return out


def remote_parent(path):
    path = path.strip(":")
    parent = os.path.dirname(path)
    return parent if parent else None


def ensure_dir(repl, directory):
    directory = directory.strip(":")
    if not directory:
        return
    repl.exec(
        "import os\n"
        "try:\n"
        "    os.mkdir(%r)\n"
        "except OSError:\n"
        "    pass\n" % directory
    )


def upload_file(repl, local, remote):
    remote = remote.strip(":")
    parent = remote_parent(remote)
    if parent:
        ensure_dir(repl, parent)
    repl.exec("open(%r, 'wb').close()\n" % remote)
    total = os.path.getsize(local)
    sent = 0
    with open(local, "rb") as f:
        while True:
            chunk = f.read(384)
            if not chunk:
                break
            repl.exec("f=open(%r,'ab')\nf.write(%r)\nf.close()\n" % (remote, chunk), timeout=10)
            sent += len(chunk)
    print("uploaded %s -> :%s (%d bytes)" % (local, remote, total))


def parse_mapping(value):
    if ":" not in value:
        raise argparse.ArgumentTypeError("file mapping must be local:remote")
    local, remote = value.split(":", 1)
    return local, remote


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    upload = sub.add_parser("upload")
    upload.add_argument("files", nargs="+", type=parse_mapping)

    exec_cmd = sub.add_parser("exec")
    exec_cmd.add_argument("code")

    sub.add_parser("reset")

    args = parser.parse_args()
    repl = RawRepl(args.port)
    did_reset = False
    try:
        repl.enter()
        if args.cmd == "upload":
            for local, remote in args.files:
                upload_file(repl, local, remote)
        elif args.cmd == "exec":
            sys.stdout.buffer.write(repl.exec(args.code))
        elif args.cmd == "reset":
            try:
                repl.exec("import machine\nmachine.reset()\n")
            except Exception:
                pass
            did_reset = True
    finally:
        if not did_reset:
            try:
                repl.exit()
            finally:
                repl.close()
        else:
            repl.close()


if __name__ == "__main__":
    main()
