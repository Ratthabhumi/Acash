import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Download, FileUp } from 'lucide-react';
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

const fileToBase64 = (file: File): Promise<string> => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(String(reader.result).split(',')[1]);
  reader.onerror = reject;
  reader.readAsDataURL(file);
});

export const TransactionJournalPanel: React.FC = () => {
  const [state, setState] = useState<Row | null>(null);
  const [event, setEvent] = useState<AuthoredEvent | null>(null);
  const [form, setForm] = useState<Row>({});
  const [preview, setPreview] = useState<Row | null>(null);
  const [duplicateOk, setDuplicateOk] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<Row | null>(null);
  const [importRows, setImportRows] = useState<Row[]>([]);
  const [importLoading, setImportLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const downloadTemplate = async () => {
    const r = await callTxn('GET', 'import-template');
    if (r.http !== 200) { setMessage(txnTh(r.body.status)); return; }
    const blob = new Blob([r.body.csv as string], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'acash_transactions_template.csv';
    a.click(); URL.revokeObjectURL(url);
  };

  const previewCsv = async () => {
    if (!csvFile) return;
    setImportLoading(true); setMessage(null); setImportPreview(null);
    try {
      const b64 = await fileToBase64(csvFile);
      const r = await callTxn('POST', 'import-preview', { csv_bytes_base64: b64 });
      if (r.http === 200) {
        setImportPreview(r.body);
        setImportRows(r.body.rows ?? []);
        setMessage(null);
      } else {
        setMessage(txnTh(r.body.code ?? r.body.status));
        if (r.http === 422 && r.body.errors) {
          setImportPreview({ errors: r.body.errors, accepted_count: r.body.accepted_count ?? 0, rejected_count: r.body.rejected_count ?? 0 });
        }
      }
    } finally { setImportLoading(false); }
  };

  const confirmCsv = async () => {
    if (!importPreview || !csvFile) return;
    const r = await callTxn('POST', 'import-confirm', {
      base_revision: state?.revision, confirm: true,
      preview_sha256: importPreview.preview_sha256,
      rows: importRows,
    });
    setMessage(txnTh(r.body.code ?? r.body.status));
    if (r.http === 200) {
      setCsvFile(null); setImportPreview(null); setImportRows([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
    await load();
  };

  const canWrite = state?.odr_005 === 'RATIFIED';
  const accounts: string[] = Array.from(new Set<string>([...(state?.projection?.cash ?? []), ...(state?.projection?.positions ?? [])].map((r: Row) => r.account_ref)));
  const securities: string[] = Array.from(new Set<string>((state?.projection?.positions ?? []).map((r: Row) => r.security_id)));
  return (
    <section aria-labelledby="sec-journal" className="bg-surface border border-default rounded-lg p-4 space-y-4 text-sm">
      <div>
        <h2 id="sec-journal" className="text-base font-semibold text-primary">ประวัติธุรกรรม · Transaction journal</h2>
        <p className="text-secondary">บันทึกรายการที่ซื้อขาย/ฝากถอนไปแล้วจากหลักฐานของโบรกเกอร์ ไม่มีการส่งคำสั่งไปยังโบรกเกอร์ · คำนวณจำนวนหุ้นและเงินสดใน Python</p>
        {state?.baseline && <p className="text-secondary">ฐานตั้งต้น: statement วันที่ <span className="font-mono-code">{state.baseline.cutoff}</span> · รายการหลังวันนี้เท่านั้นที่ถูกนับ · {txnTh(state.corrections)}</p>}
        {state && state.status !== 'OK' && <p role="alert" className="text-amber-600">{txnTh(state.code ?? state.status)}</p>}
        {state && !canWrite && state.status === 'OK' && <p className="text-amber-600">{txnTh('TRANSACTION_AUTHORING_AUTHORIZATION_REQUIRED')}</p>}
      </div>

      <div className="border border-default rounded-lg p-3 space-y-3">
        <div className="flex items-center gap-2">
          <FileUp className="w-4 h-4 text-muted" aria-hidden />
          <h3 className="font-medium text-primary">นำเข้าประวัติธุรกรรม CSV</h3>
        </div>
        <p className="text-xs text-secondary">เลือกไฟล์ CSV ที่มีคอลัมน์ตามรูปแบบมาตรฐาน ตรวจสอบผลกระทบก่อนยืนยัน ไฟล์จะไม่อัปโหลดไปที่ไหน</p>
        <div className="flex flex-wrap items-center gap-2">
          <input ref={fileInputRef} type="file" accept=".csv,text/csv" disabled={!canWrite || importLoading}
            onChange={(e) => { setCsvFile(e.target.files?.[0] ?? null); setImportPreview(null); setMessage(null); }}
            className="text-xs file:mr-2 file:px-3 file:py-1.5 file:rounded file:border-0 file:bg-surface-muted file:text-primary" />
          <button type="button" disabled={!canWrite || !csvFile || importLoading} onClick={() => void previewCsv()}
            className="px-3 py-1.5 rounded bg-accent text-white disabled:opacity-50">ตรวจสอบไฟล์</button>
          <button type="button" onClick={() => void downloadTemplate()} className="inline-flex items-center gap-1 px-3 py-1.5 rounded border border-default text-secondary hover:bg-surface-muted">
            <Download className="w-3.5 h-3.5" /> ดาวน์โหลดตัวอย่าง
          </button>
        </div>
        {importPreview && (
          <div className="space-y-3 border border-default rounded p-3 bg-surface-muted/30">
            {'preview_sha256' in importPreview && (
              <>
                <div className="flex flex-wrap gap-3 text-xs">
                  <span className="text-secondary">รายการที่รับ: <span className="font-mono-code text-primary">{importPreview.accepted_count}</span></span>
                  <span className="text-secondary">ใหม่: <span className="font-mono-code text-primary">{importPreview.new_count}</span></span>
                  <span className="text-secondary">มีอยู่แล้ว: <span className="font-mono-code text-primary">{importPreview.already_imported_count}</span></span>
                  <span className="text-secondary">ฐานตั้งต้น: <span className="font-mono-code text-primary">{importPreview.baseline_cutoff}</span></span>
                </div>
                <SimpleTable head={['แถว', 'รหัส', 'ประเภท', 'บัญชี', 'วันที่', 'หลักทรัพย์', 'เงินสุทธิ', 'สกุล']}
                  rows={importRows.map((r: Row, i: number) => [i + 1, r.transaction_id, r.event_type, r.account_ref, r.trade_date, r.security_id ?? '-', r.net_cash ?? '-', r.currency ?? '-'])} />
                <div className="grid md:grid-cols-2 gap-3">
                  <Projection p={importPreview.effect?.before} title="ก่อนนำเข้า" />
                  <Projection p={importPreview.effect?.after} title="หลังนำเข้า" />
                </div>
                <button type="button" disabled={importPreview.new_count === 0} onClick={() => void confirmCsv()}
                  className="px-4 py-1.5 rounded bg-accent text-white disabled:opacity-50">ยืนยันนำเข้า</button>
              </>
            )}
            {'errors' in importPreview && importPreview.errors?.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-primary">รายการที่ถูกปฏิเสธ ({importPreview.rejected_count ?? importPreview.errors.length})</p>
                <ul className="text-xs space-y-1">
                  {(importPreview.errors as Row[]).map((e: Row, i: number) => (
                    <li key={i} className="text-secondary"><span className="font-mono-code text-primary">แถว {e.row_number}</span> · {txnTh(e.code)} {e.where ? `· ${e.where}` : ''}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Record transaction">
        {AUTHORED_EVENTS.map((e) => (
          <button key={e} type="button" disabled={!canWrite} onClick={() => open(e)}
            className="px-3 py-1.5 rounded border border-default text-primary hover:bg-surface-muted disabled:opacity-50">{EVENT_LABEL_TH[e]}</button>
        ))}
      </div>
      {event && (
        <form className="space-y-2 border border-default rounded p-3" onSubmit={(e) => { e.preventDefault(); void review(); }} aria-label={`${event} form`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {EVENT_FIELDS[event].map((f) => (
              <label key={f} className="flex flex-col gap-0.5">
                <span className="text-muted text-xs">{f}{OPTIONAL_FIELDS.has(f) ? ' (optional)' : ''}</span>
                <input name={f} value={form[f] ?? ''} list={f === 'account_ref' ? 'txn-accounts' : f === 'security_id' ? 'txn-securities' : undefined}
                  type={f.endsWith('_date') ? 'date' : 'text'} inputMode={['quantity', 'price', 'gross_amount', 'commission', 'fees', 'net_cash'].includes(f) ? 'decimal' : undefined}
                  onChange={(ev) => { setForm({ ...form, [f]: ev.target.value }); setPreview(null); }}
                  className="px-2 py-1.5 rounded border border-default bg-surface font-mono-code" />
              </label>
            ))}
          </div>
          <datalist id="txn-accounts">{accounts.map((a) => <option key={a} value={a} />)}</datalist>
          <datalist id="txn-securities">{securities.map((s) => <option key={s} value={s} />)}</datalist>
          <p className="text-xs text-muted">กรอกตามหลักฐานจริง: ราคาที่ได้จริง ค่าธรรมเนียม และเงินสุทธิ (ซื้อ/ถอน/ค่าธรรมเนียมเป็นค่าติดลบ) ระบบไม่เดาค่าแทน</p>
          <div className="flex gap-2">
            <button type="submit" className="px-3 py-1.5 rounded bg-accent text-white">ตรวจสอบก่อนบันทึก</button>
            <button type="button" onClick={() => setEvent(null)} className="px-3 py-1.5 rounded border border-default">ยกเลิก</button>
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
          <button type="button" onClick={() => void confirm()} className="px-3 py-1.5 rounded bg-accent text-white">ยืนยันบันทึก</button>
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
