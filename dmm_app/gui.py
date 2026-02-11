from __future__ import annotations

import queue
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dmm_app.commands import INSTRUMENT_PROFILES, InstrumentProfile, idn_matches_profile
from dmm_app.logging_util import CsvLogger
from dmm_app.models import InstrumentType, MeasurementFunction, Reading, SerialSettings
from dmm_app.poller import PollRequest, PollingWorker, parse_primary_value
from dmm_app.scpi import SCPIClient
from dmm_app.transport import SerialTransport

BAUD_RATES = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]


@dataclass
class MeasurementRow:
    container: QWidget
    function_combo: QComboBox
    latest_label: QLabel
    remove_button: QPushButton
    last_valid_function: MeasurementFunction


class DMMAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCPI Instrument Client")
        self.resize(980, 640)
        self.setMinimumSize(860, 540)

        self._transport: SerialTransport | None = None
        self._scpi: SCPIClient | None = None
        self._poller: PollingWorker | None = None
        self._logger: CsvLogger | None = None
        self._device_idn: str = "UNKNOWN"
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._measurement_rows: list[MeasurementRow] = []

        self._build_ui()
        self._refresh_ports()
        self._reload_functions_for_instrument()

        self._event_timer = QTimer(self)
        self._event_timer.setInterval(100)
        self._event_timer.timeout.connect(self._process_events)
        self._event_timer.start()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        connection_box = QGroupBox("Connection")
        connection_layout = QGridLayout(connection_box)

        connection_layout.addWidget(QLabel("Instrument"), 0, 0)
        self._instrument_combo = QComboBox()
        self._instrument_combo.addItems([item.value for item in InstrumentType])
        self._instrument_combo.currentIndexChanged.connect(self._on_instrument_changed)
        connection_layout.addWidget(self._instrument_combo, 1, 0)

        connection_layout.addWidget(QLabel("Serial Port"), 0, 1)
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(260)
        connection_layout.addWidget(self._port_combo, 1, 1)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_ports)
        connection_layout.addWidget(refresh_button, 1, 2)

        connection_layout.addWidget(QLabel("Baud Rate"), 0, 3)
        self._baud_combo = QComboBox()
        self._baud_combo.addItems(BAUD_RATES)
        self._baud_combo.setCurrentText("9600")
        connection_layout.addWidget(self._baud_combo, 1, 3)

        self._connect_button = QPushButton("Connect")
        self._connect_button.clicked.connect(self._toggle_connection)
        connection_layout.addWidget(self._connect_button, 1, 4)

        idn_button = QPushButton("Request *IDN?")
        idn_button.clicked.connect(self._request_idn)
        connection_layout.addWidget(idn_button, 1, 5)

        self._status_label = QLabel("Disconnected")
        connection_layout.addWidget(self._status_label, 1, 6)
        root_layout.addWidget(connection_box)

        measure_box = QGroupBox("Measurement")
        measure_layout = QVBoxLayout(measure_box)
        measure_layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Function"))
        header.addStretch(1)
        header.addWidget(QLabel("Latest"))
        measure_layout.addLayout(header)

        self._measurement_rows_layout = QVBoxLayout()
        self._measurement_rows_layout.setSpacing(6)
        measure_layout.addLayout(self._measurement_rows_layout)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Interval (ms)"))
        self._interval_input = QLineEdit("1000")
        self._interval_input.setMaximumWidth(100)
        controls.addWidget(self._interval_input)

        self._start_button = QPushButton("Start")
        self._start_button.clicked.connect(self._start_polling)
        controls.addWidget(self._start_button)

        self._stop_button = QPushButton("Stop")
        self._stop_button.clicked.connect(self._stop_polling)
        controls.addWidget(self._stop_button)

        self._snapshot_button = QPushButton("Snapshot")
        self._snapshot_button.clicked.connect(self._take_snapshot)
        controls.addWidget(self._snapshot_button)

        self._add_measurement_button = QPushButton("Add Measurement")
        self._add_measurement_button.clicked.connect(self._add_measurement)
        controls.addWidget(self._add_measurement_button)
        controls.addStretch(1)
        measure_layout.addLayout(controls)
        root_layout.addWidget(measure_box)

        logging_box = QGroupBox("Logging")
        logging_layout = QHBoxLayout(logging_box)
        self._log_checkbox = QCheckBox("Enable logging")
        self._log_checkbox.toggled.connect(self._toggle_logging)
        logging_layout.addWidget(self._log_checkbox)

        choose_file_button = QPushButton("Choose file")
        choose_file_button.clicked.connect(self._choose_log_file)
        logging_layout.addWidget(choose_file_button)

        self._log_path_label = QLabel("")
        logging_layout.addWidget(self._log_path_label, stretch=1)
        root_layout.addWidget(logging_box)

        output_box = QGroupBox("Output")
        output_layout = QVBoxLayout(output_box)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        output_layout.addWidget(self._output)
        root_layout.addWidget(output_box, stretch=1)

    def _refresh_ports(self) -> None:
        ports = SerialTransport.list_serial_ports()
        selected = self._port_combo.currentText()
        self._port_combo.clear()
        self._port_combo.addItems(ports)
        if selected and selected in ports:
            self._port_combo.setCurrentText(selected)
        elif ports:
            self._port_combo.setCurrentIndex(0)
        self._append_output(f"Port list refreshed ({len(ports)} found).")

    def _toggle_connection(self) -> None:
        if self._transport and self._transport.is_open:
            self._disconnect()
        else:
            self._connect()

    def _selected_instrument(self) -> InstrumentType:
        return InstrumentType(self._instrument_combo.currentText())

    def _selected_profile(self) -> InstrumentProfile:
        return INSTRUMENT_PROFILES[self._selected_instrument()]

    def _on_instrument_changed(self, _: int) -> None:
        if self._transport and self._transport.is_open:
            return
        self._reload_functions_for_instrument()

    def _reload_functions_for_instrument(self) -> None:
        profile = self._selected_profile()
        self._clear_measurement_rows()
        default_function = MeasurementFunction.VOLTAGE
        if default_function not in profile.commands:
            default_function = next(iter(profile.commands))
        self._add_measurement_row(default_function)
        self._refresh_measurement_controls()
        self._append_output(f"Loaded profile: {profile.instrument.value}.")

    def _clear_measurement_rows(self) -> None:
        for row in self._measurement_rows:
            self._measurement_rows_layout.removeWidget(row.container)
            row.container.deleteLater()
        self._measurement_rows.clear()

    def _add_measurement_row(self, function: MeasurementFunction | None = None) -> None:
        profile = self._selected_profile()
        available_functions = list(profile.commands.keys())
        if function is None:
            used = {MeasurementFunction(row.function_combo.currentText()) for row in self._measurement_rows}
            function = next((item for item in available_functions if item not in used), None)
            if function is None:
                QMessageBox.information(
                    self,
                    "No Additional Measurement",
                    "All available measurements for this instrument are already in the list.",
                )
                return

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        function_combo = QComboBox()
        function_combo.addItems([item.value for item in available_functions])
        function_combo.setCurrentText(function.value)
        row_layout.addWidget(function_combo)

        row_layout.addStretch(1)

        latest_label = QLabel("--")
        latest_label.setMinimumWidth(160)
        row_layout.addWidget(latest_label)

        remove_button = QPushButton("Remove")
        row_layout.addWidget(remove_button)

        row = MeasurementRow(
            container=row_widget,
            function_combo=function_combo,
            latest_label=latest_label,
            remove_button=remove_button,
            last_valid_function=function,
        )
        remove_button.clicked.connect(lambda: self._remove_measurement_row(row))
        function_combo.currentIndexChanged.connect(lambda _idx, r=row: self._on_measurement_function_changed(r))

        self._measurement_rows.append(row)
        self._measurement_rows_layout.addWidget(row_widget)
        self._refresh_measurement_controls()

    def _add_measurement(self) -> None:
        if self._poller and self._poller.is_alive():
            return
        if self._selected_instrument() == InstrumentType.MP730889:
            QMessageBox.information(
                self,
                "Not Supported",
                "MP730889 cannot run voltage and current measurements at the same time.",
            )
            return
        self._add_measurement_row()

    def _remove_measurement_row(self, row: MeasurementRow) -> None:
        if self._poller and self._poller.is_alive():
            return
        if len(self._measurement_rows) <= 1:
            return
        if row not in self._measurement_rows:
            return
        self._measurement_rows.remove(row)
        self._measurement_rows_layout.removeWidget(row.container)
        row.container.deleteLater()
        self._refresh_measurement_controls()

    def _refresh_measurement_controls(self) -> None:
        profile = self._selected_profile()
        is_polling = bool(self._poller and self._poller.is_alive())
        row_count = len(self._measurement_rows)
        max_rows = len(profile.commands)
        can_multi = self._selected_instrument() == InstrumentType.OWON_SPE6103

        if can_multi:
            self._add_measurement_button.setToolTip("")
            self._add_measurement_button.setEnabled((not is_polling) and row_count < max_rows)
        else:
            self._add_measurement_button.setEnabled(False)
            self._add_measurement_button.setToolTip(
                "MP730889 cannot read voltage and current simultaneously."
            )

        for row in self._measurement_rows:
            row.function_combo.setEnabled(not is_polling)
            row.remove_button.setEnabled(can_multi and (not is_polling) and row_count > 1)

        self._start_button.setEnabled(not is_polling)
        self._stop_button.setEnabled(is_polling)
        self._snapshot_button.setEnabled(not is_polling)

    def _has_function_in_other_rows(
        self, target_row: MeasurementRow, function: MeasurementFunction
    ) -> bool:
        for row in self._measurement_rows:
            if row is target_row:
                continue
            if MeasurementFunction(row.function_combo.currentText()) == function:
                return True
        return False

    def _on_measurement_function_changed(self, row: MeasurementRow) -> None:
        selected = MeasurementFunction(row.function_combo.currentText())
        if self._has_function_in_other_rows(row, selected):
            with QSignalBlocker(row.function_combo):
                row.function_combo.setCurrentText(row.last_valid_function.value)
            QMessageBox.warning(
                self,
                "Duplicate Measurement",
                "Each measurement row must use a different function.",
            )
            return
        row.last_valid_function = selected
        self._refresh_measurement_controls()

    def _validate_unique_measurement_rows(self) -> bool:
        seen: set[MeasurementFunction] = set()
        duplicates: list[MeasurementFunction] = []
        for row in self._measurement_rows:
            function = MeasurementFunction(row.function_combo.currentText())
            if function in seen and function not in duplicates:
                duplicates.append(function)
            seen.add(function)
        if not duplicates:
            return True

        duplicate_names = ", ".join(item.value for item in duplicates)
        QMessageBox.warning(
            self,
            "Duplicate Measurements",
            f"Duplicate measurement rows detected: {duplicate_names}. Use unique functions per row.",
        )
        return False

    def _query_device_idn(self, announce: bool = True) -> str:
        if not self._scpi:
            return "UNKNOWN"
        profile = self._selected_profile()
        try:
            response = self._scpi.query(profile.idn_query).strip()
            self._device_idn = response if response else "UNKNOWN"
            if announce:
                self._append_output(f"{profile.idn_query} -> {self._device_idn}")
            return self._device_idn
        except Exception as exc:  # pragma: no cover - hardware dependency
            self._device_idn = "UNKNOWN"
            if announce:
                self._append_output(f"{profile.idn_query} failed: {exc}")
            return self._device_idn

    def _validate_device_identity(self, profile_instrument: InstrumentType) -> bool:
        profile = INSTRUMENT_PROFILES[profile_instrument]
        if self._device_idn == "UNKNOWN":
            QMessageBox.critical(
                self,
                "Identity Validation Failed",
                "Unable to read device identity. Check cabling/SCPI mode and try again.",
            )
            return False
        if idn_matches_profile(profile, self._device_idn):
            return True

        expected = ", ".join(profile.idn_expected_tokens)
        QMessageBox.critical(
            self,
            "Instrument Mismatch",
            (
                "Selected instrument does not match connected device.\n\n"
                f"Selected: {profile.instrument.value}\n"
                f"Expected ID contains one of: {expected}\n"
                f"Received ID: {self._device_idn}"
            ),
        )
        return False

    def _connect(self) -> None:
        port = self._port_combo.currentText().strip()
        if not port:
            QMessageBox.critical(self, "Connection", "Select a serial port before connecting.")
            return
        try:
            baud = int(self._baud_combo.currentText().strip())
        except ValueError:
            QMessageBox.critical(self, "Connection", "Baud rate must be an integer.")
            return

        try:
            settings = SerialSettings(port=port, baudrate=baud)
            self._transport = SerialTransport(settings)
            self._transport.open()
            self._scpi = SCPIClient(self._transport)
            self._connect_button.setText("Disconnect")
            self._instrument_combo.setEnabled(False)
            instrument = self._selected_instrument()
            self._query_device_idn(announce=False)
            if not self._validate_device_identity(instrument):
                self._disconnect()
                return
            self._status_label.setText(f"Connected: {port} @ {baud} ({instrument.value})")
            self._append_output(f"Connected to {port} at {baud} baud for {instrument.value}.")
            self._append_output(f"Device ID: {self._device_idn}")
        except Exception as exc:  # pragma: no cover - hardware dependency
            self._transport = None
            self._scpi = None
            QMessageBox.critical(self, "Connection failed", str(exc))
            self._status_label.setText("Disconnected")

        self._refresh_measurement_controls()

    def _disconnect(self) -> None:
        self._stop_polling()
        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
        self._transport = None
        self._scpi = None
        self._device_idn = "UNKNOWN"
        self._connect_button.setText("Connect")
        self._instrument_combo.setEnabled(True)
        self._status_label.setText("Disconnected")
        self._append_output("Disconnected.")
        self._refresh_measurement_controls()

    def _request_idn(self) -> None:
        if not self._scpi:
            QMessageBox.warning(self, "Not connected", "Connect to the instrument first.")
            return
        idn = self._query_device_idn(announce=True)
        if idn == "UNKNOWN":
            QMessageBox.critical(self, "ID query failed", "Failed to query device ID.")

    def _build_poll_requests(self, profile: InstrumentProfile) -> tuple[list[PollRequest], list[str]]:
        requests: list[PollRequest] = []
        setup_commands: list[str] = []

        for slot_index, row in enumerate(self._measurement_rows):
            function = MeasurementFunction(row.function_combo.currentText())
            command = profile.commands.get(function)
            if command is None:
                raise ValueError(f"{function.value} is not available for {profile.instrument.value}.")
            requests.append(
                PollRequest(
                    slot_index=slot_index,
                    function=function,
                    query_command=command.query_command,
                    unit=command.unit,
                )
            )
            setup_commands.extend(command.prepare_commands)

        deduped_setup: list[str] = []
        seen: set[str] = set()
        for setup_command in setup_commands:
            if setup_command in seen:
                continue
            seen.add(setup_command)
            deduped_setup.append(setup_command)
        return requests, deduped_setup

    def _start_polling(self) -> None:
        if not self._scpi:
            QMessageBox.warning(self, "Not connected", "Connect to the instrument before starting polling.")
            return
        if self._poller and self._poller.is_alive():
            return
        if not self._validate_unique_measurement_rows():
            return

        try:
            interval_ms = int(self._interval_input.text().strip())
            if interval_ms < 200 or interval_ms > 60_000:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Interval", "Interval must be an integer between 200 and 60000 ms.")
            return

        profile = self._selected_profile()
        try:
            requests, setup_commands = self._build_poll_requests(profile)
            for setup_command in setup_commands:
                self._scpi.write(setup_command)
        except Exception as exc:  # pragma: no cover - hardware dependency
            QMessageBox.critical(self, "Configuration failed", str(exc))
            return

        self._poller = PollingWorker(
            scpi=self._scpi,
            instrument=profile.instrument,
            device_idn=self._device_idn,
            measurements=requests,
            interval_seconds=interval_ms / 1000.0,
            on_reading=lambda reading: self._events.put(("reading", reading)),
            on_error=lambda err: self._events.put(("error", err)),
        )
        self._poller.start()
        function_list = ", ".join(request.function.value for request in requests)
        self._append_output(
            f"Polling started: {profile.instrument.value} [{function_list}], every {interval_ms} ms."
        )
        self._refresh_measurement_controls()

    def _stop_polling(self) -> None:
        if self._poller and self._poller.is_alive():
            self._poller.stop()
            self._poller.join(timeout=1.5)
            self._append_output("Polling stopped.")
        self._poller = None
        self._refresh_measurement_controls()

    def _take_snapshot(self) -> None:
        if not self._scpi:
            QMessageBox.warning(self, "Not connected", "Connect to the instrument before taking a snapshot.")
            return
        if not self._validate_unique_measurement_rows():
            return

        profile = self._selected_profile()
        try:
            requests, setup_commands = self._build_poll_requests(profile)
            for setup_command in setup_commands:
                self._scpi.write(setup_command)
            for request in requests:
                raw = self._scpi.query(request.query_command)
                reading = Reading(
                    timestamp=datetime.now(),
                    slot_index=request.slot_index,
                    instrument=profile.instrument,
                    device_idn=self._device_idn,
                    function=request.function,
                    raw_response=raw,
                    value=parse_primary_value(raw),
                    unit=request.unit,
                )
                self._consume_reading(reading, label_prefix="Snapshot")
        except Exception as exc:  # pragma: no cover - hardware dependency
            QMessageBox.critical(self, "Snapshot failed", str(exc))

    def _toggle_logging(self, enabled: bool) -> None:
        if enabled:
            if not self._log_path_label.text():
                self._choose_log_file()
                if not self._log_path_label.text():
                    self._log_checkbox.setChecked(False)
                    return
            if not self._logger:
                self._logger = CsvLogger(self._log_path_label.text())
            self._append_output(f"Logging enabled: {self._logger.path}")
        else:
            if self._logger:
                self._logger.close()
                self._logger = None
            self._append_output("Logging disabled.")

    def _choose_log_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose log file",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path = f"{path}.csv"
        if self._logger:
            self._logger.close()
            self._logger = None
        self._log_path_label.setText(path)
        if self._log_checkbox.isChecked():
            self._logger = CsvLogger(path)
            self._append_output(f"Logging file set: {path}")

    def _process_events(self) -> None:
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                break

            if kind == "reading":
                reading = payload
                if isinstance(reading, Reading):
                    self._consume_reading(reading)
            elif kind == "error":
                self._append_output(f"Polling error: {payload}")
                self._stop_polling()

    def _consume_reading(self, reading: Reading, label_prefix: str | None = None) -> None:
        display = reading.raw_response if reading.value is None else f"{reading.value:.6g} {reading.unit}"
        if 0 <= reading.slot_index < len(self._measurement_rows):
            self._measurement_rows[reading.slot_index].latest_label.setText(display)
        prefix = "" if not label_prefix else f"{label_prefix} | "
        self._append_output(
            f"{prefix}{reading.instrument.value} | Row {reading.slot_index + 1} | "
            f"{reading.function.value}: {display}"
        )
        if self._log_checkbox.isChecked() and self._logger:
            self._logger.write_reading(reading)

    def _append_output(self, text: str) -> None:
        self._output.append(text)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_polling()
        self._disconnect()
        if self._logger:
            self._logger.close()
            self._logger = None
        super().closeEvent(event)
