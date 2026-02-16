"""Agent Builder: Uses LangSmith and LangChain to build each agent from .cursor/agents specs.

Orchestrates building agents in dependency order:
  database-designer -> document-doctor -> validators -> orchestrator -> integrator -> legal-luminary

Each build step reads BUILD.md + PLAN.md, uses LangChain LLM to generate/validate code, traces to LangSmith.
"""

import os
import re
from pathlib import Path
from typing import TypedDict, Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "eli5" / ".env")

os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "AgentBuilder")


class BuilderState(TypedDict, total=False):
    agent_specs: dict[str, dict[str, str]]
    target_dir: Path
    built_agents: list[str]
    errors: list[str]


AGENT_ORDER = [
    "database-designer",
    "document-doctor",
    "validator",
    "orchestrator",
    "integrator",
    "legal-luminary",
]


def load_agent_spec(agent_dir: Path) -> dict[str, str]:
    build_md = agent_dir / "BUILD.md"
    plan_md = agent_dir / "PLAN.md"
    out: dict[str, str] = {}
    if build_md.exists():
        out["build"] = build_md.read_text()
    if plan_md.exists():
        out["plan"] = plan_md.read_text()
    return out


def load_all_specs(agents_dir: Path) -> dict[str, dict[str, str]]:
    specs: dict[str, dict[str, str]] = {}
    for name in AGENT_ORDER:
        agent_path = agents_dir / name
        if agent_path.is_dir():
            specs[name] = load_agent_spec(agent_path)
    return specs


def extract_build_tasks(build_content: str) -> list[str]:
    match = re.search(r"## Build tasks\s*\n\n(.*?)(?=\n## |\Z)", build_content, re.DOTALL)
    if not match:
        return []
    text = match.group(1)
    tasks = re.findall(r"[-*]\s+\*\*([^*]+)\*\*\s+(.+?)(?=\n[-*]\s+\*\*|\Z)", text, re.DOTALL)
    return [f"{t[0]}: {t[1].strip()}" for t in tasks]


def build_agent_with_llm(
    agent_name: str,
    build_content: str,
    plan_content: str,
    target_base: Path,
    use_llm: bool = True,
) -> tuple[bool, str]:
    """Generate or validate agent code from spec. Returns (success, message)."""
    if not use_llm:
        tasks = extract_build_tasks(build_content)
        return True, f"Dry-run: {agent_name} has {len(tasks)} build tasks"

    try:
        from langchain_ollama import ChatOllama
        from langsmith import traceable

        @traceable(name=f"build_{agent_name}")
        def _generate() -> str:
            base_url = os.environ.get("OLLAMA_BASE_URL")
            llm = ChatOllama(
                model="granite-code:4b",
                base_url=base_url if base_url else None,
                temperature=0,
            )
            prompt = f"""You are building the {agent_name} agent for Legal Luminary.

BUILD.md excerpt:
{build_content[:3000]}

PLAN.md excerpt:
{plan_content[:2000] if plan_content else 'N/A'}

Output a brief implementation checklist (bullet points) for this agent. No code.
Focus on: 1) inputs/outputs 2) key functions 3) LangGraph nodes if applicable."""
            return llm.invoke(prompt).content

        checklist = _generate()
        out_dir = target_base / agent_name.replace("-", "_")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "IMPLEMENTATION_CHECKLIST.md").write_text(checklist)
        return True, f"Wrote checklist to {out_dir}/IMPLEMENTATION_CHECKLIST.md"
    except Exception as e:
        return False, str(e)


def run_builder(
    agents_dir: Path,
    target_dir: Path,
    use_llm: bool = True,
) -> BuilderState:
    state: BuilderState = {
        "agent_specs": {},
        "target_dir": target_dir,
        "built_agents": [],
        "errors": [],
    }
    specs = load_all_specs(agents_dir)
    state["agent_specs"] = {k: v for k, v in specs.items()}

    for agent_name in AGENT_ORDER:
        if agent_name not in specs or not specs[agent_name]:
            continue
        build_content = specs[agent_name].get("build", "")
        plan_content = specs[agent_name].get("plan", "")
        ok, msg = build_agent_with_llm(
            agent_name, build_content, plan_content, target_dir, use_llm=use_llm
        )
        if ok:
            state.setdefault("built_agents", []).append(agent_name)
            print(f"  [OK] {agent_name}: {msg}")
        else:
            state.setdefault("errors", []).append(f"{agent_name}: {msg}")
            print(f"  [ERR] {agent_name}: {msg}")

    return state


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build agents from .cursor/agents specs")
    parser.add_argument(
        "--agents-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / ".cursor" / "agents",
        help="Path to .cursor/agents",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(__file__).parent / "legal-luminary" / "generated",
        help="Output directory for generated artifacts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate specs only, no LLM calls",
    )
    args = parser.parse_args()

    if not args.agents_dir.exists():
        print(f"Agents dir not found: {args.agents_dir}")
        return

    print("Agent Builder — LangSmith + LangChain")
    print("=" * 50)
    print(f"Agents dir: {args.agents_dir}")
    print(f"Target: {args.target}")
    print(f"Mode: {'dry-run' if args.dry_run else 'LLM'}")
    print("")

    state = run_builder(args.agents_dir, args.target, use_llm=not args.dry_run)

    print("")
    print(f"Built: {state.get('built_agents', [])}")
    if state.get("errors"):
        print(f"Errors: {state['errors']}")


if __name__ == "__main__":
    main()
