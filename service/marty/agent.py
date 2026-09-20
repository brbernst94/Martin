"""Marty's agent loop: Claude + repo tools + web search."""
from __future__ import annotations

import json
import logging
import os

import anthropic

from .repo import Repo

log = logging.getLogger("marty.agent")

MODEL = os.environ.get("MARTY_MODEL", "claude-opus-5")
# Capture is bookkeeping, not judgment — deciding what to file is much easier
# than deciding what to think. Opus for both roughly doubled the bill.
CAPTURE_MODEL = os.environ.get("MARTY_CAPTURE_MODEL", "claude-sonnet-5")
# One cheap call decides whether the capture pass runs at all. Most exchanges
# contain nothing durable, and skipping them skips a whole tool loop.
GATE_MODEL = os.environ.get("MARTY_GATE_MODEL", "claude-haiku-4-5")
EFFORT = os.environ.get("MARTY_EFFORT", "high")
MAX_TOKENS = 16000
MAX_TURNS = 20
MAX_PAUSE_RESUMES = 5

# $ per million tokens, for the cost line in the logs. Cache reads are a tenth
# of input; cache writes are 1.25x.
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def _cost(model: str, usage) -> float:
    inp, out = PRICES.get(model, PRICES["claude-opus-5"])
    fresh = getattr(usage, "input_tokens", 0) or 0
    write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    output = getattr(usage, "output_tokens", 0) or 0
    return (fresh * inp + write * inp * 1.25 + read * inp * 0.1 + output * out) / 1_000_000

# Loaded into every system prompt so Marty always argues from the real plan.
# Preloaded into every prompt. Everything else he reads on demand — preloading
# eight documents cost ~14k tokens on every single API call, and a tool loop
# makes several per exchange.
CORE_DOCS = [
    ".claude/agents/marty.md",      # who he is and how he talks
    "company/business-brief.md",    # what the business is
    "company/knowledge.md",         # what Brian and Patrick have told him
]

# Named so he knows to go read them rather than guessing.
ON_DEMAND_DOCS = [
    "company/decisions.md", "company/brand.md", "company/icp.md",
    "company/open-questions.md", "company/naming.md", "company/glossary.md",
    "marketing/strategy.md", "marketing/channels.md", "marketing/pricing.md",
    "marketing/calendar.md", "marketing/guerrilla.md", "marketing/retention.md",
    "marketing/paid-media.md", "marketing/experiments.md",
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

    def audience_rules(self, speaker: str) -> list[str]:
        """How to talk to whoever is in front of you.

        Brian and Patrick are experts in different things and need different
        briefings. Same facts, same decisions, different vocabulary.
        """
        if speaker == "patrick":
            return [
                "=== YOU ARE TALKING TO PATRICK ===",
                "",
                "Patrick is the founder and the artist. Every print, sticker and third "
                "piece comes from his hands. He is the expert on the work; you are not, "
                "and you never tell him how to make art.",
                "",
                "Talk to him about the work. His vocabulary is correct here and you "
                "should use it — pulls, proofs, registration, spot color, stock, "
                "editions. That is his trade, not jargon.",
                "",
                "Never brief him in marketing metrics. No CAC, no LTV, no funnel, no "
                "impressions, no conversion rate. He does not need them and they make "
                "the work feel like output. Translate:",
                "- not 'engagement rate' → 'people saved this one a lot more than the "
                "others'",
                "- not 'top of funnel' → 'people who've never heard of us'",
                "- not 'this converted at 4%' → 'four in a hundred who saw it signed up'",
                "",
                "What he needs from you: what to make, by when, and why that subject "
                "rather than another. Give him a constraint and a reason, never a brief "
                "full of numbers. If a deadline is tight, say so plainly and say what "
                "happens if it slips.",
                "",
                "His studio time is the scarcest thing in the company, so never ask for "
                "work casually. If you want something extra made, say what it costs him "
                "in hours and what it buys. He is allowed to say no.",
                "",
                "Be direct about deadlines and vague about taste. 'The coaster art has "
                "to be at the printer by 10/1' is yours to say. 'Make it more playful' "
                "is not.",
            ]
        if speaker == "brian":
            return [
                "=== YOU ARE TALKING TO BRIAN ===",
                "",
                "Brian is the CEO. He owns the business, the money and the final call on "
                "spend. He is an expert on the business and on this industry — not on "
                "marketing, and not on printmaking. Both of those vocabularies are "
                "yours, not his.",
                "",
                "Talk money, dates, decisions and tradeoffs. Numbers with units. What it "
                "costs, what it returns, what is blocked and by whom.",
                "",
                "Never use craft terms with him. A 'pull' is Patrick printing. A 'proof' "
                "is a test print. 'Registration' is whether the colors line up. Say the "
                "plain thing.",
                "",
                "Marketing terms that are load-bearing — CAC, churn, LTV, conversion "
                "rate — he needs, so define each once and then use it freely: 'CAC, what "
                "it costs us to get one subscriber, is about $40.' Everything else in "
                "plain English.",
            ]
        return [
            "=== AUDIENCE UNKNOWN ===",
            "",
            "You do not know who this is. Use plain English throughout — no craft "
            "vocabulary and no marketing jargon. Answer the question and do not assume "
            "authority to make commitments on the company's behalf.",
        ]

    def system_prompt(self, allow_writes: bool, speaker: str = "") -> list[dict]:
        """Two blocks, stable first.

        The stable block — identity, the repo map, the always-loaded docs — is
        the expensive one, so it goes first and carries the cache breakpoint.
        Everything that varies by pass or by who is talking goes in a second,
        uncached block after it. The other way round (which is how this started)
        gives every combination of person and pass its own cache entry, and each
        one pays full price for the same 12k tokens.
        """
        stable = [
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
            "=== THE REPO ===",
        ]
        try:
            stable.append("\n".join(self.repo.tree()))
        except Exception as exc:  # noqa: BLE001
            stable.append(f"(file listing unavailable: {exc})")

        stable += [
            "",
            "These are loaded below in full. Everything else, read with read_file when "
            "it is relevant — don't answer from memory about a document you haven't "
            "opened this turn. The ones you reach for most:",
            *(f"  {d}" for d in ON_DEMAND_DOCS),
        ]

        for path in CORE_DOCS:
            try:
                stable += ["", f"=== {path} ===", self.repo.read(path, max_chars=20_000)]
            except Exception as exc:  # noqa: BLE001
                stable.append(f"\n=== {path} === (unreadable: {exc})")

        variable = list(self._capture_rules() if allow_writes else self._answering_rules())
        if not allow_writes:
            variable += ["", *self.audience_rules(speaker)]

        return [
            {"type": "text", "text": "\n".join(stable),
             "cache_control": {"type": "ephemeral", "ttl": "1h"}},
            {"type": "text", "text": "\n".join(variable)},
        ]

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
                effort: str | None = None, speaker: str = "",
                model: str | None = None) -> tuple[str, list[dict]]:
        """Run to completion. Returns (reply_text, updated_history).

        Writes are off by default. Every tool call is a full model round trip, so
        letting Marty file paperwork mid-answer added a minute per file while
        Brian watched a status line. Answering is the critical path; capture runs
        afterwards via capture().
        """
        self.repo.ensure()
        messages = list(history)
        tools = list(REPO_TOOLS if allow_writes else READ_TOOLS) + [WEB_SEARCH_TOOL]
        system = self.system_prompt(allow_writes, speaker)

        resumes = 0
        spend = 0.0
        calls = 0
        cache_hits = 0
        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=model or MODEL,
                max_tokens=MAX_TOKENS,
                # Auto-caches the last cacheable block, which is the growing
                # message history — otherwise every tool call in the loop
                # re-sends the whole thread at full price.
                cache_control={"type": "ephemeral"},
                system=system,
                thinking={"type": "adaptive"},
                output_config={"effort": effort or EFFORT},
                tools=tools,
                messages=messages,
            )

            calls += 1
            spend += _cost(model or MODEL, response.usage)
            if (getattr(response.usage, "cache_read_input_tokens", 0) or 0) > 0:
                cache_hits += 1

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

        log.info("%s: %d call(s), %d cached, $%.3f",
                 "capture" if allow_writes else "answer", calls, cache_hits, spend)
        self.last_cost = spend

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

    def worth_recording(self, history: list[dict]) -> bool:
        """Cheap yes/no on whether the capture pass is worth running.

        Most exchanges are questions, chatter or acknowledgements and produce no
        writes. Running a full tool loop to discover that is the single most
        wasteful thing this service does.
        """
        tail = []
        for message in history[-4:]:
            content = message.get("content")
            if isinstance(content, str):
                text = content
            else:
                parts = []
                for b in content if isinstance(content, list) else []:
                    kind = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
                    if kind == "text":
                        parts.append(b.get("text", "") if isinstance(b, dict)
                                     else getattr(b, "text", ""))
                text = " ".join(parts)
            if text.strip():
                tail.append(f"{message['role'].upper()}: {text[:2000]}")

        if not tail:
            return False

        try:
            result = self.client.messages.create(
                model=GATE_MODEL,
                max_tokens=8,
                system=(
                    "You decide whether a conversation excerpt needs to be recorded in "
                    "a company's strategy repo.\n\n"
                    "Answer YES only if it contains a new fact about the business, "
                    "product, costs, customers or market stated by a person; a decision "
                    "that was made; or a change that contradicts something previously "
                    "believed.\n\n"
                    "Answer NO for questions, analysis, recommendations, chatter, "
                    "acknowledgements, and anything the assistant merely reasoned to.\n\n"
                    "Reply with exactly YES or NO."
                ),
                messages=[{"role": "user", "content": "\n\n".join(tail)}],
            )
            answer = next((b.text for b in result.content if b.type == "text"), "").strip()
            log.info("capture gate: %s ($%.4f)", answer or "?", _cost(GATE_MODEL, result.usage))
            return answer.upper().startswith("YES")
        except Exception as exc:  # noqa: BLE001 — on doubt, record it
            log.warning("capture gate failed, recording anyway: %s", exc)
            return True

    def capture(self, history: list[dict]) -> str | None:
        """Second pass, after the reply is sent. Records anything durable.

        Runs at low effort — deciding what to file is mechanical next to deciding
        what to think. Brian is not waiting on this.
        """
        if not self.worth_recording(history):
            return None

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
                model=CAPTURE_MODEL,
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
