"""
Root of the Voidorchestra module.
Holds module-level things, like the config settings.
"""
from configparser import ConfigParser
from os import getenv
from pathlib import Path
from typing import Dict

# Config -----------------------------------------------------------------------
__version__: str = "0.1a"
ENVIRONMENT_VARIABLE: str = "VOIDORCHESTRA"
config_file_location: str = getenv(ENVIRONMENT_VARIABLE)
if not config_file_location:
    raise OSError(f"No {ENVIRONMENT_VARIABLE} environment variable")

config_file_path: Path = Path(config_file_location)
if not config_file_path.exists():
    raise OSError(f"No configuration file at {config_file_location}")

config: ConfigParser = ConfigParser()
config_paths: Dict[str, Path] = {}
config.read(config_file_path)

# If any of the paths aren't absolute, adjust them to be relative to the root path of this project.
root_path = Path(config_file_location).parent
for key, value in config["PATHS"].items():
    if not Path(value).is_absolute():
        config["PATHS"][key] = str(root_path / value)
    else:
        config["PATHS"][key] = value

    # Then save as an actual Path
    config_paths[key] = Path(config["PATHS"][key])
