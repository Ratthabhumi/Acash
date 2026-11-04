import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';
import {
  MarketStatus, PROVIDER_INFO, RefreshRecord, callMarket, marketTh, refreshBlocker,
} from '../../services/marketRefresh';

interface Props {
  /** Called whenever the panel learns whether a last successful market valuation is available. */
  onMarketView: (available: boolean) => void;
}

const RIGHTS: Array<[string, string]> = [
  ['governance_authorized', 'ODR'], ['contract_verified', 'Contract'], ['credentials_configured', 'Key'],
  ['entitlement_verified', 'Entitlement'], ['display_permitted', 'Display'], ['calculation_permitted', 'Calc'],
  ['derived_value_permitted', 'Derived'], ['cache_permitted', 'Cache'], ['real_response_verified', 'Live'],
];

export const MarketRefreshPanel: React.FC<Props> = ({ onMarketView }) => {
  const [status, setStatus] = useState<MarketStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await callMarket<MarketStatus>('GET', 'status');
    const body = r.body as MarketStatus;
    setStatus(body);
    onMarketView(!!body.last_success?.report_generation_id);
  }, [onMarketView]);

  useEffect(() => { void load(); }, [load]);

  const refresh = async () => {
    setBusy(true);
    setMessage(null);
    const r = await callMarket<RefreshRecord>('POST', 'refresh');
    const body = r.body as RefreshRecord & { status: string };
    setMessage(body.status === 'REFRESHED' ? marketTh(body.valuation_status) : marketTh(body.status));
    await load();
    setBusy(false);
  };

  const blocker = refreshBlocker(status);
  const credits = status?.marketdata_credits ?? null;
  const last = status?.last_success ?? null;
  const attempt = status?.last_attempt ?? null;
  const attemptFailed = attempt && attempt.status !== 'REFRESHED';
  return (
    <section aria-labelledby="sec-market" className="bg-surface border border-default rounded-lg p-4 space-y-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 id="sec-market" className="text-sm font-semibold text-primary">ACASH Market Data</h2>
          <p className="text-secondary">ราคาจากผู้ให้บริการที่ได้รับอนุญาต · มูลค่าคำนวณใน Python (PPDS) · ไม่มีการส่งคำสั่งซื้อขาย</p>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={busy || blocker !== null}
          aria-describedby="refresh-blocker"
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded bg-accent text-white font-medium disabled:opacity-50">
          <RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} /> {busy ? 'Refreshing…' : 'Refresh Prices'}
        </button>
      </div>
      {blocker && <p id="refresh-blocker" className="text-secondary">ปุ่มยังใช้ไม่ได้: {marketTh(blocker)}</p>}
      {message && <p role="status" className="text-primary">{message}</p>}
      <SimpleTable head={['Provider', 'Coverage', 'Status', ...RIGHTS.map(([, label]) => label)]}
        rows={(status?.providers ?? []).map((p) => [
          PROVIDER_INFO[p.provider_id]?.name ?? p.provider_id,
          PROVIDER_INFO[p.provider_id]?.coverage ?? '',
          <span key={p.provider_id} title={p.detail}><StatusBadge status={p.status} /> {marketTh(p.status)}</span>,
          ...RIGHTS.map(([key]) => <span key={key} title={marketTh(p.capabilities?.[key] ?? 'UNKNOWN')}>{p.capabilities?.[key] ?? 'UNKNOWN'}</span>),
        ])} />
      <p className="text-[11px] text-muted">READY หมายถึง Owner รับรองสิทธิ์ครบตาม ODR-004 แล้วเท่านั้น ไม่ใช่หลักฐานว่าดึงข้อมูลจริงสำเร็จ (Live = NOT_OBSERVED)</p>
      {credits && (
        <p className="text-[11px] text-muted">MarketData.app Free: เหลือ {credits.remaining}/{credits.limit} credits
          {' '}(กันใช้แล้ว {credits.reserved} · หน้าต่าง {credits.window} · รีเซ็ต 09:30 New York)</p>
      )}
      {attemptFailed && (
        <p role="alert" className="text-amber-600">ครั้งล่าสุดที่กด ({attempt.completed_at}): {marketTh(attempt.status)}{attempt.code ? ` · ${attempt.code}` : ''}</p>
      )}
      {!last && <p className="text-secondary">ยังไม่มีผลประเมินมูลค่าจากราคาตลาดที่ใช้ได้ (NOT_ESTABLISHED)</p>}
      {last && last.refresh_id && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-secondary">
            <span><StatusBadge status="LAST_SUCCESSFUL_VALUATION" /> <span className="font-mono-code">{last.completed_at}</span></span>
            <span>Valuation: {marketTh(last.valuation_status)}</span>
            <span>FX: {marketTh(last.fx_status)}</span>
            <span>Holdings: {marketTh(last.holdings_basis ?? 'STATEMENT_BASELINE')}</span>
            <span>{last.persisted ? 'บันทึกผลไว้ในเครื่อง (ผู้ให้บริการอนุญาต cache)' : 'เก็บไว้ในหน่วยความจำเท่านั้น หายเมื่อปิดโปรแกรม (ไม่ได้รับอนุญาต cache)'}</span>
            <span>Priced {last.priced_symbols_count}/{last.requested_symbols_count} · other date {last.stale_symbols_count} · no price {last.unavailable_symbols_count}</span>
            {last.meta?.coverage && (
              <span>ไม่ได้นับในมูลค่านี้ (ไม่ใช่ศูนย์): รายการที่มีแค่มูลค่า {last.meta.coverage.value_only ?? 0} · บัญชีที่มีแค่ยอดรวม {last.meta.coverage.total_only_accounts ?? 0} · หลักทรัพย์ที่ดึงราคาไม่ได้ {last.meta.coverage.unsupported_instruments ?? 0}</span>
            )}
            {last.meta && <span>Holdings as observed on {last.meta.holdings_observed_on}; broker totals from that date are not compared with these prices</span>}
          </div>
          {last.meta?.flags && last.meta.flags.length > 0 && (
            <div className="flex flex-wrap gap-1">{last.meta.flags.map((f) => <StatusBadge key={f} status={f} />)}</div>
          )}
          {last.holdings && (
            <>
              <h3 className="text-sm font-semibold text-primary">Holdings (priced subset)</h3>
              <SimpleTable head={['Account', 'Security', 'Quantity', 'Price', 'Ccy', 'Source', 'Market time', 'Value', `Value (${last.holdings.reporting_currency})`, 'Weight*', 'Unrealized P&L']}
                rows={last.holdings.rows.map((h) => [
                  h.account_ref, h.security_id, h.quantity, h.price, h.price_currency,
                  `${h.provider_id ?? '-'} · ${h.price_type === 'EOD_CLOSE' ? 'PREVIOUS_ELIGIBLE_EOD' : h.price_type === 'LAST_TRADE' ? 'REALTIME_IEX_ONLY' : h.price_type ?? '-'}`,
                  h.market_timestamp ?? '-', h.market_value_local ?? 'NOT_ESTABLISHED', h.market_value_reporting,
                  h.weight_of_priced_subtotal ?? 'NOT_ESTABLISHED', h.unrealized_pnl_local ?? h.unrealized_status,
                ])} />
              <p className="text-[11px] text-muted">* สัดส่วนเทียบกับยอดรวมเฉพาะรายการที่มีราคา ({last.holdings.priced_subtotal} {last.holdings.reporting_currency}) ไม่ใช่ทั้งพอร์ต · ราคา last trade ไม่ใช่ราคาที่ซื้อขายได้จริง</p>
            </>
          )}
          <SimpleTable head={['Security', 'Price', 'Currency', 'Type', 'Source', 'Market time', 'Used']} rows={(last.quotes ?? []).map((q) => [
            q.security_id, q.price, q.currency, q.price_type === 'EOD_CLOSE' ? 'PREVIOUS_ELIGIBLE_EOD' : `${q.price_type} · ${q.coverage}`,
            q.provider_id, q.market_timestamp ?? q.market_date, q.used ? 'YES' : 'NO (other date)',
          ])} />
        </div>
      )}
    </section>
  );
};
