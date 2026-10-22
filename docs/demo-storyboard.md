# Demo storyboard

Target: a screen recording under **2:00**, recorded by Posh, submitted Mon 26 Oct. The demo link stays up through 10 Nov (Daniel owns the public deploy).

## Recording setup

Record in **Live** mode against the local API, so events and moments arrive over the SSE feed on camera and the wrong-stat shot is live. Keep the cached build as the fallback take.

```bash
# Terminal 1: API
pip install -r requirements-dev.txt
python -m uvicorn api.main:app --port 8000

# Terminal 2: web app against the API (opens in Live mode)
cd web && npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
# open http://127.0.0.1:5173/
```

- Fallback take with no backend: `http://127.0.0.1:5173/?demo=cached`. It runs as a replay of the five fixture moments: use **55′ press** then **Play** in shot 2, and the press moment sits at 58′ with 5 turnovers over 6.7 minutes. Shot 6 needs the API.
- Browser at 1280×800 or larger, zoom 110–125% so the narration text is readable in the video.
- Before recording, set Speed to **120×**, persona to **Analyst**, language to **English**, register to **Persona default**.
- Open `http://127.0.0.1:8000/docs` in a second tab for shot 6.
- With `MECHI_EXPLAINER=foundry`, wait until `curl -s http://127.0.0.1:8000/health` shows `explainer.warm.done` equal to `total` and `running: false` before recording. Every Why? panel then opens instantly. A restart reuses `.cache/explanations.json`.

## Shot list

| # | Time | Screen | Action | Voice-over (draft) |
|---|---|---|---|---|
| 1 | 0:00–0:12 | Title, then the match view in Live mode, status **Ready** | Show the header "One match, told your way, in your language.", the **Live / Replay** toggle and the "live feed" source label | "Broadcasts show what happened. Mechi Yako explains why it mattered, for each fan, in their language, starting with Kiswahili." |
| 2 | 0:12–0:30 | Live controls, moment list | Click **Join at 55′**. The pill turns **LIVE**, the score shows 1–0 with the 19′ goal already listed, then the 60′ shot, 61′ press and 63′ equaliser stream in as the server sends them. The score goes 1–1 at 63′ | "Here is a synthetic match between two fictional clubs, streamed live from the server. As events arrive, the pipeline detects the moments that matter: a Red Kites press, a shot, the equaliser." |
| 3 | 0:30–0:50 | Moment detail on **61′ Pressure spell** | Click **Pause** after the equaliser. Select the press moment. Analyst text shows. Switch persona to **Newcomer** | "An analyst gets the numbers: four turnovers in five point seven minutes. A newcomer gets the same facts, with pressing explained in plain words." |
| 4 | 0:50–1:15 | Moment detail on **63′ Goal** | Select the equaliser with persona **Casual fan**. Toggle **English → Kiswahili** | "Switch to Kiswahili and the line is written natively from the same facts. It uses a curated football lexicon, and nothing is translated from English." |
| 5 | 1:15–1:30 | QA badge and the note under the text | Point at **QA pass** and "cites 1 event". Switch register to **Formal broadcast** | "Every line cites the event IDs behind it. Language QA checks each number, name and term against the fact layer before it reaches the screen." |
| 6 | 1:30–1:48 | API docs tab (`/docs`) | Run `POST /matches/m-demo-001/claims/check` with a wrong stat (body below). Show `"status": "blocked"`, `"recomputed": 5`. Then `GET /audit` shows the entry | "If any agent claims a number the raw events cannot reproduce, the verifier blocks it and logs the decision for audit." |
| 7 | 1:48–1:58 | Back to the match view, or an architecture slide | End on the match view, or on the pipeline diagram from the README | "Built on Microsoft Foundry agents, deployed on Azure Container Apps. One match, told your way." |

Shot 6 is optional. Cut it if the run is over time, or if it reads like an error on screen. The 0:18 left without it can go to shot 4.

### Exact on-screen lines (from the deterministic writers)

These are the texts Live mode shows today, from `POST /narrate` with `source: live` for `mom-pressure-06` (shot 3) and `mom-goal-04` (shots 4–5). All pass language QA. If a writer changes, regenerate them the same way and refresh this table.

| Shot | Persona · language · register | Text |
|---|---|---|
| 3 | Analyst · EN · formal | Between 56' and 61', Red Kites pressed high and won the ball repeatedly in the Blue Herons half. Red Kites forced 4 turnovers and made 4 pressure actions in the Blue Herons half over 5.7 minutes. |
| 3 | Newcomer · EN · simple | Red Kites are pressing: they chase Blue Herons close to their own goal to win the ball back quickly. Pressing means chasing the opponents high up the pitch to win the ball back quickly. |
| 4 | Casual · EN · casual | GOAL! Omar Diallo levels it for Red Kites — 1–1 and game on! |
| 4 | Casual · SW · casual | Goooli! Omar Diallo anatikisa nyavu dakika ya 63! Red Kites wamesawazisha, sasa ni 1–1. Mchezo upya! |
| 5 | Casual · SW · formal | Dakika ya 63, Omar Diallo anafunga bao la kusawazisha kwa Red Kites. Matokeo sasa ni Blue Herons 1–1 Red Kites. |

The cached fallback (`web/public/demo-bundle.json`, fixture moments) shows the same shot 4–5 lines. Its shot 3 analyst line reads "Between 55' and 61' … forced 5 turnovers and made 5 pressure actions … over 6.7 minutes."

The Kiswahili lines were reviewed and approved by native speakers Eric Amenya and Daniel Githumbi on 20 Oct. If a narrator template changes after that, get it re-reviewed and re-record shots 4–5.

### Shot 6 request body

```json
{ "moment_id": "mom-pressure-06", "metric": "high_turnovers", "value": 99, "source": "live" }
```

Expected response (abridged):

```json
{ "metric": "high_turnovers", "claimed": 99, "recomputed": 4, "status": "blocked", "reason": "raw events give 4", "checker": "agents-verifier-v1", "via": "agents.verifier" }
```

## Pitch text checklist

The written submission and the voice-over together must name each of these.

- [ ] **Microsoft Foundry.** Models and agent orchestration. Say plainly what runs on Foundry at submission time and what runs as a deterministic stand-in (persona writer, Kiswahili narrator, language QA and verifier currently run deterministically behind interfaces a Foundry adapter can replace).
- [ ] **Agents.** Moment Detector, Explainer, Verifier, Persona Writer, Kiswahili Narrator, Language QA, and how claim-then-verify connects them.
- [ ] **Azure Container Apps.** Hosts the FastAPI service and the static web build (Daniel's deploy).
- [ ] **Database.** Azure Cosmos DB for match state and the audit log. Confirm with Daniel whether the audit log is persisted at submission time or still in memory, and word the pitch to match.
- [ ] **Synthetic data.** Fictional clubs and players, seeded generator, realism report.
- [ ] **Kiswahili-first.** Native generation from facts, curated lexicon, three registers, review status stated honestly.
- [ ] **Explainability.** Event-ID citations on every line, QA badge, blocked wrong-stat with audit entry.

## Submission checklist (manual)

- [ ] Representative confirmed on the hackathon Projects page (Posh by default).
- [ ] Projects page access confirmed for both team members.
- [x] Native Kiswahili speakers (Eric Amenya, Daniel Githumbi) reviewed and approved every demo line and `lexicon/sw.yaml` on 20 Oct. Lexicon `review.status` is `approved` and the bundle is rebuilt.
- [ ] Video recorded, under 2:00, uploaded, and the link added to the README.
- [ ] Live demo link from Daniel's deploy added to the README, and `/health` returns `"status": "ok"` on it.
- [ ] Cached fallback checked on the deployed URL with `?demo=cached`.
- [ ] Submitted Mon 26 Oct.
