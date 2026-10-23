# 🔬 Mediverse — Optical Measurement & Analysis Prototype

**Bridging optics, embedded systems, and software to explore sensor-based optical measurements.**

Mediverse is a student-built hardware–software prototype that combines optical principles, embedded electronics, sensor interfacing, servo-controlled positioning, and real-time data visualization. The project explores how variations in received light intensity can be measured, recorded, and analysed through a low-cost experimental setup.

🏆 **Recognition:** Received special recognition for innovation at an IEEE EMBS BMSIT&M event.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Motivation](#-motivation)
- [Objectives](#-objectives)
- [How It Works](#-how-it-works)
- [System Architecture](#-system-architecture)
- [Hardware Components](#-hardware-components)
- [Software Stack](#-software-stack)
- [Features](#-features)
- [Measurement Methodology](#-measurement-methodology)
- [Repository Structure](#-repository-structure)
- [Getting Started](#-getting-started)
- [Operating the Prototype](#-operating-the-prototype)
- [Data Format](#-data-format)
- [Current Status](#-current-status)
- [Limitations](#-limitations)
- [Future Improvements](#-future-improvements)
- [Recognition](#-recognition)
- [Contributing](#-contributing)
- [Disclaimer](#-disclaimer)
- [License](#-license)

---

## 🧪 Overview

Mediverse explores the use of optical measurements and embedded data acquisition in an accessible experimental platform.

The prototype uses an ESP32 microcontroller to interface with a light source, a light-dependent resistor (LDR), and a servo motor. A Python-based desktop dashboard communicates with the microcontroller over USB serial, enabling hardware control, sensor testing, measurement logging, and visualization.

The project is inspired by optical measurement approaches, including the principles used in polarimetry. Its intended experimental configuration explores how received light intensity changes with optical alignment and the presence of a sample.

**Mediverse is currently an educational and experimental prototype.** Its optical configuration, calibration, repeatability, and suitability for any specific biomedical application require further verification.

## 💡 Motivation

Optical measurement techniques can provide useful ways to investigate the interaction between light and materials. However, exploring these principles often requires a combination of optical components, electronics, data acquisition, and analysis software.

Mediverse aims to bring these elements together in a compact, accessible platform that allows students to:

- Experiment with light-intensity measurements.
- Interface physical sensors with a microcontroller.
- Control mechanical positioning using a servo motor.
- Acquire and analyse measurements using Python.
- Develop a foundation for future optical sensing research.

## 🎯 Objectives

- Build a low-cost optical measurement prototype.
- Integrate sensing, embedded control, and desktop software.
- Measure changes in received light intensity under different experimental conditions.
- Record sensor measurements in a structured CSV format.
- Visualize measurements to support observation and comparison.
- Establish a foundation for improved calibration and future experimental studies.

## ⚙️ How It Works

The prototype consists of two main parts: the physical measurement system and the software dashboard.

### 1. Optical measurement setup

A light source illuminates the optical path. The transmitted light reaches the LDR, which converts changes in illumination into changes in electrical resistance. A voltage-divider circuit converts the sensor response into a voltage that can be sampled by the ESP32's ADC.

A servo motor provides controlled mechanical positioning for the optical assembly.

The intended polarimetry configuration includes polarizing elements and a sample in the optical path. The performance of this configuration depends on verifying the optical components, alignment, and calibration.

### 2. Embedded data acquisition

The ESP32:

- Reads the LDR through an ADC input.
- Collects repeated readings for a measurement.
- Calculates summary statistics such as the median, minimum, and maximum.
- Controls the LED and servo through supported commands.
- Transmits measurement information over USB serial.

### 3. Desktop visualization

The Python application communicates with the ESP32 over a serial connection. It provides a graphical interface for interacting with the prototype, monitoring sensor readings, controlling hardware, and observing measurement data.

The software stack uses Tkinter for the interface, Matplotlib for plotting, and PySerial for serial communication.

## 🏗️ System Architecture

```text
                 OPTICAL MEASUREMENT SYSTEM
                 ──────────────────────────

       LED Light Source
              │
              ▼
     Optical Elements / Sample
       (experimental setup)
              │
              ▼
         LDR Sensor
              │
              ▼
       Voltage Divider
              │
              ▼
        ESP32 ADC Input
              │
              ▼
     Embedded Measurement Logic
       ├── Repeated ADC readings
       ├── Median / Min / Max
       ├── LED control
       └── Servo positioning
              │
         USB Serial
              │
              ▼
       Python Desktop App
       ├── Tkinter interface
       ├── Matplotlib plots
       ├── Hardware controls
       └── Measurement logging
              │
              ▼
         CSV Data Files
```

## 🔩 Hardware Components

| Component | Purpose |
|---|---|
| ESP32 development board | Embedded control and data acquisition |
| Light-dependent resistor (LDR) | Detects changes in received light intensity |
| LED and current-limiting resistor | Provides a controllable light source |
| MG90S servo motor | Enables controlled mechanical positioning |
| 10 kΩ resistor | Forms the LDR voltage-divider circuit |
| Optical films or polarizing elements | Used in the intended optical experiment; component type must be verified |
| Breadboard and jumper wires | Circuit prototyping and connections |
| USB connection | Power for the ESP32 and serial communication with the computer |

*The final component list and optical arrangement should be updated to match the actual hardware assembled.*

## 💻 Software Stack

| Technology | Role |
|---|---|
| C++ / Arduino framework | ESP32 firmware |
| Arduino IDE | Firmware development and upload |
| Python | Dashboard and data-processing logic |
| Tkinter | Desktop graphical interface |
| Matplotlib | Measurement visualization |
| PySerial | USB serial communication |
| CSV | Structured measurement storage |

## ✨ Features

### Embedded system

- ESP32-based sensor acquisition.
- LDR measurement through the ADC.
- Repeated sensor readings with summary statistics.
- LED control.
- Servo positioning commands.
- Serial communication with a desktop computer.

### Desktop application

- Graphical interface for hardware interaction.
- Serial connection and command controls.
- Sensor testing and measurement monitoring.
- Visualization of measurement data.
- Structured CSV logging for later analysis.

### Experimental workflow

- Reference measurements without a sample.
- Sample measurements with a sample inserted.
- Comparison of readings under matched experimental conditions.
- A foundation for future calibration, repeatability analysis, and improved plotting.

*Feature availability depends on the current firmware and dashboard implementation. Only verified functions should be presented as completed capabilities.*

## 📐 Measurement Methodology

Mediverse uses an LDR to obtain a relative measurement of received light intensity.

### Sensor response

An LDR generally decreases in resistance as incident illumination increases. In the voltage-divider arrangement used by this prototype, the ADC reading increases with illumination.

The ESP32 ADC provides digital readings nominally spanning 0–4095 in a 12-bit configuration. These values are **raw ADC counts, not calibrated lux or absolute optical power**.

### Reference and sample measurements

A basic experimental comparison can follow this procedure:

1. Keep the light source, sensor, distance, and optical alignment fixed.
2. Record a reference measurement without the sample.
3. Insert the sample without disturbing the rest of the setup.
4. Record the sample measurement.
5. Repeat the measurements to evaluate consistency.
6. Compare the resulting measurements and document experimental conditions.

### Polarimetry principles

For ideal linearly polarized light passing through an analyser, Malus's law describes the transmitted intensity:

\[
I(\theta)=I_0\cos^2(\theta)
\]

where:

- \(I(\theta)\) is the transmitted intensity at the relative angle \(\theta\).
- \(I_0\) is the maximum transmitted intensity.
- \(\theta\) is the angle between the relevant polarization directions.

Applying this relationship experimentally requires verified polarizers, controlled alignment, a suitable angular reference, and calibration. A servo command alone does not establish the actual optical angle, and LDR readings alone do not demonstrate that a polarimetry experiment has been validated.

## 📁 Repository Structure

The project is organized around the ESP32 firmware and the Python desktop application.

```text
mediverse/
├── mediverse_firmware/
│   ├── mediverse_firmware.ino
│   └── ReadingStats.h
├── mediverse_dashboard.py
├── serial_logger.py
├── analyze_measurements.py
├── requirements.txt
├── README.md
└── .gitignore
```

*This is the intended layout based on the current development files. Adjust filenames and folders to match the actual repository before publishing.*

## 🚀 Getting Started

### Prerequisites

- An ESP32 development board compatible with the firmware.
- Arduino IDE.
- Python 3.
- USB data cable.
- The required sensor, LED, servo, and supporting circuit components.
- A Windows, Linux, or macOS computer.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/mediverse.git
cd mediverse
```

Replace `YOUR_USERNAME` with the GitHub username or organization that owns the repository.

### 2. Set up the Python environment

Create and activate a virtual environment.

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

If a requirements file is not present, the currently used dashboard dependencies include:

```bash
python -m pip install pyserial matplotlib
```

Tkinter is included with many Python installations, but some Linux distributions require a separate system package.

### 3. Upload the ESP32 firmware

1. Open `mediverse_firmware/mediverse_firmware.ino` in Arduino IDE.
2. Select the appropriate ESP32 board, such as **ESP32 Dev Module**, if it matches your hardware.
3. Select the correct serial port.
4. Install any missing firmware libraries.
5. Compile and upload the firmware.
6. Open Serial Monitor at the firmware's configured baud rate, currently 115200 baud, if you need to inspect boot messages.

### 4. Connect the hardware

Check the wiring against the pin definitions in the firmware before powering the prototype.

In particular:

- Confirm the LDR voltage-divider connections.
- Use a suitable current-limiting resistor for the LED.
- Verify the servo's power requirements and provide an appropriate supply.
- Connect the ESP32 and external servo supply grounds together when required by the circuit.
- Do not power the servo directly from an ESP32 GPIO.
- Avoid commanding servo movement until its mechanical range and wiring have been checked.

### 5. Launch the dashboard

From the project root:

```bash
python mediverse_dashboard.py
```

Select the correct serial port and connect to the ESP32. The current firmware configuration uses **115200 baud**.

## 🎛️ Operating the Prototype

The firmware exposes the following serial commands:

| Command | Function |
|---|---|
| `H` | Display available commands |
| `T` | Run a sensor test with the LED on |
| `L` | Turn the LED on |
| `X` | Turn the LED off |
| `J0`–`J180` | Command a logical servo position |
| `P900`–`P2100` | Set a servo pulse width for unloaded calibration, where supported |
| `R` | Run a reference scan, subject to firmware safety checks |
| `S` | Run a sample scan, subject to firmware safety checks |

**Important:** The firmware includes safety guards for scan operations until the servo range and optical zero are verified. Do not bypass these checks simply to enable scanning. Complete the physical and optical calibration first.

## 📊 Data Format

The firmware's scan output uses CSV-style rows with the following fields:

```text
scan_id,measurement_type,angle_deg,adc_median,adc_min,adc_max,n,status
```

| Field | Description |
|---|---|
| `scan_id` | Identifier for a scan |
| `measurement_type` | Reference or sample measurement |
| `angle_deg` | Commanded or reported measurement angle |
| `adc_median` | Median ADC reading |
| `adc_min` | Minimum ADC reading |
| `adc_max` | Maximum ADC reading |
| `n` | Number of readings summarized |
| `status` | Measurement status, including relevant sensor conditions |

The ADC minimum and maximum help indicate variation during a measurement. Status values can identify conditions such as saturation, depending on the firmware implementation.

Sensor readings should be retained with their experimental conditions, including optical alignment, sample placement, ambient light, and supply configuration. These factors can influence the results.

## 🛠️ Current Status

| Area | Status |
|---|---|
| ESP32 firmware compilation and upload | Tested |
| USB serial communication | Tested |
| LED control | Implemented; verify on the assembled circuit |
| LDR response to illumination | Tested |
| Servo movement commands | Basic movement tested |
| Python dashboard serial connection | Tested |
| Optical component verification | Pending |
| Optical zero and angular calibration | Pending |
| Complete reference/sample scan validation | Pending |
| Measurement repeatability study | Pending |
| Biomedical or clinical validation | Not established |

This status table distinguishes demonstrated prototype functions from work that remains to be validated.

## 🔭 Future Improvements

Potential next steps include:

- **Optical alignment:** Build a rigid optical mount and reduce ambient-light interference.
- **Component verification:** Confirm that the optical films are genuine linear polarizers and characterize the optical path.
- **Calibration:** Establish the servo's physical range, optical zero, and repeatable angular positions.
- **Improved detection:** Evaluate a photodiode with an appropriate amplifier for more controlled quantitative measurements.
- **Live visualization:** Display incoming sensor measurements in real time and distinguish sensor tests from angular scans.
- **Repeatability analysis:** Record repeated reference and sample measurements and calculate variability.
- **Data export:** Add reliable measurement metadata, graph export, and reproducible analysis workflows.
- **Experimental validation:** Test known reference materials before drawing conclusions about sample properties.
- **Future research:** Investigate whether a carefully validated optical method could support a specific biomedical research application.

## 🏆 Recognition

Mediverse received special recognition for innovation at an IEEE EMBS event hosted by BMSIT&M.

This recognition represents an important milestone in developing the prototype, presenting the idea, and exploring the integration of optics, electronics, embedded systems, and software.

The project is an ongoing engineering effort, and further work will focus on improving the optical setup, validating measurements, and strengthening experimental repeatability.

## 🤝 Contributing

Suggestions, issue reports, and technical discussions are welcome.

If you would like to contribute:

1. Fork the repository.
2. Create a feature branch.
3. Make a focused change.
4. Test the firmware or software affected by your change.
5. Submit a pull request describing the change and its testing.

Please include relevant hardware details, wiring changes, software versions, and reproducible steps when reporting issues.

## ⚠️ Disclaimer

Mediverse is an educational and experimental prototype. It is **not a medical device**, does not diagnose fibrosis or any other disease, and must not be used to make clinical decisions.

Any future biomedical application would require appropriate technical verification, analytical validation, and clinical evaluation before it could support medical claims.

## 📄 License

No license has been specified yet. Until a license is added to the repository, others should not assume they have permission to redistribute or reuse the project's code.

If you intend to release the software as open source, consider adding an appropriate license file and documenting any third-party libraries or hardware designs used.
