# Decisions

## 2026-02-11 - Python + PySide6 (Qt) desktop application
### Decision
Use a Python desktop app with PySide6 (Qt) for the GUI implementation.

### Why
Avoids system Tk runtime issues on modern macOS and provides a stronger widget/tooling baseline while keeping serial integration straightforward.

### Alternatives considered
- Tkinter: smaller dependency footprint but unstable on current macOS runtime in this environment.
- Electron/Tauri: more packaging complexity for hardware I/O MVP.

### Consequences
- Pros: stable modern GUI runtime and richer UI controls.
- Cons: larger dependency/runtime footprint than Tkinter.

## 2026-02-11 - Supported runtime and dependency baseline
### Decision
Use Homebrew Python 3.12 (or newer) in a project-local virtual environment and install dependencies from `requirements.txt`.

### Why
System Python 3.9 on macOS caused installation/runtime issues while installing GUI dependencies; a modern user-managed interpreter is more reliable.

### Alternatives considered
- Continue with Apple Command Line Tools Python 3.9.
- Pin older PySide6 versions to fit system Python.

### Consequences
- Pros: predictable dependency installs and fewer platform-specific crashes.
- Cons: requires one-time setup of Python toolchain for each developer machine.

## 2026-02-11 - Layered architecture (transport/client/poller/gui)
### Decision
Separate transport, SCPI command handling, polling, and GUI concerns.

### Why
Improves testability and supports extension to additional transports and meter functions without major rewrites.

### Alternatives considered
- Single-file monolithic GUI script.
- GUI directly issuing serial I/O without intermediary abstractions.

### Consequences
- Pros: maintainable and scalable design.
- Cons: slightly more initial code and project structure overhead.

## 2026-02-11 - Command registry for measurement functions
### Decision
Represent supported DMM functions as data entries in a command catalog.

### Why
Adding new functions becomes additive and low risk (new map entry plus UI exposure).

### Alternatives considered
- Hard-coded branching logic for each mode in GUI handlers.
- Dynamic runtime command entry with no schema.

### Consequences
- Pros: cleaner scaling path and clearer ownership of SCPI details.
- Cons: requires discipline to keep command metadata accurate.

## 2026-02-11 - CSV logging with opt-in checkbox and file prompt
### Decision
Enable logging through an explicit checkbox; prompt for file destination when enabled; write CSV rows per reading.

### Why
Matches lab workflow expectations and keeps logging behavior explicit and auditable.

### Alternatives considered
- Always-on default logging.
- Database-backed logging from first release.

### Consequences
- Pros: simple, transparent, and broadly compatible.
- Cons: no built-in query/index capabilities beyond CSV tools.

## 2026-02-11 - Runtime identity verification
### Decision
Use `*IDN?` as a baseline validation step after connection.

### Why
Reference manual reviewed targets MP730424; runtime check reduces risk when targeting MP730889.

### Alternatives considered
- Assume full command compatibility.
- Block functionality unless exact model string matches expected target.

### Consequences
- Pros: pragmatic safety gate without blocking development.
- Cons: still requires physical verification for complete command coverage.

## 2026-02-11 - Instrument profile selection (MP730889 + Owon SPE6103)
### Decision
Introduce a selectable instrument profile in the GUI and route SCPI measurement/configuration commands through instrument-specific command maps.

### Why
The Multicomp DMM and Owon PSU use different measurement command patterns (for example, `MEAS1?` vs `MEASure:VOLTage?`), so command routing must be explicit to avoid protocol mismatches.

### Alternatives considered
- Keep one global command set and ask users to adapt manually.
- Hard-code branch logic in GUI event handlers without a profile model.

### Consequences
- Pros: scalable structure for adding current and other measurements per instrument.
- Cons: slightly more setup logic and testing surface area.

## 2026-02-11 - Enforce instrument identity validation at connect
### Decision
After connection, query `*IDN?` and reject the session if the returned identity does not match the selected instrument profile.

### Why
Prevents sending the wrong SCPI command set to a mismatched device and avoids silent misconfiguration.

### Alternatives considered
- Warn only and allow continued operation.
- No validation and rely on user discipline.

### Consequences
- Pros: safer operation and clearer operator feedback.
- Cons: requires maintaining profile ID match tokens and may need tuning for firmware/model variants.

## 2026-02-11 - Multi-row measurements with capability gating
### Decision
Support multiple measurement rows for OWON (voltage/current) and lock MP730889 to a single active measurement row.

### Why
OWON can read both voltage and current via separate SCPI queries in one cycle, while MP730889 is constrained to one active measurement mode at a time.

### Alternatives considered
- Keep a single global measurement row for all devices.
- Allow multi-row on MP and accept mode-switch side effects.

### Consequences
- Pros: aligns UI behavior to instrument capability and minimizes operator error.
- Cons: adds dynamic row state management and per-cycle batching logic.
