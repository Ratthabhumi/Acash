import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ChevronLeft, ChevronRight, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react';
import {
  ACCOUNT_ROLES, Account, CASH_KINDS, CAPACITY_FIELDS, CLASSIFICATIONS, CapacityDoc, INSTRUMENT_TYPES, Issue, Position,
  SnapshotDoc, capacityForSave, clearPlaceholders, compact, emptyCapacity, emptySnapshot, isDecimalText, messageTh,
} from '../../services/privateInput';
import { upiRepository } from '../../services/upiRepository';

const callInput = upiRepository.callInput;

const STEPS = ['สิทธิ์และความเป็นส่วนตัว', 'บัญชี Dime!', 'หลักทรัพย์', 'เงินสดและสกุลเงิน', 'ความสามารถทางการเงิน', 'ตรวจทานและบันทึก'];
const CAPACITY_LABELS: Record<string, string> = {
  monthly_income_thb: 'รายได้ต่อเดือน (THB)', essential_expenses_thb: 'ค่าใช้จ่ายจำเป็นต่อเดือน (THB)',
  obligations_thb: 'ภาระหนี้ต่อเดือน (THB)', emergency_reserve_thb: 'เงินสำรองฉุกเฉินที่มี (THB)',
  reserve_target_months: 'เป้าหมายเงินสำรอง (เดือน)', planned_contribution_thb: 'เงินลงทุนตามแผนต่อเดือน (THB)',
  flexible_contribution_thb: 'เงินลงทุนยืดหยุ่นต่อเดือน (THB)', exceptional_expenses_12m_thb: 'ค่าใช้จ่ายพิเศษใน 12 เดือน (THB)',
  quant_budget_thb: 'งบสมมุติสำหรับ quant (THB, ไม่ใช่เงินจริง)',
};
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const inputCls = 'w-full bg-surface border border-default rounded px-2 py-1 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent';

const Field: React.FC<{ label: string; value: string; onChange: (v: string) => void; placeholder?: string; decimal?: boolean; mono?: boolean; type?: 'date' | 'datetime-local' }> =
  ({ label, value, onChange, placeholder, decimal, mono, type }) => {
    const bad = decimal && value !== '' && !isDecimalText(value);
    return (
      <label className="block space-y-0.5">
        <span className="text-[11px] text-secondary">{label}</span>
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} inputMode={decimal ? 'decimal' : undefined}
          aria-invalid={bad || undefined} className={`${inputCls} ${mono || decimal ? 'font-mono-code' : ''} ${bad ? 'border-red-500' : ''}`} />
        {bad && <span className="text-[11px] text-red-400">ตัวเลขและจุดทศนิยมเท่านั้น เช่น 1234.56</span>}
      </label>
    );
  };

const Select: React.FC<{ label: string; value: string; options: readonly string[]; onChange: (v: string) => void }> = ({ label, value, options, onChange }) => (
  <label className="block space-y-0.5">
    <span className="text-[11px] text-secondary">{label}</span>
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      {options.map((o) => <option key={o} value={o}>{o || '—'}</option>)}
    </select>
  </label>
);

const CURRENCIES = ['', 'THB', 'USD'] as const;
const Ccy: React.FC<{ label: string; value: string; onChange: (v: string) => void }> = ({ label, value, onChange }) => (
  <Select label={label} value={value} onChange={onChange}
    options={value && !(CURRENCIES as readonly string[]).includes(value) ? [...CURRENCIES, value] : CURRENCIES} />
);

const BANGKOK = '+07:00';
const toLocalInput = (iso: string) => (iso.endsWith(BANGKOK) ? iso.slice(0, 16) : '');
const fromLocalInput = (v: string) => (v ? `${v.slice(0, 16)}:00${BANGKOK}` : '');

type ReportState = { status: string; generation_id?: string; generated_at?: string; preflight?: string; inputs_changed_since?: boolean };

const stepFor = (where = ''): number => {
  if (where.startsWith('capacity') || CAPACITY_FIELDS.some((f) => where.includes(f))) return 4;
  if (/positions|prices|securities/.test(where)) return 2;
  if (/cash|fx_rates|report_currenc|reporting_currency/.test(where)) return 3;
  return 1;
};

const Card: React.FC<{ title: string; onRemove?: () => void; children: React.ReactNode }> = ({ title, onRemove, children }) => (
  <div className="border border-default rounded-md p-3 space-y-2 bg-surface-muted/40">
    <div className="flex items-center justify-between">
      <span className="text-xs font-semibold text-primary">{title}</span>
      {onRemove && <button type="button" onClick={onRemove} aria-label={`ลบ ${title}`} className="text-muted hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>}
    </div>
    {children}
  </div>
);

const AddButton: React.FC<{ label: string; onClick: () => void }> = ({ label, onClick }) => (
  <button type="button" onClick={onClick} className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-dashed border-default text-secondary hover:text-primary">
    <Plus className="w-3.5 h-3.5" /> {label}
  </button>
);

const Issues: React.FC<{ title: string; items: Issue[]; tone: 'error' | 'warn'; onGo: (step: number) => void }> = ({ title, items, tone, onGo }) => items.length === 0 ? null : (
  <div className={`rounded-md border p-3 space-y-1 text-xs ${tone === 'error' ? 'border-red-500/50' : 'border-amber-500/50'}`}>
    <div className="font-semibold text-primary">{title}</div>
    <ul className="space-y-1">
      {items.map((i, n) => (
        <li key={n}><span className="text-primary">{messageTh(i.code)}</span>
          {i.where && <span className="text-muted font-mono-code"> · {i.where}</span>}
          <span className="text-muted font-mono-code"> · {i.code}</span>
          {i.where && <button type="button" onClick={() => onGo(stepFor(i.where))} className="ml-2 underline text-accent">ไปแก้ที่ขั้นตอน {stepFor(i.where) + 1}</button>}</li>
      ))}
    </ul>
  </div>
);

interface Props { token: string; hasReport: boolean; onGenerated: () => void }

export const SetupWizard: React.FC<Props> = ({ token, hasReport, onGenerated }) => {
  const [step, setStep] = useState(0);
  const [snap, setSnap] = useState<SnapshotDoc>(emptySnapshot);
  const [cap, setCap] = useState<CapacityDoc>(emptyCapacity);
  const [revisions, setRevisions] = useState<Record<string, string>>({ snapshot: 'ABSENT', capacity: 'ABSENT' });
  const [auth, setAuth] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Issue[]>([]);
  const [warnings, setWarnings] = useState<Issue[]>([]);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [report, setReport] = useState<ReportState | null>(null);
  const [recovery, setRecovery] = useState(false);
  const [quick, setQuick] = useState(true);

  const editSnap = (fn: (d: SnapshotDoc) => void) => { setSnap((prev) => { const next = clone(prev); fn(next); return next; }); setDirty(true); };
  const editAccount = (i: number, fn: (a: Account) => void) => editSnap((d) => fn(d.accounts[i]));

  const load = useCallback(async () => {
    setBusy(true);
    setNotice('');
    const status = await callInput(token, 'GET', 'status');
    if (status.http !== 200) { setErrors([{ code: status.body.status }]); setBusy(false); return; }
    setAuth({ odr_001: String(status.body.odr_001), odr_003: String(status.body.odr_003) });
    setReport((status.body.report as ReportState | undefined) ?? null);
    setRecovery(status.body.recovery_pending === true);
    const revs: Record<string, string> = {};
    for (const kind of ['snapshot', 'capacity'] as const) {
      const r = await callInput(token, 'GET', kind);
      revs[kind] = String(r.body.revision ?? 'ABSENT');
      const doc = r.http === 200 ? clearPlaceholders(r.body.document) : null;
      if (kind === 'snapshot') setSnap(doc && typeof doc === 'object' ? { ...emptySnapshot(), ...(doc as Partial<SnapshotDoc>) } : emptySnapshot());
      else setCap(doc && typeof doc === 'object' ? { ...emptyCapacity(), ...(doc as Partial<CapacityDoc>) } : emptyCapacity());
    }
    setRevisions(revs);
    setErrors([]);
    setWarnings([]);
    setDirty(false);
    setBusy(false);
  }, [token]);

  const refreshStatus = async () => {
    const s = await callInput(token, 'GET', 'status');
    if (s.http !== 200) return;
    setReport((s.body.report as ReportState | undefined) ?? null);
    setRecovery(s.body.recovery_pending === true);
  };

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!dirty) return undefined;
    const guard = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [dirty]);

  const collect = (body: Record<string, unknown>) => {
    const errs: Issue[] = [], warns: Issue[] = [];
    for (const kind of ['snapshot', 'capacity']) {
      const part = body[kind] as { errors?: Issue[]; warnings?: Issue[] } | undefined;
      const tag = (i: Issue): Issue => (kind === 'capacity' ? { ...i, where: `capacity.${i.where ?? ''}` } : i);
      if (part) { errs.push(...(part.errors ?? []).map(tag)); warns.push(...(part.warnings ?? []).map(tag)); }
    }
    return { errs, warns };
  };

  const validate = async () => {
    setBusy(true);
    setNotice('');
    const r = await callInput(token, 'POST', 'validate', { snapshot: compact(snap), capacity: capacityForSave(cap) });
    if (r.http !== 200) setErrors([{ code: r.body.status }]);
    else {
      const { errs, warns } = collect(r.body);
      setErrors(errs);
      setWarnings(warns);
      if (!errs.length) setNotice('ข้อมูลผ่านการตรวจโดย Python แล้ว');
    }
    setBusy(false);
  };

  const save = async () => {
    setBusy(true);
    setNotice('');
    const r = await callInput(token, 'PUT', 'inputs', {
      snapshot: compact(snap), capacity: capacityForSave(cap), base_revisions: revisions, confirm_replace: true,
    });
    setBusy(false);
    if (r.http === 200) {
      setRevisions(r.body.revisions as Record<string, string>);
      setErrors([]);
      setDirty(false);
      setConfirm(false);
      setNotice('บันทึก snapshot และ capacity พร้อมกันแล้ว (ไฟล์เดิมสำรองไว้ใน data/private/backups)');
      void refreshStatus();
      return;
    }
    if (r.http === 422 && r.body.status === 'INVALID') {
      const { errs, warns } = collect(r.body);
      setErrors(errs);
      setWarnings(warns);
      return;
    }
    setErrors([{ code: String(r.body.status), where: String(r.body.code ?? '') }]);
  };

  const generate = async () => {
    setBusy(true);
    setNotice('');
    const r = await callInput(token, 'POST', 'generate', {});
    setBusy(false);
    void refreshStatus();
    if (r.http === 200) { setErrors([]); onGenerated(); return; }
    const checks = (r.body.checks as { check: string; status: string; detail: string }[] | undefined) ?? [];
    setErrors([{ code: r.body.status, where: String(r.body.code ?? '') },
      ...checks.filter((c) => c.status === 'FAIL' || c.status === 'BLOCKED').map((c) => ({ code: c.detail.split(':')[0] || c.status, where: c.check }))]);
  };

  const canSave = auth.odr_003 === 'RATIFIED';
  const priceFor = (sid: string) => snap.prices.find((p) => p.security_id === sid);
  const securityFor = (sid: string) => snap.securities.find((s) => s.security_id === sid);
  const setPrice = (sid: string, field: 'price' | 'currency' | 'as_of', value: string) => editSnap((d) => {
    let row = d.prices.find((p) => p.security_id === sid);
    if (!row) { row = { security_id: sid, currency: 'USD', price: '', as_of: d.valuation_date, source_id: 'DIME_APP_DISPLAY' }; d.prices.push(row); }
    row[field] = value;
    if (!row.price) d.prices = d.prices.filter((p) => p !== row);
  });
  const setSecurity = (sid: string, field: string, value: string) => editSnap((d) => {
    let row = d.securities.find((s) => s.security_id === sid);
    if (!row) { row = { security_id: sid, classification: 'UNKNOWN', methodology: 'NOT_CLASSIFIED' }; d.securities.push(row); }
    (row as unknown as Record<string, string>)[field] = value;
    row.methodology = row.classification === 'UNKNOWN' ? 'NOT_CLASSIFIED' : 'OWNER_DECLARED_WITH_EVIDENCE';
    const extras = [row.evidence_ref, row.instrument_type, row.exchange_mic, row.isin, row.figi, row.trading_currency].some(Boolean);
    if (row.classification === 'UNKNOWN' && !extras) d.securities = d.securities.filter((s) => s !== row);
  });
  const renameSecurity = (ai: number, pi: number, next: string) => editSnap((d) => {
    const prev = d.accounts[ai].positions![pi].security_id;
    d.accounts[ai].positions![pi].security_id = next;
    const stillUsed = d.accounts.some((a) => (a.positions ?? []).some((p) => p.security_id === prev));
    if (!stillUsed) {
      d.prices.forEach((p) => { if (p.security_id === prev) p.security_id = next; });
      d.securities.forEach((s) => { if (s.security_id === prev) s.security_id = next; });
    }
  });

  const body = (() => {
    switch (step) {
      case 0: return (
        <div className="space-y-3 text-xs">
          <div className="rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3 flex gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="space-y-1">
              <div className="font-semibold text-primary">ACASH ได้รับอนุญาตให้อ่านและวิเคราะห์ข้อมูลพอร์ตส่วนตัวในเครื่องนี้เท่านั้น ไม่มีสิทธิ์ซื้อขายหรือโอนเงิน</div>
              <div className="text-secondary">ข้อมูลอยู่ใน data/private/ บนเครื่องนี้เท่านั้น ไม่ถูกส่งขึ้น GitHub ไม่ส่งออกนอกเครื่อง ไม่เชื่อมต่อโบรกเกอร์ และไม่มีการส่งคำสั่งซื้อขายจริง</div>
            </div>
          </div>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div><dt className="text-muted">ODR-001 อ่านและวิเคราะห์</dt><dd className="font-mono-code text-primary">{auth.odr_001 ?? '…'}</dd></div>
            <div><dt className="text-muted">ODR-003 บันทึกข้อมูลจากหน้าจอนี้</dt><dd className="font-mono-code text-primary">{auth.odr_003 ?? '…'}</dd></div>
          </dl>
          {!canSave && auth.odr_003 && (
            <p className="text-amber-300">กรอกและตรวจข้อมูลได้ แต่ยังบันทึกไม่ได้จนกว่าเจ้าของจะอนุมัติ ODR-003 (docs/governance/ODR_UPI_LOCAL_INPUT_AUTHORING_003.md)</p>
          )}
          <p className="text-secondary">Snapshot คือภาพ ณ วันหนึ่ง ไม่ใช่ประวัติการซื้อขาย ระบบจึงไม่สร้างผลตอบแทนย้อนหลังจาก snapshot</p>
          <fieldset className="flex flex-wrap gap-3" aria-label="รูปแบบการกรอก">
            <label className="flex items-center gap-1"><input type="radio" checked={quick} onChange={() => setQuick(true)} /> เริ่มต้นเร็ว: วันที่ ยอดรวมบัญชี เงินสด อัตราแลกเปลี่ยน และ capacity</label>
            <label className="flex items-center gap-1"><input type="radio" checked={!quick} onChange={() => setQuick(false)} /> ละเอียด: กรอกรายหลักทรัพย์ด้วย</label>
          </fieldset>
          <button type="button" onClick={() => void load()} disabled={busy} className="inline-flex items-center gap-1 px-2 py-1 rounded border border-default text-secondary">
            <RefreshCw className="w-3.5 h-3.5" /> โหลดข้อมูลที่บันทึกไว้ล่าสุด
          </button>
        </div>
      );
      case 1: return (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Field label="รหัส snapshot" value={snap.snapshot_id} onChange={(v) => editSnap((d) => { d.snapshot_id = v; })} mono />
            <Field type="datetime-local" label="เวลาที่เปิดดูในแอป (เวลาไทย UTC+07:00)" value={toLocalInput(snap.observed_at)} onChange={(v) => editSnap((d) => { d.observed_at = fromLocalInput(v); })} mono />
            <Field type="date" label="วันที่ของมูลค่า (valuation date ตามที่แอปแสดง)" value={snap.valuation_date} onChange={(v) => editSnap((d) => { d.valuation_date = v; })} mono />
          </div>
          {snap.observed_at && !snap.observed_at.endsWith(BANGKOK) && <p className="text-[11px] text-amber-300">เวลาที่บันทึกไว้ไม่ได้อยู่ในรูปแบบเวลาไทย ({snap.observed_at}) กรุณาเลือกใหม่</p>}
          <p className="text-[11px] text-muted">เวลาที่เปิดดูอาจเป็นคนละวันกับวันที่ของมูลค่า (ตลาดสหรัฐปิดตามเวลานิวยอร์ก) ให้กรอกตามที่แอปแสดง</p>
          {snap.accounts.map((a, i) => (
            <Card key={i} title={a.account_ref || `บัญชี ${i + 1}`} onRemove={() => editSnap((d) => { d.accounts.splice(i, 1); })}>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                <Field label="รหัสบัญชี (ห้ามใช้เลขบัญชีจริง)" value={a.account_ref} onChange={(v) => editAccount(i, (x) => { x.account_ref = v.toUpperCase(); })} placeholder="DIME_SECURITIES" mono />
                <Field label="โบรกเกอร์" value={a.broker} onChange={(v) => editAccount(i, (x) => { x.broker = v.toUpperCase(); })} placeholder="DIME" mono />
                <Select label="บทบาท" value={a.role} options={ACCOUNT_ROLES} onChange={(v) => editAccount(i, (x) => { x.role = v; })} />
                <Ccy label="สกุลเงินหลัก" value={a.base_currency} onChange={(v) => editAccount(i, (x) => { x.base_currency = v; })} />
                <Field label="ยอดรวมที่แอปแสดง" value={a.reported_total?.amount ?? ''} decimal
                  onChange={(v) => editAccount(i, (x) => { x.reported_total = { amount: v, currency: x.reported_total?.currency || x.base_currency }; })} />
                <Ccy label="สกุลเงินของยอดรวม" value={a.reported_total?.currency ?? ''}
                  onChange={(v) => editAccount(i, (x) => { x.reported_total = { amount: x.reported_total?.amount ?? '', currency: v }; })} />
              </div>
              <div className="text-[11px] text-muted">ยอดพอร์ตย่อยที่แอปแสดง (ถ้ามี)</div>
              {(a.sub_portfolio_totals ?? []).map((t, j) => (
                <div key={j} className="grid grid-cols-[1fr_1fr_6rem_auto] gap-2 items-end">
                  <Field label="ชื่อพอร์ตย่อย" value={t.sub_portfolio} onChange={(v) => editAccount(i, (x) => { x.sub_portfolio_totals![j].sub_portfolio = v; })} />
                  <Field label="ยอด" value={t.amount} decimal onChange={(v) => editAccount(i, (x) => { x.sub_portfolio_totals![j].amount = v; })} />
                  <Ccy label="สกุล" value={t.currency} onChange={(v) => editAccount(i, (x) => { x.sub_portfolio_totals![j].currency = v; })} />
                  <button type="button" aria-label="ลบยอดพอร์ตย่อย" onClick={() => editAccount(i, (x) => { x.sub_portfolio_totals!.splice(j, 1); })} className="mb-1 text-muted hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              <AddButton label="เพิ่มยอดพอร์ตย่อย" onClick={() => editAccount(i, (x) => { x.sub_portfolio_totals = [...(x.sub_portfolio_totals ?? []), { sub_portfolio: '', amount: '', currency: x.base_currency }]; })} />
            </Card>
          ))}
          <div className="flex flex-wrap gap-2">
            {([['DIME_SECURITIES', 'LONG_TERM', 'USD', 'Dime! Securities'], ['DIME_FCD', 'CASH_RESERVE', 'USD', 'Dime! FCD'], ['DIME_SAVE', 'CASH_RESERVE', 'THB', 'Dime! Save'], ['', 'OTHER', 'THB', 'บัญชีอื่น']] as const).map(([ref, role, ccy, label]) => (
              <AddButton key={label} label={label} onClick={() => editSnap((d) => { d.accounts.push({ account_ref: ref, broker: ref ? 'DIME' : '', role, base_currency: ccy }); })} />
            ))}
          </div>
        </div>
      );
      case 2: return (
        <div className="space-y-3">
          {quick && <p className="text-xs text-amber-300">โหมดเริ่มต้นเร็ว: ข้ามขั้นตอนนี้ได้ รายงานจะเป็น EVIDENCE_ONLY_REPORT (ยอดรวมตามที่แอปแสดง ยังไม่แยกรายหลักทรัพย์)</p>}
          <p className="text-xs text-secondary">กรอกเฉพาะที่แอปแสดงจริง: มูลค่าอย่างเดียว, จำนวนหน่วยกับราคา, หรือข้ามไปใช้ยอดรวมบัญชีก็ได้ ไม่ต้องกรอกทุกตัว ระบบไม่เดาค่าที่ขาด</p>
          {snap.accounts.map((a, ai) => (
            <Card key={ai} title={a.account_ref || `บัญชี ${ai + 1}`}>
              {(a.positions ?? []).map((p, pi) => {
                const price = priceFor(p.security_id);
                const sec = securityFor(p.security_id);
                const setPos = (field: keyof Position, v: string) => editAccount(ai, (x) => { (x.positions![pi] as unknown as Record<string, string>)[field] = v; });
                return (
                  <Card key={pi} title={p.security_id || `หลักทรัพย์ ${pi + 1}`} onRemove={() => editAccount(ai, (x) => { x.positions!.splice(pi, 1); })}>
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                      <Field label="รหัสหลักทรัพย์ (ticker)" value={p.security_id} mono onChange={(v) => renameSecurity(ai, pi, v.toUpperCase())} />
                      <Field label="พอร์ตย่อย" value={p.sub_portfolio} onChange={(v) => setPos('sub_portfolio', v)} />
                      <Field label="มูลค่าที่แอปแสดง" value={p.observed_market_value ?? ''} decimal onChange={(v) => setPos('observed_market_value', v)} />
                      <Ccy label="สกุลเงินของมูลค่า" value={p.observed_market_value_currency ?? ''} onChange={(v) => setPos('observed_market_value_currency', v)} />
                      <Field label="จำนวนหน่วย" value={p.quantity ?? ''} decimal onChange={(v) => setPos('quantity', v)} />
                      <Field label="ราคาต่อหน่วย" value={price?.price ?? ''} decimal onChange={(v) => setPrice(p.security_id, 'price', v)} />
                      <Ccy label="สกุลเงินของราคา" value={price?.currency ?? ''} onChange={(v) => setPrice(p.security_id, 'currency', v)} />
                      <Field type="date" label="วันที่ราคา" value={price?.as_of ?? ''} mono onChange={(v) => setPrice(p.security_id, 'as_of', v)} />
                      <Field label="ต้นทุนรวม (ถ้ามี)" value={p.cost_basis_total ?? ''} decimal onChange={(v) => setPos('cost_basis_total', v)} />
                      <Ccy label="สกุลเงินต้นทุน" value={p.cost_basis_currency ?? ''} onChange={(v) => setPos('cost_basis_currency', v)} />
                      <Select label="กลุ่ม (ต้องมีเอกสารอ้างอิง)" value={sec?.classification ?? 'UNKNOWN'} options={CLASSIFICATIONS} onChange={(v) => setSecurity(p.security_id, 'classification', v)} />
                      <Field label="แหล่งอ้างอิง เช่น factsheet" value={sec?.evidence_ref ?? ''} onChange={(v) => setSecurity(p.security_id, 'evidence_ref', v)} />
                      <Select label="ประเภท" value={sec?.instrument_type ?? ''} options={INSTRUMENT_TYPES} onChange={(v) => setSecurity(p.security_id, 'instrument_type', v)} />
                    </div>
                  </Card>
                );
              })}
              <AddButton label="เพิ่มหลักทรัพย์" onClick={() => editAccount(ai, (x) => { x.positions = [...(x.positions ?? []), { security_id: '', sub_portfolio: '' }]; })} />
            </Card>
          ))}
          {snap.accounts.length === 0 && <p className="text-xs text-muted">เพิ่มบัญชีในขั้นตอนก่อนหน้าก่อน</p>}
        </div>
      );
      case 3: return (
        <div className="space-y-3">
          <div className="text-xs text-secondary rounded-md border border-default p-3 space-y-1">
            <div>มูลค่าสุทธิ (NAV) = เงินสดที่ชำระแล้ว + ดอกเบี้ยค้างรับ + มูลค่าหลักทรัพย์ แปลงเป็นสกุลเงินรายงานด้วยอัตราที่คุณกรอกเท่านั้น</div>
            <div>ยอดรวมที่แอปแสดงใช้กระทบยอดกับรายการ ไม่ถูกบวกซ้ำ · เงิน USD ก้อนเดียวกันต้องกรอกที่บัญชีเดียว · ระบบไม่สร้างอัตรากลับด้าน (THB→USD) ให้เอง</div>
          </div>
          {snap.accounts.map((a, i) => (
            <Card key={i} title={`เงินสด · ${a.account_ref || `บัญชี ${i + 1}`}`}>
              {(a.cash ?? []).map((c, j) => (
                <div key={j} className="grid grid-cols-[1fr_6rem_10rem_auto] gap-2 items-end">
                  <Field label="ยอด" value={c.amount} decimal onChange={(v) => editAccount(i, (x) => { x.cash![j].amount = v; })} />
                  <Ccy label="สกุล" value={c.currency} onChange={(v) => editAccount(i, (x) => { x.cash![j].currency = v; })} />
                  <Select label="ประเภท" value={c.kind} options={CASH_KINDS} onChange={(v) => editAccount(i, (x) => { x.cash![j].kind = v; })} />
                  <button type="button" aria-label="ลบเงินสด" onClick={() => editAccount(i, (x) => { x.cash!.splice(j, 1); })} className="mb-1 text-muted hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
              <AddButton label="เพิ่มเงินสด / ดอกเบี้ยค้างรับ" onClick={() => editAccount(i, (x) => { x.cash = [...(x.cash ?? []), { currency: x.base_currency, amount: '', kind: 'SETTLED' }]; })} />
            </Card>
          ))}
          <Card title="สกุลเงินรายงานและอัตราแลกเปลี่ยน">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <Select label="สกุลเงินรายงานหลัก" value={snap.reporting_currency} options={['THB', 'USD']}
                onChange={(v) => editSnap((d) => { d.reporting_currency = v; if (!d.report_currencies.includes(v)) d.report_currencies.unshift(v); })} />
              <Select label="รายงานเพิ่มเป็น" value={snap.report_currencies.filter((c) => c !== snap.reporting_currency)[0] ?? ''} options={['', 'THB', 'USD']}
                onChange={(v) => editSnap((d) => { d.report_currencies = v && v !== d.reporting_currency ? [d.reporting_currency, v] : [d.reporting_currency]; })} />
            </div>
            {snap.fx_rates.map((r, j) => (
              <div key={j} className="grid grid-cols-2 sm:grid-cols-[5rem_5rem_1fr_8rem_1fr_auto] gap-2 items-end">
                <Ccy label="จาก" value={r.from} onChange={(v) => editSnap((d) => { d.fx_rates[j].from = v; })} />
                <Ccy label="เป็น" value={r.to} onChange={(v) => editSnap((d) => { d.fx_rates[j].to = v; })} />
                <Field label="อัตรา (ตามที่แอปแสดง)" value={r.rate} decimal onChange={(v) => editSnap((d) => { d.fx_rates[j].rate = v; })} />
                <Field type="date" label="วันที่ของอัตรา" value={r.as_of} mono onChange={(v) => editSnap((d) => { d.fx_rates[j].as_of = v; })} />
                <Field label="แหล่งที่มา" value={r.source_id} mono onChange={(v) => editSnap((d) => { d.fx_rates[j].source_id = v.toUpperCase(); })} />
                <button type="button" aria-label="ลบอัตรา" onClick={() => editSnap((d) => { d.fx_rates.splice(j, 1); })} className="mb-1 text-muted hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            ))}
            <AddButton label="เพิ่มอัตราแลกเปลี่ยน" onClick={() => editSnap((d) => { d.fx_rates.push({ from: 'USD', to: 'THB', rate: '', as_of: d.valuation_date, source_id: 'DIME_APP_DISPLAY' }); })} />
          </Card>
        </div>
      );
      case 4: return (
        <div className="space-y-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {CAPACITY_FIELDS.map((f) => (
              <Field key={f} label={CAPACITY_LABELS[f]} value={cap[f]} decimal onChange={(v) => { setCap((c) => ({ ...c, [f]: v })); setDirty(true); }} />
            ))}
            <Field label="ระยะเวลาลงทุน (ปีเต็ม)" value={String(cap.horizon_years)} onChange={(v) => { setCap((c) => ({ ...c, horizon_years: v })); setDirty(true); }} mono />
          </div>
          <p className="text-[11px] text-muted">ถ้าไม่มีให้กรอก 0 อย่างชัดเจน (ช่องว่างไม่ถือเป็นศูนย์) · งบ quant เป็นตัวเลขสมมุติเพื่อวางแผนเท่านั้น ไม่มีการใช้เงินจริง (real capital USD 0.00)</p>
        </div>
      );
      default: return (
        <div className="space-y-3 text-xs">
          <p className="text-secondary">กด "ตรวจข้อมูล" ให้ Python ตรวจทั้งหมดก่อน ระบบไม่รวม ไม่ลบ และไม่แก้ค่าให้อัตโนมัติ</p>
          {recovery && <p className="text-red-400">{messageTh('INPUT_RECOVERY_REQUIRED')}</p>}
          <div className="rounded-md border border-default p-2 text-secondary">
            <span>รายงานล่าสุด: </span>
            {report?.status === 'CONSISTENT'
              ? <span className="font-mono-code text-primary">{report.generated_at} · {report.preflight}{report.inputs_changed_since ? ' · ข้อมูลเปลี่ยนหลังสร้างรายงาน กรุณาสร้างใหม่' : ' · ตรงกับข้อมูลที่บันทึกไว้'}</span>
              : <span className="font-mono-code text-primary">{report?.status ?? '…'}</span>}
          </div>
          <p className="text-[11px] text-muted">"บันทึก" เขียนข้อมูลที่กรอกลงเครื่อง · "ตรวจและสร้างรายงาน" สร้างรายงานจากข้อมูลที่บันทึกไว้แล้วเท่านั้น</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => void validate()} disabled={busy} className="px-3 py-1.5 rounded border border-default text-primary hover:bg-surface-muted disabled:opacity-50">ตรวจข้อมูล</button>
          </div>
          <label className="flex items-start gap-2">
            <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} disabled={!canSave} />
            <span>ยืนยันแทนที่ข้อมูลที่บันทึกไว้ใน data/private/ (ไฟล์เดิมจะถูกสำรองไว้)</span>
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => void save()} disabled={busy || !canSave || !confirm}
              className="px-3 py-1.5 rounded bg-accent text-white disabled:opacity-50">บันทึก</button>
            <button type="button" onClick={() => void generate()} disabled={busy || dirty}
              className="px-3 py-1.5 rounded border border-default text-primary hover:bg-surface-muted disabled:opacity-50">ตรวจและสร้างรายงาน</button>
          </div>
          {!canSave && <p className="text-amber-300">{messageTh('AUTHORING_AUTHORIZATION_REQUIRED')}</p>}
          {dirty && <p className="text-muted">มีการแก้ไขที่ยังไม่บันทึก รายงานจะสร้างจากข้อมูลที่บันทึกไว้เท่านั้น</p>}
        </div>
      );
    }
  })();

  return (
    <section aria-labelledby="setup-title" className="bg-surface border border-default rounded-lg p-4 space-y-4">
      <div>
        <h2 id="setup-title" className="text-base font-semibold text-primary">{hasReport ? 'อัปเดต snapshot พอร์ต' : 'ยังไม่มีพอร์ตส่วนตัว — ตั้งค่าพอร์ตของคุณ'}</h2>
        <p className="text-xs text-secondary">กรอกตามที่แอป Dime! แสดง ตัวเลขทุกตัวถูกตรวจและคำนวณโดย Python ในเครื่องนี้</p>
      </div>
      <ol className="flex flex-wrap gap-1" aria-label="ขั้นตอน">
        {STEPS.map((s, i) => (
          <li key={s}>
            <button type="button" onClick={() => setStep(i)} aria-current={step === i ? 'step' : undefined}
              className={`text-[11px] px-2 py-1 rounded ${step === i ? 'bg-accent text-white' : 'bg-surface-muted text-secondary hover:text-primary'}`}>
              {i + 1}. {s}
            </button>
          </li>
        ))}
      </ol>
      {busy && <div className="text-xs text-muted">กำลังทำงาน…</div>}
      {body}
      <Issues title="ต้องแก้ไขก่อน" items={errors} tone="error" onGo={setStep} />
      <Issues title="ข้อควรตรวจ (ไม่บล็อก)" items={warnings} tone="warn" onGo={setStep} />
      {notice && <div className="flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="w-3.5 h-3.5" /> {notice}</div>}
      <div className="flex justify-between">
        <button type="button" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-default text-secondary disabled:opacity-40"><ChevronLeft className="w-3.5 h-3.5" /> ก่อนหน้า</button>
        <button type="button" onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))} disabled={step === STEPS.length - 1}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-default text-secondary disabled:opacity-40">ถัดไป <ChevronRight className="w-3.5 h-3.5" /></button>
      </div>
    </section>
  );
};
