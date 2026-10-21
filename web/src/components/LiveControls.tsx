import { FULL_TIME_S, formatClock } from "../clock";
import type { LiveStatus } from "../live/useLiveFeed";
import { SPEEDS } from "./ReplayControls";

const JOIN_AT_S = 55 * 60;

interface Props {
  status: LiveStatus;
  clockS: number;
  speed: number;
  error: string | null;
  onStart: (fromS: number) => void;
  onPause: () => void;
  onResume: () => void;
  onSpeed: (speed: number) => void;
  onSwitchToReplay: () => void;
}

function pillText(status: LiveStatus, clockS: number): string {
  switch (status) {
    case "idle":
      return "Ready";
    case "connecting":
      return "Connecting…";
    case "live":
      return `LIVE ${Math.floor(clockS / 60)}′`;
    case "paused":
      return "Paused";
    case "ended":
      return "Full time";
    case "error":
      return "Disconnected";
  }
}

export function LiveControls({
  status,
  clockS,
  speed,
  error,
  onStart,
  onPause,
  onResume,
  onSpeed,
  onSwitchToReplay,
}: Props) {
  const primary =
    status === "idle"
      ? { label: "Go live", action: () => onStart(0) }
      : status === "live" || status === "connecting"
        ? { label: "Pause", action: onPause }
        : status === "paused"
          ? { label: "Resume", action: onResume }
          : status === "error"
            ? { label: "Retry", action: onResume }
            : { label: "Restart", action: () => onStart(0) };
  const showRestart = status === "live" || status === "paused" || status === "error";
  const pct = Math.min(100, (clockS / FULL_TIME_S) * 100);

  return (
    <>
      <section className="live" aria-label="Live feed controls">
        <span className={`live__pill live__pill--${status}`} data-testid="live-status" aria-live="polite">
          {pillText(status, clockS)}
        </span>
        <button type="button" className="btn btn--primary" onClick={primary.action}>
          {primary.label}
        </button>
        {showRestart && (
          <button type="button" className="btn" onClick={() => onStart(0)}>
            Restart
          </button>
        )}
        <button type="button" className="btn" onClick={() => onStart(JOIN_AT_S)}>
          Join at 55′
        </button>
        <div
          className="live__progress"
          role="progressbar"
          aria-label="Match progress"
          aria-valuemin={0}
          aria-valuemax={FULL_TIME_S}
          aria-valuenow={Math.floor(clockS)}
          aria-valuetext={formatClock(clockS)}
        >
          <span className="live__progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <label className="replay__speed">
          Speed
          <select value={speed} onChange={(e) => onSpeed(Number(e.target.value))}>
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
        </label>
      </section>
      {status === "error" && (
        <div className="live__error" role="alert">
          <span>{error ?? "Live feed disconnected"}. The API may have stopped.</span>
          <div className="panel__actions">
            <button type="button" className="btn btn--primary" onClick={onResume}>
              Retry
            </button>
            <button type="button" className="btn" onClick={onSwitchToReplay}>
              Switch to replay
            </button>
          </div>
        </div>
      )}
    </>
  );
}
