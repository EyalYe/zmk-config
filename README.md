# tbk_nini — ZMK config

A split ~3x6+ column-staggered keyboard running [ZMK](https://zmk.dev), with:

- a **PAW3395 optical trackball** on the right half,
- a **dongle as the BLE central** (both halves are peripherals), and
- a **Prospector** color status screen (ST7789V) mounted on the dongle.

## Architecture

```
   left half                right half                 dongle                 host
 (nice!nano v2)           (nice!nano v2)              (XIAO BLE)              (PC etc.)
  peripheral               peripheral                 CENTRAL
  keys ──────BLE──────►                ──────BLE──────►  ├─ merges both halves' keys
                          trackball ───(input-split)──►  ├─ runs the keymap
                          (PAW3395)                      ├─ forwards pointer via listener
                                                         ├─ Prospector display
                                                         └─────── USB/BLE HID ──────►
```

Instead of one half being the central, a dedicated **dongle** is the central.
It owns the keymap and sends all HID (keys + mouse) to the host, which keeps
both halves as low-power peripherals and gives the dongle a screen. This is why
the dongle build uses a **mock kscan** (it has no keys of its own) plus a
physical layout / matrix-transform so the keymap still has positions to bind to.

### How the trackball reaches the host

1. The physical **PAW3395** sensor sits on the right half (`pixart,paw3395` on
   SPI, see the pinout below).
2. The right half exposes it over the split link as a `zmk,input-split`
   (`device = <&trackball>`), so raw motion events travel peripheral → central.
3. On the dongle, a matching `zmk,input-split` + `zmk,input-listener` receive
   those events and turn them into HID mouse reports sent to the host.

### Layer-dependent pointer behavior

The dongle's input-listener changes what trackball motion does based on the
active layer (`boards/shields/tbk_nini/tbk_nini_dongle.overlay`):

| Layer | Behavior | Processors |
|-------|----------|------------|
| default | **disabled** (movement scaled to 0) | `zip_xy_scaler 0 1` |
| 1 | normal cursor | `zip_xy_scaler 1 3` |
| 8 | scroll wheel | `zip_xy_to_scroll_mapper` + `zip_scroll_scaler 1 12` |
| 9 | sniper / precision | `zip_xy_scaler 5 2`, `zip_y_scaler 3 2` |

So the cursor only moves while you're holding the relevant layer, which avoids
accidental drift.

## Trackball wiring — PAW3395 (right half)

nice!nano v2 SPI, from `boards/shields/tbk_nini/tbk_nini_right.overlay`:

| Signal | nRF52840 pin |
|--------|--------------|
| SCK | P0.08 |
| MOSI | P0.17 |
| MISO | P0.20 |
| CS | P0.22 |
| Motion / IRQ | P0.06 |

Orientation (`invert-x` / `invert-y`, optional `swap-xy`) is set on the
trackball node in the overlay; CPI and driver tuning live in
`tbk_nini_right.conf`. Driver: `badjeff/zmk-paw3395-driver`.

## Prospector display (dongle only)

Provided by `carrefinho/prospector-zmk-module` (`feat/new-status-screens`). The
adapter shield auto-enables the display and the color LVGL stack, so no extra
display config is needed — only the user-facing options in
`boards/shields/tbk_nini/tbk_nini_dongle.conf`
(`CONFIG_PROSPECTOR_STATUS_SCREEN_OPERATOR`, brightness, ambient-light sensor).

> The Prospector hardware and its display pin mapping are **XIAO-specific**
> (the adapter ships only an `xiao_ble` board overlay). It will not run on a
> nice!nano dongle without a custom board overlay describing your own wiring.

## Build targets

From `build.yaml`:

| Shield | Board | Role |
|--------|-------|------|
| `tbk_nini_left` | `nice_nano@2.0.0` | peripheral |
| `tbk_nini_right` | `nice_nano@2.0.0` | peripheral + trackball |
| `tbk_nini_dongle prospector_adapter` | `xiao_ble` | central + display |
| `settings_reset` | `nice_nano@2.0.0` | BLE settings reset utility |

Firmware is built by GitHub Actions (`.github/workflows/build.yml`); download
the `firmware` artifact and flash each `.uf2` to the matching board. Flash
`settings_reset` first if you're re-pairing after changing the split layout.

## Config file layout

| File | Scope | Purpose |
|------|-------|---------|
| `config/tbk_nini.conf` | all shields | keyboard-wide settings (name) |
| `config/tbk_nini.keymap` | all shields | the keymap (all layers) |
| `boards/shields/tbk_nini/Kconfig.defconfig` | all shields | split / central / pointing / BLE defaults |
| `…/tbk_nini_dongle.conf` | dongle | Prospector options |
| `…/tbk_nini_right.conf` | right | PAW3395 driver options |
| `…/tbk_nini_left.conf` | left | (none — comment only) |

ZMK derives the base name `tbk_nini` from each `tbk_nini_*` shield, so
`config/tbk_nini.conf` and `config/tbk_nini.keymap` are loaded for every build.

## Modules

See `config/west.yml`:

- `zmkfirmware/zmk`
- `carrefinho/prospector-zmk-module` — `feat/new-status-screens` (dongle display)
- `badjeff/zmk-paw3395-driver` — trackball driver
