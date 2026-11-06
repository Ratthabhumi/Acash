// Client for the loopback /api/upi/transactions/ routes (ODR-005). The page sends exactly what the
// Owner typed from broker evidence; Python validates, replays and returns every figure shown.
// Nothing here talks to a broker: these rows describe trades already executed elsewhere.

export const TXN_ENDPOINT = 'http://127.0.0.1:8765/api/upi/transactions/';
export const AUTHORED_EVENTS = ['BUY', 'SELL', 'DEPOSIT', 'WITHDRAWAL', 'DIVIDEND', 'FEE'] as const;
export type AuthoredEvent = typeof AUTHORED_EVENTS[number];

export const EVENT_LABEL_TH: Record<AuthoredEvent, string> = {
  BUY: '+ บันทึกซื้อ', SELL: 'บันทึกขาย', DEPOSIT: 'ฝากเงิน', WITHDRAWAL: 'ถอนเงิน', DIVIDEND: 'บันทึกปันผล', FEE: 'บันทึกค่าธรรมเนียม',
};

const TRADE = ['account_ref', 'security_id', 'trade_date', 'settlement_date', 'quantity', 'price', 'gross_amount', 'commission', 'fees', 'currency', 'net_cash'];
export const EVENT_FIELDS: Record<AuthoredEvent, string[]> = {
  BUY: TRADE, SELL: TRADE,
  DEPOSIT: ['account_ref', 'trade_date', 'currency', 'net_cash'],
  WITHDRAWAL: ['account_ref', 'trade_date', 'currency', 'net_cash'],
  DIVIDEND: ['account_ref', 'security_id', 'trade_date', 'currency', 'net_cash'],
  FEE: ['account_ref', 'trade_date', 'currency', 'net_cash'],
};
export const OPTIONAL_FIELDS = new Set(['settlement_date', 'commission', 'fees']);

export const TXN_TH: Record<string, string> = {
  RECORDED: 'บันทึกแล้ว', ALREADY_RECORDED: 'รายการนี้บันทึกไว้แล้ว (ไม่บันทึกซ้ำ)',
  IMPORTED: 'นำเข้าสำเร็จ', ALREADY_IMPORTED: 'รายการทั้งหมดมีอยู่แล้ว (ไม่บันทึกซ้ำ)',
  IMPORT_PREVIEW: 'ตรวจสอบข้อมูลก่อนยืนยัน', IMPORT_REFUSED: 'ไฟล์มีรายการที่ไม่ผ่านการตรวจสอบ',
  CSV_NO_VALID_ROWS: 'ไม่พบรายการที่ถูกต้องในไฟล์', CSV_HEADER_MISSING: 'ไฟล์ไม่มีหัวตาราง',
  CSV_COLUMNS_UNSUPPORTED: 'คอลัมน์บางคอลัมน์ไม่รองรับ', CSV_DECIMAL_INVALID: 'ตัวเลขไม่ถูกต้อง',
  CSV_DUPLICATE_TRANSACTION_ID: 'รหัสรายการซ้ำกันในไฟล์', CSV_DUPLICATE_ECONOMIC_RECORD: 'รายการเศรษฐกิจซ้ำกันในไฟล์',
  CSV_BASE64_INVALID: 'ไฟล์เข้ารหัสผิดรูปแบบ', PREVIEW_HASH_MISMATCH: 'ข้อมูลที่ยืนยันเปลี่ยนแปลงจากตอนตรวจสอบ ให้ตรวจสอบใหม่',
  POSSIBLE_DUPLICATE: 'มีรายการเหมือนกันทุกช่องอยู่แล้ว ถ้าเป็นการซื้อขายจริงอีกครั้ง ให้ติ๊กยืนยันรายการซ้ำ',
  TXN_ID_CONFLICT: 'รหัสรายการชนกับรายการอื่น', REVISION_CONFLICT: 'ข้อมูลเปลี่ยนจากหน้าต่างอื่น โหลดใหม่แล้วลองอีกครั้ง',
  CONFIRMATION_REQUIRED: 'ต้องยืนยันก่อนบันทึก', TRANSACTION_AUTHORING_AUTHORIZATION_REQUIRED: 'ODR-005 ยังไม่ได้รับการรับรอง จึงบันทึกไม่ได้',
  AUTHORIZATION_REQUIRED: 'ต้องได้รับอนุญาต ODR-001 และ ODR-002 ก่อน', TXN_POSITION_OVERSOLD: 'ขายเกินจำนวนที่ถืออยู่',
  TXN_CASH_NEGATIVE: 'เงินสดติดลบ (เงินสดตั้งต้นใน snapshot อาจขาด ให้ตรวจใน Setup Wizard)',
  TXN_BEFORE_BASELINE_CUTOFF: 'วันที่นี้อยู่ใน statement ที่บันทึกแล้ว จึงไม่นับซ้ำ', TXN_FUTURE_TRADE_DATE: 'บันทึกได้เฉพาะรายการที่เกิดขึ้นแล้ว',
  TXN_ACCOUNT_UNKNOWN: 'ไม่พบบัญชีนี้ใน snapshot', TXN_SECURITY_UNKNOWN: 'ไม่พบหลักทรัพย์นี้ ให้เพิ่มใน Setup Wizard ก่อน',
  TXN_CURRENCY_MISMATCH: 'สกุลเงินไม่ตรงกับหลักทรัพย์', TXN_NET_CASH_INCONSISTENT: 'เงินสุทธิไม่ตรงกับยอดรวมและค่าธรรมเนียม',
  TXN_GROSS_INCONSISTENT_WITH_QUANTITY_PRICE: 'ยอดรวมไม่ตรงกับจำนวน × ราคา', TXN_NET_CASH_SIGN_INVALID: 'เครื่องหมายเงินสุทธิผิด (ซื้อ/ถอน/ค่าธรรมเนียม = ติดลบ)',
  NOT_ENABLED_PENDING_OWNER_DECISION: 'ยังแก้/ยกเลิกรายการไม่ได้ (ต้องให้ Owner อนุมัติรูปแบบการแก้ไขก่อน)',
  APPLIED: 'นับแล้ว', BEFORE_BASELINE_CUTOFF: 'อยู่ใน statement แล้ว (ไม่นับซ้ำ)',
};
export const txnTh = (code: string): string => TXN_TH[code] ?? code;

export function newTransactionId(): string {
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return 'TX_' + Array.from(bytes, (b) => letters[b % 26]).join('');
}

export interface TxnCall { http: number; body: Record<string, any> }

export type ImportRoute = 'import-template' | 'import-preview' | 'import-confirm';

export async function callTxn(method: 'GET' | 'POST', route: 'state' | 'preview' | 'record' | ImportRoute, body?: unknown): Promise<TxnCall> {
  try {
    const response = await fetch(TXN_ENDPOINT + route, {
      method,
      headers: method === 'POST' ? { 'Content-Type': 'application/json' } : undefined,
      body: method === 'POST' ? JSON.stringify(body ?? {}) : undefined,
      cache: 'no-store', credentials: 'include', referrerPolicy: 'no-referrer',
    });
    const out: unknown = await response.json().catch(() => null);
    return { http: response.status, body: (out && typeof out === 'object' ? out : { status: 'INVALID_RESPONSE' }) as Record<string, any> };
  } catch {
    return { http: 0, body: { status: 'SERVICE_UNAVAILABLE' } };
  }
}
