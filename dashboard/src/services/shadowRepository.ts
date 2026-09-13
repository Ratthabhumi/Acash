/**
 * ACASH Shadow Tournament — Read-Only Data Repository
 *
 * Architecture:
 * - Polls /api/shadow/status when a live backend is available.
 * - Falls back to mock demo data with isMockData=true clearly set.
 * - READ-ONLY: zero mutation capability — dashboard never writes to runtime.
 * - No trading credentials handled. No order submission path exists.
 *
 * SHADOW / SIMULATED ONLY — NOT Paper — NOT Live — NOT HYP_003
 */

import { TournamentState, ShadowApiResponse } from '../types/shadow';
import { mockTournamentState } from './shadowMockData';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

// Live API base URL — configure via Vite env variable when backend exists.
// Falls back to mock data if empty/unavailable.
const SHADOW_API_BASE = ((import.meta as unknown) as Record<string, unknown> & { env?: Record<string, string> }).env?.VITE_SHADOW_API_URL ?? '';

const POLL_INTERVAL_MS = 15_000; // 15 seconds

// ---------------------------------------------------------------------------
// Repository interface
// ---------------------------------------------------------------------------

export interface IShadowRepository {
  getState(): Promise<ShadowApiResponse<TournamentState>>;
  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
    onError?: (err: Error) => void
  ): () => void; // Returns unsubscribe function
}

// ---------------------------------------------------------------------------
// Implementation: Mock (no live API configured)
// ---------------------------------------------------------------------------

class MockShadowRepository implements IShadowRepository {
  async getState(): Promise<ShadowApiResponse<TournamentState>> {
    // Refresh the fetchedAt timestamp each call
    const state = {
      ...mockTournamentState,
      _meta: {
        ...mockTournamentState._meta,
        fetchedAtUtc: new Date().toISOString(),
      },
    };
    return {
      ok: true,
      data: state,
      error: null,
      fetchedAtUtc: new Date().toISOString(),
    };
  }

  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
  ): () => void {
    // Immediately fire once
    void this.getState().then(callback);

    const interval = setInterval(() => {
      void this.getState().then(callback);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }
}

// ---------------------------------------------------------------------------
// Implementation: Live API (when VITE_SHADOW_API_URL is set)
// ---------------------------------------------------------------------------

class LiveShadowRepository implements IShadowRepository {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async getState(): Promise<ShadowApiResponse<TournamentState>> {
    const fetchedAt = new Date().toISOString();
    try {
      const resp = await fetch(`${this.baseUrl}/api/shadow/status`, {
        headers: { Accept: 'application/json' },
        // No credentials, no auth headers — read-only public endpoint on private tailnet
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      }

      const data: TournamentState = await resp.json() as TournamentState;
      return { ok: true, data, error: null, fetchedAtUtc: fetchedAt };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        ok: false,
        data: null,
        error: `Shadow API unreachable: ${message}`,
        fetchedAtUtc: fetchedAt,
      };
    }
  }

  subscribe(
    callback: (state: ShadowApiResponse<TournamentState>) => void,
    onError?: (err: Error) => void,
  ): () => void {
    let active = true;

    const poll = async () => {
      if (!active) return;
      try {
        const result = await this.getState();
        if (active) callback(result);
      } catch (err) {
        if (active && onError) {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      }
    };

    void poll();
    const interval = setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }
}

// ---------------------------------------------------------------------------
// Factory — resolves to live or mock based on environment
// ---------------------------------------------------------------------------

function createShadowRepository(): IShadowRepository {
  if (SHADOW_API_BASE && SHADOW_API_BASE.startsWith('http')) {
    return new LiveShadowRepository(SHADOW_API_BASE);
  }
  return new MockShadowRepository();
}

export const shadowRepository: IShadowRepository = createShadowRepository();
