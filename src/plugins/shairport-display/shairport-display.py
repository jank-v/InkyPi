from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image
import logging
import requests

logger = logging.getLogger(__name__)


class ShairportDisplay(BasePlugin):
    """Plugin to display Now Playing information from Shairport Sync via MQTT."""

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        metadata = self._get_metadata(settings)

        template_params = {
            "title": metadata.get("title", "Not Playing"),
            "artist": metadata.get("artist", ""),
            "album": metadata.get("album", ""),
            "artwork_data": metadata.get("artwork_data"),
            "is_playing": metadata.get("is_playing", False),
            "plugin_settings": settings
        }

        image = self.render_image(
            dimensions,
            "shairport-display.html",
            "shairport-display.css",
            template_params
        )
        return image

    def _get_metadata(self, settings):
        """Fetch metadata from a local metadata service or MQTT retained messages."""
        metadata = {
            "title": settings.get("default_title", "Not Playing"),
            "artist": settings.get("default_artist", ""),
            "album": settings.get("default_album", ""),
            "artwork_data": None,
            "is_playing": False
        }

        # Try to get metadata from a local HTTP endpoint (if metadata reader is running)
        metadata_url = settings.get("metadata_url", "http://localhost:5000/metadata")
        try:
            response = requests.get(metadata_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                metadata["title"] = data.get("title", metadata["title"])
                metadata["artist"] = data.get("artist", metadata["artist"])
                metadata["album"] = data.get("album", metadata["album"])
                metadata["is_playing"] = data.get("is_playing", False)

                # Handle artwork
                artwork_url = data.get("artwork_url")
                artwork_base64 = data.get("artwork_base64")

                if artwork_base64:
                    metadata["artwork_data"] = f"data:image/jpeg;base64,{artwork_base64}"
                elif artwork_url:
                    metadata["artwork_data"] = artwork_url

        except requests.RequestException as e:
            logger.warning(f"Could not fetch metadata from {metadata_url}: {e}")

        return metadata
