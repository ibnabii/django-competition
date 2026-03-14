import yaml
from pathlib import Path
from ..models.config import Config  # import Pydantic model

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config(path: str | Path = None) -> Config:
    """
    Load Config instance from YAML file.
    If path is None, uses default config.yaml in project root.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(**data)  # validation happens automatically
