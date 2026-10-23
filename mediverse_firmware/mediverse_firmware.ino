/*
  MEDIVERSE / FIBROS workshop measurement firmware

  Intended baseline board: the photos appear to show a classic ESP32-WROOM-32 DevKit.
  Confirm the board marking and header labels before wiring. This pinout does NOT
  automatically fit ESP32-C3/S3/C6 or another board.

  Photo-based component observations (not manufacturer verification):
    - Servo label appears to read TowerPro MG90S, although the guide lists SG90.
    - Visible red LED appears to have two leads. If it is a normal 2-lead LED,
      wire GPIO25 -> 220 ohm resistor -> LED anode; LED cathode -> GND.
    - The guide instead says common-anode LED. Inspect/count the leads and ask the
      organiser if uncertain. Do not use both wiring schemes at once.

  Default pin assumptions (verify against your exact board):
    LDR divider midpoint -> GPIO34 (ADC1 input; classic ESP32 only)
    Servo signal         -> GPIO18
    LED control           -> GPIO25 (logic is configurable below)

  IMPORTANT COMMISSIONING SAFETY:
  - The scan is intentionally disabled by default until servo travel and optical zero
    have been checked on the physical apparatus and the constants below are updated.
  - Initially, servo scan pulse bounds are conservative (1000..2000 us). They may not
    represent 180 degrees of actual travel. Do not claim that commanded angles equal
    measured physical angles; the hobby servo provides no independent angle feedback.
  - To calibrate, remove the polarizer carrier/load, start at 1500 us, and use Pxxxx
    commands in small increments. Stop immediately if it buzzes at an endpoint, strains,
    hits a hard stop, or the mounting flexes. Increase the calibration range cautiously.
  - The photographed servo appears to be an MG90S, not the guide's SG90. Verify its
    exact rated supply. TowerPro's MG90S page lists 4.8 V operating voltage and an
    external adapter. Do not power it from an ESP32 GPIO or 3V3 pin.
  - Have the organiser inspect the circuit before connecting power.

  CSV rows sent to Serial:
  scan_id,measurement_type,angle_deg,adc_median,adc_min,adc_max,n,status
*/

#include <Arduino.h>
#include <ESP32Servo.h>
#include "ReadingStats.h"
// ---------- EDIT AFTER CHECKING THE EXACT BOARD ----------
constexpr int LDR_PIN   = 34;  // ADC1 on classic ESP32 DevKit/WROOM-32 only
constexpr int SERVO_PIN = 18;  // choose an available output-capable GPIO on your board
constexpr int LED_PIN   = 25;
// The photo appears to show a conventional 2-lead red LED, so default is false.
// Set true ONLY if the actual component is confirmed to be a common-anode multi-lead LED.
// Normal 2-lead LED wiring: GPIO25 -> 220 ohm resistor -> long-leg/anode;
// short-leg/cathode -> GND. Common-anode wiring is described below.
constexpr bool LED_IS_COMMON_ANODE = false;

// ---------- SERVO CALIBRATION ----------
// The scan's logical 0..180 degrees map to these measured safe pulse endpoints.
// Start conservative; calibrate the real unit before setting the verification flags.
constexpr int SCAN_MIN_PULSE_US = 1000;
constexpr int SCAN_MAX_PULSE_US = 2000;

// Servo library's permitted pulse range. These are not the scan endpoints.
constexpr int SERVO_ATTACH_MIN_US = 500;
constexpr int SERVO_ATTACH_MAX_US = 2400;

// Manual pulse-command limits used during unloaded calibration. Widen only after
// careful testing and organiser approval if this range is insufficient.
constexpr int CAL_TEST_MIN_US = 900;
constexpr int CAL_TEST_MAX_US = 2100;

// Change BOTH to true only after verifying the actual physical travel and 0-degree
// optical alignment. The code will refuse scans while either remains false.
constexpr bool SERVO_RANGE_VERIFIED = false;
constexpr bool OPTICAL_ZERO_VERIFIED = false;

// ---------- MEASUREMENT SETTINGS ----------
constexpr unsigned long SETTLE_MS = 300;  // validate experimentally for servo + LDR
constexpr int NUM_SAMPLES = 15;           // odd number so median is well defined
constexpr unsigned long SAMPLE_SPACING_MS = 8;
constexpr int SATURATION_LOW = 5;
constexpr int SATURATION_HIGH = 4090;
constexpr int ADC_BITS = 12;

Servo polarizerServo;
uint32_t nextScanId = 1;
bool ledOn = false;

void setLED(bool on) {
  ledOn = on;
  if (LED_IS_COMMON_ANODE) {
    // Only for verified common-anode package: common anode -> 3V3; chosen cathode
    // -> 220 ohm resistor -> GPIO25. LOW sinks current and turns that channel ON.
    digitalWrite(LED_PIN, on ? LOW : HIGH);
  } else {
    // For a verified conventional 2-lead LED: GPIO25 -> 220 ohm resistor -> anode;
    // cathode -> GND. HIGH sources current and turns the LED ON.
    digitalWrite(LED_PIN, on ? HIGH : LOW);
  }
}

int pulseForAngle(int angle) {
  angle = constrain(angle, 0, 180);
  return (int)map(angle, 0, 180, SCAN_MIN_PULSE_US, SCAN_MAX_PULSE_US);
}

void moveLogicalAngle(int angle) {
  polarizerServo.writeMicroseconds(pulseForAngle(angle));
}

int medianOf(int *values, int n) {
  // insertion sort; n is small (15), so this is simple and deterministic
  for (int i = 1; i < n; i++) {
    int key = values[i];
    int j = i - 1;
    while (j >= 0 && values[j] > key) {
      values[j + 1] = values[j];
      j--;
    }
    values[j + 1] = key;
  }
  return values[n / 2];
}

ReadingStats readSensorStats() {
  int samples[NUM_SAMPLES];
  (void)analogRead(LDR_PIN);  // discard a settling conversion
  delay(5);
  (void)analogRead(LDR_PIN);

  int minimum = 4095;
  int maximum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    int value = analogRead(LDR_PIN);
    samples[i] = value;
    if (value < minimum) minimum = value;
    if (value > maximum) maximum = value;
    delay(SAMPLE_SPACING_MS);
  }

  int sorted[NUM_SAMPLES];
  for (int i = 0; i < NUM_SAMPLES; i++) sorted[i] = samples[i];
  int med = medianOf(sorted, NUM_SAMPLES);

  const char *status = "OK";
  if (med <= SATURATION_LOW) status = "SAT_LOW";
  else if (med >= SATURATION_HIGH) status = "SAT_HIGH";

  ReadingStats result = {med, minimum, maximum, NUM_SAMPLES, status};
  return result;
}

void printCSVRow(uint32_t scanId, const char *type, int angle, ReadingStats s) {
  Serial.print(scanId); Serial.print(',');
  Serial.print(type); Serial.print(',');
  Serial.print(angle); Serial.print(',');
  Serial.print(s.median); Serial.print(',');
  Serial.print(s.minimum); Serial.print(',');
  Serial.print(s.maximum); Serial.print(',');
  Serial.print(s.n); Serial.print(',');
  Serial.println(s.status);
}

void sensorTest() {
  setLED(true);
  delay(SETTLE_MS);
  ReadingStats s = readSensorStats();
  Serial.print("# SENSOR_TEST median="); Serial.print(s.median);
  Serial.print(" min="); Serial.print(s.minimum);
  Serial.print(" max="); Serial.print(s.maximum);
  Serial.print(" n="); Serial.print(s.n);
  Serial.print(" status="); Serial.println(s.status);
  Serial.println("# Compare readings with the optical path dark, then illuminated; values must respond.");
}

void runScan(const char *measurementType) {
  if (!SERVO_RANGE_VERIFIED || !OPTICAL_ZERO_VERIFIED) {
    Serial.println("# SCAN BLOCKED: calibrate safe pulse endpoints and optical zero first.");
    Serial.println("# Verify servo travel unloaded, avoid endpoint buzz/stall, then edit the two verification flags.");
    Serial.println("# Set SCAN_MIN_PULSE_US and SCAN_MAX_PULSE_US to tested safe endpoints for the intended sweep.");
    return;
  }
  if (SCAN_MIN_PULSE_US >= SCAN_MAX_PULSE_US) {
    Serial.println("# ERROR: SCAN_MIN_PULSE_US must be lower than SCAN_MAX_PULSE_US.");
    return;
  }

  const uint32_t scanId = nextScanId++;
  Serial.print("# BEGIN scan_id="); Serial.print(scanId);
  Serial.print(" type="); Serial.println(measurementType);
  Serial.println("# Keep the apparatus fixed; do not touch the polarizing films during a scan.");

  setLED(true);
  for (int angle = 0; angle <= 180; angle += 10) {
    moveLogicalAngle(angle);
    delay(SETTLE_MS);
    ReadingStats stats = readSensorStats();
    printCSVRow(scanId, measurementType, angle, stats);
    delay(20);
  }

  Serial.print("# END scan_id="); Serial.println(scanId);
  Serial.println("# Confirm that 19 CSV rows were captured and review status flags before interpreting the graph.");
  moveLogicalAngle(90);
}

void printHelp() {
  Serial.println("# Commands:");
  Serial.println("# R = reference scan (no sample); S = sample scan (sample inserted)");
  Serial.println("# T = sensor test with LED on; L = LED on; X = LED off");
  Serial.println("# J0..J180 = move to a logical position using current scan pulse bounds");
  Serial.println("# P900..P2100 = set servo pulse in microseconds for unloaded calibration only");
  Serial.println("# H = help");
  Serial.println("# Serial CSV rows: scan_id,measurement_type,angle_deg,adc_median,adc_min,adc_max,n,status");
  Serial.println("# R/S require SERVO_RANGE_VERIFIED and OPTICAL_ZERO_VERIFIED = true after physical checks.");
}

String commandBuffer;

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();
  if (command.length() == 0) return;

  if (command == "R") {
    runScan("reference");
  } else if (command == "S") {
    Serial.println("# Before S: insert the investigation sample without moving any other component.");
    runScan("sample");
  } else if (command == "T") {
    sensorTest();
  } else if (command == "L") {
    setLED(true);
    Serial.println(LED_IS_COMMON_ANODE
    ? "# LED on (verified common-anode mode, active LOW)."
    : "# LED on (standard 2-lead LED mode, active HIGH). Verify physical wiring.");
  } else if (command == "X") {
    setLED(false);
    Serial.println("# LED off.");
  } else if (command == "H" || command == "?") {
    printHelp();
  } else if (command.startsWith("J")) {
    int angle = command.substring(1).toInt();
    if (command.length() < 2 || angle < 0 || angle > 180) {
      Serial.println("# ERROR: use J0 through J180.");
      return;
    }
    moveLogicalAngle(angle);
    Serial.print("# Requested logical position "); Serial.print(angle);
    Serial.println(" degrees. This is not an independent measurement of physical angle.");
  } else if (command.startsWith("P")) {
    int pulse = command.substring(1).toInt();
    if (command.length() < 2 || pulse < CAL_TEST_MIN_US || pulse > CAL_TEST_MAX_US) {
      Serial.print("# ERROR: calibration pulses limited to "); Serial.print(CAL_TEST_MIN_US);
      Serial.print(".."); Serial.print(CAL_TEST_MAX_US); Serial.println(" us in this firmware.");
      return;
    }
    Serial.println("# WARNING: PULSE TEST ONLY with carrier/load removed. Stop immediately at buzzing, strain, or a hard stop.");
    polarizerServo.writeMicroseconds(pulse);
    Serial.print("# Requested pulse "); Serial.print(pulse); Serial.println(" us.");
  } else {
    Serial.println("# Unknown command. Send H for help.");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  setLED(false);
  analogReadResolution(ADC_BITS);
  analogSetPinAttenuation(LDR_PIN, ADC_11db);

  polarizerServo.setPeriodHertz(50);
  polarizerServo.attach(SERVO_PIN, SERVO_ATTACH_MIN_US, SERVO_ATTACH_MAX_US);
  polarizerServo.writeMicroseconds(1500); // centre position; no claim of calibrated zero
  delay(500);

  Serial.println("# MEDIVERSE FIBROS workshop measurement firmware ready.");
  Serial.println("# Board assumption: classic ESP32 DevKit / ESP32-WROOM-32. Verify board and pinout.");
  Serial.println(LED_IS_COMMON_ANODE
    ? "# LED mode: common-anode (use only if package/pinout is confirmed)."
    : "# LED mode: standard 2-lead LED (use only if package has exactly two leads). ");
  Serial.println("# Photo suggests TowerPro MG90S; verify the exact servo supply requirement.");
  Serial.println("# Do not start R/S until the circuit is approved and servo range/optical zero are calibrated.");
  printHelp();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (commandBuffer.length() > 0) {
        handleCommand(commandBuffer);
        commandBuffer = "";
      }
    } else if (commandBuffer.length() < 32) {
      commandBuffer += c;
    } else {
      commandBuffer = "";
      Serial.println("# ERROR: command too long; buffer cleared.");
    }
  }
}
