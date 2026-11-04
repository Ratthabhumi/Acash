// Read-only owner-wealth summary: declared external cash plus the latest broker-displayed
// observation. Values are decimal strings computed by Python; this module formats nothing.

export const WEALTH_ENDPOINT = 'http://127.0.0.1:8765/api/upi/wealth';

export interface ExternalAccountView {
  account_ref: string; institution: string; owner_label: string; balance: string; currency: string;
  precision: 'EXACT' | 'APPROXIMATE'; evidence_type: 'OWNER_DECLARED' | 'OWNER_ESTIMATE';
  liquidity_status: 'WITHDRAWABLE' | 'SPENDING'; reserve_eligible: boolean; observed_at: string;
}

export interface ExternalCashView {
  status?: string; code?: string; scope: string; evidence_quality: string;
  accounts: ExternalAccountView[]; total: string; approximate_component: string;
  target: string | null; target_currency: string; gap: string | null;
  reserve_eligible_total: string; designated_reserve_total: string; notes: string[];
}

export interface BrokerObservationView {
  status: string; code?: string; observation_id?: string; broker?: string; observed_at?: string;
  displayed_total?: string; categories?: Record<string, string>; evidence_status?: string;
  arithmetic?: string;
}

export interface ClassificationCoverage {
  status: string; code?: string; instrument_count: number; classified_count: number; unknown_count: number;
  coverage_by_count: string; coverage_by_value: string; by_class?: Record<string, string>;
  note?: string;
}

export interface EconomicAllocation {
  status: string; denominator: string; denominator_value?: string;
  by_class: Record<string, { value: string; weight: string }>; note?: string;
}

export interface WealthComparison {
  status: string; difference: string | null; difference_pct: string | null;
  broker_observed_at?: string; calculated_valuation_date?: string; note?: string;
}

export interface ConsolidatedView {
  status: string; broker_total?: string; broker_observed_at?: string | null; external_cash: string;
  consolidated_total: string | null; evidence_quality: string; note?: string;
}

export interface WealthReport {
  status: string; external_cash?: ExternalCashView; broker_observation?: BrokerObservationView;
  comparison?: WealthComparison; consolidated?: ConsolidatedView; classification?: ClassificationCoverage;
  economic_allocation?: EconomicAllocation;
}

export async function fetchWealth(signal?: AbortSignal): Promise<WealthReport | null> {
  try {
    const response = await fetch(WEALTH_ENDPOINT, {
      method: 'GET', cache: 'no-store', credentials: 'include', referrerPolicy: 'no-referrer', signal,
    });
    if (!response.ok) return null;
    const body: unknown = await response.json().catch(() => null);
    return body && typeof body === 'object' ? (body as WealthReport) : null;
  } catch {
    return null;
  }
}
