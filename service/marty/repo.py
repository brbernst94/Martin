"""The strategy repo, as a working copy Marty can read and commit to."""
from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path

log = logging.getLogger("marty.repo")

# Without this git blocks forever on a credential prompt when the token is bad,
# which would hang the container at boot instead of crashing with a clear error.
os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")

# Marty is never allowed to touch these, whatever he decides.
FORBIDDEN_PREFIXES = (".git/", ".github/workflows/", "service/.env")

_lock = threading.Lock()


def _writable_dir(preferred: str) -> Path:
    """Use REPO_DIR when we can write there, otherwise fall back to /tmp.

    Railway volumes need a paid plan and are easy to miss in the UI. A missing
    volume should cost a re-clone at boot, not a crash loop.
    """
    path = Path(preferred)
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.touch()
        probe.unlink()
        return path
    except OSError:
        fallback = Path("/tmp/marty-repo")
        log.warning("%s is not writable — falling back to %s (repo re-clones on restart)",
                    preferred, fallback)
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


class Repo:
    def __init__(self) -> None:
        self.dir = _writable_dir(os.environ.get("REPO_DIR", "/data/repo"))
        self.slug = os.environ["GITHUB_REPO"]
        self.branch = os.environ.get("GITHUB_BRANCH", "main")
        self._token = os.environ["GITHUB_TOKEN"]

    # -- plumbing ---------------------------------------------------------

    @property
    def _remote(self) -> str:
        return f"https://x-access-token:{self._token}@github.com/{self.slug}.git"

    def _git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.dir if self.dir.exists() else None,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "***")

    # -- lifecycle --------------------------------------------------------

    def ensure(self) -> None:
        """Clone on first boot, pull on every subsequent call."""
        with _lock:
            if not (self.dir / ".git").exists():
                self.dir.parent.mkdir(parents=True, exist_ok=True)
                log.info("cloning %s into %s", self.slug, self.dir)
                subprocess.run(
                    ["git", "clone", "--depth", "50", "--branch", self.branch,
                     self._remote, str(self.dir)],
                    check=True, capture_output=True, text=True, timeout=300,
                )
                self._git("config", "user.name", "Marty (CMO)")
                self._git("config", "user.email", "marty@bot.local")
            else:
                try:
                    self._git("fetch", "origin", self.branch)
                    self._git("reset", "--hard", f"origin/{self.branch}")
                except RuntimeError as exc:
                    log.warning("pull failed, continuing on local copy: %s", self._scrub(str(exc)))

    # -- reads ------------------------------------------------------------

    def resolve(self, rel: str) -> Path:
        """Resolve a repo-relative path, refusing anything outside the repo.

        Absolute paths are rejected rather than silently reinterpreted as
        repo-relative — a caller that passes /etc/passwd should get an error,
        not a quiet read of <repo>/etc/passwd.
        """
        if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise ValueError(f"path must be repo-relative, got: {rel}")
        target = (self.dir / rel).resolve()
        root = self.dir.resolve()
        if not str(target).startswith(str(root) + os.sep) and target != root:
            raise ValueError(f"path escapes the repo: {rel}")
        return target

    def read(self, rel: str, max_chars: int = 60_000) -> str:
        path = self.resolve(rel)
        if not path.is_file():
            raise FileNotFoundError(rel)
        text = path.read_text(errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + f"\n\n[truncated at {max_chars} chars]"
        return text

    def tree(self, subdir: str = "") -> list[str]:
        base = self.resolve(subdir) if subdir else self.dir
        out = []
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.dir).as_posix()
            if rel.startswith(".git/") or "/node_modules/" in rel:
                continue
            out.append(rel)
        return out

    def grep(self, pattern: str, max_hits: int = 60) -> list[str]:
        try:
            raw = self._git("grep", "-n", "-i", "-I", "--", pattern, check=False)
        except RuntimeError:
            return []
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        return lines[:max_hits]

    # -- writes -----------------------------------------------------------

    def write_and_commit(self, rel: str, content: str, message: str) -> str:
        if any(rel.startswith(p) for p in FORBIDDEN_PREFIXES):
            raise PermissionError(f"{rel} is off limits")
        self.resolve(rel)  # validate before doing any network work

        with _lock:
            self.ensure()
            path = self.resolve(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

            self._git("add", "--", rel)
            status = self._git("status", "--porcelain", "--", rel)
            if not status:
                return f"{rel} was already identical — nothing committed."

            body = (
                f"{message}\n\n"
                "Written by Marty from Slack.\n\n"
                "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
            )
            self._git("commit", "-m", body)

            for attempt in range(3):
                try:
                    self._git("push", "origin", f"HEAD:{self.branch}")
                    break
                except RuntimeError as exc:
                    if attempt == 2:
                        raise RuntimeError(self._scrub(str(exc))) from exc
                    log.warning("push failed, rebasing and retrying")
                    self._git("fetch", "origin", self.branch)
                    self._git("rebase", f"origin/{self.branch}", check=False)

            sha = self._git("rev-parse", "--short", "HEAD")
            return f"Committed {rel} as {sha} and pushed to {self.branch}."
