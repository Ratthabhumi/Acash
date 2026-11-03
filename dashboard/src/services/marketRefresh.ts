// Client for the loopback /api/upi/market/ routes. The page only displays what Python returns:
// provider states come from the backend capability checks, prices and values from PPDS, and no
// credential ever reaches the browser.

export const MARKET_ENDPOINT = 'http://127.0.0.1:8765/api/upi/market/';
export const PRICE_PROVIDERS = ['ALPACA_BASIC', 'MASSIVE_BASIC'] as const;

export interface ProviderStatus { provider_id: string; status: string; detail?: string }

export interface MarketQuote {
  security_id: string; provider_id: string; price: string; currency: string; price_type: string;
  coverage: string; market_date: string; market_timestamp: string | null; retrieved_at: string; used: boolean;
}

export interface RefreshRecord {
  refresh_id: string; requested_at: string; completed_at: string;
  provider_statuses: Record<string, string>; requested_symbols_count: number; priced_symbols_count: number;
  stale_symbols_count: number; unavailable_symbols_count: number; valuation_status: string; fx_status: string;
  report_generation_id: string | null;
  meta?: { market_date: string | null; holdings_observed_on: string; flags: string[]; price_sources: string[];
           coverage: Record<string, number> };
  quotes?: MarketQuote[];
}

export interface MarketStatus {
  status: string; odr_004?: string; odr_001?: string; providers?: ProviderStatus[]; last_refresh?: RefreshRecord | null;
}

export interface MarketCall<T> { http: number; body: T }

export const PROVIDER_INFO: Record<string, { name: string; coverage: string }> = {
  ALPACA_BASIC: { name: 'Alpaca Basic', coverage: 'IEX real-time (single venue, not consolidated)' },
  MASSIVE_BASIC: { name: 'Massive Basic', coverage: 'Previous session close (EOD)' },
  BOT_REFERENCE_FX: { name: 'BOT FX', coverage: 'Reference USD/THB (not executable)' },
  WEBULL_TH_OPENAPI: { name: 'Webull Thailand', coverage: 'Pending entitlement · no adapter' },
};

export const MARKET_TH: Record<string, string> = {
  READY: 'พร้อมใช้ (Owner รับรองสิทธิ์แล้ว ยังไม่ใช่หลักฐานว่าดึงจริงสำเร็จ)',
  NOT_CONFIGURED: 'ยังไม่มีตัวเชื่อมต่อ',
  GOVERNANCE_REQUIRED: 'ต้องได้รับอนุญาตใน ODR-004 ก่อน (scope_providers)',
  CREDENTIALS_REQUIRED: 'ยังไม่ได้ตั้งค่า API key ในเครื่อง (Windows Credential Manager)',
  ENTITLEMENT_REQUIRED: 'ยังไม่ได้ยืนยันสิทธิ์ข้อมูลกับผู้ให้บริการ',
  DISPLAY_RIGHTS_UNVERIFIED: 'ยังไม่ได้ยืนยันสิทธิ์การแสดงผล',
  QUERIED: 'ดึงข้อมูลแล้ว',
  NOT_NEEDED: 'ไม่ต้องใช้ (ได้ราคาครบจากแหล่งก่อนหน้า)',
  PROVIDER_ACCESS_DENIED: 'ผู้ให้บริการปฏิเสธ (key ผิดหรือไม่มีสิทธิ์)',
  PROVIDER_RATE_LIMITED: 'ถูกจำกัดจำนวนคำขอ ลองใหม่ภายหลัง',
  PROVIDER_UNAVAILABLE: 'ผู้ให้บริการไม่พร้อม',
  PROVIDER_UNREACHABLE: 'เชื่อมต่อผู้ให้บริการไม่ได้',
  PROVIDER_RESPONSE_INVALID: 'ข้อมูลตอบกลับผิดรูปแบบ จึงไม่ใช้',
  MARKET_DATA_AUTHORIZATION_REQUIRED: 'ODR-004 ยังไม่ได้รับการรับรอง จึงดึงราคาไม่ได้',
  NO_READY_PRICE_PROVIDER: 'ยังไม่มีแหล่งราคาที่พร้อมใช้',
  REFRESH_IN_PROGRESS: 'กำลังอัปเดตอยู่แล้ว',
  RATE_LIMITED: 'กดถี่เกินไป รอสักครู่',
  INPUTS_CHANGED_DURING_REFRESH: 'ข้อมูลพอร์ตเปลี่ยนระหว่างอัปเดต ลองใหม่',
  NO_INPUT: 'ยังไม่มีข้อมูลพอร์ต ให้กรอกใน Setup Wizard ก่อน',
  INDICATIVE_VALUATION: 'มูลค่าโดยประมาณ (ราคาจากแหล่งเดียว วันเดียวกันทั้งหมด)',
  MIXED_SOURCE_INDICATIVE_VALUATION: 'มูลค่าโดยประมาณจากหลายแหล่งราคา',
  PARTIAL_INDICATIVE_VALUATION: 'มูลค่าบางส่วน: มีรายการที่ไม่มีราคา/ไม่มีจำนวน ไม่ได้นับรวม (ไม่ใช่มูลค่าพอร์ตทั้งหมด)',
  UNAVAILABLE: 'ไม่มีราคาที่ใช้ได้ จึงไม่คำนวณมูลค่า',
  NOT_REQUIRED: 'ไม่ต้องใช้อัตราแลกเปลี่ยน',
  REFERENCE_FX_ON_MARKET_DATE: 'ใช้อัตราอ้างอิง ธปท. วันเดียวกับราคา (ไม่ใช่อัตราแลกจริงของ Dime!)',
  FX_UNAVAILABLE_FOR_MARKET_DATE: 'ไม่มีอัตราแลกเปลี่ยนของวันที่ราคา',
  FX_PROVIDER_NOT_READY: 'ยังไม่มีแหล่งอัตราแลกเปลี่ยนที่พร้อม',
  NOT_REQUESTED_NO_PRICES: 'ไม่ได้ขออัตราแลกเปลี่ยนเพราะไม่มีราคา',
};

export const marketTh = (code: string): string =>
  MARKET_TH[code] ?? (code.startsWith('PRICES_ONLY_') ? 'ได้ราคาแล้วแต่คำนวณมูลค่าไม่ได้ (ขาดอัตราแลกเปลี่ยน) จึงคงรายงานเดิมไว้' : code);

export function refreshBlocker(status: MarketStatus | null): string | null {
  if (!status || status.status !== 'OK') return status?.status ?? 'SERVICE_UNAVAILABLE';
  if (status.odr_004 !== 'RATIFIED') return 'MARKET_DATA_AUTHORIZATION_REQUIRED';
  const ready = (status.providers ?? []).some((p) => (PRICE_PROVIDERS as readonly string[]).includes(p.provider_id) && p.status === 'READY');
  return ready ? null : 'NO_READY_PRICE_PROVIDER';
}

export async function callMarket<T>(method: 'GET' | 'POST', route: 'status' | 'refresh' | 'view',
                                    signal?: AbortSignal): Promise<MarketCall<T | { status: string }>> {
  try {
    const response = await fetch(MARKET_ENDPOINT + route, {
      method,
      headers: method === 'POST' ? { 'Content-Type': 'application/json' } : undefined,
      body: method === 'POST' ? '{}' : undefined,
      cache: 'no-store',
      credentials: 'include',
      referrerPolicy: 'no-referrer',
      signal,
    });
    const body: unknown = await response.json().catch(() => null);
    return { http: response.status, body: (body && typeof body === 'object' ? body : { status: 'INVALID_RESPONSE' }) as T };
  } catch {
    return { http: 0, body: { status: 'SERVICE_UNAVAILABLE' } };
  }
}
