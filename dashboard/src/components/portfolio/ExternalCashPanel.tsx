import React, { useEffect, useState } from 'react';
import { StatusBadge } from '../common/StatusBadge';
import { fetchWealth, WealthReport } from '../../services/wealth';

// Read-only: shows the Owner's declared external cash next to the broker's latest displayed total.
// The consolidated figure is explicitly mixed evidence and never enters the broker valuation.

const money = (value: string | null | undefined, ccy = 'THB') =>
  value == null ? '—' : `${Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${ccy}`;

export const ExternalCashPanel: React.FC = () => {
  const [report, setReport] = useState<WealthReport | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void fetchWealth(controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      setReport(result);
      setFailed(result === null);
    });
    return () => controller.abort();
  }, []);

  if (failed) return <p className="text-xs text-secondary">อ่านข้อมูลเงินสดนอกพอร์ตไม่ได้ (บริการไม่ตอบสนอง) — ตัวเลขในหน้ารายงานยังใช้ได้ตามปกติ</p>;
  if (!report) return <p className="text-xs text-secondary">กำลังโหลดเงินสดนอกพอร์ต…</p>;

  const cash = report.external_cash;
  const obs = report.broker_observation;
  const cmp = report.comparison;
  const cons = report.consolidated;

  return (
    <section aria-labelledby="sec-wealth" className="bg-surface border border-default rounded-lg p-4 space-y-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="sec-wealth" className="text-sm font-semibold text-primary">เงินสดนอกพอร์ตและหลักฐานล่าสุด</h2>
        <span className="text-[11px] text-muted">Owner-declared · ไม่ใช่ยอดจาก API ธนาคาร</span>
      </div>

      {cash && cash.status !== 'NO_EXTERNAL_CASH' ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          <div className="bg-surface-muted rounded-md p-2">
            <div className="text-[10px] text-muted">เงินสดนอกพอร์ต (มีจริง)</div>
            <div className="font-mono-code text-sm text-primary">{money(cash.total)}</div>
            <div className="text-[10px] text-secondary">ประมาณ {money(cash.approximate_component)} เป็นการประมาณ</div>
          </div>
          <div className="bg-surface-muted rounded-md p-2">
            <div className="text-[10px] text-muted">เป้าหมายเงินสดนอกพอร์ต</div>
            <div className="font-mono-code text-sm text-primary">{money(cash.target, cash.target_currency)}</div>
            <div className="text-[10px] text-secondary">เป้าหมายของ Owner ไม่ใช่ยอดที่มี</div>
          </div>
          <div className="bg-surface-muted rounded-md p-2">
            <div className="text-[10px] text-muted">ยังขาดอีก</div>
            <div className="font-mono-code text-sm text-primary">{money(cash.gap)}</div>
            <div className="text-[10px] text-secondary">เทียบกับเป้าหมายเงินสดนอกพอร์ตเท่านั้น</div>
          </div>
          <div className="bg-surface-muted rounded-md p-2">
            <div className="text-[10px] text-muted">เงินสำรองที่กำหนดไว้ (Owner)</div>
            <div className="font-mono-code text-sm text-primary">{money(cash.designated_reserve_total)}</div>
            <div className="text-[10px] text-secondary">Make + LHB · ไม่รวม KBank (เงินใช้จ่าย)</div>
          </div>
        </div>
      ) : (
        <p className="text-secondary">ยังไม่มีทะเบียนเงินสดนอกพอร์ต</p>
      )}

      {cash?.accounts?.length ? (
        <table className="w-full text-[11px]">
          <thead><tr className="text-muted text-left"><th className="py-1">บัญชี</th><th>ยอด</th><th>ความแม่นยำ</th><th>สภาพคล่อง</th><th>ใช้เป็นเงินสำรอง</th></tr></thead>
          <tbody>
            {cash.accounts.map((a) => (
              <tr key={a.account_ref} className="border-t border-default">
                <td className="py-1 text-primary">{a.owner_label || a.institution}</td>
                <td className="font-mono-code">{money(a.balance, a.currency)}</td>
                <td>{a.precision === 'APPROXIMATE' ? 'ประมาณ' : 'ยืนยันจำนวน'}</td>
                <td>{a.liquidity_status === 'WITHDRAWABLE' ? 'ถอนได้' : 'ใช้จ่ายประจำ'}</td>
                <td>{a.reserve_eligible ? 'ได้' : 'ไม่ได้'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      {obs && obs.status === 'OBSERVED' ? (
        <div className="space-y-1 border-t border-default pt-2">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={obs.evidence_status ?? 'BROKER_DISPLAYED_OBSERVATION'} />
            <span className="text-primary">Dime! แสดง {money(obs.displayed_total)}</span>
            <span className="text-secondary">เมื่อ {obs.observed_at} · ผลรวมหมวดตรงกับยอดที่แสดง</span>
          </div>
          {cmp ? (
            <p className="text-secondary">
              เทียบกับ ACASH ที่คำนวณไว้ ({cmp.calculated_valuation_date}): <strong>{cmp.status}</strong> ·
              ต่าง {money(cmp.difference)} ({cmp.difference_pct}%) — {cmp.note}
            </p>
          ) : null}
        </div>
      ) : null}

      {cons?.consolidated_total ? (
        <div className="border-t border-default pt-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted">ความมั่งคั่งรวมตามหลักฐานล่าสุด</span>
            <span className="font-mono-code text-sm text-primary">{money(cons.consolidated_total)}</span>
            <StatusBadge status={cons.evidence_quality} />
          </div>
          <p className="text-[10px] text-muted">Mixed evidence / mixed observation time: ยอดโบรกเกอร์กับเงินสดนอกพอร์ตไม่ได้ถูกตรวจพร้อมกัน และเงินนอกพอร์ตไม่ถูกนำไปคิดใน NAV ของโบรกเกอร์</p>
        </div>
      ) : null}

      {report.classification && report.classification.status !== 'NO_CLASSIFICATION' ? (
        <div className="border-t border-default pt-2 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted">การจัดประเภทสินทรัพย์ (Economic)</span>
            <span className="font-mono-code text-primary">{report.classification.classified_count}/{report.classification.instrument_count}</span>
            <span className="text-secondary">มูลค่าที่จำแนกได้ {(Number(report.classification.coverage_by_value) * 100).toFixed(1)}%</span>
            <StatusBadge status={report.classification.status} />
          </div>
          <p className="text-[10px] text-muted">
            ยังไม่จำแนก {report.classification.unknown_count} ตัว — คงสถานะ Unknown จนกว่าจะมีหลักฐานจากผู้ออกหลักทรัพย์ ไม่เดาจาก ticker
          </p>
        </div>
      ) : null}

      <p className="text-[10px] text-muted">{cash?.notes?.join(' · ')}</p>
    </section>
  );
};
