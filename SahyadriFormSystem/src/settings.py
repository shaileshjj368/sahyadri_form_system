"""User-editable settings, stored as `settings.json` beside the app.

The file is created with defaults on first run. Anyone can open it in
Notepad to change the handwriting look or the speech engine; unknown or
invalid values fall back to the defaults, so a typo never stops the app.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Settings:
    # --- PDF handwriting ---------------------------------------------------
    handwriting: bool = True          # False = previous printed (Noto Sans) look
    handwriting_weight: str = 'regular'   # 'regular' (ballpoint) or 'bold' (marker)
    ink_color: str = '#1c3096'        # ballpoint blue
    handwriting_wobble: bool = True   # tiny per-word baseline variation

    # --- Speech-to-text ----------------------------------------------------
    # 'online'  : Google speech recognition (needs internet; fast and accurate)
    # 'auto'    : online, and the offline model only if there is no internet
    # 'offline' : bundled offline model only
    speech_engine: str = 'online'
    speech_language: str = 'mr-IN'
    # Optional: a Google Cloud Speech-to-Text API key. When set, the official
    # Cloud API is used instead of the free Google web speech service.
    google_cloud_api_key: str = ''

    @classmethod
    def load(cls, path: Path) -> 'Settings':
        settings = cls()
        try:
            raw = json.loads(Path(path).read_text(encoding='utf-8'))
        except FileNotFoundError:
            settings.save(path)
            return settings
        except Exception:
            return settings
        valid = {f.name: f.type for f in fields(cls)}
        for key, value in (raw or {}).items():
            if key in valid and isinstance(value, type(getattr(settings, key))):
                setattr(settings, key, value)
        if settings.speech_engine not in ('online', 'auto', 'offline'):
            settings.speech_engine = 'online'
        if settings.handwriting_weight not in ('regular', 'bold'):
            settings.handwriting_weight = 'regular'
        return settings

    def save(self, path: Path) -> None:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                                  encoding='utf-8')
        except Exception:
            pass

    def ink_rgb(self) -> tuple[int, int, int]:
        value = (self.ink_color or '').strip().lstrip('#')
        try:
            if len(value) == 6:
                return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            pass
        return (28, 48, 150)
