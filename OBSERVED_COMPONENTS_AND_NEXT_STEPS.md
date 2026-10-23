# Mediverse: Component identification from the participant's photos

## What appears to be present

1. **ESP32 development board:** appears to be a classic ESP32-WROOM-32-style board with micro-USB and EN/BOOT buttons. Confirm the shield/module marking and actual header labels before wiring.
2. **Servo:** case appears to say TowerPro MG90S, while the participant guide names SG90. Confirm the exact item and use its own rated supply. TowerPro's manufacturer page lists the MG90S at 4.8 V operating voltage and says it uses an external adapter.
3. **LED:** the visible red LED appears to have two leads. That suggests a conventional 2-lead red LED, whereas the guide says common-anode. Count the leads in person. If two leads, wire GPIO25 -> 220 ohm resistor -> anode; cathode -> GND, active HIGH. If the actual supplied component has multiple leads and a common anode, get its pinout from the organiser and configure firmware for common-anode active-LOW wiring. Do not mix these circuits.
4. **LDR:** a typical two-lead photoresistor is visible.
5. **Resistors:** two resistors are visible and match the stated count, but the pictures are too blurred to prove their values. Confirm 220 ohm and 10 kilohm using packaging, a multimeter, or the organiser.
6. **Breadboard and jumper wires:** visible. Keep the servo linkage clear of the wiring.
7. **Optical films / sample:** translucent dark sheets may be polarizing films, but the photos do not prove which sheet is which. A white textured sheet cannot be identified confidently as polarizing film. Test suspected polarizer film against a white LCD screen; brightness should change as it is rotated. Overlay two candidate films and rotate one: crossed orientations should strongly reduce transmission. Ask the organiser to identify the investigation sample before placing it in the optical path.
8. **Servo supply:** no clearly identifiable separate regulated servo supply is visible. Confirm that one is provided before powering the servo. Do not power the servo from the ESP32 3V3 pin or a GPIO.

## Conditional pin assignment for a confirmed classic ESP32-WROOM-32 board

- GPIO34: LDR divider midpoint / ADC1 input.
- GPIO18: servo signal.
- GPIO25: LED control.
- 3V3 and GND: LDR divider supply/reference.

Do not apply these assignments to an ESP32-C3/S3/C6 or another variant without checking its pinout.

## LDR divider

```text
ESP32 3V3 ---- LDR ----+---- GPIO34 (classic ESP32 only)
                       |
                      10 kΩ
                       |
                      GND
```

With this topology the ADC node typically rises as the LDR is illuminated more strongly. Readings are raw ADC counts, not calibrated lux.

## Before wiring

- Count the LED leads; confirm LED type and polarity.
- Verify resistor values.
- Read the board's module and pin labels.
- Confirm the servo model, rated voltage, and pin order.
- Confirm a suitable regulated servo supply is provided.
- Identify both polarizer films and the supplied sample with the organiser.
- Have the organiser inspect the circuit before powering it.
