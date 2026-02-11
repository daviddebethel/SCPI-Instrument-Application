from __future__ import annotations

import threading

from dmm_app.transport import Transport


class SCPIClient:
    def __init__(self, transport: Transport, terminator: str = "\n", encoding: str = "ascii"):
        self._transport = transport
        self._terminator = terminator
        self._encoding = encoding
        self._lock = threading.Lock()

    def write(self, command: str) -> None:
        payload = f"{command}{self._terminator}".encode(self._encoding)
        with self._lock:
            self._transport.write(payload)

    def query(self, command: str) -> str:
        payload = f"{command}{self._terminator}".encode(self._encoding)
        with self._lock:
            self._transport.write(payload)
            response = self._transport.read_until(self._terminator.encode(self._encoding))
        return response.decode(self._encoding, errors="replace").strip()

