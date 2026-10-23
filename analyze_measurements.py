#!/usr/bin/env python3
"""Validate Mediverse CSV data and generate comparison/normalized graphs.

Install: python -m pip install matplotlib
Run: python analyze_measurements.py mediverse_measurements.csv --out results

Only rows with status OK are included in the graphs. Saturation flags are reported,
not silently converted to plausible values. Repeated scans are aggregated by angle.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
import statistics
import sys

import matplotlib.pyplot as plt

EXPECTED_ANGLES = list(range(0, 181, 10))
VALID_TYPES = {"reference", "sample"}
REQUIRED_COLUMNS = {
    "scan_id", "measurement_type", "angle_deg", "adc_median",
    "adc_min", "adc_max", "n", "status"
}


def load_rows(path: Path):
    grouped = {"reference": defaultdict(list), "sample": defaultdict(list)}
    excluded = []
    total = 0
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
            missing_cols = REQUIRED_COLUMNS - columns
            if missing_cols:
                raise ValueError("CSV missing columns: " + ", ".join(sorted(missing_cols)))
            for row in reader:
                if not row or not row.get("measurement_type"):
                    continue
                total += 1
                typ = row["measurement_type"].strip().lower()
                if typ not in VALID_TYPES:
                    excluded.append((row, "unknown measurement_type"))
                    continue
                try:
                    angle = int(row["angle_deg"])
                    value = int(row["adc_median"])
                    n = int(row["n"])
                except (ValueError, TypeError):
                    excluded.append((row, "non-numeric field"))
                    continue
                status = (row.get("status") or "").strip().upper()
                if status != "OK":
                    excluded.append((row, f"status={status or 'MISSING'}"))
                    continue
                if angle not in EXPECTED_ANGLES:
                    excluded.append((row, "angle not in required 0..180 by 10° grid"))
                    continue
                if not 0 <= value <= 4095 or n <= 0:
                    excluded.append((row, "out-of-range ADC value or sample count"))
                    continue
                grouped[typ][angle].append(value)
    except OSError as exc:
        raise ValueError(f"Could not read {path}: {exc}") from exc
    return grouped, excluded, total


def aggregate(data):
    result = {}
    spread = {}
    counts = {}
    for angle, values in data.items():
        result[angle] = statistics.mean(values)
        spread[angle] = statistics.stdev(values) if len(values) >= 2 else 0.0
        counts[angle] = len(values)
    return result, spread, counts


def describe_curve(label, values):
    if not values:
        return [f"{label}: no valid data points"]
    angles = sorted(values)
    vmin_angle = min(angles, key=lambda a: values[a])
    vmax_angle = max(angles, key=lambda a: values[a])
    vmin, vmax = values[vmin_angle], values[vmax_angle]
    return [
        f"{label}:",
        f"  valid angles: {len(values)}/{len(EXPECTED_ANGLES)}",
        f"  minimum aggregated ADC median: {vmin:.2f} at {vmin_angle}°",
        f"  maximum aggregated ADC median: {vmax:.2f} at {vmax_angle}°",
        f"  peak-to-peak ADC span: {vmax - vmin:.2f}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", help="CSV created by serial_logger.py")
    parser.add_argument("--out", default="mediverse_results", help="Directory for graph and report outputs")
    args = parser.parse_args()
    csv_path = Path(args.csv_file)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        grouped, excluded, total = load_rows(csv_path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    means, spreads, counts = {}, {}, {}
    for typ in VALID_TYPES:
        means[typ], spreads[typ], counts[typ] = aggregate(grouped[typ])

    valid_total = sum(sum(len(v) for v in grouped[t].values()) for t in VALID_TYPES)
    print(f"Rows considered: {total}; valid rows: {valid_total}; excluded/status-flagged rows: {len(excluded)}")
    if excluded:
        print("Excluded rows (first 20):")
        for row, why in excluded[:20]:
            print(f"  scan={row.get('scan_id')} type={row.get('measurement_type')} angle={row.get('angle_deg')}: {why}")
        if len(excluded) > 20:
            print(f"  ... plus {len(excluded) - 20} more")

    for typ in sorted(VALID_TYPES):
        missing = [a for a in EXPECTED_ANGLES if a not in means[typ]]
        print(f"{typ}: missing valid measurements at {missing if missing else 'none'}")

    if not means["reference"] or not means["sample"]:
        print("Both reference and sample valid data are required to make the comparison graphs.", file=sys.stderr)
        return 3

    # Required graph: raw ADC readings from reference and sample on the same axes.
    fig, ax = plt.subplots(figsize=(10, 6))
    for typ, label in (("reference", "Reference (no sample)"), ("sample", "Sample inserted")):
        angles = sorted(means[typ])
        y = [means[typ][a] for a in angles]
        yerr = [spreads[typ][a] if counts[typ][a] >= 2 else 0 for a in angles]
        ax.errorbar(angles, y, yerr=yerr, marker="o", linewidth=1.8, capsize=3, label=label)
    ax.set_title("Mediverse: LDR ADC response versus polarizer angle")
    ax.set_xlabel("Commanded polarizer angle (degrees)")
    ax.set_ylabel("LDR voltage-divider ADC reading (raw counts, 0–4095 scale)")
    ax.set_xticks(EXPECTED_ANGLES)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    raw_path = out_dir / "comparison_raw_adc.png"
    fig.savefig(raw_path, dpi=180)
    plt.close(fig)

    # Supplementary graph: each curve scaled by its own maximum to compare shape only.
    fig, ax = plt.subplots(figsize=(10, 6))
    for typ, label in (("reference", "Reference, normalized to its own maximum"),
                       ("sample", "Sample, normalized to its own maximum")):
        curve = means[typ]
        max_value = max(curve.values()) if curve else 0
        if max_value <= 0:
            print(f"Cannot normalize {typ}: its maximum is not positive.")
            continue
        angles = sorted(curve)
        y = [curve[a] / max_value for a in angles]
        ax.plot(angles, y, marker="o", linewidth=1.8, label=label)
    ax.set_title("Supplementary shape comparison (each curve normalized independently)")
    ax.set_xlabel("Commanded polarizer angle (degrees)")
    ax.set_ylabel("Normalized ADC response (unitless; own maximum = 1)")
    ax.set_xticks(EXPECTED_ANGLES)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    normalized_path = out_dir / "comparison_normalized_shape.png"
    fig.savefig(normalized_path, dpi=180)
    plt.close(fig)

    report = [
        "MEDIVERSE MEASUREMENT SUMMARY",
        f"Input file: {csv_path.resolve()}",
        f"CSV rows considered: {total}",
        f"Valid rows included: {valid_total}",
        f"Rows excluded or status-flagged: {len(excluded)}",
        "",
        *describe_curve("Reference", means["reference"]),
        "",
        *describe_curve("Sample", means["sample"]),
        "",
        "Interpretation cautions:",
        "- These are raw ADC counts from an LDR voltage divider, not calibrated optical intensity units.",
        "- The normalized plot compares curve shape; because each curve is divided by its own maximum, it removes absolute scale differences.",
        "- Do not treat a curve difference as proof of fibrosis. Consider alignment, ambient light, LED stability, sensor saturation, and sample position.",
        "- Repeated scans are aggregated by mean of the scan-level ADC medians; error bars show the sample standard deviation when repeats exist.",
    ]
    report_path = out_dir / "summary.txt"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    # Long-form aggregated table for easy spreadsheet import.
    aggregate_path = out_dir / "aggregated_by_angle.csv"
    with aggregate_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["measurement_type", "angle_deg", "mean_of_scan_medians", "scan_count", "sd_across_scans", "status_note"])
        for typ in ("reference", "sample"):
            for angle in EXPECTED_ANGLES:
                if angle in means[typ]:
                    writer.writerow([typ, angle, f"{means[typ][angle]:.3f}", counts[typ][angle], f"{spreads[typ][angle]:.3f}", "OK"])
                else:
                    writer.writerow([typ, angle, "", 0, "", "MISSING_VALID_MEASUREMENT"])

    print("\n".join(report))
    print(f"\nWrote: {raw_path}, {normalized_path}, {report_path}, {aggregate_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
