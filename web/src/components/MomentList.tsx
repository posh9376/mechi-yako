import { minuteMark } from "../clock";
import { momentTypeLabel } from "../labels";
import type { Language, Moment } from "../types";

interface Props {
  moments: Moment[];
  totalMoments: number;
  selectedId: string | null;
  language: Language;
  onSelect: (id: string) => void;
}

export function MomentList({ moments, totalMoments, selectedId, language, onSelect }: Props) {
  if (totalMoments === 0) {
    return (
      <section className="moments moments--empty" aria-label="Moments">
        <p>No moments were detected for this match.</p>
      </section>
    );
  }
  if (moments.length === 0) {
    return (
      <section className="moments moments--empty" aria-label="Moments">
        <p>No moments yet. Press Play or jump ahead to see them appear.</p>
      </section>
    );
  }
  return (
    <section className="moments" aria-label="Moments">
      <ol className="moments__list">
        {moments.map((m) => (
          <li key={m.id}>
            <button
              type="button"
              className={m.id === selectedId ? "moment is-selected" : "moment"}
              aria-pressed={m.id === selectedId}
              onClick={() => onSelect(m.id)}
            >
              <span className="moment__minute">{minuteMark(m.t_peak)}</span>
              <span className="moment__body">
                <span className={`moment__type moment__type--${m.type}`}>
                  {momentTypeLabel(m.type, language)}
                </span>
                <span className="moment__headline">{m.headline.en}</span>
              </span>
              <span className="moment__team">{m.team}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
