#!/usr/bin/env bash
# Install all skills from .claude/skills/ to the global ~/.claude/skills/ directory.
# Uses symlinks so updates to the source are reflected globally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_SKILLS="$SCRIPT_DIR/.claude/skills"
GLOBAL_SKILLS="$HOME/.claude/skills"

if [ ! -d "$LOCAL_SKILLS" ]; then
    echo "No skills found in $LOCAL_SKILLS"
    exit 1
fi

mkdir -p "$GLOBAL_SKILLS"

for skill_dir in "$LOCAL_SKILLS"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    target="$GLOBAL_SKILLS/$skill_name"

    if [ -L "$target" ]; then
        echo "Updating symlink: $skill_name"
        rm "$target"
    elif [ -e "$target" ]; then
        echo "Skipping $skill_name (already exists as non-symlink, remove manually to override)"
        continue
    else
        echo "Installing: $skill_name"
    fi

    ln -s "$skill_dir" "$target"
done

echo "Done. All skills in $GLOBAL_SKILLS (may include skills from other sources):"
ls -l "$GLOBAL_SKILLS"/
