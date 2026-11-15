# Fractal Design Scape: USB HID protocol

This document describes how the USB dongle of the Fractal Design Scape wireless headset talks to a host computer.

## Status of this document

- The author wrote this document from tests on one headset and one dongle. Other firmware can behave differently.
- Every item marked "tested" was observed on the real device. Items marked "not tested" were not observed.
- This document does not contain vendor code or vendor documentation.
- This is not an official document. Fractal Design did not write it and does not support it.
- "Fractal Design" and "Scape" are names of their owners.
- This document is not legal advice. Check the law in your country before you reverse engineer a product.
- Use the commands at your own risk. A wrong write command can change the settings of your headset.

## Device

| Item | Value |
|---|---|
| USB ID | `36bc:0001` (Fractal Scape Dongle) |
| Interface 0 | Audio control |
| Interface 1 | Audio streaming, output (speakers) |
| Interface 2 | Audio streaming, input (microphone) |
| Interface 3 | HID |
| HID endpoint | One interrupt IN endpoint, `0x84`, 64 bytes, 1 ms interval. No OUT endpoint. |

The host cannot see the headset. The host sees only the dongle.
The dongle stays connected when the headset is on the dock.

### HID report descriptor

The descriptor is 177 bytes long. It declares these top-level collections:

| Usage page | Report ID | Content |
|---|---|---|
| Consumer (`0x0C`) | `0x0C` | Input, 6 bits: usages `0xE9`, `0xEA`, `0xE2`, `0xCD`, `0xB5`, `0xB6` |
| Vendor (`0xFF13`) | `6` out, `7` in | 61 bytes each |
| Telephony (`0x0B`) | `5` | Buttons and LED outputs |
| Vendor (`0xFF00`) | `2` | 63 bytes, input and output. Commands use this report. |

All commands in this document use report ID `2` on the `0xFF00` collection.
The other collections were not tested.

## Send a command and read the reply

1. Send an output report with report ID `2`.
2. Read the input report that the dongle sends back.

On Linux, use `write()` and then `read()` on the `/dev/hidrawN` node of the dongle.
Pad the report with zeros to 64 bytes in total.

```
send:   02 <group> <command> <argument bytes> 00 ...
reply:  02 <group> <command> <data bytes> 00 ...
```

Notes (tested):

- The dongle does not send reports by itself. It sends a reply only when you send a command.
- The dongle sends each reply to every program that has the `hidraw` node open.
  If two programs send commands at the same time, they can take the replies of each other.
  Run only one program at a time.
- Commands with group `0xF1` go to the headset. The headset must be awake.
- Commands with group `0x11` go to the dongle.

## Dock detection

Send `02 11 21`. The dongle answers at all times. Offset 3 of the reply (report ID removed) shows the dock status:

| Offset 3 | Meaning |
|---|---|
| `1` | The headset is awake (off the dock) |
| `0` | The headset is on the dock |

Tested: the value changed when the author lifted the headset and when the author put it on the dock.
No answer in 0.4 seconds means that the dongle is not usable. Treat it as docked.

A group `0xF1` command (for example `F1 21`) gets no answer while the headset is on the dock.
No byte in the `F1 21` state shows the dock status.

Poll every 0.25 to 0.5 seconds. Accept a change only after two polls agree.
The dongle gives short false answers while the headset goes onto the dock.

## Read commands

| Send | Reply | Meaning |
|---|---|---|
| `02 F1 21` | 64 bytes | Headset state. See the next section. |
| `02 11 21` | `11 21 00 <0 or 1> ...` | Dongle state. Offset 3 is `1` while the headset is awake and `0` while it is on the dock (tested). |
| `02 F1 01` | `F1 01 00 03 30` | Version information (meaning of `03 30` not known) |
| `02 11 01` | `11 01 00 03 21` | Version information (meaning of `03 21` not known) |
| `02 FF 21` | All zeros | No data |

## Headset state (`F1 21`)

The offsets below do not include the report ID. Add 1 to each offset for raw `hidraw` data.

| Offset | Meaning | Values |
|---|---|---|
| 0, 1 | Copy of the command bytes | `F1 21` |
| 3 | Mic arm is connected | `1` connected, `0` removed (tested) |
| 4 | Mic is muted | `1` muted, `0` not muted (tested) |
| 5 | EQ preset | `1` to `3` (tested) |
| 13 | Hall sensor of the mic arm | `1` arm up, `0` arm down or removed (tested) |
| 15 | Sidetone is on | `1` on, `0` off (tested) |
| 16 | Sidetone volume in percent | `0` to `100` (tested) |
| 19 | Environmental noise cancellation (ENC) is on | `1` on, `0` off (tested) |
| 25 | Copy of the EQ preset (offset 5) | `1` to `3` (tested) |
| 32 | EQ change flag | Changes to `1` for less than one second when the EQ preset changes (tested) |
| 38 | Copy of the mute flag (offset 4) | `1` muted, `0` not muted (tested) |
| 14 | Probably the battery level in percent | Always read `100` while the headset was full. Not tested. |
| 18, 20 | Unknown | Always read `1` while the headset was awake |
| 6, 12 | Unknown | Always read `0` |
| 7 to 11, 17 | Unknown | Always read `0`. Not tested. |

Offset 26 changed from `0x4b` to `0x45` during one test. The reason is not known.

Example reply (raw `hidraw` data, headset awake):

```
02 f1 21 00 01 01 01 00 00 00 00 00 00 00 01 64 01 64 00 01 00 01 00 00 00 00 01 4b 10
```

### Mic arm and mute

The hall sensor (offset 13) is on the hinge of the mic arm.
It is not a dock sensor and it is not a wear sensor.
It did not change when the headset was lifted, docked or worn.

When you raise the arm, the headset mutes the mic. Offsets 4 and 13 both change to `1`.
You can also mute the mic with the arm down. Use the mute control on the headset. The arm glows red.

| State | Offset 3 | Offset 4 | Offset 13 |
|---|---|---|---|
| Arm up | 1 | 1 | 1 |
| Arm down, mic live | 1 | 0 | 0 |
| Arm removed | 0 | 1 | 0 |
| Arm down, muted with the button | 1 | 1 | 0 |

### EQ preset

Each press of the EQ button changes the preset in this order: 1, 2, 3, 1.
Offsets 5 and 25 show the preset. Offset 32 changes to `1` for less than one second at each change.
The names of the presets are not known.

## Write commands

A write command has the same format as a read command. The reply format depends on the command.

### Sidetone

Sidetone plays your own voice in the headphones.

| Item | Value |
|---|---|
| Command | `F1 34` |
| Argument 1 | Mode: `0` disable, `1` enable, `2` volume up, `3` volume down |
| Argument 2 | Number of steps for modes `2` and `3`. Use `0` for modes `0` and `1`. |

```
disable:      02 F1 34 00 00
enable:       02 F1 34 01 00
volume up 5:  02 F1 34 02 05
volume down 5: 02 F1 34 03 05
```

The reply has this format (report ID removed):

| Offset | Meaning |
|---|---|
| 0, 1 | `F1 34` |
| 3 | Sidetone state: `1` on, `0` off |
| 4 | Sidetone volume in percent, `0` to `100` |

Tested:

- One step changes the volume by 1 percent. The volume stops at `100`.
- A step count of 5 from 98 percent gave 100 percent.
- The state read (offsets 15 and 16) shows the new values at once.

Not confirmed: the author did not hear a difference in the headphones when sidetone was on, off, or at 50 percent.
The author does not know if the headset applies the setting.
The author did not test the lower limit of the volume.

### Environmental noise cancellation (ENC)

ENC reduces the background noise that the microphone picks up.

| Item | Value |
|---|---|
| Command | `F1 36` |
| Argument 1 | `1` on, `0` off |

```
ENC on:   02 F1 36 01
ENC off:  02 F1 36 00
```

Tested: the state read shows the new value at offset 19.
The reply to the command does not repeat the new value. Read the state again to check it.

### Not tested

- Commands that set the EQ preset, the EQ curve, the microphone EQ or the lighting.
- Firmware update commands. Do not send unknown commands to the dongle.

## Volume knob

The volume knob does not change a byte of the `F1 21` state.
In one test the volume of the dongle sound card changed from 100% to 70% when the knob turned down.
The author did not find out how the knob and the sound card volume connect.
To read or set the volume, use the volume of the audio device.

## Example code

`scape_state.py` prints the state of the dongle once each second.
The user needs read and write access to the `hidraw` node of the dongle.
