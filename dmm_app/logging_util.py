from __future__ import annotations

import csv
from pathlib import Path

from dmm_app.models import Reading


class CsvLogger:
    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self._path.exists() and self._path.stat().st_size > 0
        self._file = self._path.open("a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        if not file_exists:
            self._writer.writerow(
                [
                    "timestamp",
                    "measurement_slot",
                    "device_name",
                    "device_idn",
                    "function",
                    "value",
                    "unit",
                    "raw_response",
                ]
            )
            self._file.flush()

    @property
    def path(self) -> str:
        return str(self._path)

    def write_reading(self, reading: Reading) -> None:
        self._writer.writerow(
            [
                reading.timestamp.isoformat(timespec="seconds"),
                reading.slot_index + 1,
                reading.instrument.value,
                reading.device_idn,
                reading.function.value,
                "" if reading.value is None else f"{reading.value:.12g}",
                reading.unit,
                reading.raw_response,
            ]
        )
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()
