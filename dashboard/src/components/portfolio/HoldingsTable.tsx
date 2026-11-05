import React, { useMemo, useState } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { NOT_ESTABLISHED, formatDec } from '../../services/upiView';
import type { PositionRow } from '../../services/upiView';

// One row per held line, exactly as Python projected it. Sorting is a view concern only: values are
// compared as decimal strings and never converted to floating point, no weight or P&L is recomputed,
// and a row without an established cost basis stays explicit instead of showing a zero.

type SortKey = 'security_id' | 'value_reporting' | 'weight' | 'unrealized_pnl_local';

const cmpDec = (a: string, b: string): number => {
  const norm = (v: string): [number, string] => {
    const negative = v.startsWith('-');
    const digits = (negative ? v.slice(1) : v).replace('.', '').replace(/^0+/, '') || '0';
    const point = (negative ? v.slice(1) : v).indexOf('.');
    const scale = point === -1 ? 0 : (negative ? v.slice(1) : v).length - point - 1;
    return [negative ? -1 : 1, `${digits.length}:${scale}:${digits}`];
  };
  const [sa, da] = norm(a);
  const [sb, db] = norm(b);
  if (sa !== sb) return sa - sb;
  return da < db ? -1 : da > db ? 1 : 0;
};

const cmp = (a: PositionRow, b: PositionRow, key: SortKey): number => {
  if (key === 'security_id') return a.security_id.localeCompare(b.security_id);
  const left = a[key];
  const right = b[key];
  if (left === null || left === undefined) return right === null || right === undefined ? 0 : 1;
  if (right === null || right === undefined) return -1;
  return -cmpDec(left, right); // largest first; negative values sort below positives
};

const HEAD: Array<[string, SortKey | null, string]> = [
  ['หลักทรัพย์', 'security_id', 'Security'],
  ['บัญชี', null, 'Account'],
  ['ประเภท/ชั้นสินทรัพย์', null, 'Instrument type and economic class'],
  ['จำนวน', null, 'Quantity'],
  ['ราคา', null, 'Price in its own currency'],
  ['มูลค่า', 'value_reporting', 'Qualified value in the reporting currency'],
  ['น้ำหนัก', 'weight', 'Share of total best evidence'],
  ['กำไร/ขาดทุนที่ยังไม่รับรู้', 'unrealized_pnl_local', 'Unrealised P&L in the local currency'],
];

interface Props {
  rows: PositionRow[];
  ccy: string;
  /** Total best evidence and the qualified row total, copied from Python. */
  total: string | null;
  positionValueTotal: string | null;
  status: string;
  weightBasis: string | null;
}

export const HoldingsTable: React.FC<Props> = ({ rows, ccy, total, positionValueTotal, status, weightBasis }) => {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('value_reporting');
  const [open, setOpen] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matched = q
      ? rows.filter((r) => [r.security_id, r.account_ref, r.instrument_type, r.economic_class, r.figi, r.isin]
        .some((value) => value?.toLowerCase().includes(q)))
      : rows;
    return [...matched].sort((a, b) => cmp(a, b, sort));
  }, [rows, query, sort]);

  if (status !== 'AVAILABLE' || rows.length === 0) {
    return (
      <div className="bg-surface border border-default rounded-lg p-4 text-xs text-secondary">
        {status === 'AVAILABLE' ? 'ไม่มีรายการหลักทรัพย์ในรายงานนี้' : `ยังไม่มีข้อมูลรายบรรทัด (${status})`}
        <p className="text-[11px] text-muted mt-1">ไม่มีการคำนวณแทนข้อมูลที่ขาดหาย</p>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-default rounded-lg p-4 space-y-3 w-full min-w-0 max-w-full">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-primary">Holdings</h3>
          <p className="text-[11px] text-secondary">
            {filtered.length} จาก {rows.length} รายการ
            {positionValueTotal ? ` · มูลค่าหลักทรัพย์รวม ${formatDec(positionValueTotal)} ${ccy}` : ''}
            {total ? ` · จาก total best evidence ${formatDec(total)} ${ccy}` : ''}
          </p>
        </div>
        <label className="relative block max-w-xs">
          <span className="sr-only">ค้นหาหลักทรัพย์</span>
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ค้นหา ticker / บัญชี / FIGI"
            className="w-full bg-surface border border-default rounded-md pl-8 pr-2 py-1.5 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent" />
        </label>
      </div>

      <div className="md:hidden space-y-2" aria-label="Holdings (compact)">
        <label className="flex items-center gap-2 text-[11px] text-muted">
          เรียงตาม
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}
            className="bg-surface border border-default rounded px-2 py-1 text-xs text-primary">
            <option value="value_reporting">มูลค่า</option>
            <option value="weight">น้ำหนัก</option>
            <option value="security_id">ชื่อหลักทรัพย์</option>
            <option value="unrealized_pnl_local">กำไร/ขาดทุน</option>
          </select>
        </label>
        {filtered.map((row) => {
          const key = `${row.account_ref}:${row.security_id}:${row.sub_portfolio ?? ''}:${row.source}`;
          const expanded = open === key;
          return (
            <div key={key} className="bg-surface-muted/40 border border-default rounded-lg p-2 text-xs">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <span className="font-mono-code text-primary">{row.security_id}</span>
                  <span className="block text-[11px] text-muted">{row.account_ref} · {row.instrument_type ?? NOT_ESTABLISHED}</span>
                </div>
                <div className="text-right shrink-0">
                  <span className="font-mono-code tabular-nums text-primary">{formatDec(row.value_reporting)}</span>
                  <span className="block text-[11px] text-muted">{row.weight === null ? NOT_ESTABLISHED : row.weight}</span>
                </div>
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-1 text-[11px]">
                <div><dt className="text-muted">จำนวน</dt><dd className="font-mono-code">{row.quantity ?? NOT_ESTABLISHED}</dd></div>
                <div><dt className="text-muted">ราคา</dt><dd className="font-mono-code">{row.price === null ? NOT_ESTABLISHED : `${formatDec(row.price)} ${row.price_currency}`}</dd></div>
                <div><dt className="text-muted">ชั้นสินทรัพย์</dt><dd>{row.economic_class ?? NOT_ESTABLISHED}</dd></div>
                <div><dt className="text-muted">P&amp;L</dt><dd className="font-mono-code">{row.unrealized_pnl_local === null ? 'ไม่มีต้นทุน' : `${formatDec(row.unrealized_pnl_local)} ${row.price_currency}`}</dd></div>
              </dl>
              <button type="button" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded}
                className="mt-1 text-[11px] text-secondary underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded">
                {expanded ? 'ซ่อนรายละเอียด' : 'รายละเอียด FIGI/ISIN'}
              </button>
              {expanded && (
                <p className="mt-1 text-[11px] font-mono-code text-secondary break-all">
                  FIGI {row.figi ?? NOT_ESTABLISHED} · ISIN {row.isin ?? NOT_ESTABLISHED} · {row.source}
                </p>
              )}
            </div>
          );
        })}
      </div>
      <div className="hidden md:block overflow-x-auto w-full max-w-full">
        <table className="w-full text-xs">
          <caption className="sr-only">รายการหลักทรัพย์ที่ถือครอง</caption>
          <thead>
            <tr className="text-left text-[11px] text-muted border-b border-subtle">
              {HEAD.map(([label, key, title]) => (
                <th key={label} scope="col" title={title} className="py-1.5 pr-3 font-medium">
                  {key ? (
                    <button type="button" onClick={() => setSort(key)} aria-pressed={sort === key}
                      className="inline-flex items-center gap-1 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded">
                      {label}{sort === key ? ' ↓' : ''}
                    </button>
                  ) : label}
                </th>
              ))}
              <th scope="col" className="py-1.5 font-medium"><span className="sr-only">รายละเอียด</span></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const key = `${row.account_ref}:${row.security_id}:${row.sub_portfolio ?? ''}:${row.source}`;
              const expanded = open === key;
              return (
                <React.Fragment key={key}>
                  <tr className="border-b border-subtle/60 align-top">
                    <td className="py-1.5 pr-3">
                      <span className="font-mono-code text-primary">{row.security_id}</span>
                      <span className="block text-[11px] text-muted">{row.instrument_type ?? NOT_ESTABLISHED}</span>
                    </td>
                    <td className="py-1.5 pr-3 text-secondary">{row.account_ref}</td>
                    <td className="py-1.5 pr-3 text-secondary">{row.economic_class ?? NOT_ESTABLISHED}</td>
                    <td className="py-1.5 pr-3 font-mono-code tabular-nums">{row.quantity === null ? NOT_ESTABLISHED : row.quantity}</td>
                    <td className="py-1.5 pr-3 font-mono-code tabular-nums">
                      {row.price === null ? NOT_ESTABLISHED : `${formatDec(row.price)} ${row.price_currency}`}
                    </td>
                    <td className="py-1.5 pr-3 font-mono-code tabular-nums">{formatDec(row.value_reporting)}</td>
                    <td className="py-1.5 pr-3 font-mono-code tabular-nums">{row.weight === null ? NOT_ESTABLISHED : row.weight}</td>
                    <td className="py-1.5 pr-3 font-mono-code tabular-nums">
                      {row.unrealized_pnl_local === null
                        ? <span className="text-muted">ไม่มีต้นทุน</span>
                        : `${formatDec(row.unrealized_pnl_local)} ${row.price_currency}`}
                    </td>
                    <td className="py-1.5">
                      <button type="button" onClick={() => setOpen(expanded ? null : key)} aria-expanded={expanded}
                        className="p-1 rounded hover:bg-surface-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        aria-label={`รายละเอียด ${row.security_id}`}>
                        <ChevronDown className={`w-3.5 h-3.5 text-muted transition-transform ${expanded ? 'rotate-180' : ''}`} />
                      </button>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="border-b border-subtle/60 bg-surface-muted/40">
                      <td colSpan={HEAD.length + 1} className="py-2 pr-3">
                        <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1 text-[11px]">
                          {([['FIGI', row.figi], ['ISIN', row.isin], ['Identity', row.identity_status],
                            ['Source', row.source], ['Cost basis', row.cost_basis_local], ['Cost status', row.cost_basis_status],
                            ['Sub-portfolio', row.sub_portfolio], ['Valuation date', row.valuation_date]] as const).map(([k, v]) => (
                            <div key={k}>
                              <dt className="text-muted">{k}</dt>
                              <dd className="font-mono-code text-primary break-all">{v ?? NOT_ESTABLISHED}</dd>
                            </div>
                          ))}
                        </dl>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted">
        น้ำหนักอ้างอิง {weightBasis ?? NOT_ESTABLISHED} · ไม่รวมเงินสดและส่วนต่างที่ยังกระทบยอดไม่ได้ ·
        รายการที่ไม่มีต้นทุนจะไม่แสดงกำไร/ขาดทุน
      </p>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-secondary">
        <StatusBadge status="NO_ORDER_CONTROL" />
        <span>หน้านี้แสดงผลเท่านั้น ไม่มีปุ่มสั่งซื้อขาย</span>
      </div>
    </div>
  );
};
