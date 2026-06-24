# Audits

This folder holds **read-only review snapshots** — structured audits of
repo state at a point in time. They are written for human decision-making,
not as executable experiment artefacts.

## Pattern

| Property | Rule |
|---|---|
| Naming | `YYYY-MM-DD_<scope>_audit.md` |
| Tracking | Committed when the audit's recommendations land; may start untracked during the review session |
| Scope | One audit per review pass; cross-reference `EXPERIMENTS.md` and program docs, do not duplicate raw registries |
| Action | Audits **recommend**; implementation happens in `docs/`, `experiments/`, or `programs/` via separate commits |

Audits are **not** part of the experiment registry (`EXPERIMENTS.md`).
They do not trigger data runs or protocol amendments by themselves.

## Index

| Date | File | Scope |
|---|---|---|
| 2026-06-24 | [`2026-06-24_E001-E007_audit.md`](2026-06-24_E001-E007_audit.md) | E001–E007 quality review; M001 inheritance list; lab Phase 1 close recommendations |
