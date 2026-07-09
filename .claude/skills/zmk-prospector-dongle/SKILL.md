---
name: zmk-prospector-dongle
description: >-
  Integrate or debug the carrefinho/prospector-zmk-module (feat/new-status-screens)
  on a ZMK dongle-as-central build. Use when touching this zmk-config's dongle
  shield, display/LVGL config, west.yml, or when the prospector screen is blank,
  garbled, monochrome, or missing battery/keyboard info. Also the reference for
  how ZMK resolves .conf/.keymap files from the config/ folder.
---

# ZMK + Prospector dongle integration

This repo builds a split keyboard (`tbk_nini`) with a **dongle as central** on
`xiao_ble//zmk`, plus the **prospector_adapter** shield (color ST7789V status
screen) from `carrefinho/prospector-zmk-module`, branch `feat/new-status-screens`.

Dongle build target (`build.yaml`):
`board: xiao_ble//zmk`, `shield: tbk_nini_dongle prospector_adapter`.

## The #1 thing to get right: how ZMK finds `.conf` / `.keymap` files

ZMK's config resolution lives in `zmk/app/boards/post_boards_shields.cmake`
(NOT `app/CMakeLists.txt`). For a shield, it builds **candidate base names** by
stripping trailing `_`-segments down to the shield *directory* name, then looks
in the `config/` folder (ZMK_CONFIG) for each candidate.

For `shield: tbk_nini_dongle prospector_adapter` the candidate names are:
`tbk_nini` (dir name for tbk_nini_dongle), `prospector_adapter`, `prospector`,
`tbk_nini_dongle`. Board fallbacks: `xiao_ble`, `default`.

Consequences (verified against source):
- `config/tbk_nini.conf` **IS loaded** for the dongle (and left/right) — because
  `tbk_nini_dongle` reduces to the shield-dir name `tbk_nini`. Same for
  `config/tbk_nini.keymap`. This is why one keymap serves all three shields.
- A file whose name matches **no** candidate is silently **ignored**. There is
  no `<keyword>.conf` catch-all. e.g. a file named `dongle_display.conf` never
  loads — its settings simply don't apply. Don't create configs by ad-hoc names.
- The shield's own `boards/shields/tbk_nini/tbk_nini_dongle.conf` is **always**
  merged by Zephyr (standard shield behavior, independent of the above). It's the
  guaranteed-loaded, dongle-only place for config.
- `config/tbk_nini.conf` also loads for left/right builds, so PROSPECTOR_* keys
  there produce harmless "unmet dep" warnings on the halves. Put dongle-only
  settings in `boards/shields/tbk_nini/tbk_nini_dongle.conf` if you want them scoped.

To confirm what actually loaded, read the CI build log for lines:
`ZMK Config Kconfig: .../<file>.conf` and `Using keymap file: ...`.

## Prospector provides these defaults automatically

`boards/shields/prospector_adapter/Kconfig.defconfig` (active whenever the
`prospector_adapter` shield is in the build) already forces, as defaults:
`ZMK_DISPLAY=y`, `ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y`,
`ZMK_DISPLAY_STATUS_SCREEN_CUSTOM`, and the full color LVGL stack
(`LV_COLOR_DEPTH_16`, `LV_Z_BITS_PER_PIXEL=16`, `LV_Z_VDB_SIZE=50`,
double VDB, flush thread, `LV_DPI_DEF=261`, `ST7789V_RGB565`, PWM/LED for
backlight). So you do **not** need a `dongle_display.conf` to turn the display on.

User-facing prospector options (set them in the dongle-only shield conf
`boards/shields/tbk_nini/tbk_nini_dongle.conf` so they don't warn on the halves):
- `CONFIG_PROSPECTOR_STATUS_SCREEN_{OPERATOR,FIELD,RADII}=y` (Classic is default)
- `CONFIG_PROSPECTOR_USE_AMBIENT_LIGHT_SENSOR=y|n` (default y; selects APDS9960)
- `CONFIG_PROSPECTOR_FIXED_BRIGHTNESS=1..100` (default 50)
- `CONFIG_PROSPECTOR_ROTATE_DISPLAY_180`, `CONFIG_PROSPECTOR_SHOW_MODIFIERS`
- RAM-overflow workaround only if the build fails linking: `CONFIG_LV_Z_VDB_SIZE=25`.

## Gotchas that broke this repo (fixed) — check these first when debugging

1. **Blank/garbled/monochrome color screen** → a local `Kconfig.defconfig` was
   forcing OLED/mono defaults (`SSD1306=y`, `LV_COLOR_DEPTH_1`,
   `LV_Z_BITS_PER_PIXEL=1`, `LV_Z_VDB_SIZE=64`) under `if ZMK_DISPLAY`/`if LVGL`.
   Because prospector forces `ZMK_DISPLAY=y` on the dongle, those blocks fired and
   fought prospector's color settings (Kconfig `default` races are order-dependent
   and fragile). Fix: do **not** set display/LVGL defaults in the keyboard's own
   `Kconfig.defconfig` when the dongle uses prospector. Scope any OLED defaults to
   `if SHIELD_..._LEFT || SHIELD_..._RIGHT` only.

2. **Dongle overlay fails to build / `RC` undefined** → the dongle overlay uses
   `RC(row,col)` in its `matrix-transform`, but `RC` is defined in
   `<dt-bindings/zmk/matrix_transform.h>`. `<input/processors.dtsi>` does NOT pull
   it in. If you drop `#include "<keyboard>.dtsi"` (which is correct for a
   mock-kscan dongle), you must add `#include <dt-bindings/zmk/matrix_transform.h>`
   explicitly.

3. **Dongle overlay pattern**: central dongle uses a mock kscan and its own
   physical layout — never include the halves' matrix `.dtsi` (its GPIO kscan
   references pins the xiao doesn't have). Correct skeleton:
   ```
   #include <dt-bindings/zmk/matrix_transform.h>
   #include <input/processors.dtsi>
   / {
       chosen { zmk,kscan = &mock_kscan; zmk,physical-layout = &physical_layout0; };
       mock_kscan: mock_kscan_0 { compatible = "zmk,kscan-mock"; columns=<0>; rows=<0>; events=<0>; };
       /* split_inputs trackball_split (input-split, reg=0, NO device) + input-listener */
       /* default_transform (RC map, key count must match the keymap) + physical_layout0 */
   };
   ```
   The peripheral that owns the trackball (here `tbk_nini_right`) defines the real
   `paw3395` device and an `input-split` with `device = <&trackball>` at the same
   `reg` index; the central's `input-split` has matching `reg` and no `device`.

4. **Keyboard name shown on screen**: keep `CONFIG_ZMK_KEYBOARD_NAME` consistent
   across every loaded conf (the shield conf and `config/tbk_nini.conf`) or the
   last-merged one wins unpredictably.

## west.yml requirements
Remote `carrefinho` + project `prospector-zmk-module` at revision
`feat/new-status-screens`. The trackball driver comes from `badjeff/zmk-paw3395-driver`.

## Verifying a change
Can't flash locally — push and read the GitHub Actions `build` job log. Confirm:
the expected `.conf`/keymap "loaded" lines appear, no `RC`/undefined-macro DTS
errors, no RAM/flash overflow at link. A wrong-named conf failing silently shows
up as its `CONFIG_*` simply not taking effect, not as an error.
