"""Marty's agent loop: Claude + repo tools + web search."""
from __future__ import annotations

import json
import logging
import os

import anthropic

from .repo import Repo

log = logging.getLogger("marty.agent")

MODEL = os.environ.get("MARTY_MODEL", "claude-opus-5")
EFFORT = os.environ.get("MARTY_EFFORT", "high")
MAX_TOKENS = 16000
MAX_TURNS = 20
MAX_PAUSE_RESUMES = 5

# Loaded into every system prompt so Marty always argues from the real plan.
CORE_DOCS = [
    ".claude/agents/marty.md",
    "company/business-brief.md",
    "company/brand.md",
    "company/icp.md",
    "company/open-questions.md",
    "marketing/strategy.md",
]

REPO_TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Read a file from the strategy repo. Use this before answering anything "
            "that the repo already has a position on, and always before rewriting a file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Repo-relative path, e.g. marketing/channels.md"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_files",
        "description": "List files in the strategy repo, optionally under a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {"subdir": {"type": "string", "description": "Optional subdirectory, e.g. marketing/competitors"}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_repo",
        "description": "Case-insensitive search across the repo. Returns path:line:text.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write a file to the strategy repo and push the commit. This is how you make a "
            "decision permanent. Always read the file first and write it back whole. The "
            "commit message states the decision, not the file list."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Full new contents of the file."},
                "commit_message": {"type": "string", "description": "One line, states the decision."},
            },
            "required": ["path", "content", "commit_message"],
            "additionalProperties": False,
        },
    },
]

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 8,
}


class Marty:
    def __init__(self, repo: Repo) -> None:
        self.repo = repo
        self.client = anthropic.Anthropic()

    # -- prompt -----------------------------------------------------------

    def system_prompt(self) -> list[dict]:
        parts = [
            "You are Marty, CMO of a monthly art-bundle business. Everything about who "
            "you are and how you speak is in the agent definition below. Follow it exactly.",
            "",
            "You are talking in Slack. That means: short. Slack-length, not email-length. "
            "Lead with the answer. No headers or bullet lists unless the answer genuinely "
            "has parts. Never open with a restatement of the question.",
            "",
            "Slack formatting: *bold* uses single asterisks, _italic_ single underscores, "
            "`code` backticks. Markdown headers (#) do not render — don't use them.",
            "",
            "When you change your mind about something in the repo, write the file. A "
            "decision that only exists in a Slack message is not a decision.",
            "",
            "=== THE REPO ===",
        ]
        try:
            parts.append("\n".join(self.repo.tree()))
        except Exception as exc:  # noqa: BLE001
            parts.append(f"(file listing unavailable: {exc})")

        for path in CORE_DOCS:
            try:
                parts += ["", f"=== {path} ===", self.repo.read(path, max_chars=20_000)]
            except Exception as exc:  # noqa: BLE001
                parts.append(f"\n=== {path} === (unreadable: {exc})")

        # One cached block: this prefix is identical across turns, so it caches.
        return [{"type": "text", "text": "\n".join(parts), "cache_control": {"type": "ephemeral"}}]

    # -- tools ------------------------------------------------------------

    def run_tool(self, name: str, args: dict) -> tuple[str, bool]:
        """Returns (result_text, is_error)."""
        try:
            if name == "read_file":
                return self.repo.read(args["path"]), False
            if name == "list_files":
                return "\n".join(self.repo.tree(args.get("subdir", ""))), False
            if name == "search_repo":
                hits = self.repo.grep(args["pattern"])
                return "\n".join(hits) if hits else "No matches.", False
            if name == "write_file":
                return self.repo.write_and_commit(
                    args["path"], args["content"], args["commit_message"]
                ), False
            return f"Unknown tool: {name}", True
        except Exception as exc:  # noqa: BLE001
            log.warning("tool %s failed: %s", name, exc)
            return f"{type(exc).__name__}: {exc}", True

    # -- the loop ---------------------------------------------------------

    def respond(self, history: list[dict], on_tool=None) -> tuple[str, list[dict]]:
        """Run to completion. Returns (reply_text, updated_history)."""
        self.repo.ensure()
        messages = list(history)
        tools = REPO_TOOLS + [WEB_SEARCH_TOOL]
        system = self.system_prompt()

        resumes = 0
        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                thinking={"type": "adaptive"},
                output_config={"effort": EFFORT},
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "refusal":
                detail = getattr(response, "stop_details", None)
                reason = getattr(detail, "explanation", None) or "no explanation given"
                return f"I can't answer that one. ({reason})", messages

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                resumes += 1
                if resumes > MAX_PAUSE_RESUMES:
                    break
                continue

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                break

            results = []
            for block in tool_uses:
                if on_tool:
                    on_tool(block.name, block.input)
                text, is_error = self.run_tool(block.name, dict(block.input))
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text or "(empty)",
                    "is_error": is_error,
                })
            messages.append({"role": "user", "content": results})
        else:
            log.warning("hit MAX_TURNS without finishing")

        reply = "\n\n".join(
            b.text for b in messages[-1]["content"]
            if getattr(b, "type", None) == "text" and getattr(b, "text", "").strip()
        ) if messages and messages[-1]["role"] == "assistant" else ""

        return reply or "(I got stuck on that one — try asking again.)", messages
