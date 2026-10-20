import { formatClock } from "../clock";
import type { FeedDone, FeedHandlers, FeedMatchEvent, FeedOptions, FeedSnapshot, Moment } from "../types";

/** URL for `GET /matches/{id}/feed` (server-sent events). */
export function feedUrl(matchUrl: string, opts: FeedOptions): string {
  const params = new URLSearchParams({ speed: String(opts.speed) });
  if (opts.startS !== null && opts.startS > 0) params.set("start", formatClock(opts.startS));
  return `${matchUrl}/feed?${params}`;
}

/**
 * Subscribe to the live feed. Closes itself on `done` and on any error: EventSource
 * otherwise reconnects on its own and the server would replay from the original start.
 */
export function openFeed(url: string, handlers: FeedHandlers): () => void {
  const es = new EventSource(url);
  let closed = false;
  const close = () => {
    closed = true;
    es.close();
  };

  const on = <T>(name: string, handle: (payload: T) => void) => {
    es.addEventListener(name, (e) => {
      if (closed) return;
      handle(JSON.parse((e as MessageEvent<string>).data) as T);
    });
  };

  on<FeedSnapshot>("snapshot", handlers.onSnapshot);
  on<FeedMatchEvent>("match_event", handlers.onEvent);
  on<Moment>("moment", handlers.onMoment);
  on<FeedDone>("done", (done) => {
    close();
    handlers.onDone(done);
  });
  es.onerror = () => {
    if (closed) return;
    close();
    handlers.onError("Live feed disconnected");
  };

  return close;
}
