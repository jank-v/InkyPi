#!/usr/bin/env python3
"""
Shairport Sync Metadata Server

Subscribes to Shairport Sync MQTT topics and exposes current
Now Playing metadata via a simple HTTP API for the InkyPi plugin.
"""

import argparse
import base64
import json
import logging
import os
import threading
from flask import Flask, jsonify
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Current metadata state (thread-safe via GIL for simple reads/writes)
metadata = {
    "title": "",
    "artist": "",
    "album": "",
    "genre": "",
    "artwork_base64": None,
    "is_playing": False,
    "player_state": "stopped",
    "volume": 0,
    "client_name": "",
}


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        logger.info("Connected to MQTT broker")
        topic_prefix = userdata.get("topic_prefix", "shairport-sync")
        # Subscribe to all shairport-sync topics
        client.subscribe(f"{topic_prefix}/#")
        logger.info(f"Subscribed to {topic_prefix}/#")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    """Callback when disconnected from MQTT broker."""
    logger.warning(f"Disconnected from MQTT broker (rc={rc})")


def on_message(client, userdata, msg):
    """Callback when a message is received from MQTT."""
    global metadata
    
    topic = msg.topic
    topic_prefix = userdata.get("topic_prefix", "shairport-sync")
    
    # Remove prefix to get the relative topic
    relative_topic = topic[len(topic_prefix) + 1:] if topic.startswith(topic_prefix) else topic
    
    try:
        # Handle different topic types
        if relative_topic == "artist":
            metadata["artist"] = msg.payload.decode("utf-8")
            logger.debug(f"Artist: {metadata['artist']}")
            
        elif relative_topic == "title":
            metadata["title"] = msg.payload.decode("utf-8")
            logger.debug(f"Title: {metadata['title']}")
            
        elif relative_topic == "album":
            metadata["album"] = msg.payload.decode("utf-8")
            logger.debug(f"Album: {metadata['album']}")
            
        elif relative_topic == "genre":
            metadata["genre"] = msg.payload.decode("utf-8")
            logger.debug(f"Genre: {metadata['genre']}")
            
        elif relative_topic == "cover" or relative_topic == "artwork":
            # Artwork comes as binary data
            if msg.payload:
                metadata["artwork_base64"] = base64.b64encode(msg.payload).decode("utf-8")
                logger.debug("Received artwork")
            else:
                metadata["artwork_base64"] = None
                logger.debug("Artwork cleared")
                
        elif relative_topic == "play_start" or relative_topic == "play_resume":
            metadata["is_playing"] = True
            metadata["player_state"] = "playing"
            logger.info("Playback started/resumed")
            
        elif relative_topic == "play_end" or relative_topic == "play_flush":
            metadata["is_playing"] = False
            metadata["player_state"] = "stopped"
            # Clear metadata on stop
            metadata["title"] = ""
            metadata["artist"] = ""
            metadata["album"] = ""
            metadata["artwork_base64"] = None
            logger.info("Playback ended")
            
        elif relative_topic == "pause":
            metadata["is_playing"] = False
            metadata["player_state"] = "paused"
            logger.info("Playback paused")
            
        elif relative_topic == "volume":
            try:
                metadata["volume"] = float(msg.payload.decode("utf-8"))
            except ValueError:
                pass
                
        elif relative_topic == "client_name":
            metadata["client_name"] = msg.payload.decode("utf-8")
            logger.debug(f"Client: {metadata['client_name']}")
            
        elif relative_topic == "active_start":
            logger.info("Shairport session started")
            
        elif relative_topic == "active_end":
            logger.info("Shairport session ended")
            metadata["is_playing"] = False
            metadata["player_state"] = "stopped"
            metadata["title"] = ""
            metadata["artist"] = ""
            metadata["album"] = ""
            metadata["artwork_base64"] = None
            
    except Exception as e:
        logger.error(f"Error processing message on {topic}: {e}")


@app.route("/metadata")
def get_metadata():
    """Return current metadata as JSON."""
    return jsonify(metadata)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


def run_mqtt_client(host, port, topic_prefix, username=None, password=None):
    """Run the MQTT client in a separate thread."""
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata={"topic_prefix": topic_prefix}
    )
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    if username and password:
        client.username_pw_set(username, password)
    
    try:
        client.connect(host, port, 60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"MQTT connection error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Shairport Sync Metadata Server")
    parser.add_argument("--mqtt-host", default=os.environ.get("MQTT_HOST", "localhost"),
                        help="MQTT broker host (default: localhost)")
    parser.add_argument("--mqtt-port", type=int, default=int(os.environ.get("MQTT_PORT", 1883)),
                        help="MQTT broker port (default: 1883)")
    parser.add_argument("--mqtt-user", default=os.environ.get("MQTT_USER"),
                        help="MQTT username (optional)")
    parser.add_argument("--mqtt-pass", default=os.environ.get("MQTT_PASS"),
                        help="MQTT password (optional)")
    parser.add_argument("--topic-prefix", default=os.environ.get("TOPIC_PREFIX", "shairport-sync"),
                        help="MQTT topic prefix (default: shairport-sync)")
    parser.add_argument("--http-host", default=os.environ.get("HTTP_HOST", "0.0.0.0"),
                        help="HTTP server host (default: 0.0.0.0)")
    parser.add_argument("--http-port", type=int, default=int(os.environ.get("HTTP_PORT", 5000)),
                        help="HTTP server port (default: 5000)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting Shairport Metadata Server")
    logger.info(f"MQTT: {args.mqtt_host}:{args.mqtt_port} (prefix: {args.topic_prefix})")
    logger.info(f"HTTP: {args.http_host}:{args.http_port}")
    
    # Start MQTT client in background thread
    mqtt_thread = threading.Thread(
        target=run_mqtt_client,
        args=(args.mqtt_host, args.mqtt_port, args.topic_prefix, args.mqtt_user, args.mqtt_pass),
        daemon=True
    )
    mqtt_thread.start()
    
    # Run Flask app
    app.run(host=args.http_host, port=args.http_port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
