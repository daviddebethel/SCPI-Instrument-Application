from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class InstrumentType(str, Enum):
    MP730889 = "Multicomp Pro MP730889 DMM"
    OWON_SPE6103 = "OWON SPE6103 PSU"


class MeasurementFunction(str, Enum):
    VOLTAGE = "Voltage"
    CURRENT = "Current"


@dataclass(frozen=True)
class SerialSettings:
    port: str
    baudrate: int
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1
    timeout_seconds: float = 1.0


@dataclass(frozen=True)
class Reading:
    timestamp: datetime
    slot_index: int
    instrument: InstrumentType
    device_idn: str
    function: MeasurementFunction
    raw_response: str
    value: float | None
    unit: str
