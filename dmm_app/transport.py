from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

from dmm_app.models import SerialSettings

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - import guard for environments without pyserial
    serial = None
    list_ports = None


class Transport(ABC):
    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def write(self, payload: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_until(self, terminator: bytes) -> bytes:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError


class SerialTransport(Transport):
    def __init__(self, settings: SerialSettings):
        self._settings: Final[SerialSettings] = settings
        self._connection = None

    @staticmethod
    def list_serial_ports() -> list[str]:
        if list_ports is None:
            return []
        return [port.device for port in list_ports.comports()]

    def open(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Install dependencies first.")
        if self._connection and self._connection.is_open:
            return
        self._connection = serial.Serial(
            port=self._settings.port,
            baudrate=self._settings.baudrate,
            bytesize=self._settings.bytesize,
            parity=self._settings.parity,
            stopbits=self._settings.stopbits,
            timeout=self._settings.timeout_seconds,
        )

    def close(self) -> None:
        if self._connection and self._connection.is_open:
            self._connection.close()

    def write(self, payload: bytes) -> None:
        if not self._connection or not self._connection.is_open:
            raise RuntimeError("Serial connection is not open.")
        self._connection.write(payload)

    def read_until(self, terminator: bytes) -> bytes:
        if not self._connection or not self._connection.is_open:
            raise RuntimeError("Serial connection is not open.")
        return self._connection.read_until(expected=terminator)

    @property
    def is_open(self) -> bool:
        return bool(self._connection and self._connection.is_open)

