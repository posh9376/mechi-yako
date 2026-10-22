# Team tasks — Daniel vs Posh

Split so we do not edit the same files or wait on each other.  
Contract between tracks: `docs/event-schema.md` + fact-layer fixtures (change only by agreement).

**Representative / submitter:** Posh (default)  
**Daily check-in:** 15 min — what shipped, blockers, checkpoint

---

## File ownership (do not cross without a PR ping)

| Area | Owner | Paths |
|---|---|---|
| Event schema & docs (data) | **Daniel** | `docs/event-schema.md`, `docs/architecture.md` (data/pipeline sections) |
| Synthetic data & generator | **Daniel** | `generator/`, `data/matches/`, `data/fixtures/` |
| Pipeline & agents (core) | **Daniel** | `pipeline/` (non-API), `agents/moment_detector/`, `agents/explainer/`, `agents/verifier/` |
| Infra & deployment | **Daniel** | `infra/`, Container Apps / Key Vault / public link, deploy scripts, `.env.example` (Azure placeholders) |
| API layer | **Posh** | `api/` (or `pipeline/api/`) — FastAPI, routes, live feed wiring |
| Backend tests | **Posh** | `tests/pipeline/`, `tests/generator/`, `tests/agents/`, `tests/api/` |
| Personas & Kiswahili | **Posh** | `agents/persona/`, `agents/narrator/`, `agents/language_qa/`, `lexicon/` |
| Front end | **Both (alternate)** | `web/` — see [Web alternation](#web-alternation-daniel--posh) |
| Demo video & pitch copy | **Posh** | `docs/demo-storyboard.md`, pitch text on Projects page |
| README / Multi-Agent write-up | **Shared** | `README.md` — Daniel: pipeline/infra/Azure; Posh: API/UX/Kiswahili/pitch |
| Shared contract | **Both** | Schema freeze PRs need both approvals |

If you need a change in the other person’s tree: open a PR, do not push straight to their paths on `main`.

---

## Web alternation (Daniel ↔ Posh)

`web/` is shared. Avoid merge fights:

1. **Claim before you code** — in the daily check-in or a GitHub Issue, say which UI slice you own that day.
2. **One active PR per area** — do not both edit the same component files in parallel.
3. **Suggested slice split** (swap if you prefer; keep ownership explicit):

| Slice | First owner | Notes |
|---|---|---|
| App shell, match view, replay controls, score bar | **Posh** (first pass) | Fixture-driven early |
| Persona switch + EN/SW toggle | **Posh** | |
| Why? panel (events + verifier badge) | **Daniel** | Needs API/audit shape from Posh |
| Lower third / overlay JSON | **Daniel** | |
| QA badge + loading/error/cached demo path | **Posh** | |
| Polish / responsive / smoke fixes | **Alternate** | Whoever is free; one PR at a time |

4. Prefer **feature folders / components** so PRs touch disjoint files when possible.

---

## Daniel — data, pipeline, infra, deploy (+ web slices)

### Now → Sun Oct 18
- [x] Event schema v1 → `docs/event-schema.md`
- [x] Hand-scripted demo match → `data/matches/` (Blue Herons / Red Kites storyline)
- [x] Fact-layer fixtures for ≥3 moments → `data/fixtures/` (unblocks Posh API + UI)
- [x] Basic realism pass/fail on the demo match
- [ ] Thin generator later if time (do not block fixtures)
- [ ] Agree web slice claims for the week with Posh

### Mon Oct 19 → Tue Oct 20
- [x] Replay engine (local queue interface) in `pipeline/`
- [x] Match-state aggregator
- [x] Moment detector (5 types)
- [x] Hand off callable library / module contracts so Posh can expose them via API
- [ ] Start claimed web slice (e.g. Why? panel shell against fixtures)

### Wed Oct 21 → Thu Oct 22
- [x] Claim schema + template explainer (Foundry swap later) — started early Oct 18
- [x] Verifier (approve / correct / block + audit log) as library
- [ ] Coordinate with Posh so injected wrong-stat test lives under his `tests/`
- [x] Foundry-backed explainer (optional upgrade) — `agents/foundry.py`; numbers stay template-verified
- [x] Continue web slice (Why? panel / lower third) — `feature/daniel-web-why-overlay`

### Fri Oct 23 → Sun Oct 25
- [x] **Deploy** API + web to Azure Container Apps
- [x] Secrets stay on the Container App; skip budget alert (Azure free trial already has spending limit On)
- [x] Pre-generate & cache demo outputs (with Posh on cache format)
- [x] Public link + testing instructions
- [ ] Feature freeze support (bugs only after Sun evening)

### Shared with Posh
- [ ] Register on aka.ms if not done
- [x] Kiswahili review of demo lines (read; don’t rewrite lexicon without Posh) — approved Oct 20
- [ ] Smoke-test demo path daily from Phase 3
- [ ] Submission buffer Mon Oct 26

---

## Posh — API, backend tests, language, video (+ web slices)

### Now → Sun Oct 18
- [ ] Confirm Representative + Projects page access
- [ ] Persona definitions (analyst / casual / newcomer)
- [ ] Lexicon skeleton: **demo-match terms only** (~40–60) → `lexicon/sw.yaml`
- [ ] Formal-broadcast register guide (3–5 sample lines)
- [ ] `web/` first slices: app shell, match view, switches (fixtures)
- [ ] Scaffold `api/` + test layout (can return fixture JSON)

### Mon Oct 19 → Thu Oct 22
- [ ] **Fact-layer API + live feed** wrapping Daniel’s pipeline modules
- [ ] **Backend tests** for aggregator, detector, API routes (against demo match)
- [ ] English persona writers; Kiswahili narrator; language QA badge
- [ ] **Verified-claims API + audit log endpoints** once verifier exists
- [ ] Injected wrong-stat failure test in `tests/`
- [ ] Wire UI to live API when ready (feature-flag base URL)

### Fri Oct 23 → Sun Oct 25
- [ ] Remaining web slices (QA badge, cached demo path); leave deploy to Daniel
- [ ] Second register (casual) only if ahead
- [ ] Screen-record + edit demo video (&lt; 2:00)
- [ ] Pitch text (name Foundry, agents, ACA, DB)
- [ ] Help Daniel with cache payload shape / health checks if needed

### Shared with Daniel
- [x] Native review of every demo-match Kiswahili line — lexicon and demo lines approved Oct 20 (Eric Amenya, Daniel Githumbi)
- [ ] README API / UX / Kiswahili / Multi-Agent sections
- [ ] Submit Mon Oct 26; keep demo live through Nov 10

---

## Integration handoffs (order)

| When | Deliverable | Who builds | Who consumes |
|---|---|---|---|
| Sun Oct 18 | Schema frozen + fixtures | **Daniel** | Posh (API stub + UI) |
| Tue Oct 20 | Pipeline modules (replay/state/moments) | **Daniel** | Posh wraps in **API** + tests |
| Tue Oct 20 | Fact-layer HTTP API + live feed | **Posh** | Both (UI) |
| Thu Oct 22 | Explainer + verifier libraries | **Daniel** | Posh exposes claims API + tests |
| Thu Oct 22 | Verified-claims + audit HTTP API | **Posh** | Both (Why? panel) |
| Sat Oct 24 | Cached bundle format agreed | Both | **Daniel** deploys |
| Sun Oct 25 | Public link stable | **Daniel** (infra) — live as of 22 Oct | Posh films; both smoke-test |

---

## Conflict rules

1. **One owner per path** (table above), except `web/` which uses [alternation](#web-alternation-daniel--posh).
2. **Schema/fixture changes** = both agree in the same PR.
3. **API is Posh’s:** Daniel’s pipeline code should be importable libraries; Posh owns routes and HTTP contracts.
4. **Tests are Posh’s:** Daniel can add failing reproductions as issues/PRs; Posh lands them under `tests/`.
5. **Infra is Daniel’s:** Posh does not change `infra/` or production deploy config without a ping.
6. **Stub vs live:** UI/API can run on fixtures until pipeline handoff; feature-flag the API base URL.
7. **Time-box:** &gt;0.5 day over estimate → simplify or cut at next check-in.
8. **Freeze:** after Sun Oct 25 evening — bugs only.
