"""Minimal socket client for reporting StockPulse metadata to herdr."""

import json
import os
import socket
import sys
import threading
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
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise OSError("APPDATA is not set; set HERDR_SOCKET_PATH to the herdr socket")
        return os.path.join(appdata, "herdr", "herdr.sock")
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
    try:
        pipe = os.fdopen(descriptor, "r+b", buffering=0)
    except OSError:
        os.close(descriptor)  # descriptor 가 handle 을 가지고 있으므로 닫으면 handle 도 닫힌다
        raise
    with pipe:
        pipe.write(payload)
        return _read_line(pipe.read)


def _exchange_pipe_with_timeout(path, payload):
    # Named pipe reads have no socket timeout, so run the exchange on a daemon thread and stop waiting after the limit.
    outcome = {}

    def run():
        try:
            outcome["raw"] = _exchange_pipe(path, payload)
        except Exception as error:  # noqa: BLE001 - re-raised on the calling thread below
            outcome["error"] = error

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(SOCKET_TIMEOUT_SECONDS)
    if worker.is_alive():
        raise TimeoutError(f"no response within {SOCKET_TIMEOUT_SECONDS} seconds")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["raw"]


def request(method, params):
    message = {"id": f"stockpulse:{time.time_ns()}", "method": method, "params": params}
    payload = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        raw = (_exchange_pipe_with_timeout if IS_WINDOWS else _exchange_unix)(socket_path(), payload)
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
