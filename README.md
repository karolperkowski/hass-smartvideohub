# hass-smartvideohub

Home Assistant integration for Blackmagic Design video routing devices, including:

- **Smart Videohub** (4x4 up to 40x40)
- **Blackmagic Web Presenter** (streaming control)
- **Teranex Mini** (LUT and video output control)

The integration connects over raw TCP on port 9990 and updates Home Assistant in real time whenever routing changes are made on the device or from any other controller.

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add `https://github.com/karolperkowski/hass-smartvideohub` as an **Integration**
4. Search for **Smart Video Hub** and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/smartvideohub` directory into your Home Assistant `custom_components` folder and restart.

---

## Configuration

After installation, add the integration via **Settings → Devices & Services → Add Integration → Smart Video Hub**.

| Field | Required | Default | Description |
|---|---|---|---|
| Host | Yes | — | IP address of the device |
| Port | No | 9990 | TCP port (9990 for all models) |

---

## Options

After setup, click **Configure** on the integration card to access options.

| Option | Description |
|---|---|
| Log level | Controls integration verbosity. Use `debug` to troubleshoot connection or parsing issues. No restart required. |

---

## Entities

### Smart Videohub (40x40, 12x12, etc.)

Each output port becomes a **media player** entity with:

- **State**: Name of the currently routed input (e.g. `TMAINT-01`)
- **Source select**: Route any input to this output
- **Source list**: All available inputs

Entity IDs follow the format `media_player.<mac>_<output_label>`, e.g. `media_player.7c2e0d0a2d90_1w6_12_tv1`.

### Blackmagic Web Presenter

- **Switch**: Start/stop streaming (On Air / Idle)
- **Select**: Platform, Video Mode, Quality Level
- **Text**: Stream Key
- **Button**: Reboot device

### Teranex Mini

- **Select**: LUT selection

---

## Dashboard

The integration works well with [mini-media-player](https://github.com/kalkih/mini-media-player) for a source selection UI. Example card:

```yaml
type: custom:mini-media-player
entity: media_player.7c2e0d0a2d90_1w6_12_tv1
source: full
icon: mdi:television-box
hide:
  power: true
  power_state: true
  controls: true
  volume: true
shortcuts:
  label: Source
  columns: 3
  buttons:
    - name: TXMAINT-01
      type: source
      id: TXMAINT-01
```

---

## Behaviour

- **Real-time updates**: Routing and label changes made on the device or by other controllers are reflected immediately in HA
- **Reconnection**: If the TCP connection is lost, the integration waits 30 seconds then reconnects automatically
- **Keepalive**: A PING is sent every 120 seconds to keep the connection alive
- **TCP buffering**: Data is buffered correctly across multiple TCP chunks, so large hubs with many inputs/outputs (e.g. 40x40) are fully supported

---

## Debugging

Enable debug logging via **Settings → Devices & Services → Smart Video Hub → Configure** and set Log level to `debug`. No restart required.

Alternatively, add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.smartvideohub: debug
```

Debug output includes TCP chunk sizes, block transitions, every parsed input/output label, routing entries, and prelude completion summary.

---

## Supported Devices

Tested with:
- Blackmagic Smart Videohub 40x40

Should work with any device supporting the Blackmagic Videohub TCP protocol on port 9990.
