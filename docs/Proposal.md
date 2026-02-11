# MP730889 SCPI GUI Proposal

## Goal
Build a simple desktop GUI application for engineers to communicate with a Multicomp Pro MP730889 digital multimeter over a serial connection, starting with voltage measurement and scaling to broader SCPI coverage.

## Scope (Current MVP)
1. Select instrument profile (MP730889 DMM or Owon SPE6103 PSU).
2. Select serial port and baud rate before connect.
3. Connect and disconnect safely.
4. Query device identity/info (`*IDN?`).
5. Select measurement function from GUI (voltage now, current planned next).
6. Add/remove measurement rows (OWON supports multiple rows, MP remains single-row).
7. Configure editable polling interval in GUI.
8. Start/stop polling with GUI controls.
9. Display returned measurement values in a dedicated output area.
10. Enable/disable logging through checkbox.
11. Prompt for log file path when logging is enabled.

## Non-Goals (MVP)
- Full meter function coverage in first release.
- Calibration workflows.
- Multi-device orchestration.
- Remote/cloud telemetry.

## Architecture Summary
- `Transport` layer: interface + `SerialTransport` implementation.
- `SCPIClient`: thread-safe SCPI write/query operations.
- `Command registry`: declarative command mapping for measurement modes.
- `Polling worker`: background thread for periodic measurements.
- `Logger`: CSV persistence when enabled.
- `GUI`: PySide6 (Qt) control panel, status, and output display.

## SCPI Baseline Used
From the reviewed Multicomp and Owon SCPI manuals:
- Identity: `*IDN?`
- MP730889 voltage read path: `SYSTem:REMote` + `CONFigure:VOLTage:DC` then `MEAS1?`
- Owon SPE6103 voltage read path: `SYSTem:REMote` then `MEASure:VOLTage?`

Note: The reviewed Multicomp manual is for MP730424. Runtime model verification via `*IDN?` is required for MP730889 compatibility.

## Extensibility Plan
- Add additional functions by extending the command registry.
- Add advanced serial settings (parity/stop bits/timeout) in the GUI without changing core architecture.
- Add USB/LAN transport by implementing additional `Transport` classes.
- Introduce structured error codes and retry policies in SCPI layer.

## Acceptance Criteria
- User can connect to a chosen port/baud and issue `*IDN?`.
- User can select DC/AC voltage and see live values.
- Poll interval is editable and enforced.
- Logging prompts for destination and writes CSV records with timestamp/value/raw response.
