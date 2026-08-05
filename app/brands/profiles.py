"""
Brand profile loader.

Each brand has an isolated profile (colors, logo, language, voice prompt,
reference image set). Services always resolve the active brand first, then pull
that brand's settings. Brand identities must never bleed into one another:
FieldPie outputs are American English, Evatro outputs are Turkish.

Phase 0 (current): thin dataclass + YAML loader so the structure is fixed. The
YAML files under app/brands/*.yaml are the source of truth for brand config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_BRANDS_DIR = Path(__file__).parent


@dataclass
class BrandProfile:
    """A single brand's identity and generation settings."""

    key: str
    name: str
    language: str  # e.g. "en-US" or "tr-TR"
    solutions: list[str]
    colors: dict[str, str]
    voice_prompt: str
    reference_set_path: str
    logo_path: str = ""
    extra: dict = field(default_factory=dict)


def load_brand(key: str) -> BrandProfile:
    """Load a brand profile by key ('fieldpie' or 'evatro')."""
    path = _BRANDS_DIR / f"{key}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown brand '{key}': {path} not found")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return BrandProfile(
        key=data["key"],
        name=data["name"],
        language=data["language"],
        solutions=data.get("solutions", []),
        colors=data.get("colors", {}),
        voice_prompt=data.get("voice_prompt", ""),
        reference_set_path=data.get("reference_set_path", ""),
        logo_path=data.get("logo_path", ""),
        extra=data.get("extra", {}),
    )
