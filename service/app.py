"""Marty on Slack. Socket Mode, so Railway needs no public ingress.

Run:  python app.py      (env from service/.env.example)
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from marty import Marty, Repo, Threads

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("marty.app")

SLACK_LIMIT = 2900  # Slack hard-caps a message block at 3000 chars

repo = Repo()
marty = Marty(repo)
threads = Threads()
app = App(token=os.environ["SLACK_BOT_TOKEN"])

ALLOWED = {u.strip() for u in os.environ.get("MARTY_ALLOWED_USERS", "").split(",") if u.strip()}
BOT_USER_ID: str | None = None


# --- helpers -----------------------------------------------------------------

def chunks(text: str, size: int = SLACK_LIMIT) -> list[str]:
    """Split on paragraph boundaries where possible, never mid-word."""
    if len(text) <= size:
        return [text]
    out, current = [], ""
    for para in text.split("\n\n"):
        if len(current) + len(para) + 2 <= size:
            current += ("\n\n" if current else "") + para
            continue
        if current:
            out.append(current)
        while len(para) > size:
            cut = para.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            out.append(para[:cut])
            para = para[cut:].lstrip()
        current = para
    if current:
        out.append(current)
    return out


def strip_mention(text: str) -> str:
    return re.sub(r"<@[UW][A-Z0-9]+>", "", text or "").strip()


def allowed(user_id: str) -> bool:
    return not ALLOWED or user_id in ALLOWED


def handle(client, channel: str, reply_ts: str | None, convo_key: str,
           user: str, text: str) -> None:
    """reply_ts is the thread to answer in, or None to reply at top level.

    In a DM there is no reason to bury the answer in a thread, and the whole DM
    is one conversation — so DMs key on the channel and reply inline.
    """
    if not allowed(user):
        client.chat_postMessage(
            channel=channel, thread_ts=reply_ts,
            text="I only take direction from Brian and Patrick.",
        )
        return

    body = strip_mention(text)
    if not body:
        return

    if body.lower() in {"reset", "new thread", "forget"}:
        threads.clear(convo_key)
        client.chat_postMessage(channel=channel, thread_ts=reply_ts, text="Cleared. Starting fresh.")
        return

    placeholder = client.chat_postMessage(
        channel=channel, thread_ts=reply_ts, text="_thinking…_"
    )

    started = time.monotonic()

    def note(tool_name: str, args: dict) -> None:
        label = {
            "read_file": f"reading `{args.get('path', '')}`",
            "list_files": "listing the repo",
            "search_repo": f"searching for `{args.get('pattern', '')}`",
            "write_file": f"writing `{args.get('path', '')}`",
        }.get(tool_name, tool_name)
        elapsed = int(time.monotonic() - started)
        suffix = f" ({elapsed}s)" if elapsed >= 10 else ""
        try:
            client.chat_update(
                channel=channel, ts=placeholder["ts"], text=f"_{label}…{suffix}_"
            )
        except Exception:  # noqa: BLE001, best-effort status only
            pass

    history = threads.get(convo_key)
    history.append({"role": "user", "content": body})

    updated: list[dict] = []
    try:
        reply, updated = marty.respond(history, on_tool=note)
        threads.set(convo_key, updated)
    except Exception as exc:  # noqa: BLE001
        log.exception("turn failed")
        reply = f"Something broke on my end: `{type(exc).__name__}: {exc}`"

    parts = chunks(reply)
    client.chat_update(channel=channel, ts=placeholder["ts"], text=parts[0])
    for part in parts[1:]:
        client.chat_postMessage(channel=channel, thread_ts=reply_ts, text=part)

    # Capture runs after the answer is on screen, off the critical path.
    if not updated:
        return
    threading.Thread(
        target=run_capture, args=(client, channel, reply_ts, updated), daemon=True
    ).start()


def run_capture(client, channel: str, reply_ts: str | None, history: list[dict]) -> None:
    """Record anything durable from the exchange. Silent when there's nothing."""
    try:
        pushed = marty.capture(history)
    except Exception as exc:  # noqa: BLE001
        log.exception("capture failed")
        pushed = f"FAILED: {type(exc).__name__}: {exc}"

    if not pushed:
        return
    text = (f":warning: couldn't save that to the repo — {pushed}"
            if pushed.startswith("FAILED") else f"_filed {pushed}_")
    try:
        client.chat_postMessage(channel=channel, thread_ts=reply_ts, text=text)
    except Exception:  # noqa: BLE001
        log.warning("could not post capture confirmation")


# --- Slack events ------------------------------------------------------------

@app.event("app_mention")
def on_mention(event, client):
    thread_ts = event.get("thread_ts") or event["ts"]
    handle(
        client,
        channel=event["channel"],
        reply_ts=thread_ts,
        convo_key=thread_ts,
        user=event.get("user", ""),
        text=event.get("text", ""),
    )


@app.event("message")
def on_message(event, client):
    # Ignore edits, deletions, joins, and anything Marty said himself.
    if event.get("subtype") or event.get("bot_id"):
        return

    is_dm = event.get("channel_type") == "im"
    in_thread = bool(event.get("thread_ts"))
    mentioned = BOT_USER_ID and f"<@{BOT_USER_ID}>" in event.get("text", "")

    # In channels, only answer when mentioned (app_mention covers that) or when
    # the thread is already one of his.
    if not is_dm and not (in_thread and threads.get(event["thread_ts"])):
        return
    if mentioned and not is_dm:
        return  # app_mention will handle it; don't answer twice

    if is_dm and not in_thread:
        # The whole DM is one conversation; answer inline, not in a thread.
        reply_ts, convo_key = None, f"dm:{event['channel']}"
    else:
        reply_ts = convo_key = event.get("thread_ts") or event["ts"]

    handle(
        client,
        channel=event["channel"],
        reply_ts=reply_ts,
        convo_key=convo_key,
        user=event.get("user", ""),
        text=event.get("text", ""),
    )


# --- morning brief (off unless BRIEF_CRON is set) ----------------------------

def post_morning_brief() -> None:
    channel = os.environ.get("BRIEF_CHANNEL")
    if not channel:
        log.warning("BRIEF_CRON set but BRIEF_CHANNEL is not — skipping")
        return

    log.info("running the morning brief")
    prompt = (
        "Run your morning brief now, following .claude/skills/marty-morning-brief/SKILL.md. "
        "Scan, update whatever the findings justify, write the brief to "
        "marketing/briefs/YYYY-MM-DD.md with write_file, and then reply with the brief "
        "itself — nothing else, no preamble about having done it."
    )
    try:
        reply, _ = marty.respond([{"role": "user", "content": prompt}], allow_writes=True)
    except Exception as exc:  # noqa: BLE001
        log.exception("brief failed")
        reply = f"Brief failed: `{type(exc).__name__}: {exc}`"

    parts = chunks(reply)
    first = app.client.chat_postMessage(channel=channel, text=parts[0])
    for part in parts[1:]:
        app.client.chat_postMessage(channel=channel, thread_ts=first["ts"], text=part)
    pushed = marty.publish()
    if pushed:
        app.client.chat_postMessage(channel=channel, thread_ts=first["ts"], text=f"_pushed {pushed}_")


def start_scheduler() -> None:
    cron = os.environ.get("BRIEF_CRON", "").strip()
    if not cron:
        log.info("BRIEF_CRON unset — morning brief is off, Marty runs on demand")
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    tz = os.environ.get("BRIEF_TZ", "America/Denver")
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(post_morning_brief, CronTrigger.from_crontab(cron, timezone=tz))
    scheduler.start()
    log.info("morning brief scheduled: %s (%s)", cron, tz)


# --- health endpoint so Railway sees a listening port ------------------------

class Health(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"marty ok")

    def log_message(self, *args):  # silence per-request logging
        pass


def start_health_server() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Health)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("health server on :%s", port)


def main() -> None:
    global BOT_USER_ID
    repo.ensure()
    log.info("repo ready at %s", repo.dir)

    problem = repo.verify_push_access()
    if problem:
        log.error("=" * 72)
        log.error("WRITE ACCESS PROBLEM: %s", problem)
        log.error("Marty will answer questions but cannot record anything.")
        log.error("=" * 72)
    else:
        log.info("github write access confirmed for %s", repo.slug)

    BOT_USER_ID = app.client.auth_test()["user_id"]
    log.info("connected to Slack as %s", BOT_USER_ID)

    start_health_server()
    start_scheduler()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()


if __name__ == "__main__":
    main()
