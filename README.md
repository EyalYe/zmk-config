# tbk_nini — ZMK config

Split 3x6+ keyboard with a **PAW3395 trackball** on the right half and a
**Prospector** dongle status screen (color ST7789V) as the BLE central.

## Build targets

See `build.yaml`:

| Shield | Board | Role |
|--------|-------|------|
| `tbk_nini_left` | `nice_nano@2.0.0` | peripheral |
| `tbk_nini_right` | `nice_nano@2.0.0` | peripheral + trackball |
| `tbk_nini_dongle prospector_adapter` | `xiao_ble` | central + display |
| `settings_reset` | `nice_nano@2.0.0` | BLE reset util |

The dongle is the central; both halves are peripherals. The Prospector display
is XIAO-specific (the adapter shield only ships an `xiao_ble` board overlay).

## Trackball — PAW3395 (right half)

Wired to the nice!nano v2 SPI. Pins from `boards/shields/tbk_nini/tbk_nini_right.overlay`:

| Signal | nRF52840 pin |
|--------|--------------|
| SCK | P0.08 |
| MOSI | P0.17 |
| MISO | P0.20 |
| CS | P0.22 |
| Motion / IRQ | P0.06 |

Driver: `pixart,paw3395` (from the `badjeff/zmk-paw3395-driver` module).
Orientation (`invert-x` / `invert-y` / optional `swap-xy`) is set on the
trackball node in the overlay. Driver tuning lives in `tbk_nini_right.conf`.

## Modules

- `zmkfirmware/zmk`
- `carrefinho/prospector-zmk-module` (`feat/new-status-screens`) — dongle display
- `badjeff/zmk-paw3395-driver` — trackball driver

See `config/west.yml`.
