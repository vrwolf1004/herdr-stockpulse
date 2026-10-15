"""Minimal socket client for reporting StockPulse metadata to herdr."""

import json
import os
import socket
import sys
import time

IS_WINDOWS = sys.platform == "win32"
SOCKET_TIMEOUT_SECONDS = 3


class HerdrError(Exception):
    """A herdr socket request failed."""


def socket_path():
    configured = os.environ.get("HERDR_SOCKET_PATH")
    if configured:
        return configured
    if IS_WINDOWS:
        return os.path.join(os.environ.get("APPDATA", ""), "herdr", "herdr.sock")
    return os.path.expanduser("~/.config/herdr/herdr.sock")


def _read_line(read):
    data = b""
    while not data.endswith(b"\n"):
        chunk = read(65536)
        if not chunk:
            break
        data += chunk
    return data


def _exchange_unix(path, payload):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(SOCKET_TIMEOUT_SECONDS)
    try:
        client.connect(path)
        client.sendall(payload)
        return _read_line(client.recv)
    finally:
        client.close()


def _exchange_pipe(path, payload):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    handle = kernel32.CreateFileW("\\\\.\\pipe\\" + path, 0xC0000000, 0, None, 3, 0, None)
    if handle is None or handle == wintypes.HANDLE(-1).value:
        raise OSError(f"named pipe open failed ({ctypes.get_last_error()})")
    descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    with os.fdopen(descriptor, "r+b", buffering=0) as pipe:
        pipe.write(payload)
        return _read_line(pipe.read)


def request(method, params):
    message = {"id": f"stockpulse:{time.time_ns()}", "method": method, "params": params}
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        raw = (_exchange_pipe if IS_WINDOWS else _exchange_unix)(socket_path(), payload)
    except OSError as error:
        raise HerdrError(f"{method}: {error}") from error
    response = json.loads(raw.decode("utf-8")) if raw else {}
    if "error" in response:
        raise HerdrError(f"{method}: {response['error']}")
    return response.get("result", {})


def try_request(method, params):
    try:
        request(method, params)
        return True
    except (HerdrError, ValueError):
        return False
