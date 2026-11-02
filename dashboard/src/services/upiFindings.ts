// Human-readable findings for the reason codes emitted by acash.invest.wealth_pack.
// Severity is a static, documented presentation rule per code; it is not a risk score:
//   CRITICAL   a displayed figure may be wrong or out of date (broker totals disagree, stale valuation)
//   IMPORTANT  figures are correct but incomplete, or a planning constraint applies
//   INFO       an analysis is not available by design in a snapshot-only report
// Codes missing from this table are shown as IMPORTANT with their raw code, never hidden.
// No imports, so the Node test runner can load this module directly.

export type Severity = 'CRITICAL' | 'IMPORTANT' | 'INFO';

export interface Finding {
  code: string;
  severity: Severity;
  title: string;
  implication: string;
  action?: string;
  detail?: string;
}

type Entry = Omit<Finding, 'code' | 'detail'>;

export const FINDINGS: Record<string, Entry> = {
  ACCOUNT_TOTALS_NOT_FULLY_RECONCILED: {
    severity: 'CRITICAL',
    title: 'ยอดรวมบางบัญชียังไม่ตรงกับรายการที่กรอก',
    implication: 'ยอดที่โบรกเกอร์แสดงกับผลรวมรายการที่ระบุได้ไม่ตรงกันเกินเกณฑ์ปัดเศษ หรือมีหลักฐานไม่พอให้เทียบ',
    action: 'เปิดส่วน Accounts & Holdings ดูบัญชีที่ไม่ใช่ RECONCILED แล้วตรวจรายการที่ขาดหรือกรอกซ้ำใน snapshot',
  },
  STALE_VALUATION: {
    severity: 'CRITICAL',
    title: 'ข้อมูลมูลค่าเก่ากว่าช่วงที่ยอมรับได้',
    implication: 'ตัวเลขทั้งหน้าอาจไม่สะท้อนพอร์ตปัจจุบัน',
    action: 'บันทึก snapshot ใหม่จากแอปแล้วสร้างรายงานใหม่',
  },
  UNCLASSIFIED_HOLDINGS_PRESENT: {
    severity: 'IMPORTANT',
    title: 'ยังมีสินทรัพย์บางส่วนที่ระบุรายละเอียดไม่ได้',
    implication: 'สัดส่วนพอร์ตและการกระจุกตัวเป็นเพียงค่าประมาณตามหลักฐาน (ขอบล่าง) ไม่ใช่ค่าทั้งพอร์ต',
    action: 'กรอกรายการหุ้น/กองทุนที่อยู่ในยอดรวมของบัญชีให้ครบ',
  },
  UNKNOWN_CLASSIFICATION_PRESENT: {
    severity: 'IMPORTANT',
    title: 'บางหลักทรัพย์ยังไม่มีการจัดประเภทที่มีหลักฐาน',
    implication: 'สัดส่วนตามประเภทสินทรัพย์ไม่ครอบคลุมหลักทรัพย์เหล่านั้น',
    action: 'เพิ่มการจัดประเภทพร้อม evidence_ref ในรายการ securities',
  },
  COST_BASIS_INCOMPLETE: {
    severity: 'IMPORTANT',
    title: 'ต้นทุนของบางรายการยังไม่ทราบ',
    implication: 'กำไร/ขาดทุนที่ยังไม่รับรู้คำนวณได้เฉพาะส่วนที่รู้ต้นทุน',
    action: 'กรอกต้นทุนเฉพาะที่แอปแสดงจริง ห้ามประมาณ',
  },
  SECURITY_IDENTITY_UNVERIFIED: {
    severity: 'IMPORTANT',
    title: 'บางหลักทรัพย์ยังไม่มีรหัสยืนยันตัวตน',
    implication: 'หลักทรัพย์เดียวกันในหลายบัญชีจะไม่ถูกรวมกัน การกระจุกตัวอาจต่ำกว่าความจริง',
    action: 'เพิ่ม ISIN หรือ FIGI ถ้ามี',
  },
  RESERVE_SHORTFALL: {
    severity: 'IMPORTANT',
    title: 'เงินสำรองยังต่ำกว่าเป้าหมาย',
    implication: 'เงินสำรองฉุกเฉินต่ำกว่าเป้าตามสมมติฐานรายจ่ายที่กรอกไว้ใน capacity',
    action: 'ดูส่วน Financial Capacity ว่าแต่ละแผนการลงทุนรายเดือนใช้เวลากี่เดือนเติมเงินสำรองให้ถึงเป้า',
  },
  EVIDENCE_ONLY_REPORT: {
    severity: 'IMPORTANT',
    title: 'รายงานนี้มีแค่ยอดรวม ไม่มีรายการย่อย',
    implication: 'คำนวณสัดส่วน การกระจุกตัว กำไร/ขาดทุน และแผนเติมเงินตามสัดส่วนไม่ได้',
    action: 'กรอกเงินสดหรือจำนวนหุ้นพร้อมราคาอย่างน้อยบางรายการ',
  },
  PERFORMANCE_NOT_ESTABLISHED: {
    severity: 'INFO',
    title: 'ยังคำนวณผลตอบแทนย้อนหลังไม่ได้',
    implication: 'ไม่มีประวัติกระแสเงินและมูลค่าพอร์ตครบ จึงไม่มี TWR/XIRR หรือกราฟผลตอบแทน',
  },
  OVERLAP_NOT_ESTABLISHED: {
    severity: 'INFO',
    title: 'ยังวิเคราะห์การซ้อนทับของกองทุนไม่ได้',
    implication: 'ไม่มีข้อมูลองค์ประกอบกองทุน (look-through) ที่ลงวันที่',
  },
  MARKET_SESSION_NOT_VERIFIED: {
    severity: 'INFO',
    title: 'รายงานไม่ได้ยืนยันเวลาตลาดของราคา',
    implication: 'preflight ตรวจได้เฉพาะราคาที่ซื้อขายบน NYSE ปี 2026–2028; ตลาดอื่นยังไม่ได้ตรวจ',
  },
  V38_ROUTE_EVIDENCE_INCOMPLETE: {
    severity: 'INFO',
    title: 'ค่าธรรมเนียมและค่าแลกเงินยังไม่มีหลักฐานครบ',
    implication: 'ต้นทุนการโอน/แลกเงินยังเป็นข้อมูลที่เจ้าของต้องยืนยัน',
  },
};

const ORDER: Record<Severity, number> = { CRITICAL: 0, IMPORTANT: 1, INFO: 2 };

// `warnings` are the codes classifyView kept (authority codes already removed); `reasons` are
// the full decision reasons from the view, used for the exact detail text.
export function findingsFor(warnings: string[], reasons: string[]): Finding[] {
  const out: Finding[] = [];
  for (const code of warnings) {
    const reason = reasons.find((r) => r.split(':')[0] === code) ?? code;
    const entry = FINDINGS[code] ?? { severity: 'IMPORTANT' as Severity, title: code, implication: 'Unrecognised status code; see the detail.' };
    out.push({ code, ...entry, detail: reason });
  }
  return out.sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
}
