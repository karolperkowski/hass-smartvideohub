# hass-smartvideohub

Home Assistant integration for Blackmagic Design video routing devices, including:

- **Smart Videohub** (4x4 up to 40x40)
- **Blackmagic Web Presenter** (streaming control)
- **Teranex Mini** (LUT and video output control)

The integration connects over raw TCP and updates Home Assistant in real time whenever routing changes are made on the device or elsewhere.

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

### Options

| Option | Description |
|---|---|
| Hide default inputs | When enabled, inputs that have not been renamed from their factory default (e.g. `Input 1`) are hidden from source lists |

---

## Entities

### Smart Videohub (40x40, 12x12, etc.)

Each output port becomes a **media player** entity with:
- **State**: Name of the currently routed input
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

## Tips

- Works well with [mini-media-player](https://github.com/kalkih/mini-media-player) for source selection on dashboards
- The integration reconnects automatically after a 30-second delay if the TCP connection is lost
- A keepalive ping is sent every 120 seconds to maintain the connection
- All label changes made directly on the device are reflected in Home Assistant in real time

---

## Supported Devices

Tested with:
- Blackmagic Smart Videohub 40x40

Should work with any device that supports the Blackmagic Videohub TCP protocol on port 9990.
