#!/usr/bin/env python3
"""Capture Mediverse ESP32 CSV rows to a durable local CSV file.

Install: python -m pip install pyserial
Example: python serial_logger.py --port COM5 --out mediverse_measurements.csv
Linux example: python serial_logger.py --port /dev/ttyUSB0 --out mediverse_measurements.csv
Close Arduino Serial Monitor first; only one program can own the serial port.
"""
import argparse
import csv
import sys
import threading
import time
from pathlib import Path

import serial

HEADER = [
    "scan_id", "measurement_type", "angle_deg", "adc_median",
    "adc_min", "adc_max", "n", "status"
]
VALID_TYPES = {"reference", "sample"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM5 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--out", default="mediverse_measurements.csv")
    args = parser.parse_args()

    output = Path(args.out)
    write_header = not output.exists() or output.stat().st_size == 0
    stop = threading.Event()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
    except serial.SerialException as exc:
        print(f"Could not open {args.port}: {exc}", file=sys.stderr)
        return 2

    # Many ESP32 boards reset when the serial port opens.
    time.sleep(2.0)
    print(f"Connected to {args.port} at {args.baud} baud. Logging data rows to {output.resolve()}")
    print("Commands: r = reference scan, s = sample scan, t = sensor test, h = help, q = quit")
    print("Close Arduino Serial Monitor before starting this logger.")

    file_handle = output.open("a", newline="", encoding="utf-8")
    writer = csv.writer(file_handle)
    if write_header:
        writer.writerow(HEADER)
        file_handle.flush()

    def reader() -> None:
        while not stop.is_set():
            try:
                raw = ser.readline()
            except serial.SerialException as exc:
                print(f"Serial read error: {exc}", file=sys.stderr)
                stop.set()
                break
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("#"):
                print(line)
                continue
            try:
                row = next(csv.reader([line]))
                if len(row) != len(HEADER) or row[1].strip().lower() not in VALID_TYPES:
                    print(f"[serial] {line}")
                    continue
                # Check key fields before persisting; retain status-flagged rows too.
                int(row[0]); int(row[2]); int(row[3]); int(row[4]); int(row[5]); int(row[6])
                writer.writerow(row)
                file_handle.flush()
                print(f"[saved] scan {row[0]} {row[1]} angle={row[2]}° ADC median={row[3]} status={row[7]}")
            except (ValueError, csv.Error, IndexError):
                print(f"[serial] {line}")

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        while not stop.is_set():
            try:
                command = input("> ").strip().lower()
            except EOFError:
                break
            if command in {"q", "quit", "exit"}:
                break
            if command in {"r", "s", "t", "h", "?", "l", "x"}:
                ser.write((command + "\n").encode("ascii"))
            else:
                print("Use r, s, t, h, l, x, or q.")
    except KeyboardInterrupt:
        print("\nStopping logger...")
    finally:
        stop.set()
        thread.join(timeout=1.5)
        file_handle.close()
        ser.close()
    print(f"Finished. Data file: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
