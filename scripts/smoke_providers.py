"""
Manual smoke test for the AI provider layer.

Run this locally with real API keys in your .env to confirm each provider works
end-to-end. It is NOT part of automated tests (it makes paid API calls).

Usage:
    python -m scripts.smoke_providers --text
    python -m scripts.smoke_providers --gemini
    python -m scripts.smoke_providers --openai
    python -m scripts.smoke_providers --all

Images are written to ./generated/ (gitignored).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.providers.factory import get_text_provider
from app.providers.gemini import GeminiImageProvider
from app.providers.openai_image import OpenAIImageProvider

OUT = Path("generated")


def _save(name: str, data: bytes) -> None:
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    path.write_bytes(data)
    print(f"  wrote {path} ({len(data)} bytes)")


def test_text() -> None:
    print("[text] Claude...")
    provider = get_text_provider()
    out = provider.generate(
        "Write one short, scroll-stopping FieldPie headline about retail "
        "shelf audits. Return only the headline.",
        max_tokens=64,
    )
    print(f"  -> {out!r}")


def test_gemini() -> None:
    print("[image] Gemini (gemini-3-pro-image)...")
    data = GeminiImageProvider().generate(
        "A clean modern SaaS marketing image, teal accent, white background, "
        "the words 'Shelf Audits' in a rounded teal pill."
    )
    _save("gemini_test.png", data)


def test_openai() -> None:
    print("[image] OpenAI (gpt-image, fallback)...")
    data = OpenAIImageProvider().generate(
        "A clean modern SaaS marketing image, teal accent, white background."
    )
    _save("openai_test.png", data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", action="store_true")
    parser.add_argument("--gemini", action="store_true")
    parser.add_argument("--openai", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all or args.text:
        test_text()
    if args.all or args.gemini:
        test_gemini()
    if args.all or args.openai:
        test_openai()
    if not any([args.text, args.gemini, args.openai, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
