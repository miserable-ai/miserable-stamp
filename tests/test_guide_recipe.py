"""The `git wip` recipe in the tenant guide, run as written in a scratch repository."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

GUIDE = Path(__file__).resolve().parent.parent / "docs" / "tenant-guide.md"
SECTION = "## Work in progress: `git wip`"
UNSTAMPED = 'def a():\n    """@relation(SR-1, role=Implements)"""\n'


def _blocks() -> list[str]:
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(SECTION)
    end = text.find("\n## ", start + len(SECTION))
    section = text[start : end if end != -1 else len(text)]
    return re.findall(r"^```sh\n(.*?)^```$", section, flags=re.DOTALL | re.MULTILINE)


def _block(containing: str) -> str:
    found = [b for b in _blocks() if containing in b]
    assert len(found) == 1, f"expected one sh block containing {containing!r}"
    return found[0]


class Scratch:
    """A repository on branch `feature` with a bare `origin`, and a private HOME and PATH."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / "home"
        self.bin = root / "bin"
        self.repo = root / "repo"
        self.remote = root / "origin.git"
        for d in (self.home, self.bin, self.repo):
            d.mkdir()
        self.recipe = self.home / "git-wip.sh"
        self.recipe.write_text(_block("git_wip()"), encoding="utf-8")
        stamp_dir = Path(sys.executable).parent
        self.env = {
            "HOME": str(self.home),
            "PATH": os.pathsep.join([str(self.bin), str(stamp_dir), os.environ["PATH"]]),
            "GIT_CONFIG_GLOBAL": str(self.home / ".gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Dev",
            "GIT_AUTHOR_EMAIL": "dev@example.com",
            "GIT_COMMITTER_NAME": "Dev",
            "GIT_COMMITTER_EMAIL": "dev@example.com",
            "LC_ALL": "C",
        }
        self.git("init", "-q", "--bare", str(self.remote), cwd=root)
        self.git("init", "-q", "-b", "main")
        self.git("remote", "add", "origin", str(self.remote))
        (self.repo / ".gitignore").write_text("secret.txt\n")
        (self.repo / "readme.txt").write_text("hello\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "start")
        self.git("push", "-q", "origin", "main")
        self.git("checkout", "-q", "-b", "feature")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        return done.stdout

    def wip(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        script = '. "$1"; shift; git_wip "$@"'
        return subprocess.run(
            ["sh", "-c", script, "sh", str(self.recipe), *args],
            cwd=cwd or self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def remote_refs(self) -> dict[str, str]:
        out = self.git("for-each-ref", "--format=%(refname) %(objectname)", cwd=self.remote)
        refs = {}
        for line in out.splitlines():
            name, sha = line.split(" ", 1)
            refs[name] = sha
        return refs

    def fake(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    s = Scratch(tmp_path)
    s.git("config", "miserable.login", "octo-dev")
    return s


def test_snapshot_is_pushed_to_the_wip_ref_with_files_stamped(scratch: Scratch) -> None:
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    refs = scratch.remote_refs()
    assert "refs/heads/wip/octo-dev/feature" in refs
    snapshot = scratch.git("show", "refs/heads/wip/octo-dev/feature", cwd=scratch.remote)
    assert "wip: feature" in snapshot
    pushed = scratch.git("show", "refs/heads/wip/octo-dev/feature:pump.py", cwd=scratch.remote)
    assert "@id c-" in pushed
    parent = scratch.git("rev-parse", "refs/heads/wip/octo-dev/feature^", cwd=scratch.remote)
    assert parent == scratch.git("rev-parse", "HEAD")


def test_the_persons_index_and_branch_are_untouched(scratch: Scratch) -> None:
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    (scratch.repo / "readme.txt").write_text("changed\n")
    scratch.git("add", "readme.txt")
    index = scratch.repo / ".git" / "index"
    before = (index.read_bytes(), scratch.git("ls-files", "-s"), scratch.git("rev-parse", "HEAD"))
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    after = (index.read_bytes(), scratch.git("ls-files", "-s"), scratch.git("rev-parse", "HEAD"))
    assert after == before
    assert scratch.git("status", "--porcelain").splitlines() == ["M  readme.txt", "?? pump.py"]
    pushed = scratch.git("show", "refs/heads/wip/octo-dev/feature:readme.txt", cwd=scratch.remote)
    assert pushed == "changed\n"


def test_exit_1_from_stamping_is_accepted(scratch: Scratch) -> None:
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    scratch.fake("miserable-stamp", 'exec "$REAL_STAMP" "$@"')
    scratch.env["REAL_STAMP"] = str(Path(sys.executable).parent / "miserable-stamp")
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    assert "refs/heads/wip/octo-dev/feature" in scratch.remote_refs()


@pytest.mark.parametrize("body", ["exit 255", "kill -9 $$"])
def test_a_failing_stamp_aborts_before_pushing(scratch: Scratch, body: str) -> None:
    # xargs reports a stamper exit of 1 to 125 as 123; 255 and a signal make it stop with 124, 125.
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    scratch.fake("miserable-stamp", body)
    done = scratch.wip()
    assert done.returncode != 0
    assert "refs/heads/wip/octo-dev/feature" not in scratch.remote_refs()


def test_untracked_files_are_listed_and_ignored_files_left_out(scratch: Scratch) -> None:
    (scratch.repo / "notes.txt").write_text("draft\n")
    (scratch.repo / "secret.txt").write_text("token\n")
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    assert "notes.txt" in done.stdout + done.stderr
    assert ".env" in done.stdout + done.stderr
    files = scratch.git(
        "ls-tree", "-r", "--name-only", "refs/heads/wip/octo-dev/feature", cwd=scratch.remote
    ).split()
    assert "notes.txt" in files
    assert "secret.txt" not in files


def test_a_deleted_tracked_file_is_not_stamped_and_is_deleted_in_the_snapshot(
    scratch: Scratch,
) -> None:
    (scratch.repo / "readme.txt").unlink()
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    files = scratch.git(
        "ls-tree", "-r", "--name-only", "refs/heads/wip/octo-dev/feature", cwd=scratch.remote
    ).split()
    assert "readme.txt" not in files


def test_runs_from_a_subdirectory(scratch: Scratch) -> None:
    sub = scratch.repo / "src"
    sub.mkdir()
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    done = scratch.wip(cwd=sub)
    assert done.returncode == 0, done.stderr
    pushed = scratch.git("show", "refs/heads/wip/octo-dev/feature:pump.py", cwd=scratch.remote)
    assert "@id c-" in pushed


def test_detached_head_is_refused(scratch: Scratch) -> None:
    scratch.git("checkout", "-q", "--detach")
    done = scratch.wip()
    assert done.returncode != 0
    assert "detached" in done.stderr
    assert not any(r.startswith("refs/heads/wip/") for r in scratch.remote_refs())


def test_login_falls_back_to_gh(tmp_path: Path) -> None:
    scratch = Scratch(tmp_path)
    scratch.fake("gh", 'test "$*" = "api user -q .login" && echo gh-user')
    done = scratch.wip()
    assert done.returncode == 0, done.stderr
    assert "refs/heads/wip/gh-user/feature" in scratch.remote_refs()


def test_delete_removes_the_wip_ref(scratch: Scratch) -> None:
    assert scratch.wip().returncode == 0
    assert "refs/heads/wip/octo-dev/feature" in scratch.remote_refs()
    done = scratch.wip("--delete")
    assert done.returncode == 0, done.stderr
    assert "refs/heads/wip/octo-dev/feature" not in scratch.remote_refs()


def test_the_alias_form_runs_the_recipe(scratch: Scratch) -> None:
    install = _block("alias.wip")
    target = scratch.home / ".config" / "git" / "wip.sh"
    target.parent.mkdir(parents=True)
    target.write_text(scratch.recipe.read_text())
    subprocess.run(["sh", "-c", install], cwd=scratch.repo, env=scratch.env, check=True)
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    scratch.git("wip")
    assert "refs/heads/wip/octo-dev/feature" in scratch.remote_refs()
    scratch.git("wip", "--delete")
    assert "refs/heads/wip/octo-dev/feature" not in scratch.remote_refs()


def test_a_missing_stamp_command_aborts_before_pushing(scratch: Scratch) -> None:
    (scratch.repo / "pump.py").write_text(UNSTAMPED)
    path = scratch.bin / "miserable-stamp"
    path.write_text("not executable\n")
    scratch.env["PATH"] = os.pathsep.join([str(scratch.bin), "/usr/bin", "/bin"])
    done = scratch.wip()
    assert done.returncode != 0
    assert "nothing pushed" in done.stderr
    assert "refs/heads/wip/octo-dev/feature" not in scratch.remote_refs()
