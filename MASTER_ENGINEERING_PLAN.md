# Mediverse Hands-on Workshop — Master Engineering Plan

**Basis:** *Mediverse Hands-on Workshop Participant Guide, IEEE EMBS BMSIT* (uploaded by the participant).  
**Purpose:** Build a reliable educational optical measurement prototype, capture real reference/sample measurements, compare the response, and demonstrate sound engineering.  
**Important:** This is not a validated fibrosis detector or medical diagnostic device.


## 0. Update based on the participant's actual component photos

These are visual identifications, not a substitute for reading labels or checking pins in person:

- **ESP32 board:** appears to be a classic ESP32-WROOM-32-style DevKit with micro-USB and EN/BOOT buttons. The visible header labels appear consistent with the classic board, but confirm the module marking and each pin label before wiring. The tentative mapping below uses GPIO34 (ADC input), GPIO18 (servo signal), and GPIO25 (LED output).
- **Servo:** the case label appears to say **TowerPro MG90S**, whereas the participant guide lists SG90. Treat the physical servo's label as the relevant clue; verify the exact variant and its rated supply. TowerPro's own MG90S page lists 4.8 V operating voltage and says it is powered through an external adapter. Do not power it from ESP32 3V3 or a GPIO.
- **LED:** the photographed red LED appears to have **two leads**, which would be a conventional single-colour LED, not a common-anode multi-lead RGB LED. The guide says “common-anode,” so this discrepancy must be resolved by physically counting the leads and asking the organiser if there is any doubt. For a confirmed two-lead LED, use GPIO25 → 220 Ω resistor → LED anode (usually longer lead); LED cathode (usually shorter lead/flat side) → GND. This is active-HIGH. Only use the common-anode wiring/code option if the actual part has a verified shared anode and separate cathodes.
- **Resistors:** two resistors are visible, matching the guide's 220 Ω and 10 kΩ quantities, but the photo is too blurred to verify the colour bands. Use packaging markings, a multimeter in resistance mode, or organiser confirmation; do not infer the values from the pictures.
- **LDR and breadboard:** a typical two-lead LDR and mini breadboard are visible. Use the supplied 10 kΩ resistor to make the divider, after confirming its value.
- **Optical films/sample:** the tinted translucent sheets may be the polarizing films, but a photo alone cannot prove this. The white textured sheet is not visually identifiable as a polarizer. Test suspected films against an LCD display or overlay two suspected films and rotate one: the brightness should change strongly with relative orientation. Ask the organiser which item is the investigation sample. Do not assume the white textured sheet is the sample without confirmation. Handle films by the edges.
- **Power:** the photos show a micro-USB cable for the ESP32 but no clearly identifiable separate servo supply. Confirm with the organiser whether an appropriate regulated supply is provided before attempting to drive the servo.

**Immediate safety rule:** build the low-voltage sensor and LED sections only after verifying the resistor values and LED polarity; keep the servo disconnected until its supply and ground arrangement are approved. Have the organiser inspect the complete circuit before powering it.

---

## 1. What the project is

The guide describes a simplified experiment inspired by FIBROS (*Fibrotic Identification Based Response using Optical Spectroscopic Polarimetry*). The research motivation is that biological tissue changes associated with fibrosis may affect the way polarized light travels through tissue. The guide describes the research setup as using normal and fibrotic rabbit heart tissue, an 850 nm source, two linear polarizers, motorized rotation, and a photodetector. The guide lists a visible 5 mm common-anode LED and SG90 servo; the participant's photos instead appear to show a two-lead red LED and a TowerPro MG90S servo. Resolve those discrepancies physically before final wiring.

The workshop apparatus uses this path:

```text
LED → fixed polarizer P1 → investigation sample (or empty/reference path)
    → rotating polarizer P2 → LDR voltage divider → ESP32 ADC → serial data
```

The ESP32 commands the second polarizer through the angle sequence 0°, 10°, 20° ... 180°. That is **19 measurement positions per scan**. Participants first measure a reference path without the sample, then insert the sample without disturbing the rest of the apparatus and repeat the scan. The final graph should plot both series against the same angle axis.

### Optical principle

For an ideal linear polarizer pair with no sample affecting polarization, Malus's law predicts:

\[
I(\theta)=I_{\max}\cos^2(\theta-\theta_0)
\]

where \(\theta-\theta_0\) is the relative angle between the pass axes. If the axes are parallel at the chosen zero, maximum transmission is expected near 0° and 180°, with a minimum near 90°. A real setup may show a nonzero minimum because of stray light, imperfect polarizers, depolarized light, sensor offset, scattering, and misalignment. The LDR is not a calibrated photodetector; its ADC counts are an electrical proxy for the light reaching it.

The sample can reduce transmitted light, scatter light, or change polarization if it has suitable optical properties. A sample-dependent curve difference is an observation that deserves investigation, not evidence by itself of fibrosis.

## 2. Official requirements versus recommendations

### Explicit requirements in the participant guide

- Build the complete experimental setup using the specified optical order.
- Use the ESP32 to control rotating P2 and obtain the corresponding LDR readings.
- Measure from 0° through 180° in 10° increments.
- Record a reference scan with no sample and a sample scan with the sample inserted.
- Keep the other component positions as consistent as possible between scans.
- Record the angle and sensor reading for each measurement.
- Plot reference and sample on the same graph.
- Compare intensity variation, peaks/minima, and differences using the recorded data.
- Explain the setup and approach, and discuss limitations such as alignment and ambient light.
- Follow the guide’s electrical safety instructions. The organiser should check the complete setup before powering it or beginning data collection.
- The guide explicitly says simplicity, number of electrical connections, symmetry/logical arrangement, and construction quality form part of evaluation.

### Supplied components listed in the guide

ESP32 development board; SG90 180° micro servo; 5 mm common-anode LED; LDR; 220 Ω resistor; 10 kΩ resistor; linear polarizing film; mini breadboard; jumper wires; micro-USB cable; sample for investigation.

### Not specified in the guide

Exact ESP32 model/pinout; precise LED package/pinout; exact sample identity and optical properties; servo pulse endpoints; exact dimensions of the apparatus; a complete circuit diagram; numerical scoring rubric; workshop duration; any commercial/business-pitch requirement. These must not be invented.

## 3. Design options

| Option | Implementation | Added cost (rough) | Risk | Value | Recommendation |
|---|---|---:|---|---|---|
| A — minimum | Cardboard/foam-board frame, supplied components, hand-recorded measurements, spreadsheet graph | ₹0–₹150 if scrap material is available; excludes any supply the team must buy | Medium: manual transcription and weaker alignment | Meets requirements if built carefully | Good emergency fallback |
| B — improved engineering | Rigid frame, black optical shroud, careful servo calibration, repeated ADC samples/median, serial CSV logging, spreadsheet/Python graph | Roughly ₹150–₹500 additional, depending on supply and materials needed | Low–medium after calibration | Strong reliability and data quality without changing the required sensor | **Recommended** |
| C — display-heavy | Option B plus OLED display, custom enclosure/3D printing, possible extra sensor | Often ₹500–₹1,500+ additional, depending on parts and fabrication | More integration points, more time | Looks polished, but does not automatically improve the experiment | Only after B passes every acceptance test |

The costs are planning estimates rather than verified quotations; locally available material, a lab power supply, and reuse of scrap may reduce cost considerably. Do not buy optional electronics before checking what the organisers provide.

## 4. Recommended architecture

Use Option B. Do not replace the supplied LDR or polarizers for the core demonstration. Improve mechanical alignment, stray-light control, repeatability, and data handling.

```text
                  ┌───────────────────────────────┐
USB from laptop ──┤ ESP32                         │
                  │  GPIO18 ───────── Servo signal│
                  │  GPIO34 ADC ←──── LDR divider │
                  │  GPIO25 ──────── LED control  │
                  └───────────────────────────────┘
                         common ground to servo supply

Separate regulated servo supply (rating confirmed for the photographed MG90S)
    +Vservo ───────────────────── servo V+ (typically red; verify)
    GND     ────────────┬──────── servo GND (typically brown/black; verify)
                        └──────── ESP32 GND

Optics: LED → P1 → sample slot → rotating P2 → LDR
Data: ESP32 serial rows → laptop CSV logger → raw graph + supplemental normalized graph
```

The GPIO mapping above is a **conditional starting point for a classic ESP32 DevKit/ESP32-WROOM-32**, not a universal ESP32 pinout. GPIO34 is an ADC1 input on the classic ESP32 and is input-only. ESP32-C3/S3/C6 boards have different pin arrangements; identify the board before wiring.

## 5. Mechanical construction and alignment

### Frame

Build a straight, rigid optical channel from black foam board, thick cardboard, or a reused enclosure. A U-shaped base with two side walls is easy to adjust and inspect. Use movable brackets during alignment; lock them only after the beam passes through every element.

1. Mount the LED at one end, facing down the optical axis.
2. Mount P1 perpendicular to the beam. Mark its frame so it cannot rotate accidentally.
3. Add a sample slot that allows insertion/removal without shifting P1 or the LED.
4. Mount P2 in a lightweight carrier driven by the photographed MG90S (after confirming its safe travel).
5. Put the LDR at the far end and shield it from room light with a black tube or small dark chamber.
6. Avoid shiny interior surfaces. A small aperture can block stray light, but do not make it so small that the useful LED beam is mostly blocked.
7. Secure wires away from the servo linkage and rotating carrier.

### Avoiding the servo blocking the optical path

A servo body mounted directly behind the centre of a polarizer can obstruct the light. A practical low-cost workaround is to mount the servo with its shaft axis **parallel to the optical beam but offset to one side**. Attach the polarizing film in a light carrier whose usable area is large enough that the beam remains covered at every rotation angle. Because the linear polarizer is uniform, the beam does not have to pass through the centre of the disc; it must pass through the film, not the servo housing or carrier. Confirm the clear aperture at the full sweep before fixing the frame. If this arrangement cannot provide adequate clearance, use a small ring/belt drive to rotate the film while locating the servo body outside the beam.

Do not cut, bend, scratch, or touch the supplied film unnecessarily. Hold it by its edges. Avoid heavy holders that make the MG90S/servo strain or wobble. A circular frame is helpful; with a square frame, keep the beam within the area guaranteed to remain covered through rotation.

### Define the angular zero

1. Identify the film’s pass-axis orientation empirically if it is not marked. With the sample removed, rotate P2 by hand and find the highest transmitted-light reading; that corresponds approximately to parallel axes.
2. Set the servo at its intended safe scan-start position after pulse calibration.
3. Set the film carrier on the horn so P2 is parallel to P1 at logical 0°.
4. Verify a full mechanical sweep in 10° steps and confirm that the beam remains inside the clear area throughout.
5. Do not equate `servo.write(90)` with a verified physical 90° polarizer orientation. The hobby servo has no independent angle readback. Verify with a paper protractor/marks or a known reference fixture.
6. Run the reference scan. A reasonably aligned ideal-like response should show maxima near 0°/180° and a minimum near 90°, although real equipment will deviate.

The guide does not specify dimensions. Determine length, sensor distance, aperture size, and carrier diameter using the actual LED beam, film dimensions, and LDR opening rather than assuming measurements from another build.

## 6. Electrical circuit

### Conditional GPIO table — classic ESP32 DevKit / WROOM-32 only

| Component | Terminal | Connection | Purpose / precaution |
|---|---|---|---|
| ESP32 | 3V3 | LDR divider top; LED connection depends on verified LED type | For a standard two-lead LED, do not connect its anode to 3V3 in the GPIO-controlled circuit described below. Confirm board pin labels. |
| ESP32 | GND | Bottom of LDR divider; shared ground reference | Common reference for ADC and LED. |
| ESP32 | GPIO34 | Junction of LDR and 10 kΩ resistor | ADC1 input on classic ESP32; input-only pin. Do not assume this pin exists on other ESP32 variants. |
| LDR | One lead | ESP32 3V3 | Divider top; orientation of LDR itself is not polarised. |
| LDR | Other lead | GPIO34 ADC node | Light-dependent resistance changes the divider voltage. |
| 10 kΩ | One lead | GPIO34 ADC node | Forms divider. |
| 10 kΩ | Other lead | GND | Keeps ADC node defined. |
| LED — if verified as a conventional 2-lead red LED (as photo appears to show) | Anode, usually longer lead | GPIO25 through 220 Ω resistor | Active-HIGH. Confirm polarity physically; cathode goes to GND. |
| LED — only if verified as common-anode multi-lead part | Common anode | ESP32 3V3 | Do not use this row for a two-lead LED. Confirm the actual pinout with the organiser. |
| Selected common-anode LED cathode | Through 220 Ω resistor | GPIO25 | Active-LOW; one colour channel only. Use only if package is verified common-anode. |
| MG90S/servo | Signal (often orange/yellow) | GPIO18 | Servo control signal; verify cable colours and board pinout. |
| MG90S/servo | V+ (often red) | Separate regulated supply matching the actual servo rating | Do not power from a GPIO or ESP32 3V3. TowerPro's MG90S page lists 4.8 V operating voltage and says external adapter; verify exact supplied variant. |
| MG90S/servo | GND (often brown/black) | Servo supply GND, joined to ESP32 GND | Common signal reference. Keep servo current out of thin sensor ground paths where possible. |

### LDR divider derivation

Use this topology:

```text
3V3 ── LDR ──┬── GPIO34 (ADC node; classic ESP32 only)
             |
            10 kΩ
             |
            GND
```

The node voltage is approximately:

\[
V_{ADC}=V_{CC}\frac{R_{fixed}}{R_{LDR}+R_{fixed}}
\]

Here, \(R_{fixed}=10\,k\Omega\). As the LDR becomes brighter, its resistance typically falls, so the node voltage and ADC reading rise. Actual resistance depends on the particular LDR and spectrum; no calibrated lux conversion should be claimed.

### LED checks — important discrepancy between guide and photograph

The guide calls the LED “common-anode,” but the photograph appears to show an ordinary two-lead red LED. Count its leads before wiring. A conventional two-lead LED is wired GPIO25 → 220 Ω resistor → anode (usually longer leg); cathode (usually shorter leg/flat side) → GND. It is active-HIGH. A verified common-anode multi-lead package is instead wired with its common anode to 3V3 and one selected cathode through the 220 Ω resistor to GPIO25; that is active-LOW. Do not combine these arrangements. If the number of leads or pinout is uncertain, ask the organiser before connecting power. The firmware exposes `LED_IS_COMMON_ANODE` to select the matching behaviour after the component is verified.

### Servo power

Use the ESP32 USB for the ESP32 and a separately regulated supply appropriate for the supplied servo. Join grounds. Do not feed the servo’s power rail into ESP32 3V3. A servo can draw transient current when starting or under load and cause resets/noisy ADC readings if powered poorly. A capacitor across the servo supply near the servo can be an optional improvement only after the organiser approves the wiring; it does not replace a suitable supply.

### Before power-on

- Photograph/read the ESP32 model and pin labels.
- Count LED leads and confirm its type: conventional 2-lead red LED or common-anode multi-lead device; verify polarity/pinout.
- Check 220 Ω is in series with the LED channel.
- Check 10 kΩ divider and verify ADC node is not connected to 5 V.
- Confirm the photographed servo's exact model (appears MG90S) and rated voltage/pin order.
- Ensure no short between 3V3 and GND or between servo V+ and GND.
- Join ESP32 and servo-supply ground; do not connect different positive rails together by accident.
- Keep the polarizer and servo mechanical carrier clear of loose wires.
- Have the organising team inspect the circuit before the complete setup is powered.

## 7. Firmware and tools

The project folder includes `mediverse_firmware.ino`. It uses the Arduino framework and `ESP32Servo` library. The exact board and pin mapping must be confirmed first.

### Commands

- `H` — help
- `T` — sensor sanity test with LED on
- `L` / `X` — LED on / off
- `J0` through `J180` — manual logical position test using currently configured pulse bounds
- `P1500` — example manual servo pulse test (use only with carrier/load removed and test cautiously)
- `R` — reference scan
- `S` — sample scan

By default, scans are **blocked** until the source code constants `SERVO_RANGE_VERIFIED` and `OPTICAL_ZERO_VERIFIED` are both changed to `true`. This is intentional: first find the safe pulse endpoints on the unloaded servo and verify the polarizer zero. Update `SCAN_MIN_PULSE_US`/`SCAN_MAX_PULSE_US` to the tested endpoints. If the actual servo cannot safely cover the required 180° sweep, stop and consult the organiser; do not force the gear train.

Each scan prints one row per 10° position using:

```text
scan_id,measurement_type,angle_deg,adc_median,adc_min,adc_max,n,status
```

It takes 15 readings at each position and reports their median, minimum, maximum, and sample count. The median reduces the influence of isolated ADC spikes; the min/max range still exposes instability. It flags near-zero/full-scale saturation rather than quietly substituting values. `OK` rows may be analysed; flagged rows need correction/re-measurement.

### Setup

1. Install Arduino IDE and the matching ESP32 board package.
2. In Library Manager, install `ESP32Servo`.
3. Open `mediverse_firmware.ino`.
4. Check the board model and change GPIO constants to match the actual board.
5. Compile/upload with only the low-risk parts connected initially, as directed by the organiser.
6. Verify sensor response and servo centre movement.
7. Calibrate servo range and optical zero with the load removed, then reassemble the lightweight carrier.
8. After organiser approval, set both verification flags to `true`, set calibrated pulse endpoints, upload again, and run a test scan.

Do not treat a compile success as evidence that the physical wiring or measurement is correct.

## 8. Data collection workflow

Recommended primary flow: ESP32 serial CSV → laptop logger → Python graphs. Spreadsheet-only entry is the fallback if Python installation or serial logging is impractical.

Files included:

- `serial_logger.py`: captures scan rows into a CSV and lets the operator send `r`, `s`, `t`, `h`, `l`, or `x` commands without needing Arduino Serial Monitor open.
- `analyze_measurements.py`: validates the CSV, excludes flagged rows from plots while reporting them, checks all expected angles, creates the mandatory raw comparison graph and a supplementary independently-normalized shape graph, and writes an aggregated CSV and summary report.
- `measurement_template.csv`: blank CSV header template.

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the serial logger (replace `COM5` with the actual port):

```bash
python serial_logger.py --port COM5 --out mediverse_measurements.csv
```

Or Linux example:

```bash
python serial_logger.py --port /dev/ttyUSB0 --out mediverse_measurements.csv
```

With the circuit and range verified, enter `r` and save 19 reference rows. Insert the sample without moving any other component, then enter `s` and save 19 sample rows. If possible, repeat each scan two or three times without changing the setup. The analysis script aggregates repeat scans by angle and can display standard-deviation error bars.

Run analysis:

```bash
python analyze_measurements.py mediverse_measurements.csv --out results
```

Outputs include:

- `comparison_raw_adc.png` — mandatory comparison using the raw ADC response from both conditions.
- `comparison_normalized_shape.png` — supplementary shape comparison; each condition is scaled to its own maximum, so it deliberately removes absolute level differences.
- `aggregated_by_angle.csv` — aggregated values for spreadsheet use.
- `summary.txt` — min, max, peak-to-peak range, completeness and interpretation cautions.

### Scientific interpretation

Start from raw values and the mandatory graph. Note the angles of high and low readings and compare the curves. If repeated scans are available, check whether the difference is larger than ordinary scan-to-scan variability. If the sample curve is lower by a similar factor at all angles, it may simply attenuate light; that is not the same as proving it changed polarization. If the curves differ in shape, it could reflect polarization-dependent interaction, but it could also reflect sample movement, changing alignment, drift, or stray light.

Use normalization only as a secondary view. Independently normalizing both traces hides absolute attenuation differences. A sample/reference ratio may be unstable wherever reference intensity is near zero; avoid interpreting such ratios around minima. Do not convert counts to lux or claim tissue classification without calibration, appropriate samples, and validation.

## 9. Costs in India

The organiser-provided components should not be repurchased. The physical photo appears to show an MG90S servo although the guide lists SG90; do not buy a replacement unless the supplied servo is faulty or the organisers ask you to. Any optional-item price estimate is a planning value, not a quotation; actual price, stock, shipping and authenticity vary.

| Item | Needed? | Planning estimate | Priority |
|---|---|---:|---|
| Black cardboard/foam board, paper, tape, clips | Yes, unless scrap material is available | ₹0–₹150 | P0 |
| Small rigid brackets/fasteners | Helpful | ₹30–₹100 | P1 |
| Suitable regulated servo supply, only if organisers cannot provide one | Possibly necessary; verify exact servo rating first | ₹200–₹500 rough estimate | P0 if no suitable lab supply exists |
| Small decoupling capacitor for servo supply | Optional; get organiser approval | ₹5–₹30 rough estimate | P2 |
| OLED display | Not needed for the experiment; consumes time | ~₹150–₹300 rough estimate | P3 / skip |
| External ADC or alternative light sensor | Not needed for the required build; changes the hardware baseline | Variable | Skip unless measurement tests prove a need and organisers approve |

### Budget scenarios (additional spend, not including supplied components)

- **Lean:** ₹0–₹150, if the team has scrap frame material and the organiser provides an appropriate servo supply.
- **Recommended:** roughly ₹250–₹650 if a supply and a few mechanical materials must be purchased. This is a planning range, not a verified quote.
- **Optional/high-cost:** roughly ₹600–₹1,500+ if adding a display, premium enclosure or custom fabrication. I would not spend this before the core experiment passes.

Free software is sufficient: Arduino IDE, Python, `pyserial`, `matplotlib`, and Excel/Google Sheets if already available.

## 10. Competitive strategy

The guide’s stated evaluation clues are build simplicity, low connection count, symmetry/logical layout, and overall construction quality. The following are engineering recommendations, not guaranteed scoring items.

| Rank | Differentiator | Impact | Effort | Added cost | Priority |
|---:|---|---|---|---:|---|
| 1 | Stable optical alignment + dark shielding | High: lowers obvious measurement artefacts | Medium | Low | Must do |
| 2 | Verified servo angle mapping and repeatable sample slot | High: measurement comparison depends on unchanged geometry | Medium | Low | Must do |
| 3 | Automated scan with robust sensor aggregation and saturation flags | High: reduces manual errors | Medium | ₹0 software | Must do |
| 4 | CSV logging + clearly labelled raw comparison plot | High: makes results traceable and easy to explain | Low–medium | ₹0 software | Must do |
| 5 | Repeated scans and honest uncertainty/limitations | High scientific credibility | Low–medium | None | Strongly recommended |
| 6 | OLED, 3D printed shell, or decorative features | Low unless they solve a tested problem | Medium–high | Medium | Skip until core is done |

The best differentiator is not a claim that the device diagnoses fibrosis. It is a careful demonstration that shows the measurement method, real data, repeatability checks, and limits.

## 11. Risks and troubleshooting

| Symptom | Likely cause | Safe test | Corrective action |
|---|---|---|---|
| ESP32 resets when servo moves | Servo current transient or poor supply/ground | Test servo separately with approved supply; observe whether reset correlates with motion | Use suitable separate regulated servo supply and common ground; keep motor current paths away from sensor ground |
| Servo jitters or buzzes at endpoint | Pulse range exceeds safe travel, mechanical bind, power issue | Remove carrier/load; step pulse cautiously | Stop, reduce pulse range, align mechanism; never force endpoints |
| Servo moves but polarizer angle is wrong | Horn/carrier not calibrated to optical zero | Check alignment with no sample and manual marks/protractor | Refit carrier at correct zero; verify full travel |
| LED is off | Wrong pin, wrong anode/cathode identification, missing resistor, LED logic mode mismatched to actual package | Power off; count leads and inspect polarity/pinout | Select standard active-HIGH mode only for confirmed 2-lead LED; select active-LOW mode only for verified common-anode package |
| LDR reading constant | Wrong divider, ADC wrong pin, LED not illuminating, sensor saturated | Compare dark/illuminated ADC readings; inspect divider node | Correct topology and selected board pin; shield ambient light and avoid saturation |
| ADC reading fluctuates | Ambient light, moving optics, LED variation, servo supply noise, loose wire | Hold position, darken enclosure, observe min/max | Fix mounts, shield sensor, stabilise power, keep LED steady, rerun scan |
| Reading stuck near 0 or 4095 | Circuit short/open or ADC saturation | Check node voltage and wiring after powering down | Inspect wiring and divider; label saturated data invalid and recollect |
| Reference curve is not roughly max–min–max | Incorrect zero, polarizer axis not aligned, leak light, path misalignment | Remove sample; manually rotate second polarizer slowly | Calibrate zero; improve shielding/alignment; do not force data to fit a curve |
| Sample result shifts after insertion | Sample slot moves P1/P2, tilt or variable position | Repeat reference after reinserting/removing an inert placeholder | Improve slot guides and insertion stops; keep other parts fixed |
| CSV missing rows | Serial port issue, premature closing, logger not connected during scan | Count rows per scan ID; rerun affected scan | Use the logger program alone for serial access; repeat scan and check all 19 angles |
| Results look “perfect” but are unreliable | Overprocessing, fabricated/simulated data, or uncontrolled conditions | Preserve raw CSV and repeat an independent scan | Show raw data, disclose processing, record limitations; never fabricate observations |

## 12. Build sequence and acceptance gates

Time estimates below are rough active-work planning ranges, not the workshop’s stated duration.

| Phase | Rough effort | Deliverable | Acceptance gate |
|---|---:|---|---|
| Inspect components and confirm board/LED/servo/sample details | 15–30 min | Photos/notes of exact parts and pin labels | No unresolved pinout or supply assumptions before wiring |
| Build adjustable optical frame and sample slot | 45–90 min | Beam passes through all elements; servo body does not block it | All parts remain aligned across full sweep |
| Wire sensor + LED; organise servo supply | 20–45 min | Organiser-checked circuit | No shorts, correct voltage rails, common ground |
| Test LDR, LED and servo independently | 20–40 min | Sensor responds; servo moves without strain | Sensor reading changes with light; servo has no buzzing at endpoints |
| Calibrate servo pulse endpoints and optical zero | 20–45 min | Safe 0°–180° scan mapping | Beam stays through P2; angular zero is defined; no binding |
| Implement/run firmware and serial logger | 30–60 min | CSV with all 19 rows per scan | Correct type, angle, median, range, status fields |
| Collect reference/sample data; repeat if possible | 20–60+ min | Complete datasets | 19 valid or explicitly flagged values per run; repeatability assessed if time allows |
| Plot, interpret, prepare demo | 20–45 min | Graphs + concise explanation | Claims are supported by real data and limitations acknowledged |

### Critical path

Board/pin confirmation → organiser-reviewed circuit → sensor/servo tests → safe servo-range calibration → optical zero/alignment → reference scan → sample scan → graph and interpretation. Extra display or enclosure work must not delay this path.

## 13. Acceptance checklist before presenting

- [ ] The exact ESP32 board/pinout has been confirmed.
- [ ] LED type/pinout is verified; correct active-HIGH or common-anode active-LOW wiring is selected; current-limiting resistor is installed.
- [ ] LDR is in a divider and ADC node is within the board’s safe input range.
- [ ] Servo power supply meets the exact servo rating, and servo is not powered from a GPIO.
- [ ] Organiser checked the circuit before full power-on.
- [ ] LED, LDR, and servo tested separately.
- [ ] The rotating film covers the beam through the full sweep; servo housing does not obstruct light.
- [ ] Logical zero and safe travel endpoints were physically verified.
- [ ] Reference scan contains 19 readings, angles 0°..180° step 10°.
- [ ] Sample scan contains 19 readings under the same geometry.
- [ ] Any saturation/invalid rows were resolved or transparently disclosed.
- [ ] Raw CSV was saved; no simulated values are presented as experimental results.
- [ ] Required raw comparison graph is labelled and clear.
- [ ] Interpretation includes what was observed, likely explanations, and limitations.

## 14. Questions for the organisers

1. What exact ESP32 board/variant and pinout is supplied?
2. The photographed LED appears to be two-lead red, but the guide says common-anode. Which exact LED was issued, and what is its verified pinout?
3. What is the sample material, and is it supplied in a fixed shape/thickness?
4. Is a suitable regulated supply or bench power supply available for the photographed MG90S/servo, or must teams bring one?
5. Are external frame materials such as foam board, cardboard, clips, tape, or 3D-printed parts allowed?
6. Is a laptop allowed for serial logging and graphing during the workshop?
7. Is there a published scoring rubric beyond the build-quality considerations in the guide?
8. What is the actual build/measurement time available?
9. Should the required angle range be measured relative to the parallel-polarizer maximum, or will the organisers define a specific angular zero?
10. Is the organiser expected to approve the completed circuit before every team starts data collection?

## Final recommendation

Build a compact, black-shielded optical frame with the supplied LED, two polarizing films, servo-driven P2, LDR divider and ESP32. Use a laptop for serial CSV logging and Python or a spreadsheet for the graph. Spend effort on the angular zero, safe servo travel, repeatable sample positioning and real measurements. Avoid an OLED, new sensor, medical classifier, startup pitch, or elaborate dashboard unless the basic apparatus works reliably and the organisers explicitly value those additions.
