# SCPI Lab Instrument App Proposal

## Goal
Build a simple desktop GUI application for engineers to communicate with supported lab instruments over serial SCPI, starting with voltage and current measurement and scaling to broader command coverage.

## Scope (Current MVP)
1. Select instrument profile (MP730889 DMM or Owon SPE6103 PSU).
2. Select serial port and baud rate before connect.
3. Connect and disconnect safely.
4. Query and validate device identity (`*IDN?`) against selected profile.
5. Select measurement function from GUI (`Voltage`, `Current`).
6. Add/remove measurement rows (OWON supports multiple rows, MP remains single-row).
7. Prevent duplicate measurement functions across rows.
8. Configure editable polling interval in GUI.
9. Start/stop polling with GUI controls.
10. Display returned measurement values in a dedicated output area.
11. Support one-shot acquisition via `Snapshot`.
12. Enable/disable logging through checkbox.
13. Prompt for log file path when logging is enabled.

## Non-Goals (MVP)
- Full command coverage for either instrument in first release.
- Calibration workflows.
- Multi-device orchestration.
- Remote/cloud telemetry.

## Architecture Summary
- `Transport` layer: interface + `SerialTransport` implementation.
- `SCPIClient`: thread-safe SCPI write/query operations.
- `Instrument profiles`: declarative instrument-specific command mappings.
- `Polling worker`: background thread for periodic measurements.
- `Logger`: CSV persistence when enabled.
- `GUI`: PySide6 (Qt) control panel, status, dynamic measurement rows, and output display.

## SCPI Baseline Used
From the reviewed Multicomp and Owon SCPI manuals:
- Identity: `*IDN?`
- MP730889 voltage read path: `SYSTem:REMote` + `CONFigure:VOLTage:DC` then `MEAS1?`
- MP730889 current read path: `SYSTem:REMote` + `CONFigure:CURRent:DC` then `MEAS1?`
- Owon SPE6103 voltage read path: `SYSTem:REMote` then `MEASure:VOLTage?`
- Owon SPE6103 current read path: `SYSTem:REMote` then `MEASure:CURRent?`

Note: The reviewed Multicomp manual is for MP730424. Runtime model verification via `*IDN?` is required for MP730889 compatibility.

## Extensibility Plan
- Add additional functions by extending instrument profiles.
- Add advanced serial settings (parity/stop bits/timeout) in the GUI without changing core architecture.
- Add USB/LAN transport by implementing additional `Transport` classes.
- Introduce structured error codes and retry policies in SCPI layer.

## Acceptance Criteria
- User can connect to a chosen port/baud and issue `*IDN?`.
- Connection is rejected if selected profile does not match returned IDN.
- User can select voltage or current and read live values.
- OWON supports multi-row voltage/current polling in one interval cycle.
- MP remains single-row and prevents multi-measurement configuration.
- Poll interval is editable and enforced.
- Snapshot captures all configured rows.
- Logging prompts for destination and writes CSV rows including measurement slot and device identity.
