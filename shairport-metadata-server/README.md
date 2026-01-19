# Shairport Metadata Server

A lightweight service that subscribes to Shairport Sync MQTT metadata topics and exposes the current "Now Playing" information via HTTP for the InkyPi shairport-display plugin.

## Requirements

- Python 3.7+
- Shairport Sync configured with MQTT metadata output
- An MQTT broker (e.g., Mosquitto)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python server.py --mqtt-host localhost --mqtt-port 1883 --topic-prefix shairport-sync
```

### Command Line Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--mqtt-host` | `MQTT_HOST` | `localhost` | MQTT broker hostname |
| `--mqtt-port` | `MQTT_PORT` | `1883` | MQTT broker port |
| `--mqtt-user` | `MQTT_USER` | - | MQTT username (optional) |
| `--mqtt-pass` | `MQTT_PASS` | - | MQTT password (optional) |
| `--topic-prefix` | `TOPIC_PREFIX` | `shairport-sync` | MQTT topic prefix |
| `--http-host` | `HTTP_HOST` | `0.0.0.0` | HTTP server bind address |
| `--http-port` | `HTTP_PORT` | `5000` | HTTP server port |
| `--debug` | - | `false` | Enable debug logging |

## API Endpoints

### GET /metadata

Returns the current Now Playing metadata as JSON:

```json
{
  "title": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "genre": "Genre",
  "artwork_base64": "<base64 encoded image>",
  "is_playing": true,
  "player_state": "playing",
  "volume": -15.5,
  "client_name": "iPhone"
}
```

### GET /health

Health check endpoint, returns `{"status": "ok"}`.

## Shairport Sync Configuration

Add the following to your Shairport Sync config (`/etc/shairport-sync.conf`):

```
mqtt = {
  enabled = "yes";
  hostname = "localhost";
  port = 1883;
  topic = "shairport-sync";
  publish_raw = "no";
  publish_parsed = "yes";
  publish_cover = "yes";
};
```

## Running as a Service

Create a systemd service file at `/etc/systemd/system/shairport-metadata.service`:

```ini
[Unit]
Description=Shairport Metadata Server
After=network.target mosquitto.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/InkyPi/shairport-metadata-server
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable shairport-metadata
sudo systemctl start shairport-metadata
```
