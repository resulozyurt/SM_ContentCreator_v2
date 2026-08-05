"""
Model-agnostic AI provider layer.

Every provider (Claude for text, Gemini for images, OpenAI as image fallback)
sits behind a single interface (see base.py). Swapping or upgrading a model
should touch one file only. Implemented in Phase 2.
"""
