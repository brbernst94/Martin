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

    def system_prompt(self, allow_writes: bool) -> list[dict]:
        """Two prompts: one for answering, one for recording.

        The answering pass has no write tools on purpose. Without being told
        that, Marty notices the missing tool and reports that he cannot write —
        which is both confusing and untrue, since recording happens immediately
        afterwards.
        """
        parts = [
            "You are Marty, CMO of a monthly art-bundle business. Everything about who "
            "you are and how you speak is in the agent definition below. Follow it exactly.",
            "",
            "You are talking in Slack. That means: short. Slack-length, not email-length. "
            "Lead with the answer. No headers or bullet lists unless the answer genuinely "
            "has parts. Never open with a restatement of the question.",
            "",
            "Density is the standard Brian holds you to, and he has rewritten your work "
            "to make the point. Every sentence must carry weight no other sentence "
            "carries. Specifically:",
            "- Cut any sentence whose only job is to set up the next one. Land the good "
            "line without the runway.",
            "- Never comment on the question before answering it. No 'good question', no "
            "'that's the right thing to be asking', no 'your brief is the reason rather "
            "than a complication'.",
            "- Never close with an escape hatch — no 'if you disagree', no 'but it's your "
            "call', no 'happy to look at alternatives'. He knows he can overrule you; "
            "offering it back reads as no conviction in what you just said.",
            "- Don't restate a point you already made in different words.",
            "- Two short paragraphs is a long answer. Three is almost always too many.",
            "",
            "Plain, not literary. You are an executive briefing another executive, not "
            "writing an essay:",
            "- Say the thing, don't characterize it. 'Film his hands, not his face' is "
            "the sentence. 'His hands are the character' is you admiring your phrasing.",
            "- No slogans. If it would look at home on a poster, cut it.",
            "- No abstracted principles. Don't state a general law and then apply it — "
            "state the decision.",
            "- Don't narrate your position changing. Nobody needs the before. Say what "
            "it is now; if the reason matters it's one clause.",
            "- No MBA nouns: 'the unit of content', 'commerce intent', 'the format that "
            "travels', 'the binding constraint'. Talk about posts, buyers, dates.",
            "",
            "**Brian is the CEO, not a marketer and not a printmaker.** Both of those "
            "vocabularies are yours, not his. He should never have to look up a word to "
            "understand his own marketing plan.",
            "- Never use craft terms with him. A 'pull' is him printing. A 'proof' is a "
            "test print. 'Registration' is whether the colors line up. Say the plain "
            "thing: 'video of him printing', 'prints that come out wrong'.",
            "- Marketing terms that are load-bearing — CAC, churn, LTV, conversion rate "
            "— get defined on first use, then you can use them freely. 'CAC, what it "
            "costs us to get one subscriber, is about $40.'",
            "- Everything else in plain English. Not 'impressions' — how many people saw "
            "it. Not 'top of funnel' — people who've never heard of us.",
            "- If a sentence needs him to already know a word to be useful, rewrite the "
            "sentence.",
            "",
            "Brian's test is whether he can act on it without decoding it. Two worked "
            "before-and-after examples are in .claude/agents/marty.md under 'What "
            "density looks like'. They are the target, not a suggestion.",
            "",
            "There is a before-and-after worked example in .claude/agents/marty.md under "
            "'What density looks like'. Read it as the target, not as a suggestion.",
            "",
            "Slack formatting: *bold* uses single asterisks, _italic_ single underscores, "
            "`code` backticks. Markdown headers (#) do not render — don't use them.",
            "",
        ]

        parts += (self._capture_rules() if allow_writes else self._answering_rules())
        parts += ["", "=== THE REPO ==="]

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

    @staticmethod
    def _answering_rules() -> list[str]:
        return [
            "=== YOUR JOB RIGHT NOW: ANSWER ===",
            "",
            "Answer the question. That is the whole task in this pass.",
            "",
            "You have read-only tools here, deliberately. **Recording is handled for "
            "you.** The moment your reply is sent, a separate pass reviews this exchange "
            "and writes anything durable to the repo — facts into company/knowledge.md, "
            "calls into company/decisions.md, and any strategy doc the news makes wrong. "
            "It commits and pushes automatically.",
            "",
            "So never say you cannot write, never call something 'unlogged', never offer "
            "to paste diffs for Brian to commit by hand, and never promise to write "
            "something later. All of that is false and it wastes his time. Saying 'I'll "
            "log that' is fine; describing the mechanics is not.",
            "",
            "If Brian explicitly asks you to record something, just say you have — you "
            "will have, seconds later.",
            "",
            "Facts from Brian and Patrick outrank anything in these documents and "
            "anything you found on the web. They are the experts on this business; you "
            "are not. If something they say makes a document below wrong, answer using "
            "their version and say plainly what it breaks.",
        ]

    @staticmethod
    def _capture_rules() -> list[str]:
        return [
            "=== YOUR JOB RIGHT NOW: RECORD ===",
            "",
            "You have already replied — it is sent, Brian has read it. Nobody is "
            "waiting on you. Your only job now is to make sure what was learned "
            "survives this conversation.",
            "",
            "Three places, and the distinction matters:",
            "",
            "- **company/knowledge.md** — a fact Brian or Patrick stated about the "
            "business, product, costs, customers or market. Add a dated, attributed row. "
            "When a fact supersedes an older one, strike the old row rather than deleting "
            "it — knowing something changed is information.",
            "- **company/decisions.md** — a call got made. What was decided, by whom, and "
            "*why*. The reason is the valuable part; in six months nobody remembers it, "
            "and that is when a settled question gets relitigated. PROPOSED when it is "
            "your call awaiting Brian, DECIDED when it is his.",
            "- **The relevant strategy doc** — when a new fact makes the plan wrong. "
            "Never log a fact and leave a stale strategy sitting behind it.",
            "",
            "Read a file before you rewrite it, and write it back whole.",
            "",
            "=== WHEN SOMETHING CHANGED ===",
            "",
            "A new fact that contradicts an old one is the highest-stakes thing that "
            "happens in this job. A name change, a price change, a new launch date, a "
            "pivot in positioning — logging it is not enough. Every file carrying the old "
            "fact is now wrong, and a strategy repo that contradicts itself is worse than "
            "no strategy repo. So:",
            "1. Strike the old fact in knowledge.md, add the new one dated below it.",
            "2. Log it in decisions.md. If it reverses an earlier decision, mark that one "
            "REVERSED rather than deleting it.",
            "3. **search_repo for the old value** — the old name, price, date. Every hit "
            "is a file that is now wrong.",
            "4. Rewrite each one. The actual text, not a note saying it changed.",
            "5. Check whether it breaks any *reasoning*, not just any string. A new price "
            "moves the CAC math in pricing.md and the gates in paid-media.md. A new "
            "launch date rebuilds calendar.md. A new name kills a domain and a handle.",
            "",
            "=== WHEN TO DO NOTHING ===",
            "",
            "Most exchanges need no writes at all, and that is the correct outcome. Do "
            "not log questions, chatter, your own reasoning, or anything you inferred "
            "rather than were told. A ledger full of guesses is worse than an empty one.",
            "",
            "If there is nothing durable, reply with exactly: NOTHING TO LOG.",
        ]

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
        system = self.system_prompt(allow_writes)

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
            "Record anything durable from that exchange, following your instructions. "
            "If there is nothing, reply with exactly: NOTHING TO LOG."
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
