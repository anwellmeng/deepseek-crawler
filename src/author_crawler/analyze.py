from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from .config import (
    FAILED_JSONS_DIR,
    FINISHED_SITES_DIR,
    JSONS_DIR,
    LOGS_DIR,
    SKIPPED_SITES_DIR,
    TO_ANALYZE_DIR,
)

SYSTEM_PROMPT = """You extract contact info from scraped author-website Markdown.

INPUT: One Markdown string (may contain multiple pages). Links may be absolute or relative. Emails may be obfuscated (e.g., "name [at] domain [dot] com", "name(at)domain(dot)com", "name at domain dot com"), include spaces, or zero-width chars.

TASK: Find
1) author email addresses
2) links to a contact form

OUTPUT: Return ONLY a single JSON object (no code fences, no prose):
{"emails":[...],"contact_links":[...]}

RULES
- Always include both keys; if none, use empty arrays.
- Do not guess or invent data.
- Deduplicate. Priority order: author > agent/publicist > publisher/booking.
- Exclude: newsletter signups, press kits, social DMs, RSS, generic support portals.
- No extra prose in your response.

EMAILS
- Accept from visible text and mailto:.
- Normalize: lowercase; replace [at]/(at)/" at " -> "@"; [dot]/(dot)/" dot " -> "."; remove spaces/zero-width.
- Validate simple pattern: local@domain.tld, tld 2-24 letters.
- Discard obvious decoys like example@example.com.

CONTACT FORMS
- Include pages that host a contact form or clearly instruct submitting a message.
- Prefer on-site forms; if none, include reputable off-site forms used by the author (Typeform, Google Forms).
- Do NOT count mailto: as a contact form.
- If a <form> action is shown, include the PAGE URL containing it.
- If a base URL is present in the Markdown (e.g., "Source: https://site.com/page"), resolve relative paths against it; otherwise return the relative path.

END: Output exactly the JSON object per schema above.
"""

LIMIT = 122_000

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def count_tokens(text: str) -> int:
    if _ENC:
        return len(_ENC.encode(text))
    return int(len(text) / 4)


def unique_name(target_dir: Path, base: str, suffix: str) -> Path:
    candidate = target_dir / f"{base}{suffix}"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = target_dir / f"{base}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def get_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return OpenAI(base_url=base_url, api_key=api_key)


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "run_log.txt"
    sys.stdout = log_path.open("a", encoding="utf-8")
    sys.stderr = sys.stdout
    print("\n--- New run started ---")


def process_file(file: Path, client: OpenAI) -> None:
    md = file.read_text(encoding="utf-8")
    tok = count_tokens(md)

    if tok > LIMIT:
        SKIPPED_SITES_DIR.mkdir(parents=True, exist_ok=True)
        skipped_path = unique_name(SKIPPED_SITES_DIR, f"{file.stem}_SKIPPED", file.suffix)
        file.rename(skipped_path)
        print(f"Skipped (tokens={tok}): {skipped_path}")
        return

    completion = client.chat.completions.create(
        model="meituan/longcat-flash-chat:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": md},
        ],
    )

    result = completion.choices[0].message.content
    try:
        json.loads(result)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON for {file.name}: {exc}")
        FAILED_JSONS_DIR.mkdir(parents=True, exist_ok=True)
        file.rename(FAILED_JSONS_DIR / file.name)
        return

    JSONS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = JSONS_DIR / f"{file.stem}.json"
    output_path.write_text(result, encoding="utf-8")

    FINISHED_SITES_DIR.mkdir(parents=True, exist_ok=True)
    finished_path = unique_name(FINISHED_SITES_DIR, file.stem, file.suffix)
    file.rename(finished_path)
    print(f"Moved to finished_sites: {finished_path}")


def main() -> int:
    if not TO_ANALYZE_DIR.exists():
        print(f"Error: {TO_ANALYZE_DIR} directory not found")
        return 1

    try:
        client = get_client()
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    configure_logging()

    for file in TO_ANALYZE_DIR.glob("*.md"):
        process_file(file, client)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
