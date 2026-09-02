from __future__ import annotations

import os


def demo_mode_enabled() -> bool:
    return os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def openai_explanation_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
