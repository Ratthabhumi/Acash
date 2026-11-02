// Setup Wizard documents for the loopback input routes (requests go through upiRepository).
// Documents are the canonical Python schemas (ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_2,
// ACASH_PRIVATE_CAPACITY_V1); every amount stays a string typed by the Owner. Validation,
// valuation and reconciliation happen only in Python.

export const INPUT_ENDPOINT = 'http://127.0.0.1:8765/api/upi/input/';
export const SNAPSHOT_SCHEMA = 'ACASH_PRIVATE_PORTFOLIO_SNAPSHOT_V1_2';
export const CAPACITY_SCHEMA = 'ACASH_PRIVATE_CAPACITY_V1';
export const OWNER_DATA_CLASS = 'OWNER_PRIVATE_OBSERVATION';
export const ACCOUNT_ROLES = ['LONG_TERM', 'QUANT_RESEARCH', 'CASH_RESERVE', 'OTHER'] as const;
export const CASH_KINDS = ['SETTLED', 'ACCRUED_INTEREST'] as const;
export const CLASSIFICATIONS = ['UNKNOWN', 'CORE_DIVERSIFIED', 'CORE_CONCENTRATED', 'SATELLITE', 'THEMATIC', 'SPECULATIVE'] as const;
export const INSTRUMENT_TYPES = ['', 'COMMON_STOCK', 'ETF', 'ADR', 'DR', 'CFD', 'MUTUAL_FUND', 'OTHER'] as const;

export interface Amount { amount: string; currency: string }
export interface SubTotal extends Amount { sub_portfolio: string }
export interface CashLine { currency: string; amount: string; kind: string; sub_portfolio?: string }
export interface Position {
  security_id: string; sub_portfolio: string; quantity?: string; cost_basis_total?: string; cost_basis_currency?: string;
  observed_market_value?: string; observed_market_value_currency?: string;
}
export interface Account {
  account_ref: string; broker: string; role: string; base_currency: string; reported_total?: Amount;
  sub_portfolio_totals?: SubTotal[]; cash?: CashLine[]; positions?: Position[];
}
export interface FxRate { from: string; to: string; rate: string; as_of: string; source_id: string }
export interface Price { security_id: string; currency: string; price: string; as_of: string; published_at?: string; source_id: string }
export interface Security {
  security_id: string; classification: string; methodology: string; evidence_ref?: string; instrument_type?: string;
  exchange_mic?: string; isin?: string; figi?: string; trading_currency?: string;
}
export interface SnapshotDoc {
  schema: string; data_class: string; snapshot_id: string; observed_at: string; valuation_date: string;
  evidence_source: string; reporting_currency: string; report_currencies: string[]; fx_rates: FxRate[];
  prices: Price[]; securities: Security[]; accounts: Account[];
}
export const CAPACITY_FIELDS = [
  'monthly_income_thb', 'essential_expenses_thb', 'obligations_thb', 'emergency_reserve_thb', 'reserve_target_months',
  'planned_contribution_thb', 'flexible_contribution_thb', 'exceptional_expenses_12m_thb', 'quant_budget_thb',
] as const;
export type CapacityField = typeof CAPACITY_FIELDS[number];
export type CapacityDoc = { schema: string; data_class: string; horizon_years: number | string } & Record<CapacityField, string>;

export const emptySnapshot = (): SnapshotDoc => ({
  schema: SNAPSHOT_SCHEMA, data_class: OWNER_DATA_CLASS, snapshot_id: 'OWNER_SNAPSHOT', observed_at: '', valuation_date: '',
  evidence_source: 'MANUAL_SNAPSHOT', reporting_currency: 'THB', report_currencies: ['THB'], fx_rates: [], prices: [],
  securities: [], accounts: [],
});

export const emptyCapacity = (): CapacityDoc => ({
  schema: CAPACITY_SCHEMA, data_class: OWNER_DATA_CLASS, horizon_years: '',
  ...Object.fromEntries(CAPACITY_FIELDS.map((f) => [f, ''])) as Record<CapacityField, string>,
});

const PLACEHOLDER = /^REPLACE_/i;

/** Template placeholders become empty fields so the Owner types every value. */
export function clearPlaceholders<T>(node: T): T {
  if (typeof node === 'string') return (PLACEHOLDER.test(node) ? '' : node) as T;
  if (Array.isArray(node)) return node.map(clearPlaceholders) as T;
  if (node && typeof node === 'object') {
    return Object.fromEntries(Object.entries(node).map(([k, v]) => [k, clearPlaceholders(v)])) as T;
  }
  return node;
}

/** Drops empty optional strings, empty lists and half-empty totals; never fills in a value. */
export function compact<T>(node: T): T {
  if (Array.isArray(node)) return node.map(compact) as T;
  if (node && typeof node === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(node)) {
      const c = compact(v);
      if (c === '' || c === undefined) continue;
      if (Array.isArray(c) && c.length === 0 && k !== 'fx_rates' && k !== 'prices' && k !== 'securities' && k !== 'accounts') continue;
      if (k === 'reported_total' && c && typeof c === 'object' && !(c as Amount).amount) continue;
      out[k] = c;
    }
    return out as T;
  }
  return node;
}

/** Capacity horizon is the only integer field; it is sent as typed when not a whole number so Python rejects it. */
export function capacityForSave(doc: CapacityDoc): CapacityDoc {
  const h = String(doc.horizon_years).trim();
  return compact({ ...doc, horizon_years: /^\d+$/.test(h) ? Number(h) : h });
}

export const isDecimalText = (v: string) => /^\d+(\.\d+)?$/.test(v.trim());

export interface ApiResult { http: number; body: Record<string, unknown> & { status: string } }

export interface Issue { code: string; where?: string }

export const MESSAGES_TH: Record<string, string> = {
  PRIVATE_FX_RATE_MISSING: 'ขาดอัตราแลกเปลี่ยนสำหรับคู่สกุลเงินนี้ ให้กรอกอัตราตามที่แอปแสดง ระบบไม่สร้างอัตรากลับด้านให้เอง',
  PPDS_CONSOLIDATION_FX_MISSING: 'ขาดอัตราแลกเปลี่ยนที่ใช้รวมยอดเป็นสกุลเงินรายงาน ให้เพิ่มอัตราในขั้นตอนสกุลเงิน',
  PRIVATE_DUPLICATE_CASH_LINE: 'มีรายการเงินสดซ้ำในบัญชีเดียวกัน (สกุลเงินและประเภทเดียวกัน) ให้รวมเป็นรายการเดียว',
  POSSIBLE_DUPLICATE_CASH_ACROSS_ACCOUNTS: 'ยอดเงินสดสกุลเดียวกันนี้อาจถูกนับซ้ำ: สองบัญชีของโบรกเดียวกัน (เช่น Dime! Securities กับ Dime! FCD) แสดงยอดเท่ากัน ตรวจว่าเป็นเงินก้อนเดียวกันหรือไม่ ระบบไม่ลบหรือรวมให้อัตโนมัติ',
  PRIVATE_POSITION_EVIDENCE_MISSING: 'หลักทรัพย์นี้ยังไม่มีมูลค่าหรือจำนวนหน่วย ต้องกรอกอย่างน้อยหนึ่งอย่าง',
  PRIVATE_PRICE_MISSING: 'กรอกจำนวนหน่วยแล้วแต่ยังไม่มีราคา ให้กรอกราคาและวันที่ราคา หรือกรอกมูลค่าที่แอปแสดงแทน',
  PRIVATE_MALFORMED_DECIMAL: 'ตัวเลขไม่ถูกรูปแบบ ใช้ตัวเลขและจุดทศนิยมเท่านั้น ไม่มีจุลภาคหรือสัญลักษณ์สกุลเงิน',
  PRIVATE_NUMBER_MUST_BE_STRING: 'ตัวเลขต้องกรอกเป็นข้อความ',
  PRIVATE_NEGATIVE_VALUE: 'ค่านี้ต้องไม่ติดลบ',
  PRIVATE_NONPOSITIVE_VALUE: 'ค่านี้ต้องมากกว่าศูนย์',
  PRIVATE_TIMESTAMP_INVALID: 'เวลาที่สังเกตต้องอยู่ในรูปแบบ 2026-11-02T20:00:00+07:00',
  PRIVATE_TIMESTAMP_NAIVE: 'เวลาต้องมีเขตเวลา เช่น +07:00',
  PRIVATE_DATE_INVALID: 'วันที่ต้องอยู่ในรูปแบบ ปปปป-ดด-วว (ค.ศ.)',
  PRIVATE_REF_NOT_OPAQUE: 'รหัสบัญชีต้องเป็นตัวพิมพ์ใหญ่ A–Z ตัวเลข หรือ _ และห้ามใส่เลขบัญชีจริง (ตัวเลขติดกัน 6 หลักขึ้นไป)',
  PRIVATE_LABEL_INVALID: 'ชื่อพอร์ตย่อยไม่ถูกต้อง ห้ามว่างหรือยาวเกินไป',
  PRIVATE_SECURITY_ID_INVALID: 'รหัสหลักทรัพย์ไม่ถูกต้อง',
  PRIVATE_CURRENCY_INVALID: 'สกุลเงินต้องเป็นรหัส 3 ตัวอักษร เช่น THB หรือ USD',
  PRIVATE_PRICE_DATE_MISMATCH: 'วันที่ราคาต้องตรงกับวันที่ประเมินมูลค่า',
  PRIVATE_FX_DATE_MISMATCH: 'วันที่อัตราแลกเปลี่ยนต้องตรงกับวันที่ประเมินมูลค่า',
  PRIVATE_FX_DUPLICATE_OR_IDENTITY: 'อัตราแลกเปลี่ยนซ้ำ หรือแปลงสกุลเงินเป็นตัวเอง',
  PRIVATE_UNUSED_PRICE: 'มีราคาของหลักทรัพย์ที่ไม่ได้ถืออยู่ ให้ลบออก',
  PRIVATE_PRICE_DUPLICATE: 'มีราคาซ้ำของหลักทรัพย์เดียวกัน',
  PRIVATE_DUPLICATE_POSITION_LINE: 'มีหลักทรัพย์ซ้ำในพอร์ตย่อยเดียวกัน',
  PRIVATE_EMPTY_ACCOUNT: 'บัญชีนี้ยังว่าง ให้กรอกยอดรวม เงินสด หรือหลักทรัพย์อย่างน้อยหนึ่งอย่าง',
  PRIVATE_NO_ACCOUNTS: 'ยังไม่มีบัญชี ให้เพิ่มอย่างน้อยหนึ่งบัญชี',
  PRIVATE_DUPLICATE_ACCOUNT_REF: 'รหัสบัญชีซ้ำกัน',
  PRIVATE_ACCOUNT_ROLE_INVALID: 'บทบาทบัญชีไม่ถูกต้อง',
  PRIVATE_CASH_KIND_INVALID: 'ประเภทเงินสดไม่ถูกต้อง',
  PRIVATE_VALUATION_DATE_AFTER_OBSERVATION: 'วันที่ประเมินมูลค่าต้องไม่เกินวันที่สังเกต',
  PRIVATE_REPORT_DATE_BEFORE_VALUATION: 'วันที่ประเมินมูลค่าอยู่ในอนาคต',
  PRIVATE_CLASSIFICATION_EVIDENCE_REQUIRED: 'การจัดกลุ่มนอกจาก UNKNOWN ต้องมีเอกสารอ้างอิง เช่น factsheet',
  PRIVATE_CLASSIFICATION_FOR_UNHELD_SECURITY: 'มีการจัดกลุ่มหลักทรัพย์ที่ไม่ได้ถืออยู่',
  PRIVATE_AMOUNT_CURRENCY_PAIR_INCOMPLETE: 'กรอกยอดแล้วต้องระบุสกุลเงินด้วย (และกลับกัน)',
  PRIVATE_UNKNOWN_FIELDS: 'มีช่องที่ไม่อยู่ในรูปแบบมาตรฐาน',
  PRIVATE_SUBPORTFOLIO_TOTAL_UNLABELLED: 'ยอดพอร์ตย่อยต้องมีชื่อพอร์ตย่อย',
  PRIVATE_DUPLICATE_SUBPORTFOLIO_TOTAL: 'มีชื่อพอร์ตย่อยซ้ำกัน',
  INPUT_SNAPSHOT_SCHEMA_OR_DATA_CLASS: 'ไฟล์ไม่ใช่ snapshot ส่วนตัวแบบ V1_2',
  INPUT_CAPACITY_SCHEMA_OR_DATA_CLASS: 'ไฟล์ไม่ใช่ข้อมูลความสามารถทางการเงินส่วนตัว',
  CAPACITY_MALFORMED_DECIMAL: 'ตัวเลขไม่ถูกรูปแบบ ใช้ตัวเลขและจุดทศนิยมเท่านั้น',
  CAPACITY_NUMBER_MUST_BE_STRING: 'ช่องนี้ต้องกรอก',
  CAPACITY_INVALID_AMOUNT: 'ค่านี้ต้องไม่ติดลบ',
  CAPACITY_MONTHLY_NEED_ZERO: 'ค่าใช้จ่ายจำเป็นรวมหนี้ต่อเดือนต้องมากกว่าศูนย์ จึงจะคำนวณเงินสำรองได้',
  CAPACITY_HORIZON_INVALID: 'ระยะเวลาลงทุนต้องเป็นจำนวนปีเต็มที่มากกว่าศูนย์',
  STALE_VALUATION: 'ข้อมูลราคาเก่ากว่า 7 วัน รายงานจะติดป้ายว่าข้อมูลไม่สด',
  UNEXPLAINED_DIFFERENCE: 'ยอดรวมที่แอปแสดงไม่ตรงกับผลรวมรายการที่กรอก ตรวจรายการที่ขาดหรือซ้ำ',
  INSUFFICIENT_EVIDENCE: 'หลักฐานไม่พอที่จะกระทบยอดบัญชีนี้',
  RESIDUAL_NOT_ESTABLISHED: 'ยังระบุส่วนต่างของบัญชีนี้ไม่ได้',
  REVISION_CONFLICT: 'ไฟล์ถูกแก้ไขที่อื่นหลังจากโหลด ให้กดโหลดใหม่ก่อนบันทึก (ระบบไม่เขียนทับให้)',
  AUTHORING_AUTHORIZATION_REQUIRED: 'ยังบันทึกไม่ได้: ODR-003 (สิทธิ์บันทึกข้อมูลจากหน้าจอ) ยังไม่ได้รับการอนุมัติจากเจ้าของ ตรวจข้อมูลได้ตามปกติ',
  AUTHORIZATION_REQUIRED: 'ODR-001 ยังไม่ได้อนุมัติ หรือถูกเพิกถอน',
  SESSION_TOKEN_REQUIRED: 'Session token ไม่ถูกต้อง ให้คัดลอกใหม่จากหน้าต่าง ACASH Private View',
  SESSION_EXPIRED: 'Session token หมดอายุ ปิดหน้าต่าง ACASH Private View แล้วรัน START-DASHBOARD.bat private ใหม่',
  RATE_LIMITED: 'ส่งคำขอถี่เกินไป รอสักครู่แล้วลองใหม่',
  SERVICE_UNAVAILABLE: 'เชื่อมต่อบริการในเครื่องไม่ได้ ให้รัน START-DASHBOARD.bat private',
  PREFLIGHT_INVALID: 'ข้อมูลที่บันทึกไว้ยังไม่ผ่านการตรวจ จึงยังสร้างรายงานไม่ได้',
  PREFLIGHT_BLOCKED: 'ถูกระงับโดยการตรวจสิทธิ์',
  GENERATION_FAILED: 'สร้างรายงานไม่สำเร็จ ข้อมูลเดิมยังอยู่ครบ',
  WRITE_FAILED: 'บันทึกไฟล์ไม่สำเร็จ ไฟล์เดิมยังอยู่ครบ',
  WRITE_FAILED_ROLLED_BACK: 'บันทึกไม่สำเร็จ ระบบคืนค่าไฟล์ทั้งสองเป็นชุดเดิมแล้ว',
  WRITE_FAILED_RECOVERY_PENDING: 'บันทึกไม่สำเร็จและคืนค่ายังไม่ครบ ระบบจะกู้คืนอัตโนมัติก่อนการบันทึกหรือสร้างรายงานครั้งถัดไป (สำรองอยู่ใน data/private/backups)',
  INPUT_RECOVERY_REQUIRED: 'มีการบันทึกครั้งก่อนที่ค้างอยู่และกู้คืนอัตโนมัติไม่ได้ ดูวิธีกู้คืนใน docs/research/UPI_PRIVATE_PILOT_RUNBOOK.md',
  INPUT_PATH_REFUSED: 'ปฏิเสธการเขียน: พบ symlink/junction หรือ path ผิดปกติใน data/private',
  INPUT_PATH_LINK_REFUSED: 'ปฏิเสธการเขียน: พบ symlink/junction ใน data/private',
  CONFIRMATION_REQUIRED: 'ต้องติ๊กยืนยันการแทนที่ข้อมูลก่อนบันทึก',
  GENERATION_PUBLISH_INCOMPLETE: 'เผยแพร่รายงานไม่ครบ ให้กดสร้างรายงานใหม่อีกครั้ง',
  GENERATION_INPUTS_CHANGED: 'ข้อมูลถูกแก้ระหว่างสร้างรายงาน รายงานเดิมยังอยู่ ให้กดสร้างใหม่',
  EVIDENCE_ONLY_REPORT: 'รายงานจะเป็นแบบยอดรวมตามที่แอปแสดง (EVIDENCE_ONLY) ยังไม่แยกรายหลักทรัพย์',
};

export const messageTh = (code: string) => MESSAGES_TH[code] ?? `ข้อมูลไม่ผ่านการตรวจ (${code})`;
