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

        # Create default config if it doesn't exist
        if not self.config_path.exists():
            self._create_default_config()

        # Load initial configuration
        self.reload(force=True)

    def _create_default_config(self):
        """Create a default configuration file"""
        self._config.clear()

        # Add default vars section
        self._config.add_section("vars")

        # Add nested sections
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

        # Write to file
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
            # Check if file has been modified
            current_mtime = os.path.getmtime(self.config_path)
            if not force and current_mtime <= self._last_modified:
                return False

            # Load the config
            self._config.clear()
            self._config.read(self.config_path)
            self._last_modified = current_mtime

            # Parse values from config
            self._parse_config()
            return True

        except Exception as e:
            print(f"Error reloading config: {e}")
            # Keep using existing config if reload fails
            return False

    def _parse_config(self):
        """Parse configuration values from loaded config file"""
        # Initialize dictionaries
        self.COLORS = {}
        self.ICONS = {}

        # Parse colors (convert hex strings to integers)
        for key, value in self._config.items("vars.colors"):
            if value.lower().startswith("0x"):
                self.COLORS[key.upper()] = int(value, 16)
            else:
                self.COLORS[key.upper()] = int(value)

        # Parse icons
        for key, value in self._config.items("vars.icons"):
            self.ICONS[key.upper()] = value

        # Parse prefix
        self.PREFIX = self._config.get("vars", "PREFIX")

        # Get module globals to create/update shortcuts
        module_globals = sys.modules[__name__].__dict__

        # Dynamically create/update color shortcuts
        for color_name, color_value in self.COLORS.items():
            shortcut_name = f"{color_name}_COLOR"
            module_globals[shortcut_name] = color_value

        # Dynamically create/update icon shortcuts
        for icon_name, icon_value in self.ICONS.items():
            shortcut_name = f"{icon_name}_ICON"
            module_globals[shortcut_name] = icon_value

        # Update prefix
        module_globals["PREFIX"] = self.PREFIX


# Create a global instance of the configuration
config = Config()
