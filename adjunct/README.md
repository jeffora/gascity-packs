# adjunct pack

The fleet **Adjunct's** portable operating identity, packaged as a versioned
pack so the role survives session loss. HQ-only.

## Why this exists

The Adjunct is the single instrument that stands above every city Mayor —
responsible for cross-city pack rollout, configuration-drift detection, and
consistency audits. Its identity used to live only in a hand-maintained agent
template (`agents/adjunct/prompt.template.md`) inside the HQ city. That made the
role fragile: a wedged or quarantined session was nursed rather than recovered,
and the identity could drift silently.

Packaging it makes the identity **versioned and recoverable**. Recovery becomes
"new session + load the `adjunct` skill", not nursing one persistent session
through the handoff → resume-trap → quarantine failure mode.

## What it ships

- `skills/adjunct/SKILL.md` — the full Adjunct identity and read-mostly playbook:
  theory of operation, the sweep → diff → file → gate loop, cross-city mail
  conventions, and the **cross-city-prep-worker contract** (helper workers slung
  to prepare peer-city changes inherit read + propose-only; the write stays with
  the Adjunct and stays human-gated).
- `orders/cross-city-audit.toml` + `assets/scripts/cross-city-audit.py` — a
  recurring consistency sweep, the cross-*city* analog of core's per-rig
  `cross-rig-deps`. It diffs import refs across every registered city and files
  one HQ bead (labeled `cross-city-audit`) on drift. Detect-and-file only; it
  never mutates a peer city.

## Scope

Import **only** into the HQ city, at city scope. This pack is deliberately NOT
part of the fleet-wide `gascity` pack: the Adjunct is a fleet-unique role, so its
skill must not materialize in every city the way `gascity`/`mayor` does.

```toml
# <HQ>/pack.toml
[imports.adjunct]
  source = "https://github.com/jeffora/gascity-packs/tree/main/adjunct"
  version = "sha:<pin>"
```

Then `gc import install` → `gc import check` → `gc reload --soft`.

## Companion change (HQ side)

With the skill carrying the identity, the HQ agent template
(`agents/adjunct/prompt.template.md`) is reduced to a thin stub that names the
role and points at this skill. See the rollout bead for the exact stub.
