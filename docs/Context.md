# Context

## Project one liner
Desktop SCPI control application for lab engineers to communicate with a Multicomp Pro DMM (MP730889 target) and acquire measurements over instrument I/O.

## Current objective
Deliver an MVP GUI that connects over serial, lets the user select the target instrument profile (Multicomp MP730889 or Owon SPE6103), supports one or multiple measurement rows per device capability, polls readings at a configurable interval, displays readings live, and optionally logs data to CSV.

## Repo map
- `dmm_app/`: application source code.
- `dmm_app/models.py`: domain models (serial settings, measurement function, reading).
- `dmm_app/transport.py`: transport abstraction and serial transport implementation.
- `dmm_app/scpi.py`: SCPI client wrapper for command/query.
- `dmm_app/commands.py`: measurement command catalog.
- `dmm_app/poller.py`: background polling worker.
- `dmm_app/logging_util.py`: CSV logging helper.
- `dmm_app/gui.py`: PySide6 (Qt) GUI and orchestration.
- `dmm_app/main.py`: app entrypoint.
- `docs/`: project docs and decision logs.
- `requirements.txt`: runtime dependencies.

## Key decisions (with dates)
- 2026-02-11: Chose Python desktop app for rapid delivery and straightforward serial integration.
- 2026-02-11: Migrated GUI from Tkinter to PySide6 (Qt) for better cross-platform runtime stability and richer UI controls.
- 2026-02-11: Standardized runtime on Homebrew Python 3.12 virtual environments to avoid Apple system Python + Tk/packaging issues.
- 2026-02-11: Added instrument-profile selection to support SCPI command nuances between MP730889 DMM and Owon SPE6103 PSU.
- 2026-02-11: Added connection-time IDN validation so selected instrument must match the connected device identity string.
- 2026-02-11: Added multi-row measurement scheduling for Owon so voltage and current can be queried in the same interval cycle.
- 2026-02-11: Chose modular architecture (transport/client/poller/commands/gui) to support future expansion to all DMM functions.
- 2026-02-11: Chose CSV as the initial log format for interoperability with lab workflows.
- 2026-02-11: Chose runtime SCPI identity verification (`*IDN?`) before relying on model-specific behavior.

## Constraints
- OS: macOS development environment; target desktop OS may include Windows/macOS/Linux.
- Tooling: Python 3.12+ recommended, `pyserial`, `PySide6` (Qt), virtual environment per repo.
- Security: local-only communication with instrument; no remote service exposure in MVP.
- Performance targets:
  - Poll interval configurable from 200 ms to 60,000 ms.
  - UI remains responsive during polling through background worker thread.

## Interfaces/contracts
- Device transport contract:
  - Open/close connection.
  - Write bytes.
  - Read until terminator.
- SCPI command contract:
  - Command strings terminated with newline.
  - Query returns ASCII text line.
- Data logging contract:
  - CSV columns: `timestamp,function,value,unit,raw_response`.
- GUI interaction contract:
  - User selects instrument profile prior to connection.
  - User selects port/baud prior to connection.
  - Logging enable triggers file selection flow.

## Open questions / risks
- Manual reviewed was for MP730424; MP730889 command parity and transport behavior need hardware validation.
- Line termination and timeout details may vary by firmware revision.
- Some devices require explicit remote-control enablement before SCPI commands.
- Serial parameters beyond baud (parity/stop bits) may need exposure for certain interfaces/adapters.
- PySide6 installation can fail on older/system Python distributions; team should align on one supported Python runtime.

## Next actions
- Validate MP730889 `*IDN?` response and baseline SCPI commands on real hardware.
- Confirm required serial framing details and update defaults if needed.
- Add GUI controls for advanced serial options (parity, data bits, stop bits, timeout).
- Add additional measurement functions to `dmm_app/commands.py`.
- Add unit/instrument tests with transport and SCPI mocks.
- Add structured status/error indicators (warning/error levels) in UI.
- Add log rotation or session-based file naming option.
- Add model-specific capability gating after ID query.
- Add packaging guidance (PyInstaller or equivalent) once runtime/toolchain is finalized.

## Glossary
- DMM: Digital Multimeter.
- SCPI: Standard Commands for Programmable Instruments.
- MVP: Minimum Viable Product.
- IDN: Instrument identity query (`*IDN?`).
- Polling: Periodic query loop for measurement collection.
- CSV: Comma Separated Values log format.
- Venv: Python virtual environment for isolated dependencies.
