import configparser
import os
import sys
from pathlib import Path


class Config:
    """Configuration class that loads settings from a CFG file with hot-reload support"""

    def __init__(self, config_path="config.cfg"):
        """Initialize the configuration

        Args:
            config_path (str): Path to the config.cfg file
        """
        self.config_path = Path(config_path)
        self._config = configparser.ConfigParser()
        self._last_modified = 0

        if not self.config_path.exists():
            self._create_default_config()

        self.reload(force=True)

    def _create_default_config(self):
        """Create a default configuration file"""
        self._config.clear()

        self._config.add_section("vars")

        self._config.add_section("vars.colors")
        self._config.set("vars.colors", "MAIN", "0x2d2d2d")
        self._config.set("vars.colors", "WARN", "0x7d7d7d")
        self._config.set("vars.colors", "ERROR", "0x1a1a1a")
        self._config.set("vars.colors", "SUCCESS", "0x4d4d4d")

        self._config.add_section("vars.icons")
        self._config.set("vars.icons", "MAIN", "")
        self._config.set("vars.icons", "WARN", ":warning:")
        self._config.set("vars.icons", "ERROR", ":question:")
        self._config.set("vars.icons", "SUCCESS", ":white_check_mark:")

        self._config.set("vars", "PREFIX", ".")

        with open(self.config_path, "w") as config_file:
            self._config.write(config_file)

    def reload(self, force=False):
        """Reload configuration from the CFG file if modified

        Args:
            force (bool): Force reload even if file hasn't been modified

        Returns:
            bool: True if configuration was reloaded, False otherwise
        """
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if not force and current_mtime <= self._last_modified:
                return False

            self._config.clear()
            self._config.read(self.config_path)
            self._last_modified = current_mtime

            self._parse_config()
            return True

        except Exception as e:
            print(f"Error reloading config: {e}")
            return False

    def _parse_config(self):
        """Parse configuration values from loaded config file"""
        self.COLORS = {}
        self.ICONS = {}

        for key, value in self._config.items("vars.colors"):
            if value.lower().startswith("0x"):
                self.COLORS[key.upper()] = int(value, 16)
            else:
                self.COLORS[key.upper()] = int(value)

        for key, value in self._config.items("vars.icons"):
            self.ICONS[key.upper()] = value

        self.PREFIX = self._config.get("vars", "PREFIX")

        module_globals = sys.modules[__name__].__dict__

        for color_name, color_value in self.COLORS.items():
            shortcut_name = f"{color_name}_COLOR"
            module_globals[shortcut_name] = color_value

        for icon_name, icon_value in self.ICONS.items():
            shortcut_name = f"{icon_name}_ICON"
            module_globals[shortcut_name] = icon_value

        module_globals["PREFIX"] = self.PREFIX


config = Config()
