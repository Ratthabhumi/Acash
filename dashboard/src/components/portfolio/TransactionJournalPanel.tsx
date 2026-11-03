import React, { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';
import {
  AUTHORED_EVENTS, AuthoredEvent, EVENT_FIELDS, EVENT_LABEL_TH, OPTIONAL_FIELDS, callTxn, newTransactionId, txnTh,
} from '../../services/transactions';

type Row = Record<string, any>;

const Projection: React.FC<{ p: Row | undefined; title: string }> = ({ p, title }) => (
  <div className="space-y-1">
    <h4 className="font-semibold text-primary">{title}</h4>
    <SimpleTable head={['Account', 'Security', 'Quantity', 'Cost', 'Ccy']}
      rows={(p?.positions ?? []).map((r: Row) => [r.account_ref, r.security_id, r.quantity, r.cost_total ?? r.cost_status, r.currency])} />
    <SimpleTable head={['Account', 'Cash', 'Ccy']} rows={(p?.cash ?? []).map((r: Row) => [r.account_ref, r.amount, r.currency])} />
  </div>
);

export const TransactionJournalPanel: React.FC = () => {
  const [state, setState] = useState<Row | null>(null);
  const [event, setEvent] = useState<AuthoredEvent | null>(null);
  const [form, setForm] = useState<Row>({});
  const [preview, setPreview] = useState<Row | null>(null);
  const [duplicateOk, setDuplicateOk] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => setState((await callTxn('GET', 'state')).body), []);
  useEffect(() => { void load(); }, [load]);

  const open = (e: AuthoredEvent) => {
    setEvent(e); setPreview(null); setMessage(null); setDuplicateOk(false);
    setForm({ transaction_id: newTransactionId(), event_type: e, currency: 'USD' });
  };
  const transaction = (): Row => Object.fromEntries(Object.entries(form).filter(([, v]) => v !== '' && v != null));

  const review = async () => {
    const r = await callTxn('POST', 'preview', { transaction: transaction() });
    if (r.http === 200) { setPreview(r.body); setMessage(r.body.duplicate ? txnTh(r.body.duplicate) : null); }
    else { setPreview(null); setMessage(txnTh(r.body.code ?? r.body.status)); }
  };
  const confirm = async () => {
    const body: Row = { base_revision: state?.revision, confirm: true, transaction: transaction() };
    if (duplicateOk) body.confirm_duplicate = true;
    const r = await callTxn('POST', 'record', body);
    setMessage(txnTh(r.body.code ?? r.body.status));
    if (r.http === 200) { setEvent(null); setPreview(null); }
    await load();
  };

  const canWrite = state?.odr_005 === 'RATIFIED';
  const accounts: string[] = Array.from(new Set<string>([...(state?.projection?.cash ?? []), ...(state?.projection?.positions ?? [])].map((r: Row) => r.account_ref)));
  const securities: string[] = Array.from(new Set<string>((state?.projection?.positions ?? []).map((r: Row) => r.security_id)));
  return (
    <section aria-labelledby="sec-journal" className="bg-surface border border-default rounded-lg p-4 space-y-3 text-xs">
      <div>
        <h2 id="sec-journal" className="text-sm font-semibold text-primary">ประวัติธุรกรรม · Transaction journal</h2>
        <p className="text-secondary">บันทึกรายการที่ซื้อขาย/ฝากถอนไปแล้วจากหลักฐานของโบรกเกอร์ ไม่มีการส่งคำสั่งไปยังโบรกเกอร์ · คำนวณจำนวนหุ้นและเงินสดใน Python</p>
        {state?.baseline && <p className="text-secondary">ฐานตั้งต้น: statement วันที่ <span className="font-mono-code">{state.baseline.cutoff}</span> · รายการหลังวันนี้เท่านั้นที่ถูกนับ · {txnTh(state.corrections)}</p>}
        {state && state.status !== 'OK' && <p role="alert" className="text-amber-600">{txnTh(state.code ?? state.status)}</p>}
        {state && !canWrite && state.status === 'OK' && <p className="text-amber-600">{txnTh('TRANSACTION_AUTHORING_AUTHORIZATION_REQUIRED')}</p>}
      </div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Record transaction">
        {AUTHORED_EVENTS.map((e) => (
          <button key={e} type="button" disabled={!canWrite} onClick={() => open(e)}
            className="px-3 py-1 rounded border border-default text-primary hover:bg-surface-muted disabled:opacity-50">{EVENT_LABEL_TH[e]}</button>
        ))}
      </div>
      {event && (
        <form className="space-y-2 border border-default rounded p-3" onSubmit={(e) => { e.preventDefault(); void review(); }} aria-label={`${event} form`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {EVENT_FIELDS[event].map((f) => (
              <label key={f} className="flex flex-col gap-0.5">
                <span className="text-muted">{f}{OPTIONAL_FIELDS.has(f) ? ' (optional)' : ''}</span>
                <input name={f} value={form[f] ?? ''} list={f === 'account_ref' ? 'txn-accounts' : f === 'security_id' ? 'txn-securities' : undefined}
                  type={f.endsWith('_date') ? 'date' : 'text'} inputMode={['quantity', 'price', 'gross_amount', 'commission', 'fees', 'net_cash'].includes(f) ? 'decimal' : undefined}
                  onChange={(ev) => { setForm({ ...form, [f]: ev.target.value }); setPreview(null); }}
                  className="px-2 py-1 rounded border border-default bg-surface font-mono-code" />
              </label>
            ))}
          </div>
          <datalist id="txn-accounts">{accounts.map((a) => <option key={a} value={a} />)}</datalist>
          <datalist id="txn-securities">{securities.map((s) => <option key={s} value={s} />)}</datalist>
          <p className="text-[11px] text-muted">กรอกตามหลักฐานจริง: ราคาที่ได้จริง ค่าธรรมเนียม และเงินสุทธิ (ซื้อ/ถอน/ค่าธรรมเนียมเป็นค่าติดลบ) ระบบไม่เดาค่าแทน</p>
          <div className="flex gap-2">
            <button type="submit" className="px-3 py-1 rounded bg-accent text-white">ตรวจสอบก่อนบันทึก</button>
            <button type="button" onClick={() => setEvent(null)} className="px-3 py-1 rounded border border-default">ยกเลิก</button>
          </div>
        </form>
      )}
      {message && <p role="status" className="text-primary">{message}</p>}
      {preview && (
        <div className="space-y-2 border border-default rounded p-3">
          <div className="grid md:grid-cols-2 gap-3">
            <Projection p={preview.effect?.before} title="ก่อนบันทึก" />
            <Projection p={preview.effect?.after} title="หลังบันทึก" />
          </div>
          {preview.duplicate === 'POSSIBLE_DUPLICATE' && (
            <label className="flex items-center gap-1"><input type="checkbox" checked={duplicateOk} onChange={(e) => setDuplicateOk(e.target.checked)} /> ยืนยันว่าเป็นรายการจริงอีกรายการ</label>
          )}
          <button type="button" onClick={() => void confirm()} className="px-3 py-1 rounded bg-accent text-white">ยืนยันบันทึก</button>
        </div>
      )}
      {state?.status === 'OK' && (
        <>
          <Projection p={state.projection} title="จำนวนหุ้นและเงินสดปัจจุบัน (statement + ธุรกรรม)" />
          <h4 className="font-semibold text-primary">รายการที่บันทึก</h4>
          <SimpleTable head={['Date', 'Type', 'Account', 'Security', 'Qty', 'Price', 'Net cash', 'Ccy', 'Status']}
            rows={(state.entries ?? []).map((r: Row) => [r.trade_date, r.event_type, r.account_ref, r.security_id ?? '-', r.quantity ?? '-',
              r.price ?? '-', r.net_cash ?? '-', r.currency ?? '-', <StatusBadge key="s" status={r.status} />])} />
        </>
      )}
    </section>
  );
};
