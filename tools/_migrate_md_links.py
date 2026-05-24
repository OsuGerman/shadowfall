"""One-shot migration: rewrite md cross-refs after docs/-restructure (2026-05-24).

For each target file we know its containing directory; we substitute every
bare filename (with \b boundaries) or markdown-link pointing at a known
.md by the correctly relative path from the file's own directory.

Files in `_legacy/` and `docs/meta/CHANGELOG.md` are skipped per spec.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Map filename -> new absolute (project-relative) location.
FILE_MAP: dict[str, str] = {
    # meta
    "CHANGELOG.md": "docs/meta/CHANGELOG.md",
    "canis_velocipes_philosophy.md": "docs/meta/canis_velocipes_philosophy.md",
    # project-mgmt
    "PLAN.md": "docs/project-mgmt/PLAN.md",
    "ROADMAP.md": "docs/project-mgmt/ROADMAP.md",
    "WELT_AUFBAU.md": "docs/project-mgmt/WELT_AUFBAU.md",
    # gameplay
    "POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md": "docs/gameplay/POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md",
    "POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md": "docs/gameplay/POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md",
    "VELGRAD_BESTIARIUM.md": "docs/gameplay/VELGRAD_BESTIARIUM.md",
    "VELGRAD_ITEMS_UNIQUE_BIBEL.md": "docs/gameplay/VELGRAD_ITEMS_UNIQUE_BIBEL.md",
    # lore
    "VELGRAD_LORE_BIBEL.md": "docs/lore/VELGRAD_LORE_BIBEL.md",
    "QUEST_BIBEL.md": "docs/lore/QUEST_BIBEL.md",
    # design
    "VELGRAD_RENDER_SPEC.md": "docs/design/VELGRAD_RENDER_SPEC.md",
    "VELGRAD_AUDIO_DESIGN_BIBEL.md": "docs/design/VELGRAD_AUDIO_DESIGN_BIBEL.md",
    "VELGRAD_SFX_BIBEL.md": "docs/design/VELGRAD_SFX_BIBEL.md",
    "VELGRAD_VOICE_LINES_POOL.md": "docs/design/VELGRAD_VOICE_LINES_POOL.md",
    # design legacy
    "VELGRAD_SPRITE_BIBEL.md": "docs/design/_legacy/VELGRAD_SPRITE_BIBEL.md",
    "VELGRAD_VOICE_CASTING.md": "docs/design/_legacy/VELGRAD_VOICE_CASTING.md",
    "VELGRAD_WORKFLOWS_BIBEL.md": "docs/design/_legacy/VELGRAD_WORKFLOWS_BIBEL.md",
}

# Files we should rewrite. Tuple of (project-relative path, containing dir).
TARGETS: list[str] = [
    "README.md",
    "docs/project-mgmt/PLAN.md",
    "docs/project-mgmt/ROADMAP.md",
    "docs/project-mgmt/WELT_AUFBAU.md",
    "docs/lore/QUEST_BIBEL.md",
    "docs/design/VELGRAD_RENDER_SPEC.md",
    "docs/design/VELGRAD_AUDIO_DESIGN_BIBEL.md",
    "docs/design/VELGRAD_SFX_BIBEL.md",
    "docs/gameplay/POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md",
    "docs/gameplay/VELGRAD_BESTIARIUM.md",
]


def relpath_from(file_rel: str, target_abs_rel: str) -> str:
    """Return POSIX-style relative path from the directory of *file_rel* to *target_abs_rel*."""
    src_dir = Path(file_rel).parent
    rel = os.path.relpath(target_abs_rel, start=str(src_dir) if str(src_dir) else ".")
    return rel.replace("\\", "/")


# Patterns:
#   [text](FILE.md)             markdown link, optional anchor
#   [text](./FILE.md)
#   [text](../some/FILE.md)     -- only rewrite when basename matches and current ref clearly wrong
#   bare FILE.md                -- word-boundary, no leading `(` from a link or `/`
def rewrite_file(file_rel: str) -> tuple[int, list[str]]:
    path = ROOT / file_rel
    text = path.read_text(encoding="utf-8")
    original = text
    notes: list[str] = []
    replacements = 0

    # 1) Markdown links: [text](path/maybe/FILE.md#anchor)
    md_link_re = re.compile(r"(\]\()([^)\s#]+?)(#[^)\s]+)?(\))")

    def md_link_sub(m: re.Match[str]) -> str:
        nonlocal replacements
        prefix, link, anchor, suffix = m.group(1), m.group(2), m.group(3) or "", m.group(4)
        # Skip absolute URLs
        if re.match(r"^[a-zA-Z]+://", link) or link.startswith("mailto:"):
            return m.group(0)
        # Only care about .md targets
        if not link.lower().endswith(".md"):
            return m.group(0)
        basename = link.rsplit("/", 1)[-1]
        if basename not in FILE_MAP:
            return m.group(0)
        new_target = FILE_MAP[basename]
        new_rel = relpath_from(file_rel, new_target)
        if link == new_rel:
            return m.group(0)
        replacements += 1
        return f"{prefix}{new_rel}{anchor}{suffix}"

    text = md_link_re.sub(md_link_sub, text)

    # 2) Bare mentions: FILENAME.md not part of a link/url/path component.
    #    We use word-boundary; we must not match the basename when it's already
    #    inside a path like docs/lore/X.md.
    for fname, new_target in FILE_MAP.items():
        new_rel = relpath_from(file_rel, new_target)
        # Negative-lookbehind: not preceded by '/', '\\', or '('
        pat = re.compile(rf"(?<![\w/\\(]){re.escape(fname)}\b")
        # Replacement function so we can count and avoid re-replacing where ref is already correct.
        def sub(m: re.Match[str], _new=new_rel) -> str:
            nonlocal replacements
            replacements += 1
            return _new
        # Apply
        text, n = pat.subn(sub, text)

    if text != original:
        path.write_text(text, encoding="utf-8")
    return replacements, notes


def prepend_changelog_notice() -> bool:
    chl = ROOT / "docs/meta/CHANGELOG.md"
    text = chl.read_text(encoding="utf-8")
    marker = "Pfad-Hinweis (2026-05-24)"
    if marker in text:
        return False
    block = (
        "---\n\n"
        "> **📁 Pfad-Hinweis (2026-05-24):** Die .md-Files wurden in eine `docs/`-Struktur sortiert.\n"
        "> Datei-Referenzen in diesem Changelog zeigen historisch auf die ursprünglichen Root-Pfade.\n"
        "> Aktuelle Lage:\n"
        "> - Lore/Quests: `docs/lore/`\n"
        "> - Gameplay/Skills/Bestiarium/Items: `docs/gameplay/`\n"
        "> - Design/Audio/SFX/Voice: `docs/design/` (Legacy in `docs/design/_legacy/`)\n"
        "> - Plan/Roadmap/Welt-Aufbau: `docs/project-mgmt/`\n"
        "> - Philosophy/Changelog: `docs/meta/`\n\n"
        "---\n\n"
    )
    chl.write_text(block + text, encoding="utf-8")
    return True


def main() -> None:
    summary: list[tuple[str, int]] = []
    for f in TARGETS:
        n, _notes = rewrite_file(f)
        summary.append((f, n))
    notice = prepend_changelog_notice()
    print("=== migration summary ===")
    for f, n in summary:
        print(f"  {n:4d}  {f}")
    print(f"  changelog notice prepended: {notice}")


if __name__ == "__main__":
    main()
