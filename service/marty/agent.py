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
    "company/knowledge.md",
    "company/decisions.md",
    "company/brand.md",
    "company/icp.md",
    "company/open-questions.md",
    "marketing/strategy.md",
]

READ_TOOLS = [
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
]

WRITE_TOOL = {
    "name": "write_file",
    "description": (
        "Write a file to the strategy repo. This is how you make something permanent. "
        "Always read the file first and write it back whole. Writes are staged and "
        "pushed as one commit at the end, so calling this several times is cheap."
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
}

# Writes are only offered during the capture pass, never while answering.
REPO_TOOLS = READ_TOOLS + [WRITE_TOOL]

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
            "=== CAPTURING WHAT YOU LEARN ===",
            "",
            "Your memory of this conversation is temporary. The repo is permanent. "
            "Anything worth knowing next month has to be written to a file during "
            "this conversation or it is gone.",
            "",
            "Three places, and the distinction matters:",
            "",
            "- **company/knowledge.md** — a fact Brian or Patrick stated about the "
            "business, the product, the costs, the customers, or the market. They are "
            "the experts; you are not. Their facts outrank anything you found on the "
            "web. Add a dated, attributed row. When a fact supersedes an older one, "
            "strike the old row rather than deleting it — knowing something changed is "
            "information.",
            "- **company/decisions.md** — a call got made. Record what was decided, by "
            "whom, and *why*. The reason is the valuable part; in six months nobody "
            "remembers it and that is when a settled question gets relitigated. Mark "
            "PROPOSED when it is your call awaiting Brian, DECIDED when it is his.",
            "- **The relevant strategy doc** — when a new fact changes the plan. Do not "
            "just note the fact and leave a stale strategy behind it.",
            "",
            "**Answer the question first.** If Brian asked you something, the answer is "
            "the job and the logging is bookkeeping. Never leave him waiting while you "
            "file paperwork — decide what you think, then write. A question that also "
            "contains a new fact gets both, in that order, in one turn.",
            "",
            "Say you logged it in one short clause — 'Logged.' or 'Noted in decisions.' "
            "— at the end. Never narrate the write at length, and never make the write "
            "the whole reply.",
            "",
            "Do not log chatter, your own speculation, or anything you inferred rather "
            "than were told. A ledger full of guesses is worse than an empty one. If "
            "you are unsure whether something is a durable fact or a passing remark, "
            "ask in four words rather than logging it.",
            "",
            "If Brian says 'remember this' or 'log that', it goes in without asking.",
            "",
            "=== WHEN SOMETHING CHANGES ===",
            "",
            "A new fact that contradicts an old one is the highest-stakes thing that "
            "happens in this job. A name change, a price change, a new launch date, a "
            "pivot in positioning — logging it is not enough. Every file that carried "
            "the old fact is now wrong, and a strategy repo that contradicts itself is "
            "worse than no strategy repo.",
            "",
            "When Brian or Patrick changes something, work it in this order and finish "
            "it in the same conversation:",
            "1. Strike the old fact in company/knowledge.md, add the new one dated below it.",
            "2. Log the change in company/decisions.md with the reason. If it reverses "
            "an earlier decision, mark that one REVERSED rather than deleting it.",
            "3. **search_repo for the old value** — the old name, the old price, the old "
            "date. Every hit is a file that is now wrong.",
            "4. Rewrite each one. Not a note saying it changed — the actual text.",
            "5. Reconsider whether the change breaks any *reasoning*, not just any "
            "string. A new price changes the CAC math in pricing.md and the gates in "
            "paid-media.md. A new launch date rebuilds calendar.md. A new name may "
            "invalidate a domain, a handle, and the naming rationale. Say so.",
            "6. Report in one or two sentences: what you changed and what it broke.",
            "",
            "Then act on the new fact from that moment on. It outranks anything you "
            "previously believed, anything in these documents, and anything you found "
            "on the web. Brian and Patrick are the experts on this business. You are "
            "not, and you never argue from a stale document — though you should say so "
            "plainly if the change creates a problem they may not have seen.",
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
                self._commit_messages.append(args["commit_message"])
                return self.repo.stage(args["path"], args["content"]), False
            return f"Unknown tool: {name}", True
        except Exception as exc:  # noqa: BLE001
            log.warning("tool %s failed: %s", name, exc)
            return f"{type(exc).__name__}: {exc}", True

    # -- the loop ---------------------------------------------------------

    def respond(self, history: list[dict], on_tool=None, allow_writes: bool = False,
                effort: str | None = None) -> tuple[str, list[dict]]:
        """Run to completion. Returns (reply_text, updated_history).

        Writes are off by default. Every tool call is a full model round trip, so
        letting Marty file paperwork mid-answer added a minute per file while
        Brian watched a status line. Answering is the critical path; capture runs
        afterwards via capture().
        """
        self.repo.ensure()
        messages = list(history)
        tools = list(REPO_TOOLS if allow_writes else READ_TOOLS) + [WEB_SEARCH_TOOL]
        system = self.system_prompt()

        resumes = 0
        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                thinking={"type": "adaptive"},
                output_config={"effort": effort or EFFORT},
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

        reply = ""
        if messages and messages[-1]["role"] == "assistant":
            blocks = messages[-1]["content"]
            texts = []
            for b in blocks if isinstance(blocks, list) else []:
                kind = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
                if kind != "text":
                    continue
                text = b.get("text", "") if isinstance(b, dict) else getattr(b, "text", "")
                if text.strip():
                    texts.append(text)
            reply = "\n\n".join(texts)

        return reply or "(I got stuck on that one — try asking again.)", messages

    def capture(self, history: list[dict]) -> str | None:
        """Second pass, after the reply is sent. Records anything durable.

        Runs at low effort — deciding what to file is mechanical next to deciding
        what to think. Brian is not waiting on this.
        """
        self._commit_messages = []
        prompt = (
            "You have already replied to that message — it has been sent. Now record "
            "anything durable from the exchange, following the capture rules in your "
            "instructions.\n\n"
            "Read the file before you rewrite it, and write it back whole.\n\n"
            "If nothing in that exchange was a durable fact, a decision, or a change "
            "that makes a strategy document wrong, then do nothing at all and reply "
            "with exactly: NOTHING TO LOG.\n\n"
            "Do not log chatter, questions, or your own reasoning. Only what Brian or "
            "Patrick stated, what got decided, and what that breaks."
        )
        try:
            _, _ = self.respond(
                list(history) + [{"role": "user", "content": prompt}],
                allow_writes=True,
                effort="low",
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("capture pass failed")
            return f"FAILED: {type(exc).__name__}: {exc}"
        return self.publish()

    def publish(self) -> str | None:
        """Push whatever this turn staged. Called after the reply goes out."""
        messages = getattr(self, "_commit_messages", None) or []
        if not messages:
            return None
        try:
            return self.repo.publish(messages[0])
        except Exception as exc:  # noqa: BLE001
            log.exception("publish failed")
            return f"FAILED: {type(exc).__name__}: {exc}"
