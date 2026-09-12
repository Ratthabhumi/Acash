import { ResearchRun, TradeRecord, TradeFilterOptions, TimelineEvent, LineageNode } from '../types/research';
import { mockResearchRun } from './mockData';

export interface PaginatedTradesResult {
  trades: TradeRecord[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface IResearchRunRepository {
  getLatestRun(): Promise<ResearchRun>;
  getRunById(id: string): Promise<ResearchRun | null>;
  getTrades(filterOptions?: TradeFilterOptions): Promise<PaginatedTradesResult>;
  getTradeById(tradeId: string): Promise<TradeRecord | null>;
  getTimelineEvents(): Promise<TimelineEvent[]>;
  getLineage(): Promise<LineageNode[]>;
}

export class MockResearchRunRepository implements IResearchRunRepository {
  private run: ResearchRun;

  constructor(initialData: ResearchRun = mockResearchRun) {
    this.run = initialData;
  }

  async getLatestRun(): Promise<ResearchRun> {
    // Return a deep clone to prevent accidental mutations
    return JSON.parse(JSON.stringify(this.run));
  }

  async getRunById(id: string): Promise<ResearchRun | null> {
    if (this.run.metadata.sessionId === id) {
      return JSON.parse(JSON.stringify(this.run));
    }
    return null;
  }

  async getTrades(filterOptions: TradeFilterOptions = {}): Promise<PaginatedTradesResult> {
    let filtered = [...this.run.trades];

    if (filterOptions.searchQuery) {
      const q = filterOptions.searchQuery.toLowerCase();
      filtered = filtered.filter(
        t => t.id.toLowerCase().includes(q) || t.symbol.toLowerCase().includes(q)
      );
    }

    if (filterOptions.side && filterOptions.side !== 'ALL') {
      filtered = filtered.filter(t => t.side === filterOptions.side);
    }

    if (filterOptions.outcome && filterOptions.outcome !== 'ALL') {
      if (filterOptions.outcome === 'WIN') {
        filtered = filtered.filter(t => t.status === 'CLOSED_WIN');
      } else if (filterOptions.outcome === 'LOSS') {
        filtered = filtered.filter(t => t.status === 'CLOSED_LOSS');
      }
    }

    if (filterOptions.sortBy) {
      const field = filterOptions.sortBy;
      const dir = filterOptions.sortDirection === 'desc' ? -1 : 1;
      filtered.sort((a, b) => {
        if (field === 'timestamp') {
          return (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) * dir;
        } else if (field === 'pnlBps') {
          return (a.pnlBps - b.pnlBps) * dir;
        } else if (field === 'rMultiple') {
          return (a.rMultiple - b.rMultiple) * dir;
        }
        return 0;
      });
    }

    const page = filterOptions.page || 1;
    const pageSize = filterOptions.pageSize || 15;
    const totalCount = filtered.length;
    const totalPages = Math.ceil(totalCount / pageSize);
    const startIdx = (page - 1) * pageSize;
    const paginated = filtered.slice(startIdx, startIdx + pageSize);

    return {
      trades: JSON.parse(JSON.stringify(paginated)),
      totalCount,
      page,
      pageSize,
      totalPages,
    };
  }

  async getTradeById(tradeId: string): Promise<TradeRecord | null> {
    const trade = this.run.trades.find(t => t.id === tradeId);
    return trade ? JSON.parse(JSON.stringify(trade)) : null;
  }

  async getTimelineEvents(): Promise<TimelineEvent[]> {
    return JSON.parse(JSON.stringify(this.run.timelineEvents));
  }

  async getLineage(): Promise<LineageNode[]> {
    return JSON.parse(JSON.stringify(this.run.lineage));
  }
}

// Singleton repository instance
export const researchRepository: IResearchRunRepository = new MockResearchRunRepository();
export const researchRunRepository: IResearchRunRepository = researchRepository;

