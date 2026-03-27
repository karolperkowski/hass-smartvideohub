# Session Summary — hass-smartvideohub

## Repository
- **Upstream**: https://github.com/jnimmo/hass-smartvideohub
- **Fork**: https://github.com/karolperkowski/hass-smartvideohub
- **Device**: Blackmagic Smart Videohub 40x40 (`7C2E0D0A2D90`) on `10.96.81.240:9990`

---

## Bug Fixes

### TCP Stream Buffering (`pyvideohub.py`)
The most impactful fix. TCP splits the 40-input/40-output prelude across multiple `data_received()` calls. The old code reset `current_block = None` as a local variable on every call, silently dropping anything in subsequent chunks.

**Fix**: Added `self._buffer` to accumulate incomplete data between calls. Replaced `current_block` with `self._current_block` (instance variable) so block context persists across TCP chunks.

### Input Label Updates (`pyvideohub.py`)
`dict.setdefault()` is write-once — label renames on the device were silently ignored.

**Fix**: Direct `dict[key] = value` assignment. Also cleans `filtered_inputs` when a label is reset to its default.

### Wrong Input Routed on Source Select (`pyvideohub.py`)
`set_input_by_name()` used `list.index()` as the hardware port number, which fails on non-sequential port layouts.

**Fix**: Iterate `self.inputs.items()` to look up the actual hardware port number by label.

### Automatic Label Updates After Init (`pyvideohub.py`)
Label changes after startup were stored silently but entities were never notified.

**Fix**: Fire `_send_update_callback()` when INPUT LABELS or OUTPUT LABELS change after init.

### `update_callback` Operator Precedence Bug (`media_player.py`)
`output_id == 0 | output_id == self._output_id` — bitwise `|` has higher precedence than `==`, so the broadcast `output_id=0` signal never triggered entity updates.

**Fix**: Changed to `output_id == 0 or output_id == self._output_id`.

### Entity State Shows Source Name (`media_player.py`)
`state` always returned `"playing"`. For a video router the source name is more useful.

**Fix**: Return `self._attr_source` (e.g. `TMAINT-01`) as state. Falls back to `MediaPlayerState.ON` if no source, `MediaPlayerState.OFF` when disconnected.

### Entity ID Format (`media_player.py`)
Old IDs used MAC + output number (e.g. `7c2e0d0a2d90_output_5`) — opaque and meaningless.

**Fix**: IDs now use MAC + output label (e.g. `7c2e0d0a2d90_1w6_12_tv1`) — human-readable and unique per device.

### Keepalive Fires Before Prelude (`pyvideohub.py`)
`keep_alive()` sent a PING immediately on connect, before the device finished sending the prelude. The Videohub's ACK response arrived mid-prelude and could interfere with block parsing.

**Fix**: `keep_alive()` now sleeps 120 seconds before the first PING.

### Orphaned Entity Registry Entries (`__init__.py`)
During development the `unique_id` was briefly changed from `smartvideohub_output_N` to `smartvideohub_<MAC>_output_N`, creating 40 duplicate registry entries that showed "entity no longer provided by the integration".

**Fix**: `_async_remove_orphaned_entities()` runs on startup, detects and removes any MAC-prefixed entries automatically. No-op after the first clean run.

---

## Refactoring

### `__init__.py`
- Removed bad import (`device_tracker config_entry` shadowing the parameter)
- Removed deprecated `hass.loop`
- `async_forward_entry_setups` now awaited directly (fixes entity setup race condition)
- Extracted `PLATFORMS` constant to avoid duplication
- `hass.data` cleaned up properly on unload
- Log level applied from options on startup

### `config_flow.py`
- Removed deprecated `@config_entries.HANDLERS.register` decorator
- Removed deprecated `hass.loop`
- Fixed connection leak — `client.stop()` always called after validation
- Added 10s timeout on connection validation
- Fixed docstring (was "Huawei UPS")
- Added `OptionsFlow` with log level selector (Warning / Info / Debug / Error)
- Log level applied immediately on change, no restart needed

### `media_player.py`
- Removed unused `asyncio` import
- Replaced wildcard `const` import with explicit imports
- Fixed docstring (was "Monoprice amplifier zone")
- Fixed manufacturer spelling (Blackmagic Design)
- Reverted `unique_id` to `smartvideohub_output_N` for registry compatibility
- Downgraded `update_callback` log from INFO to DEBUG
- Added `_attr_should_poll = False` explicitly
- `_connected` now updated in `update()` so disconnects reflect in state

### `pyvideohub.py`
- Removed deprecated `ensure_future` import
- Removed `loop` parameter and `_eventLoop` — uses `asyncio.get_running_loop()`
- `_stopped = False` initialised in `__init__` (was only set in `start()`)
- `keep_alive()` wired into `connection_made()`, sleeps before first ping
- `SERVER_RECONNECT_DELAY` (30s) now actually used in `connection_lost()`
- `self.initialised.clear()` on disconnect so next `await initialised.wait()` blocks correctly
- `connect()` uses `create_task` instead of `ensure_future`
- Fixed `start()`/`stop()` docstrings (referenced "envisalink")
- `stop()` guards `transport.close()` with `None` check
- `asyncio.get_event_loop()` replaced with `asyncio.get_running_loop()` (Python 3.10+ safe)
- `set_lut()` potential `UnboundLocalError` fixed
- `_send_update_callback()` default changed from `False` to `0`
- Stale comment in `get_input_list()` removed

### `select.py`
- Fixed `None.split()` crashes when stream settings not yet received
- Added `_split_option()` helper for safe parsing
- Fixed `int(None)` crash on LUT count when not yet received

### `text.py`
- Fixed `None + "/stream_key"` `TypeError` when `Unique ID` not yet in attrs

### `const.py`
- Removed unused `timedelta` import
- Added `CONF_LOG_LEVEL`, `DEFAULT_LOG_LEVEL`, `LOG_LEVELS`

### `select.py`, `button.py`, `switch.py`, `text.py`
- Replaced wildcard `from .const import *` with explicit imports

### `manifest.json`
- Updated URLs to fork
- Added codeowner (`@karolperkowski`)
- Bumped version `0.0.1` → `0.1.0`

### `translations/en.json` + `strings.json`
- Fixed port description (was listing wrong port numbers)
- Added missing `unknown` error key
- Added options flow translations with log level descriptions
- Improved error message wording

### `hacs.json`
- Removed stale `domains` key

### `README.md`
- Completely rewritten — old docs described manual YAML install from years ago
- Documents HACS install, config flow, options, entity types, dashboard example, debugging

---

## Debug Logging

Enable via **Settings → Devices & Services → Smart Video Hub → Configure** (no restart needed), or add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.smartvideohub: debug
```

Logs TCP chunk sizes, block transitions, every parsed input/output label, routing entries, and prelude completion summary.

---

## Entity ID Format

Entity IDs follow the format: `media_player.<mac>_<output_label>`

Example: `media_player.7c2e0d0a2d90_1w6_12_tv1`

- MAC prefix ensures uniqueness across multiple devices
- Output label makes IDs human-readable
- `unique_id` remains `smartvideohub_output_N` internally for registry stability

---

## Known Unresolved Items

- `brands/` directory with `icon.png` not yet added (required for HACS default store submission, not needed for custom repo)
- `quad16_output_17` and `quad16_output_18` in the QUAD 16x1 Config dashboard card belong to a separate non-Videohub device — entity IDs need to be confirmed by checking the HA entity registry

---

## Commits

| Commit | Description |
|---|---|
| `8c2ec90` | Fix input/output name mapping in pyvideohub |
| `4c18fc3` | Auto-update input/output names when device sends label changes |
| `38d9d15` | Fix missing inputs/outputs caused by TCP stream fragmentation |
| `5959ac7` | Add enhanced debug logging for TCP buffer and parser |
| `749c530` | Use output name for entity_id instead of MAC address + number |
| `06975e3` | Prefix entity_id with device MAC + output name for multi-device support |
| `eb0c184` | Show current source name as entity state instead of "playing" |
| `1fd440a` | Refactor and clean up all integration files |
| `6eff8fc` | Pre-ship fixes: crashes, translations, strings.json, README |
| `cd71c7c` | Final pre-test fixes in pyvideohub |
| `0aa87a0` | Add debug level selector in integration options |
| `e4221be` | Fix entity registry mismatch and keepalive interference with prelude |
| `5238a50` | Auto-remove orphaned entity registry entries on startup |
