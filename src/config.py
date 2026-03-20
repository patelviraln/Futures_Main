"""Configuration loader for Futures_Main project."""

import os
import yaml


def load_config(path=None):
    """Load configuration from a YAML file.

    Args:
        path: Path to config file. If None, looks for 'config.yaml' in the
              project root (parent of src/).

    Returns:
        dict with configuration values.
    """
    if path is None:
        # Default: config.yaml in the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(project_root, "config.yaml")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve relative paths to absolute based on project root
    project_root = os.path.dirname(os.path.abspath(path))
    for key in ("data_dir", "output_dir"):
        val = config.get(key, "")
        if val and not os.path.isabs(val):
            config[key] = os.path.join(project_root, val)

    return config
