"""
The change record of a report from the version tags in git.

Each tag reachable from ``main`` (or ``master``) is one row: the tag name is the revision, the date is the date of the
tag (annotated tags) or of the tagged commit, and the description is the message of an annotated tag or the subject
of the tagged commit. Descriptions can be replaced from ``conf.py`` with ``word_change_record_notes``.
"""

from __future__ import annotations

import fnmatch
import subprocess
from typing import Dict, List, Optional

from sphinx.util import logging

logger = logging.getLogger(__name__)

_FIELDS = ("issue", "revision", "date", "pages", "description")


def _git(repo: str, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def release_branch(repo: str) -> Optional[str]:
    """``main`` or ``master``, local or from ``origin``; None if neither exists."""
    for ref in ("refs/heads/main", "refs/heads/master", "refs/remotes/origin/main", "refs/remotes/origin/master"):
        if _git(repo, "rev-parse", "--verify", "--quiet", ref) is not None:
            return ref
    return None


def change_record_from_git(repo: str, pattern: str = "*", notes: Optional[Dict[str, object]] = None,
                           date_format: str = "%Y/%m/%d") -> List[Dict[str, str]]:
    """Rows of the change record, oldest first, from the tags merged into main/master that match ``pattern``."""
    notes = notes or {}
    branch = release_branch(repo)
    if branch is None:
        logger.warning("sphinx2word: word_change_record = 'git', but %s has no main or master branch; "
                       "the change record is empty", repo)
        return []
    out = _git(repo, "for-each-ref", f"--merged={branch}", "--sort=creatordate",
               f"--format=%(refname:short)%09%(creatordate:format:{date_format})%09%(contents:subject)",
               "refs/tags")
    if out is None:
        logger.warning("sphinx2word: could not read the git tags of %s; the change record is empty", repo)
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 2 or not fnmatch.fnmatchcase(parts[0], pattern):
            continue
        tag, date = parts[0], parts[1]
        row = {"issue": "", "revision": tag, "date": date, "pages": "All",
               "description": parts[2].strip() if len(parts) > 2 else ""}
        note = notes.get(tag)
        if isinstance(note, dict):
            row.update({k: str(v) for k, v in note.items() if k in _FIELDS})
        elif note is not None:
            row["description"] = str(note)
        rows.append(row)
    return rows


def normalise_change_record(entries) -> List[Dict[str, str]]:
    """Rows given in conf.py: dicts with the keys of ``_FIELDS``, or tuples in that order."""
    rows = []
    for entry in entries or []:
        if isinstance(entry, dict):
            row = {k: str(entry.get(k, "")) for k in _FIELDS}
        else:
            values = [str(v) for v in entry] + [""] * len(_FIELDS)
            row = dict(zip(_FIELDS, values))
        rows.append(row)
    return rows
