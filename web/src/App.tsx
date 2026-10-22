import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FULL_TIME_S, parseClock, scoreAt } from "./clock";
import { LiveControls } from "./components/LiveControls";
import { LowerThird } from "./components/LowerThird";
import { MomentDetail, type NarrationState } from "./components/MomentDetail";
import { MomentList } from "./components/MomentList";
import { ReplayControls } from "./components/ReplayControls";
import { ScoreBar } from "./components/ScoreBar";
import { Switches } from "./components/Switches";
import { WhyPanel, type ExplanationState } from "./components/WhyPanel";
import { useLiveFeed } from "./live/useLiveFeed";
import type { DataSource, Language, MatchData, MatchMeta, Moment, PersonaId, Register } from "./types";

type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: T };

type Mode = "live" | "replay";

const TICK_MS = 100;

interface Props {
  source: DataSource;
  onUseCached?: () => void;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function byPeak(a: Moment, b: Moment): number {
  return parseClock(a.t_peak) - parseClock(b.t_peak) || b.significance - a.significance;
}

export function App({ source, onUseCached }: Props) {
  const liveCapable = source.momentSource === "live" && !!source.openFeed && !!source.loadMeta;
  const [mode, setMode] = useState<Mode>(liveCapable ? "live" : "replay");
  const [meta, setMeta] = useState<LoadState<MatchMeta>>({ status: "idle" });
  const [replay, setReplay] = useState<LoadState<MatchData>>({ status: "idle" });
  const [clockS, setClockS] = useState(FULL_TIME_S);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(120);
  const [persona, setPersona] = useState<PersonaId>("casual");
  const [language, setLanguage] = useState<Language>("en");
  const [register, setRegister] = useState<Register | "auto">("auto");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [narration, setNarration] = useState<NarrationState>({ status: "idle" });
  const [narrationNonce, setNarrationNonce] = useState(0);
  const [fetchedExplanation, setFetchedExplanation] = useState<ExplanationState>({ status: "idle" });
  const [explanationNonce, setExplanationNonce] = useState(0);
  const live = useLiveFeed(source, speed);

  const loadMeta = useCallback(() => {
    if (!source.loadMeta) return;
    setMeta({ status: "loading" });
    source
      .loadMeta()
      .then(({ match }) => setMeta({ status: "ready", data: match }))
      .catch((err: unknown) => setMeta({ status: "error", message: errorMessage(err) }));
  }, [source]);

  const loadReplay = useCallback(() => {
    setReplay({ status: "loading" });
    source
      .loadMatch()
      .then((data) => setReplay({ status: "ready", data }))
      .catch((err: unknown) => setReplay({ status: "error", message: errorMessage(err) }));
  }, [source]);

  useEffect(() => {
    if (mode === "live" && meta.status === "idle") loadMeta();
    if (mode === "replay" && replay.status === "idle") loadReplay();
  }, [mode, meta.status, replay.status, loadMeta, loadReplay]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setClockS((c) => {
        const next = Math.min(FULL_TIME_S, c + (speed * TICK_MS) / 1000);
        if (next >= FULL_TIME_S) setPlaying(false);
        return next;
      });
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [playing, speed]);

  const replayData = replay.status === "ready" ? replay.data : null;
  const isLive = mode === "live";
  const shownClockS = isLive ? live.clockS : clockS;
  const following = isLive ? live.status === "live" : playing;

  const visibleMoments = useMemo(() => {
    if (isLive) return [...live.moments].sort(byPeak);
    if (!replayData) return [];
    return replayData.moments.filter((m) => parseClock(m.t_peak) <= clockS).sort(byPeak);
  }, [isLive, live.moments, replayData, clockS]);

  // Follow the newest moment while playing; keep the user's pick when it is still visible.
  const lastVisibleCount = useRef(0);
  useEffect(() => {
    const grew = visibleMoments.length > lastVisibleCount.current;
    lastVisibleCount.current = visibleMoments.length;
    const stillVisible = visibleMoments.some((m) => m.id === selectedId);
    if (visibleMoments.length === 0) {
      if (selectedId !== null) setSelectedId(null);
    } else if (!stillVisible || (following && grew)) {
      setSelectedId(visibleMoments[visibleMoments.length - 1].id);
    }
  }, [visibleMoments, selectedId, following]);

  const selected = visibleMoments.find((m) => m.id === selectedId) ?? null;
  const selectedMomentId = selected?.id ?? null;

  useEffect(() => {
    if (!selectedMomentId) {
      setNarration({ status: "idle" });
      return;
    }
    let cancelled = false;
    setNarration({ status: "loading" });
    source
      .narrate({
        momentId: selectedMomentId,
        persona,
        language,
        register: register === "auto" ? null : register,
      })
      .then((result) => {
        if (cancelled) return;
        setNarration(result ? { status: "ready", narration: result } : { status: "unavailable" });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setNarration({ status: "error", message: errorMessage(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [source, selectedMomentId, persona, language, register, narrationNonce]);

  // The explanation depends only on the moment, so persona/language switches reuse it.
  useEffect(() => {
    if (!selectedMomentId || !source.explain) {
      setFetchedExplanation({ status: "idle" });
      return;
    }
    let cancelled = false;
    setFetchedExplanation({ status: "loading" });
    source
      .explain(selectedMomentId)
      .then((explanation) => {
        if (!cancelled) setFetchedExplanation({ status: "ready", explanation });
      })
      .catch((err: unknown) => {
        if (!cancelled) setFetchedExplanation({ status: "error", message: errorMessage(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [source, selectedMomentId, explanationNonce]);

  const embedded = narration.status === "ready" ? narration.narration.explanation : undefined;
  const explanation: ExplanationState = source.explain
    ? fetchedExplanation
    : embedded
      ? { status: "ready", explanation: embedded }
      : narration.status === "loading"
        ? { status: "loading" }
        : { status: "idle" };

  const handlePlayPause = () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (clockS >= FULL_TIME_S) setClockS(0);
    setPlaying(true);
  };

  const switchToReplay = () => {
    setClockS(live.status === "idle" ? FULL_TIME_S : live.clockS);
    setPlaying(false);
    live.reset();
    setMode("replay");
  };

  const switchToLive = () => {
    setPlaying(false);
    live.reset();
    setMode("live");
  };

  const modeToggle = liveCapable && (
    <div className="segmented" role="radiogroup" aria-label="Feed mode">
      <button
        type="button"
        role="radio"
        aria-checked={isLive}
        className={isLive ? "segmented__item is-active" : "segmented__item"}
        onClick={() => !isLive && switchToLive()}
      >
        Live
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={!isLive}
        className={!isLive ? "segmented__item is-active" : "segmented__item"}
        onClick={() => isLive && switchToReplay()}
      >
        Replay
      </button>
    </div>
  );

  const pending = isLive ? meta : replay;
  if (pending.status === "idle" || pending.status === "loading") {
    return (
      <main className="app app--center">
        <p className="muted">Loading match…</p>
      </main>
    );
  }

  if (pending.status === "error") {
    return (
      <main className="app app--center">
        <div className="panel panel--error" role="alert">
          <h1>Could not load the match</h1>
          <p>{pending.message}</p>
          <div className="panel__actions">
            <button type="button" className="btn btn--primary" onClick={isLive ? loadMeta : loadReplay}>
              Try again
            </button>
            {!isLive && liveCapable && (
              <button type="button" className="btn" onClick={switchToLive}>
                Back to live
              </button>
            )}
            {onUseCached && (
              <button type="button" className="btn" onClick={onUseCached}>
                Use cached demo
              </button>
            )}
          </div>
        </div>
      </main>
    );
  }

  const match = isLive ? (pending.data as MatchMeta) : (pending.data as MatchData).match;
  const events = isLive ? live.events : (pending.data as MatchData).events;
  const score = isLive ? live.score : scoreAt(match, events, clockS);
  const sourceLabel = isLive
    ? `${source.label} · live feed`
    : liveCapable
      ? `${source.label} · live moments (replay)`
      : `${source.label} · ${(pending.data as MatchData).momentSource} moments`;

  return (
    <main className="app">
      <div className="topbar">
        <div className="topbar__brand">
          <span className="app__logo">Mechi Yako</span>
          <span className="app__tagline">One match, told your way, in your language.</span>
        </div>
        <div className="topbar__right">
          {modeToggle}
          <span className="app__source" data-testid="source" title={sourceLabel}>
            {sourceLabel}
          </span>
        </div>
      </div>

      <section className="hero" aria-label="Match">
        <ScoreBar match={match} score={score} clockS={shownClockS} />
        {isLive ? (
          <LiveControls
            status={live.status}
            clockS={live.clockS}
            speed={speed}
            error={live.error}
            onStart={live.start}
            onPause={live.pause}
            onResume={live.resume}
            onSpeed={setSpeed}
            onSwitchToReplay={switchToReplay}
          />
        ) : (
          <ReplayControls
            clockS={clockS}
            playing={playing}
            speed={speed}
            onPlayPause={handlePlayPause}
            onSeek={(c) => {
              setPlaying(false);
              setClockS(c);
            }}
            onSpeed={setSpeed}
          />
        )}
      </section>

      <Switches
        persona={persona}
        language={language}
        register={register}
        onPersona={setPersona}
        onLanguage={setLanguage}
        onRegister={setRegister}
      />

      <div className="app__columns">
        <div className="feed">
          <h2 className="feed__title">
            Moments <span className="feed__count">{visibleMoments.length}</span>
          </h2>
          <MomentList
            moments={visibleMoments}
            totalMoments={isLive ? null : (pending.data as MatchData).moments.length}
            waitingMessage={live.status === "idle" ? "Press Go live to start the match feed." : undefined}
            selectedId={selectedId}
            language={language}
            onSelect={setSelectedId}
          />
        </div>
        <div className="stage">
          <MomentDetail
            moment={selected}
            language={language}
            narration={narration}
            onRetry={() => setNarrationNonce((n) => n + 1)}
          />
          <WhyPanel
            moment={selected}
            events={events}
            narration={narration}
            explanation={explanation}
            onRetryExplanation={() => setExplanationNonce((n) => n + 1)}
          />
        </div>
      </div>
      <LowerThird
        match={match}
        score={score}
        clockS={shownClockS}
        moment={selected}
        language={language}
        narration={narration}
      />
      <footer className="app__footer">
        Synthetic data · fictional clubs and players · Kiswahili reviewed by native speakers
      </footer>
    </main>
  );
}
