import syntheticFull from '../fixtures/upi_synthetic_view.json';
import syntheticEvidenceOnly from '../fixtures/upi_synthetic_evidence_only_view.json';
import { LoadState, PRIVATE_ENDPOINT, TOKEN_HEADER, classifyResponse, classifyView } from './upiView';
import { ApiResult, INPUT_ENDPOINT } from './privateInput';

export type SyntheticVariant = 'FULL_REPORT' | 'EVIDENCE_ONLY_REPORT';

// Modes never fall back to each other: a failed private load is reported as its own state
// and synthetic fixtures are never substituted for owner data.
export const upiRepository = {
  loadSynthetic(variant: SyntheticVariant): LoadState {
    return classifyView(variant === 'FULL_REPORT' ? syntheticFull : syntheticEvidenceOnly, 'SYNTHETIC_DEMO');
  },

  async loadOwnerPrivate(token: string, signal?: AbortSignal): Promise<LoadState> {
    if (!token) return { status: 'AUTHORIZATION_REQUIRED', detail: 'SESSION_TOKEN_REQUIRED' };
    let response: Response;
    try {
      response = await fetch(PRIVATE_ENDPOINT, {
        method: 'GET',
        headers: { [TOKEN_HEADER]: token },
        cache: 'no-store',
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        signal,
      });
    } catch {
      return { status: 'SERVICE_UNAVAILABLE', detail: 'LOOPBACK_SERVICE_NOT_REACHABLE' };
    }
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      return response.ok
        ? { status: 'INVALID_REPORT', detail: 'VIEW_NOT_JSON' }
        : classifyResponse(response.status, null);
    }
    return classifyResponse(response.status, body);
  },

  async callInput(token: string, method: 'GET' | 'PUT' | 'POST', route: string, payload?: unknown,
                  signal?: AbortSignal): Promise<ApiResult> {
    try {
      const response = await fetch(INPUT_ENDPOINT + route, {
        method,
        headers: payload === undefined ? { [TOKEN_HEADER]: token } : { [TOKEN_HEADER]: token, 'Content-Type': 'application/json' },
        body: payload === undefined ? undefined : JSON.stringify(payload),
        cache: 'no-store',
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        signal,
      });
      const body: unknown = await response.json().catch(() => null);
      return { http: response.status, body: (body && typeof body === 'object' ? body : { status: 'INVALID_RESPONSE' }) as ApiResult['body'] };
    } catch {
      return { http: 0, body: { status: 'SERVICE_UNAVAILABLE' } };
    }
  },
};
