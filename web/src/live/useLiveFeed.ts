import { useCallback, useEffect, useRef, useState } from "react";
import { FULL_TIME_S, parseClock } from "../clock";
import type { DataSource, MatchEvent, Moment } from "../types";

export type LiveStatus = "idle" | "connecting" | "live" | "paused" | "ended" | "error";

const TICK_MS = 100;

export interface LiveFeed {
  status: LiveStatus;
  clockS: number;
  score: [number, number];
  events: MatchEvent[];
  moments: Moment[];
  error: string | null;
  /** Open a fresh feed from `fromS` (0 = kick-off), dropping anything received so far. */
  start(fromS: number): void;
  pause(): void;
  resume(): void;
  /** Close the feed and return to the not-started state. */
  reset(): void;
}

function appendUnique<T extends { id: string }>(list: T[], item: T): T[] {
  return list.some((x) => x.id === item.id) ? list : [...list, item];
}

/**
 * State for `/feed`. The server paces events; between frames the clock is interpolated
 * from the last frame's match time at `speed` match-seconds per second. Pause closes the
 * stream and resume reopens it from the last event received; the server's snapshot then
 * replaces the lists, so nothing is duplicated or skipped.
 */
export function useLiveFeed(source: DataSource, speed: number): LiveFeed {
  const [status, setStatus] = useState<LiveStatus>("idle");
  const [clockS, setClockS] = useState(0);
  const [score, setScore] = useState<[number, number]>([0, 0]);
  const [events, setEvents] = useState<MatchEvent[]>([]);
  const [moments, setMoments] = useState<Moment[]>([]);
  const [error, setError] = useState<string | null>(null);

  const closeRef = useRef<(() => void) | null>(null);
  const sessionRef = useRef(0);
  const anchorRef = useRef<{ clockS: number; at: number } | null>(null);
  const lastEventSRef = useRef(0);
  const speedRef = useRef(speed);
  const statusRef = useRef<LiveStatus>("idle");

  const updateStatus = useCallback((next: LiveStatus) => {
    statusRef.current = next;
    setStatus(next);
  }, []);

  const disconnect = useCallback(() => {
    sessionRef.current += 1;
    closeRef.current?.();
    closeRef.current = null;
    anchorRef.current = null;
  }, []);

  const connect = useCallback(
    (fromS: number, keepLists: boolean) => {
      if (!source.openFeed) return;
      disconnect();
      const session = sessionRef.current;
      const current = () => session === sessionRef.current;
      const anchor = (s: number) => {
        anchorRef.current = { clockS: s, at: performance.now() };
        setClockS((c) => (keepLists ? Math.max(c, s) : s));
      };

      updateStatus("connecting");
      setError(null);
      lastEventSRef.current = fromS;
      if (!keepLists) {
        setEvents([]);
        setMoments([]);
        setScore([0, 0]);
        setClockS(fromS);
      }

      closeRef.current = source.openFeed(
        { speed: speedRef.current, startS: fromS },
        {
          onSnapshot(snapshot) {
            if (!current()) return;
            setEvents(snapshot.events);
            setMoments(snapshot.moments);
            setScore(snapshot.score);
            anchor(parseClock(snapshot.clock));
            updateStatus("live");
          },
          onEvent(frame) {
            if (!current()) return;
            setEvents((list) => appendUnique(list, frame.event));
            setScore(frame.score);
            lastEventSRef.current = parseClock(frame.clock);
            anchor(lastEventSRef.current);
          },
          onMoment(moment) {
            if (!current()) return;
            setMoments((list) => appendUnique(list, moment));
          },
          onDone(done) {
            if (!current()) return;
            closeRef.current = null;
            anchorRef.current = null;
            setScore(done.score);
            setClockS(FULL_TIME_S);
            updateStatus("ended");
          },
          onError(message) {
            if (!current()) return;
            closeRef.current = null;
            anchorRef.current = null;
            setError(message);
            updateStatus("error");
          },
        },
      );
    },
    [source, disconnect, updateStatus],
  );

  const start = useCallback((fromS: number) => connect(fromS, false), [connect]);

  const pause = useCallback(() => {
    if (statusRef.current !== "live" && statusRef.current !== "connecting") return;
    disconnect();
    updateStatus("paused");
  }, [disconnect, updateStatus]);

  const resume = useCallback(() => connect(lastEventSRef.current, true), [connect]);

  const reset = useCallback(() => {
    disconnect();
    lastEventSRef.current = 0;
    setEvents([]);
    setMoments([]);
    setScore([0, 0]);
    setClockS(0);
    setError(null);
    updateStatus("idle");
  }, [disconnect, updateStatus]);

  useEffect(() => {
    if (speedRef.current === speed) return;
    speedRef.current = speed;
    if (statusRef.current === "live" || statusRef.current === "connecting") {
      connect(lastEventSRef.current, true);
    }
  }, [speed, connect]);

  useEffect(() => {
    if (status !== "live") return;
    const id = window.setInterval(() => {
      const a = anchorRef.current;
      if (!a) return;
      const now = Math.min(FULL_TIME_S, a.clockS + ((performance.now() - a.at) / 1000) * speedRef.current);
      setClockS((c) => Math.max(c, now));
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [status]);

  useEffect(() => disconnect, [disconnect]);

  return { status, clockS, score, events, moments, error, start, pause, resume, reset };
}
