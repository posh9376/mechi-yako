import type { DataSource, MomentSource } from "../types";
import { createApiSource } from "./api";
import { createCachedSource } from "./cached";
import { createFixtureSource } from "./fixtures";

export interface SourceConfig {
  apiBaseUrl: string;
  momentSource: MomentSource;
  cached: boolean;
}

/**
 * `?demo=cached` → pre-rendered bundle, no network.
 * `VITE_API_BASE_URL` set → live API (`?moments=fixture` pins fixture moments).
 * Otherwise → repo fixtures.
 */
export function readSourceConfig(): SourceConfig {
  const params = new URLSearchParams(window.location.search);
  return {
    apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "").trim(),
    momentSource: params.get("moments") === "fixture" ? "fixture" : "live",
    cached: params.get("demo") === "cached",
  };
}

export function createDataSource(config: SourceConfig = readSourceConfig()): DataSource {
  if (config.cached) return createCachedSource();
  if (config.apiBaseUrl) return createApiSource(config.apiBaseUrl, config.momentSource);
  return createFixtureSource();
}
