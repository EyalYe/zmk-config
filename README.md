# Corne + Dongle ZMK config

ZMK firmware for a wireless **Corne (crkbd) split keyboard** with a **USB/BLE dongle**.
The dongle runs the keymap and connects to the computer. It also has a **PAW3395 optical
sensor** (for a trackball or mouse) and **5 mouse buttons**.

![Base layer](docs/layer_base.svg)

## Contents

- [Hardware](#hardware)
- [Architecture](#architecture)
- [Dongle wiring](#dongle-wiring)
- [Keymap](#keymap)
- [Building](#building)
- [Flashing & first pairing](#flashing--first-pairing)
- [Customizing](#customizing)
- [Repository layout](#repository-layout)
- [Troubleshooting](#troubleshooting)

## Hardware

| Part            | Board         | Role                    | Shield         |
| --------------- | ------------- | ----------------------- | -------------- |
| Dongle          | nice!nano v2  | Split **central**, connects to the host | `corne_dongle` |
| Left half       | nice!nano v2  | Split peripheral        | `corne_left`   |
| Right half      | nice!nano v2  | Split peripheral        | `corne_right`  |

Other dongle parts:

- PAW3395 sensor breakout (SPI). The driver is [badjeff/zmk-paw3395-driver](https://github.com/badjeff/zmk-paw3395-driver),
  because ZMK doesn't ship a PAW3395 driver.
- 5 momentary switches, each wired between a GPIO and GND.

## Architecture

```
            ┌──────────────┐  BLE   ┌───────────────────────────┐  USB / BLE  ┌──────────┐
            │  Left half   │ ─────▶ │          Dongle           │ ──────────▶ │ Computer │
            │ (peripheral) │        │  (central, owns keymap)   │             └──────────┘
            └──────────────┘        │  • PAW3395 → pointer      │
            ┌──────────────┐  BLE   │  • 5 buttons → keymap     │
            │  Right half  │ ─────▶ │    positions 42–46        │
            │ (peripheral) │        └───────────────────────────┘
            └──────────────┘
```

- Both halves are **peripherals**. They only scan their matrix and send key positions
  to the dongle. The left half is built with `CONFIG_ZMK_SPLIT_ROLE_CENTRAL=n` to
  override the stock Corne default.
- The dongle is the **central**. It runs the keymap and all behaviors, handles the BT
  profiles, and sends HID reports. It accepts **2** peripherals
  (`ZMK_SPLIT_BLE_CENTRAL_PERIPHERALS=2`).
- The halves' batteries are reported to the host through the dongle (battery fetching and
  proxy are on).
- The halves use less power because they never talk to the host. Plug the dongle into
  USB and it never needs charging.

### Key positions

The dongle's matrix transform uses positions **0–41** for the regular 42-key Corne layout.
Its own buttons are **row 4**, positions **42–46**. A `zmk,kscan-composite` with
`row-offset = <4>` moves the 5 direct-wired buttons onto that row, so they can't collide
with the halves' keys.

## Dongle wiring

![Dongle wiring](docs/dongle_wiring.svg)

The PAW3395 uses **only high-frequency pins**. The nRF52840 datasheet marks
some GPIOs "low frequency I/O only" (≤10 kHz): P0.09/P0.10 (the NFC pins) and the
P1.xx pins near the radio. Those are fine for buttons but not for the sensor's SPI bus,
so the 5 buttons get the low-frequency pins.

| Signal          | Pro Micro pin | nRF52840 pin | Notes                               |
| --------------- | ------------- | ------------ | ----------------------------------- |
| PAW3395 SCLK    | D1            | P0.06        | SPIM2 SCK                           |
| PAW3395 MOSI    | D0            | P0.08        | SPIM2 MOSI                          |
| PAW3395 MISO    | D2            | P0.17        | SPIM2 MISO                          |
| PAW3395 NCS     | D3            | P0.20        | chip select, active low             |
| PAW3395 MOTION  | D4            | P0.22        | interrupt, active low, pull-up      |
| PAW3395 VCC/GND | VCC / GND     |              | check your breakout's voltage       |
| BTN1            | D8            | P1.04        | → GND, internal pull-up             |
| BTN2            | D9            | P1.06        | → GND                               |
| BTN3            | D10           | P0.09        | → GND (NFC pin, enabled as GPIO)    |
| BTN4            | D16           | P0.10        | → GND (NFC pin, enabled as GPIO)    |
| BTN5            | D14           | P1.11        | → GND                               |

P0.09/P0.10 default to the NFC antenna. The overlay turns them into GPIOs with
`&uicr { nfct-pins-as-gpios; }`. P0.17/P0.20 are the nice!nano's default I2C pins, but
I2C is disabled on the dongle, so they're free for SPI.

The sensor runs on `spi2` at 4 MHz, at **800 CPI** by default. See [Customizing](#customizing).

## Keymap

Five layers. The halves have the same bindings as the original `corne.keymap`, and each
layer adds a row for the 5 dongle buttons. Hold **Lower** or **Raise** for those layers;
holding **Fn** from either one opens the F-key layer. The middle dongle button toggles the
**Scroll** layer, where the sensor scrolls instead of moving the pointer.

![Full keymap](docs/keymap.svg)

<details>
<summary>Individual layers</summary>

![Base](docs/layer_base.svg)
![Lower](docs/layer_lower.svg)
![Raise](docs/layer_raise.svg)
![Fn](docs/layer_fn.svg)
![Scroll](docs/layer_scroll.svg)

</details>

| Dongle button | Base layer         |
| ------------- | ------------------ |
| BTN1          | Left click         |
| BTN2          | Scroll mode toggle |
| BTN3          | Right click        |
| BTN4          | Back (MB4)         |
| BTN5          | Forward (MB5)      |

Other layers leave them transparent, so they work the same on every layer.

**Scroll mode:** press BTN2 once and moving the sensor scrolls (vertical and horizontal).
Press BTN2 again to go back to pointer mode. It's a toggle, not a hold, and there is no
middle click.

> **Bootloader:** `Fn` + the `X` key position (red key) puts the **left half** into
> bootloader mode. To get the dongle into the bootloader, double-tap
> its reset button.

The images are generated from the keymap. After editing
[`config/corne_dongle.keymap`](config/corne_dongle.keymap), regenerate them with:

```bash
python3 scripts/gen_layout_svg.py .
```

## Building

### GitHub Actions (default)

Push the branch. The workflow in `.github/workflows/build.yml` builds every entry in
[`build.yaml`](build.yaml) and uploads a `firmware` artifact with:

- `corne_dongle-nice_nano-zmk.uf2`
- `corne_left-nice_nano-zmk.uf2`
- `corne_right-nice_nano-zmk.uf2`
- `settings_reset-nice_nano-zmk.uf2`

### Local build

This needs a west workspace with ZMK and the Zephyr SDK, plus a clone of
`zmk-paw3395-driver`. Run from the workspace root:

```bash
R=/path/to/this/repo

# Dongle (needs the PAW3395 driver module)
west build -p -s zmk/app -d build/corne_dongle -b nice_nano@2.0.0//zmk -- \
  -DSHIELD=corne_dongle -DZMK_CONFIG=$R/config \
  "-DZMK_EXTRA_MODULES=$R;$PWD/zmk-paw3395-driver"

# Left half (forced to peripheral)
west build -p -s zmk/app -d build/corne_left -b nice_nano@2.0.0//zmk -- \
  -DSHIELD=corne_left -DZMK_CONFIG=$R/config -DZMK_EXTRA_MODULES=$R \
  -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=n

# Right half
west build -p -s zmk/app -d build/corne_right -b nice_nano@2.0.0//zmk -- \
  -DSHIELD=corne_right -DZMK_CONFIG=$R/config -DZMK_EXTRA_MODULES=$R
```

Each build writes its firmware to `build/<name>/zephyr/zmk.uf2`.

## Flashing & first pairing

1. **Flash `settings_reset` to all three boards** (dongle, left, right). This clears old
   bonds. It matters most if the left half used to be the central.
2. Flash `corne_dongle` to the dongle, `corne_left` to the left half and `corne_right` to
   the right half. To flash a board: double-tap reset, then copy the `.uf2` to the
   `NICENANO` drive.
3. Power the dongle (USB) and both halves. The halves pair with the dongle automatically.
4. Connect the computer:
   - **USB:** works immediately.
   - **Bluetooth:** pair with `corne_mac`. Lower + `A` `S` `D` `F` `G` selects BT profiles 1–5.
     `Fn` + `Z` clears the current profile.

## Customizing

| What                     | Where                                                        |
| ------------------------ | ------------------------------------------------------------ |
| Keymap / dongle buttons  | `config/corne_dongle.keymap` (positions 42–46 = last row)    |
| Sensor CPI               | `cpi = <800>;` in `boards/shields/corne_dongle/corne_dongle.overlay` (50–26000, step 50) |
| Sensor orientation       | uncomment `swap-xy;`, `invert-x;`, `invert-y;` in the overlay |
| Report rate              | `CONFIG_PAW3395_REPORT_INTERVAL_MIN` in `corne_dongle.conf` (try `8` on USB) |
| Pins                     | `corne_dongle.overlay` (keep SPI on P0.xx high-frequency pins) |
| Keyboard / BT name       | `ZMK_KEYBOARD_NAME` in `boards/shields/corne_dongle/Kconfig.defconfig` |
| Halves' settings         | `config/corne.conf` (applies to `corne_left`/`corne_right`)  |
| Scroll speed             | `&zip_scroll_scaler 1 16` in `config/corne_dongle.keymap` (bigger divisor = slower) |

Ideas: use more ZMK [input processors](https://zmk.dev/docs/keymaps/input-processors), e.g. to
scale the pointer speed.

## Repository layout

```
.
├── build.yaml                         # CI build matrix (dongle, left, right, reset)
├── boards/shields/corne_dongle/       # custom dongle shield
│   ├── Kconfig.shield
│   ├── Kconfig.defconfig              # central role, 2 peripherals, keyboard name
│   ├── corne_dongle.overlay           # buttons kscan, matrix transform, PAW3395 on SPI
│   ├── corne_dongle.conf              # pointing + PAW3395 + battery proxy
│   └── corne_dongle.zmk.yml
├── config/
│   ├── west.yml                       # ZMK + badjeff/zmk-paw3395-driver
│   ├── corne_dongle.keymap            # the keymap that's actually used (47 keys)
│   ├── corne.keymap                   # 42-key keymap the half builds need
│   └── corne.conf                     # applies to the halves
├── docs/                              # generated layout + wiring SVGs
├── scripts/gen_layout_svg.py          # regenerates docs/*.svg from the keymap
└── zephyr/module.yml                  # makes this repo a Zephyr module (custom shield)
```

## Troubleshooting

- **Halves don't connect:** flash `settings_reset` to all three boards, then reflash the
  real firmware. A left half that used to be central keeps old bonds.
- **Sensor dead:** check the MOTION/NCS wiring and the breakout's supply voltage. Then
  build with `CONFIG_PAW3395_LOG_LEVEL_DBG=y` and `CONFIG_ZMK_USB_LOGGING=y`, and watch
  the dongle's USB serial output.
- **Pointer moves the wrong way:** use `swap-xy` / `invert-x` / `invert-y` in the overlay.
- **Scroll goes the wrong way:** append `&zip_scroll_transform INPUT_TRANSFORM_Y_INVERT`
  (and/or `INPUT_TRANSFORM_X_INVERT`) to the scroller's `input-processors` in
  `corne_dongle.keymap`.
- **Sensor takes a while to start:** set `CONFIG_PAW3395_INIT_POWER_UP_EXTRA_DELAY_MS`.
- **Keys on the wrong positions:** the halves must use the stock 6-column Corne transform.
  `corne_dongle.keymap` must have exactly 47 bindings per layer.
