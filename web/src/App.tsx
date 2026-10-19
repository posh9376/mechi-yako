import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FULL_TIME_S, parseClock, scoreAt } from "./clock";
import { LowerThird } from "./components/LowerThird";
import { MomentDetail, type NarrationState } from "./components/MomentDetail";
import { MomentList } from "./components/MomentList";
import { ReplayControls } from "./components/ReplayControls";
import { ScoreBar } from "./components/ScoreBar";
import { Switches } from "./components/Switches";
import { WhyPanel } from "./components/WhyPanel";
import type { DataSource, Language, MatchData, PersonaId, Register } from "./types";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: MatchData };

const TICK_MS = 100;

interface Props {
  source: DataSource;
  onUseCached?: () => void;
}

export function App({ source, onUseCached }: Props) {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [clockS, setClockS] = useState(FULL_TIME_S);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(120);
  const [persona, setPersona] = useState<PersonaId>("casual");
  const [language, setLanguage] = useState<Language>("en");
  const [register, setRegister] = useState<Register | "auto">("auto");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [narration, setNarration] = useState<NarrationState>({ status: "idle" });
  const [narrationNonce, setNarrationNonce] = useState(0);

  const loadMatch = useCallback(() => {
    setLoad({ status: "loading" });
    source
      .loadMatch()
      .then((data) => setLoad({ status: "ready", data }))
      .catch((err: unknown) =>
        setLoad({ status: "error", message: err instanceof Error ? err.message : String(err) }),
      );
  }, [source]);

  useEffect(loadMatch, [loadMatch]);

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

  const data = load.status === "ready" ? load.data : null;

  const visibleMoments = useMemo(() => {
    if (!data) return [];
    return data.moments
      .filter((m) => parseClock(m.t_peak) <= clockS)
      .sort((a, b) => parseClock(a.t_peak) - parseClock(b.t_peak) || b.significance - a.significance);
  }, [data, clockS]);

  // Follow the newest moment while playing; keep the user's pick when it is still visible.
  const lastVisibleCount = useRef(0);
  useEffect(() => {
    const grew = visibleMoments.length > lastVisibleCount.current;
    lastVisibleCount.current = visibleMoments.length;
    const stillVisible = visibleMoments.some((m) => m.id === selectedId);
    if (visibleMoments.length === 0) {
      if (selectedId !== null) setSelectedId(null);
    } else if (!stillVisible || (playing && grew)) {
      setSelectedId(visibleMoments[visibleMoments.length - 1].id);
    }
  }, [visibleMoments, selectedId, playing]);

  const selected = visibleMoments.find((m) => m.id === selectedId) ?? null;

  useEffect(() => {
    if (!selected) {
      setNarration({ status: "idle" });
      return;
    }
    let cancelled = false;
    setNarration({ status: "loading" });
    source
      .narrate({
        momentId: selected.id,
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
        setNarration({ status: "error", message: err instanceof Error ? err.message : String(err) });
      });
    return () => {
      cancelled = true;
    };
  }, [source, selected, persona, language, register, narrationNonce]);

  const handlePlayPause = () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (clockS >= FULL_TIME_S) setClockS(0);
    setPlaying(true);
  };

  if (load.status === "loading") {
    return (
      <main className="app app--center">
        <p className="muted">Loading match…</p>
      </main>
    );
  }

  if (load.status === "error") {
    return (
      <main className="app app--center">
        <div className="panel panel--error" role="alert">
          <h1>Could not load the match</h1>
          <p>{load.message}</p>
          <div className="panel__actions">
            <button type="button" className="btn btn--primary" onClick={loadMatch}>
              Try again
            </button>
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

  const { match, events, moments } = load.data;
  const score = scoreAt(match, events, clockS);

  return (
    <main className="app">
      <div className="app__brand">
        <span className="app__logo">Mechi Yako</span>
        <span className="app__tagline">One match, told your way, in your language.</span>
        <span className="app__source" data-testid="source">
          {source.label} · {load.data.momentSource} moments
        </span>
      </div>
      <ScoreBar match={match} score={score} clockS={clockS} />
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
      <Switches
        persona={persona}
        language={language}
        register={register}
        onPersona={setPersona}
        onLanguage={setLanguage}
        onRegister={setRegister}
      />
      <div className="app__columns">
        <MomentList
          moments={visibleMoments}
          totalMoments={moments.length}
          selectedId={selectedId}
          language={language}
          onSelect={setSelectedId}
        />
        <MomentDetail
          moment={selected}
          language={language}
          narration={narration}
          onRetry={() => setNarrationNonce((n) => n + 1)}
        />
      </div>
      <WhyPanel moment={selected} events={events} narration={narration} />
      <LowerThird
        match={match}
        score={score}
        clockS={clockS}
        moment={selected}
        language={language}
        narration={narration}
      />
      <footer className="app__footer">
        Synthetic data · fictional clubs and players · Kiswahili lines pending native-speaker review
      </footer>
    </main>
  );
}
