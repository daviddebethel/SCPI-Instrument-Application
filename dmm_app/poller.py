from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from dmm_app.models import InstrumentType, MeasurementFunction, Reading
from dmm_app.scpi import SCPIClient


def parse_primary_value(raw_response: str) -> float | None:
    token = raw_response.replace(",", " ").split()[0].strip() if raw_response.strip() else ""
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


@dataclass(frozen=True)
class PollRequest:
    slot_index: int
    function: MeasurementFunction
    query_command: str
    unit: str


class PollingWorker(threading.Thread):
    def __init__(
        self,
        scpi: SCPIClient,
        instrument: InstrumentType,
        device_idn: str,
        measurements: list[PollRequest],
        interval_seconds: float,
        on_reading: Callable[[Reading], None],
        on_error: Callable[[str], None],
    ):
        super().__init__(daemon=True)
        self._scpi = scpi
        self._instrument = instrument
        self._device_idn = device_idn
        self._measurements = measurements
        self._interval_seconds = interval_seconds
        self._on_reading = on_reading
        self._on_error = on_error
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                for measurement in self._measurements:
                    if self._stop_event.is_set():
                        break
                    raw = self._scpi.query(measurement.query_command)
                    reading = Reading(
                        timestamp=datetime.now(),
                        slot_index=measurement.slot_index,
                        instrument=self._instrument,
                        device_idn=self._device_idn,
                        function=measurement.function,
                        raw_response=raw,
                        value=parse_primary_value(raw),
                        unit=measurement.unit,
                    )
                    self._on_reading(reading)
            except Exception as exc:  # pragma: no cover - hardware error path
                self._on_error(str(exc))
                return

            elapsed = time.monotonic() - started
            remaining = self._interval_seconds - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)
