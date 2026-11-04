import React, { useCallback, useRef } from 'react';

// WAI-ARIA Tabs pattern: one tablist, roving tab index, arrow/Home/End keys, and only the selected
// panel is visible. Panels stay mounted so a tab switch cannot discard an unsubmitted form and
// cannot trigger a duplicate data load.

export const TAB_ORDER = ['overview', 'holdings', 'transactions', 'market', 'planning', 'data'] as const;
export type PortfolioTabId = (typeof TAB_ORDER)[number];

export const TAB_LABEL: Record<PortfolioTabId, string> = {
  overview: 'ภาพรวม',
  holdings: 'พอร์ตของฉัน',
  transactions: 'ธุรกรรม',
  market: 'ราคาตลาด',
  planning: 'วางแผนเงิน',
  data: 'ตรวจสอบข้อมูล',
};

interface TabBarProps {
  active: PortfolioTabId;
  onChange: (id: PortfolioTabId) => void;
  /** Panels that are unavailable for the current data state; rendered disabled, never hidden. */
  disabled?: Partial<Record<PortfolioTabId, boolean>>;
}

export const TabBar: React.FC<TabBarProps> = ({ active, onChange, disabled }) => {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  const focusAt = useCallback((index: number) => {
    const next = (index + TAB_ORDER.length) % TAB_ORDER.length;
    const button = refs.current[next];
    if (button) {
      button.focus();
      onChange(TAB_ORDER[next]);
    }
  }, [onChange]);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const index = TAB_ORDER.indexOf(active);
    if (event.key === 'ArrowRight') { event.preventDefault(); focusAt(index + 1); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); focusAt(index - 1); }
    else if (event.key === 'Home') { event.preventDefault(); focusAt(0); }
    else if (event.key === 'End') { event.preventDefault(); focusAt(TAB_ORDER.length - 1); }
  };

  return (
    <div role="tablist" aria-label="Portfolio sections" onKeyDown={onKeyDown}
      className="flex gap-1 overflow-x-auto border-b border-default pb-0">
      {TAB_ORDER.map((id, index) => {
        const selected = id === active;
        const isDisabled = disabled?.[id] === true;
        return (
          <button key={id} ref={(node) => { refs.current[index] = node; }} role="tab" id={`tab-${id}`}
            type="button" aria-selected={selected} aria-controls={`panel-${id}`} disabled={isDisabled}
            tabIndex={selected ? 0 : -1} onClick={() => onChange(id)}
            className={`whitespace-nowrap px-3 py-2 text-xs font-medium rounded-t border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-40 ${selected ? 'border-accent text-primary' : 'border-transparent text-secondary hover:text-primary'}`}>
            {TAB_LABEL[id]}
          </button>
        );
      })}
    </div>
  );
};

interface TabPanelProps {
  id: PortfolioTabId;
  active: PortfolioTabId;
  children: React.ReactNode;
}

export const TabPanel: React.FC<TabPanelProps> = ({ id, active, children }) => (
  <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} hidden={active !== id}>
    {children}
  </div>
);
