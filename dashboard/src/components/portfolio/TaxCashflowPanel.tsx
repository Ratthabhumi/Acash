import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';

// Dime! tax and cash-flow evidence: aggregates are shown as aggregates, and no liability is computed.
// Everything displayed comes from Python (GET /api/upi/tax); this component never adds or infers an amount.

const TAX_ENDPOINT = 'http://127.0.0.1:8765/api/upi/tax';

interface Checks {
  coverage_complete_for_year?: boolean;
  last_covered_date?: string;
  next_expected_update?: string;
  effective_withholding_ratio?: string;
  observed_ratio_is_not_a_treaty_rate?: boolean;
  missing_months?: number | null;
}

interface TaxDoc {
  status: string;
  annual_summary?: {
    tax_year?: number; covered_from?: string; covered_to?: string; source?: string; observed_at?: string;
    funds_in_usd?: string; funds_out_usd?: string; gross_dividends_usd?: string;
    withheld_usd?: string; net_dividends_usd?: string; checks?: Checks;
  };
  staged_trades?: {
    accepted_for_journal?: unknown[]; pre_baseline_candidates?: unknown[];
    rejected?: Array<{ security_id: string; reason: string }>;
  };
  cash_flows?: Array<{ description: string; classification: string; amount: string; currency: string }>;
  readiness?: Record<string, unknown>;
  tax_liability?: { status?: string; reasons?: string[]; credit_eligibility?: string };
  ruleset?: { version?: string; citations?: Record<string, string> };
  note?: string;
}

const str = (value: unknown): string => (value === null || value === undefined ? '—' : String(value));

export const TaxCashflowPanel: React.FC = () => {
  const [doc, setDoc] = useState<TaxDoc | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(TAX_ENDPOINT, { credentials: 'include', cache: 'no-store' });
      const body = (await response.json().catch(() => ({ status: 'INVALID_RESPONSE' }))) as TaxDoc;
      setDoc(body);
    } catch {
      setDoc({ status: 'SERVICE_UNAVAILABLE' });
    }
    setLoading(false);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const summary = doc?.annual_summary;
  const checks = summary?.checks ?? {};
  const staged = doc?.staged_trades;
  const readiness = doc?.readiness ?? {};
  const liability = doc?.tax_liability ?? {};

  return (
    <section aria-labelledby="tax-heading" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 id="tax-heading" className="text-sm font-semibold text-primary">ภาษีและกระแสเงิน</h3>
          <p className="text-[11px] text-secondary">
            หลักฐานจาก Dime! เท่านั้น · ไม่ใช่การยื่นภาษีและไม่ใช่การคำนวณภาษีที่ต้องชำระ
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <button type="button" onClick={() => void load()} disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1 rounded border border-default text-secondary hover:bg-surface-muted disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Reload
          </button>
          <StatusBadge status={str(doc?.status ?? 'LOADING')} size="md" />
        </div>
      </div>

      {!loading && doc && doc.status === 'NO_TAX_EVIDENCE' && (
        <div className="bg-surface border border-default rounded-lg p-4 text-xs text-secondary">
          <p className="font-semibold text-primary">ยังไม่มีหลักฐานภาษีที่บันทึกไว้</p>
          <p>{doc.note}</p>
        </div>
      )}

      {!loading && doc && doc.status === 'AVAILABLE' && (
        <>
          <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={str(liability.status ?? 'NOT_ESTABLISHED')} />
              <span className="font-mono-code text-secondary">ปีภาษี {str(summary?.tax_year)}</span>
              <span className="text-muted">
                {str(summary?.covered_from)} → {str(summary?.covered_to)} · {str(summary?.source)}
              </span>
            </div>
            {!checks.coverage_complete_for_year && (
              <p className="text-amber-700 dark:text-amber-400">
                ข้อมูลยังไม่ครบปี ({str(checks.missing_months)} ยังไม่เผยแพร่) · คาดว่าจะอัปเดต {str(checks.next_expected_update)}
              </p>
            )}
            <p className="text-[11px] text-muted">
              ยอดรวมประจำปีเป็น “ยอดควบคุม” ไม่ใช่รายการเดินบัญชี และไม่สามารถแยกเงินต้นกับเงินได้
            </p>
          </div>

          <SimpleTable head={['รายการ', 'USD', 'หมายเหตุ']} rows={[
            ['เงินโอนเข้าไทย', str(summary?.funds_in_usd), 'ไม่ใช่เงินได้ทั้งหมด'],
            ['เงินโอนออกจากไทย', str(summary?.funds_out_usd), 'ไม่ใช่ค่าใช้จ่ายลงทุนทั้งหมด'],
            ['เงินปันผลก่อนหักภาษี', str(summary?.gross_dividends_usd), 'ยอดรวมทั้งปีที่รายงาน'],
            ['ภาษีถูกหัก', str(summary?.withheld_usd), `อัตราที่พบ ${str(checks.effective_withholding_ratio)} (ไม่ใช่อัตราสนธิสัญญา)`],
            ['เงินปันผลสุทธิ', str(summary?.net_dividends_usd), 'gross − withheld'],
          ]} />

          <SimpleTable head={['ความพร้อมของหลักฐาน', 'สถานะ']} rows={[
            ['ประวัติซื้อขาย', str(readiness.trade_history)],
            ['อัตราแลกเปลี่ยนที่ใช้จริง', str(readiness.currency_conversion)],
            ['กระแสเงินสด', str(readiness.cash_flow)],
            ['เงินปันผล/ภาษีรายรายการ', str(readiness.dividends_and_tax)],
            ['ต้นทุนเปิดบัญชี (lots)', str(readiness.opening_lots)],
            ['กระทบยอดกับ snapshot', str(readiness.position_reconciliation)],
            ['ผลตอบแทนพอร์ตจริง', str(readiness.historical_performance)],
            ['เครดิตภาษีต่างประเทศ', str(readiness.foreign_tax_credit)],
          ]} />

          <SimpleTable head={['รายการที่นำเข้า', 'จำนวน']} rows={[
            ['พร้อมเป็นธุรกรรมจริง', String((staged?.accepted_for_journal ?? []).length)],
            ['ก่อน baseline (ต้อง rebase)', String((staged?.pre_baseline_candidates ?? []).length)],
            ['ถูกปฏิเสธ', (staged?.rejected ?? []).map((r) => `${r.security_id}: ${r.reason}`).join(', ') || '—'],
          ]} />

          {(doc.cash_flows ?? []).length > 0 && (
            <SimpleTable head={['รายการเงินสด', 'จำนวน', 'ประเภท']}
              rows={(doc.cash_flows ?? []).map((f) => [f.description, `${f.amount} ${f.currency}`, f.classification])} />
          )}

          <div className="bg-surface border border-default rounded-lg p-3 text-xs space-y-1">
            <p className="font-semibold text-primary">ทำไมยังไม่คำนวณภาษี</p>
            <ul className="list-disc pl-5 text-secondary">
              {(liability.reasons ?? []).map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <p className="text-[11px] text-muted">
              กฎที่อ้างอิง: {str(doc.ruleset?.version)} · เครดิตภาษี: {str(liability.credit_eligibility)}
            </p>
          </div>
        </>
      )}
    </section>
  );
};
