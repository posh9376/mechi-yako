import { FULL_TIME_S, formatClock } from "../clock";

interface Props {
  clockS: number;
  playing: boolean;
  speed: number;
  onPlayPause: () => void;
  onSeek: (clockS: number) => void;
  onSpeed: (speed: number) => void;
}

const SPEEDS = [30, 60, 120, 300];

export function ReplayControls({ clockS, playing, speed, onPlayPause, onSeek, onSpeed }: Props) {
  const atEnd = clockS >= FULL_TIME_S;
  return (
    <section className="replay" aria-label="Replay controls">
      <button type="button" className="btn btn--primary" onClick={onPlayPause}>
        {playing ? "Pause" : atEnd ? "Replay" : "Play"}
      </button>
      <button type="button" className="btn" onClick={() => onSeek(0)}>
        Kick-off
      </button>
      <button type="button" className="btn" onClick={() => onSeek(55 * 60)}>
        55′ press
      </button>
      <button type="button" className="btn" onClick={() => onSeek(FULL_TIME_S)}>
        Full time
      </button>
      <input
        className="replay__scrubber"
        type="range"
        min={0}
        max={FULL_TIME_S}
        step={15}
        value={clockS}
        aria-label="Match clock"
        aria-valuetext={formatClock(clockS)}
        onChange={(e) => onSeek(Number(e.target.value))}
      />
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
  );
}
