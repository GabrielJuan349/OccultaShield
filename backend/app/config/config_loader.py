import os
import yaml
import re
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict

class ConfigLoader:
    """
    Singleton configuration loader.
    Loads settings from detection.yaml and supports env var substitution ${VAR:default}.
    """
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load YAML and resolve environment variables."""
        config_path = Path(__file__).parent / "detection.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex to find ${VAR:default} or ${VAR}
        # Matches: ${VAR_NAME} or ${VAR_NAME:defaultValue}
        pattern = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

        def replace_env(match):
            var_name = match.group(1)
            default_val = match.group(2)
            val = os.getenv(var_name)
            if val is not None:
                return val
            if default_val is not None:
                return default_val
            return match.group(0) # Return original if not found and no default

        # Substitute environment variables in the YAML content string
        content_substituted = pattern.sub(replace_env, content)
        
        # Parse YAML
        self._config = yaml.safe_load(content_substituted)

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get config value using dot notation, e.g. 'detector.confidence_threshold'
        """
        keys = path.split('.')
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    @property
    def detector(self) -> Dict[str, Any]:
        return self._config.get('detector', {})

    @property
    def tracking(self) -> Dict[str, Any]:
        return self._config.get('tracking', {})

    @property
    def processing(self) -> Dict[str, Any]:
        return self._config.get('processing', {})

    @property
    def storage(self) -> Dict[str, Any]:
        return self._config.get('storage', {})
        
    @property
    def edition(self) -> Dict[str, Any]:
        return self._config.get('edition', {})

    @property
    def verification(self) -> Dict[str, Any]:
        return self._config.get('verification', {})

@lru_cache()
def get_config() -> ConfigLoader:
    """Return singleton instance of ConfigLoader."""
    return ConfigLoader()
