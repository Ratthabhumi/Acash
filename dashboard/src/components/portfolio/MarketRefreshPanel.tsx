import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';
import {
  MarketStatus, PROVIDER_INFO, RefreshRecord, callMarket, marketTh, refreshBlocker,
} from '../../services/marketRefresh';

interface Props {
  /** Called after a refresh that published a new market view, and when the panel finds one at load. */
  onMarketView: (available: boolean) => void;
}

export const MarketRefreshPanel: React.FC<Props> = ({ onMarketView }) => {
  const [status, setStatus] = useState<MarketStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await callMarket<MarketStatus>('GET', 'status');
    const body = r.body as MarketStatus;
    setStatus(body);
    onMarketView(!!body.last_refresh?.report_generation_id);
  }, [onMarketView]);

  useEffect(() => { void load(); }, [load]);

  const refresh = async () => {
    setBusy(true);
    setMessage(null);
    const r = await callMarket<RefreshRecord>('POST', 'refresh');
    const body = r.body as RefreshRecord & { status: string };
    setMessage(marketTh(body.status === 'REFRESHED' || body.status === 'REFRESHED_WITHOUT_VALUATION'
      ? body.valuation_status : body.status));
    await load();
    setBusy(false);
  };

  const blocker = refreshBlocker(status);
  const last = status?.last_refresh ?? null;
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
      <SimpleTable head={['Provider', 'Coverage', 'Status']} rows={(status?.providers ?? []).map((p) => [
        PROVIDER_INFO[p.provider_id]?.name ?? p.provider_id,
        PROVIDER_INFO[p.provider_id]?.coverage ?? '',
        <span key={p.provider_id} title={p.detail}><StatusBadge status={p.status} /> {marketTh(p.status)}</span>,
      ])} />
      {last && last.refresh_id && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-secondary">
            <span>Last refresh: <span className="font-mono-code">{last.completed_at}</span></span>
            <span>Valuation: {marketTh(last.valuation_status)}</span>
            <span>FX: {marketTh(last.fx_status)}</span>
            <span>Priced {last.priced_symbols_count}/{last.requested_symbols_count} · other date {last.stale_symbols_count} · no price {last.unavailable_symbols_count}</span>
            {last.meta?.coverage && (
              <span>ไม่ได้นับในมูลค่านี้ (ไม่ใช่ศูนย์): รายการที่มีแค่มูลค่า {last.meta.coverage.value_only ?? 0} · บัญชีที่มีแค่ยอดรวม {last.meta.coverage.total_only_accounts ?? 0} · หลักทรัพย์ที่ดึงราคาไม่ได้ {last.meta.coverage.unsupported_instruments ?? 0}</span>
            )}
            {last.meta && <span>Holdings as observed on {last.meta.holdings_observed_on}; broker totals from that date are not compared with these prices</span>}
          </div>
          {last.meta?.flags && last.meta.flags.length > 0 && (
            <div className="flex flex-wrap gap-1">{last.meta.flags.map((f) => <StatusBadge key={f} status={f} />)}</div>
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
