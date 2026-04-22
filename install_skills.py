#!/usr/bin/env python3
"""Install local skills into supported AI agent skill directories."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = REPO_ROOT / "agents.json"
DEFAULT_SOURCE = REPO_ROOT / "skills"
REQUIRED_AGENT_FIELDS = ("display_name", "home_env", "default_home", "skills_subdir")


@dataclass(frozen=True)
class Agent:
    agent_id: str
    display_name: str
    home_env: str
    default_home: str
    skills_subdir: str
    enabled: bool = True

    @property
    def home(self) -> Path:
        configured_home = os.environ.get(self.home_env) or self.default_home
        return Path(configured_home).expanduser()

    @property
    def target_dir(self) -> Path:
        return self.home / self.skills_subdir


@dataclass
class InstallStats:
    installed: int = 0
    updated: int = 0
    skipped: int = 0
    missing: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install repository skills into supported agent skill directories."
    )
    parser.add_argument(
        "--agent",
        action="append",
        dest="agents",
        help="Install only this agent. Repeat to install multiple agents.",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List supported agents from agents.json and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without creating directories or symlinks.",
    )
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        type=Path,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def load_agents(manifest_path: Path) -> dict[str, Agent]:
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: manifest not found: {manifest_path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"ERROR: invalid JSON in {manifest_path}: {error}") from None

    raw_agents = manifest.get("agents")
    if not isinstance(raw_agents, dict):
        raise SystemExit("ERROR: agents.json must contain an 'agents' object")

    agents: dict[str, Agent] = {}
    for agent_id, config in raw_agents.items():
        if not isinstance(config, dict):
            raise SystemExit(f"ERROR: agent '{agent_id}' must be an object")

        missing_fields = [
            field for field in REQUIRED_AGENT_FIELDS if field not in config
        ]
        if missing_fields:
            fields = ", ".join(missing_fields)
            raise SystemExit(f"ERROR: agent '{agent_id}' missing fields: {fields}")

        agents[agent_id] = Agent(
            agent_id=agent_id,
            display_name=str(config["display_name"]),
            home_env=str(config["home_env"]),
            default_home=str(config["default_home"]),
            skills_subdir=str(config["skills_subdir"]),
            enabled=bool(config.get("enabled", True)),
        )

    return agents


def discover_skills(source_dir: Path) -> list[Path]:
    if not source_dir.is_dir():
        raise SystemExit(f"ERROR: skills source directory not found: {source_dir}")

    return sorted(
        child
        for child in source_dir.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    )


def select_agents(
    agents: dict[str, Agent], selected_ids: list[str] | None
) -> list[Agent]:
    if not selected_ids:
        return [agent for agent in agents.values() if agent.enabled]

    selected: list[Agent] = []
    unknown = [agent_id for agent_id in selected_ids if agent_id not in agents]
    if unknown:
        known = ", ".join(sorted(agents))
        raise SystemExit(
            f"ERROR: unknown agent(s): {', '.join(unknown)}. Known agents: {known}"
        )

    seen: set[str] = set()
    for agent_id in selected_ids:
        if agent_id in seen:
            continue
        selected.append(agents[agent_id])
        seen.add(agent_id)
    return selected


def relative_target(source: Path, link_path: Path) -> str:
    return os.path.relpath(source, start=link_path.parent)


def install_skill(agent: Agent, skill_dir: Path, dry_run: bool) -> str:
    target_dir = agent.target_dir
    target = target_dir / skill_dir.name
    link_target = relative_target(skill_dir, target)

    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    if target.is_symlink():
        current = os.readlink(target)
        if current == link_target:
            print(f"  ok: {skill_dir.name} -> {current}")
            return "skipped"

        print(f"  update: {skill_dir.name} -> {link_target}")
        if not dry_run:
            target.unlink()
            target.symlink_to(link_target)
        return "updated"

    if target.exists():
        print(f"  skip: {skill_dir.name} already exists as non-symlink")
        return "skipped"

    print(f"  install: {skill_dir.name} -> {link_target}")
    if not dry_run:
        target.symlink_to(link_target)
    return "installed"


def install_agent(agent: Agent, skills: list[Path], dry_run: bool) -> InstallStats:
    stats = InstallStats()
    mode = "dry run" if dry_run else "install"
    print(f"{agent.display_name} ({agent.agent_id}) [{mode}]")
    print(f"  target: {agent.target_dir}")

    if not skills:
        print("  no skills found")
        stats.missing += 1
        print(
            "  summary: "
            f"installed={stats.installed}, "
            f"updated={stats.updated}, "
            f"skipped={stats.skipped}, "
            f"missing={stats.missing}"
        )
        return stats

    for skill_dir in skills:
        result = install_skill(agent, skill_dir, dry_run)
        if result == "installed":
            stats.installed += 1
        elif result == "updated":
            stats.updated += 1
        else:
            stats.skipped += 1

    print(
        "  summary: "
        f"installed={stats.installed}, "
        f"updated={stats.updated}, "
        f"skipped={stats.skipped}, "
        f"missing={stats.missing}"
    )
    return stats


def list_agents(agents: dict[str, Agent]) -> None:
    for agent_id in sorted(agents):
        agent = agents[agent_id]
        status = "enabled" if agent.enabled else "disabled"
        home_env = agent.home_env or "-"
        print(
            f"{agent.agent_id}\t{agent.display_name}\t{status}\t"
            f"{home_env}\t{agent.default_home}/{agent.skills_subdir}"
        )


def main() -> int:
    args = parse_args()
    agents = load_agents(args.manifest)

    if args.list_agents:
        list_agents(agents)
        return 0

    skills = discover_skills(args.source)
    selected_agents = select_agents(agents, args.agents)
    if not selected_agents:
        print("No enabled agents selected.")
        return 0

    totals = InstallStats()
    for index, agent in enumerate(selected_agents):
        if index:
            print()
        stats = install_agent(agent, skills, args.dry_run)
        totals.installed += stats.installed
        totals.updated += stats.updated
        totals.skipped += stats.skipped
        totals.missing += stats.missing

    print()
    print(
        "Done. "
        f"Installed: {totals.installed}, "
        f"updated: {totals.updated}, "
        f"skipped: {totals.skipped}, "
        f"missing: {totals.missing}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
