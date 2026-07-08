#!/usr/bin/env python3
"""cross-city-audit — cross-*city* drift detector for the fleet Adjunct.

The cross-city analog of core's per-rig `cross-rig-deps`. It re-derives the live
topology from `gc cities`, reads each city's `gc --city <path> import list`, and
flags DRIFT: any pack installed in more than one city but pinned to more than one
distinct ref. It is policy-free — it does not encode a "correct" ref, only the
invariant that cities sharing a pack should share its ref.

Detect-and-file ONLY. It never mutates a peer city; remediation is the Adjunct's
human-gated job. On drift it files (or refreshes) exactly one open HQ bead tagged
`[cross-city-audit]` carrying a signature of the current drift set, so persistent
drift does not spawn a duplicate bead every interval. When drift clears, the
stale bead is left for the Adjunct to close (the order does not auto-close work).

Runs as an exec order (no LLM, no agent). Output prints to stdout and is captured
in `gc order history`.
"""
import hashlib
import json
import subprocess
import sys

MARKER = "[cross-city-audit]"
LABEL = "cross-city-audit"


def run(args):
    """Run a gc command, return stdout (empty string on failure)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


def cities():
    """Live topology from `gc cities` -> {name: path}."""
    res = {}
    for line in run(["gc", "cities"]).splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("/"):
            res[parts[0]] = parts[1]
    return res


def imports(path):
    """Installed packs in a city -> {pack_name: resolved_ref}.

    `gc --city <path> import list` prints tab/space-separated rows:
        <name> <source> <installed-ref> <resolved-ref>
    We key on name and take the resolved ref (last column) as the identity that
    matters for "are two cities on the same code".
    """
    res = {}
    for line in run(["gc", "--city", path, "import", "list"]).splitlines():
        parts = line.split()
        if len(parts) >= 2 and not parts[0].startswith("-"):
            name = parts[0]
            ref = parts[-1]
            res[name] = ref
    return res


def open_audit_bead():
    """Return the id of an existing open HQ bead labeled LABEL, else None.

    Filters by label so it does not depend on title text or a JSON flag.
    """
    out = run(["gc", "bd", "list", "--status", "open", "--label", LABEL])
    for line in out.splitlines():
        # Row format: "○ un-xxx ● Pn <title...>"; the id is the first token that
        # looks like a bead id (contains a hyphen, short, alpha first char).
        for tok in line.split():
            if "-" in tok and len(tok) <= 8 and tok[0].isalpha():
                return tok
    return None


def main():
    topo = cities()
    if not topo:
        print("cross-city-audit: no cities from `gc cities`; nothing to do.")
        return 0

    # pack -> {city: ref}
    matrix = {}
    for name, path in sorted(topo.items()):
        for pack, ref in imports(path).items():
            matrix.setdefault(pack, {})[name] = ref

    drift = {}
    for pack, by_city in matrix.items():
        distinct = set(by_city.values())
        if len(by_city) > 1 and len(distinct) > 1:
            drift[pack] = by_city

    # Build a human report + a stable signature of the drift set.
    lines = []
    lines.append(f"cross-city-audit: {len(topo)} cities, {len(matrix)} distinct packs.")
    if not drift:
        lines.append("No cross-city pack drift. All shared packs share their ref.")
        print("\n".join(lines))
        return 0

    lines.append(f"DRIFT on {len(drift)} pack(s):")
    sig_parts = []
    for pack in sorted(drift):
        by_city = drift[pack]
        lines.append(f"  • {pack}:")
        for city in sorted(by_city):
            lines.append(f"      {city:<14} {by_city[city]}")
        sig_parts.append(pack + "|" + ",".join(f"{c}={by_city[c]}" for c in sorted(by_city)))
    signature = hashlib.sha1("\n".join(sig_parts).encode()).hexdigest()[:12]
    lines.append(f"signature: {signature}")
    report = "\n".join(lines)
    print(report)

    # File-or-refresh a single HQ bead. If one is already open, leave it (the
    # Adjunct owns triage); only create when none exists.
    existing = open_audit_bead()
    if existing:
        print(f"cross-city-audit: open bead {existing} already tracks drift; not duplicating.")
        return 0

    title = f"{MARKER} pack drift ({len(drift)} pack(s), sig {signature})"
    body = report + (
        "\n\nRemediation is Adjunct-gated: identify the intended ref (usually the "
        "authoring city's), then propose the exact `gc --city <path> import "
        "upgrade/install` + `reload` fan-out and get human approval before "
        "executing. Close this bead once every in-scope city shares the ref."
    )
    out = run(["gc", "bd", "create", title, "-t", "task", "-p", "2", "-l", LABEL, "-d", body])
    print(f"cross-city-audit: filed HQ bead.\n{out}".rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
