import React, { useEffect, useState } from 'react';
import { fetchSystemStatus, FrameworkStatus, frameworkLabel, SystemStatus } from '../../services/systemStatus';
import { StatusBadge } from '../common/StatusBadge';
import { SimpleTable } from '../charts/PortfolioCharts';

type Row = (string | React.ReactNode)[];

const boolTh = (v: boolean | undefined) => (v === true ? 'ใช่' : v === false ? 'ไม่' : 'ไม่ทราบ');
const availability = (fw: FrameworkStatus) => {
  if (fw.production_enabled) return 'ทำงานจริง';
  if (fw.native_smoke_verified) return 'รัน native แล้ว';
  if (fw.package_installed) return 'ติดตั้งแล้ว ยังไม่ได้รัน';
  return 'ไม่พร้อม';
};

export const SystemStatusPanel: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    fetchSystemStatus(controller.signal).then((s) => { setStatus(s); setLoading(false); });
    return () => controller.abort();
  }, []);

  if (loading) return <p className="text-sm text-secondary">กำลังโหลดสถานะระบบ...</p>;
  if (!status) return <p className="text-sm text-secondary">ไม่สามารถอ่านสถานะระบบได้</p>;

  const ops = status.ops;
  const sync = ops?.windows_sync;
  const frameworkRows: Row[] = status.frameworks.map((fw) => [
    frameworkLabel[fw.framework_id] ?? fw.framework_id,
    fw.role ?? '-',
    <StatusBadge key="s" status={availability(fw)} />,
    boolTh(fw.package_installed),
    boolTh(fw.native_smoke_verified),
    boolTh(fw.input_rights_qualified),
    boolTh(fw.production_enabled),
    fw.blocked_reason ?? '-',
  ]);

  return (
    <section aria-labelledby="sec-system" className="bg-surface border border-default rounded-lg p-4 space-y-4 text-sm">
      <h2 id="sec-system" className="text-base font-semibold text-primary">สถานะระบบ · System status</h2>
      <p className="text-secondary">ข้อมูลจากไฟล์และ adapter ที่มีอยู่ ไม่ได้เรียก process ของ framework หรือบริการภายนอก</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="border border-default rounded p-3 space-y-2">
          <h3 className="font-medium text-primary">ข้อมูลตลาดและการซิงค์</h3>
          <dl className="text-xs space-y-1">
            <div className="flex justify-between"><dt className="text-muted">Scheduled sync accepted</dt><dd className="font-mono-code text-primary">{sync?.scheduled_sync_accepted ? 'ใช่' : 'ไม่'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Last sync status</dt><dd className="font-mono-code text-primary">{sync?.status ?? 'ยังไม่มีข้อมูล'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Synced at</dt><dd className="font-mono-code text-primary">{sync?.synced_at ?? '-'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Warehouse partitions</dt><dd className="font-mono-code text-primary">{ops?.warehouse?.partitions ?? 'ยังไม่มีข้อมูล'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Latest eligible session</dt><dd className="font-mono-code text-primary">{ops?.collector?.latest_eligible_session ?? 'ยังไม่มีข้อมูล'}</dd></div>
          </dl>
        </div>
        <div className="border border-default rounded p-3 space-y-2">
          <h3 className="font-medium text-primary">Forward Shadow V2</h3>
          <dl className="text-xs space-y-1">
            <div className="flex justify-between"><dt className="text-muted">Protocol hash</dt><dd className="font-mono-code text-primary truncate max-w-[12rem]">{status.shadow.protocol_hash ?? 'ยังไม่มีข้อมูล'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Registered</dt><dd className="font-mono-code text-primary">{status.shadow.registered_at ?? '-'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">First eligible session</dt><dd className="font-mono-code text-primary">{status.shadow.first_eligible_session ?? '-'}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Forward signals</dt><dd className="font-mono-code text-primary">{status.shadow.signals}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Observed outcomes</dt><dd className="font-mono-code text-primary">{status.shadow.outcomes}</dd></div>
          </dl>
        </div>
      </div>

      <div className="border border-default rounded p-3 space-y-2">
        <h3 className="font-medium text-primary">Framework integrations</h3>
        <SimpleTable head={['Framework', 'Role', 'Status', 'Installed', 'Native', 'Qualified', 'Production', 'Blocked reason']}
          rows={frameworkRows} />
      </div>

      <div className="border border-default rounded p-3 space-y-2">
        <h3 className="font-medium text-primary">Backup</h3>
        <p className="text-xs text-secondary">{ops?.backup?.status ?? 'NOT_CONFIGURED'} · {ops?.backup?.note ?? 'no independent destination evidenced'}</p>
      </div>
    </section>
  );
};
