# User Guide

## Purpose
Run the MP730889 SCPI desktop app, connect to the meter, read values, and optionally log data.

## Prerequisites
- macOS with Homebrew available.
- Meter connected over serial (native serial or USB-serial adapter).
- Project checked out at `~/Code/Git/DMM` (or your local equivalent).

## 1. Create and activate environment
```bash
cd /Users/david/Code/Git/DMM
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies
```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-compile -r requirements.txt
```

## 3. Launch the app
```bash
python -m dmm_app.main
```

## 4. Basic usage
1. Select `Instrument` (`Multicomp Pro MP730889 DMM` or `OWON SPE6103 PSU`).
2. Click `Refresh` to load serial ports.
3. Select `Serial Port` and `Baud Rate`.
4. Click `Connect`.
   - The app validates `*IDN?` against the selected instrument profile and blocks mismatches.
5. Click `Request *IDN?` to verify communication.
6. Choose function (`Voltage` or `Current`) for the first measurement row.
7. Optional (OWON only): click `Add Measurement` to add another row (for example one row for voltage and one for current).
8. Optional: click `Remove` on any extra row to remove it.
   - Guard: duplicate functions across rows are blocked (rows must be unique).
9. Set interval in ms.
10. Click `Start` to poll all rows. The app queries each row back-to-back per interval to keep timestamps close.
11. Optional: check `Enable logging`, choose CSV file path.
12. Click `Snapshot` for a one-off reading across all rows without continuous polling.
13. Click `Stop` to end polling, `Disconnect` when done.

## Logging output
- CSV fields: `timestamp,measurement_slot,device_name,device_idn,function,value,unit,raw_response`
- A header row is written for new files.

## Troubleshooting
- Error: `No module named PySide6`
  - Run: `python -m pip install -r requirements.txt`
- Error while installing PySide6 on system Python
  - Recreate venv with Homebrew Python 3.12 and reinstall using `--no-compile`.
- No serial ports listed
  - Check cable, adapter, permissions, and reconnect device.
- Connected but no readings
  - Verify port, baud, SCPI mode on instrument, and try `*IDN?` first.
- Reading errors after connect
  - Confirm the correct `Instrument` profile is selected before connecting.
- Error: `Instrument Mismatch`
  - Select the correct instrument profile and reconnect.
- `Add Measurement` is disabled
  - This is expected for MP730889, which is restricted to one active measurement row.

## Exit and cleanup
- Close app window or disconnect device before unplugging.
- Deactivate environment with:
```bash
deactivate
```
