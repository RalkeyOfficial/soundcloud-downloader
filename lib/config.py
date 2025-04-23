import os
import json
from lib.error_handler import log_error


def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        if not os.path.exists(config_path):
            # Create empty config file if it doesn't exist
            with open(config_path, "w") as f:
                json.dump({"client_id": "", "oauth": ""}, f)

        with open(config_path, "r") as f:
            config = json.load(f)
            return config
    except (IOError, json.JSONDecodeError) as e:
        log_error(e, context={"config_path": config_path})
        raise