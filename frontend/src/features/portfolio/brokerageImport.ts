import { parseSchwabPositionsCsv } from './schwabCsv.ts'
import type { Holding } from './types.ts'

export type BrokerageId = 'schwab' | 'fidelity' | 'etrade' | 'vanguard'

export type BrokerageImportResult = {
  portfolioName: string
  initialCapital: number
  holdings: Holding[]
  notes: string[]
}

export type BrokerageOption = {
  id: BrokerageId
  label: string
  available: boolean
}

export const BROKERAGE_OPTIONS: BrokerageOption[] = [
  { id: 'schwab', label: 'Charles Schwab', available: true },
  { id: 'fidelity', label: 'Fidelity', available: false },
  { id: 'etrade', label: 'E*TRADE', available: false },
  { id: 'vanguard', label: 'Vanguard', available: false },
]

export function parseBrokeragePositionsCsv(
  brokerage: BrokerageId,
  text: string,
): BrokerageImportResult {
  switch (brokerage) {
    case 'schwab': {
      const imported = parseSchwabPositionsCsv(text)
      return {
        portfolioName: imported.portfolioName,
        initialCapital: imported.initialCapital,
        holdings: imported.holdings,
        notes: imported.notes,
      }
    }
    case 'fidelity':
    case 'etrade':
    case 'vanguard':
      throw new Error('This brokerage import is not available yet.')
    default:
      throw new Error('Choose a brokerage before importing a CSV.')
  }
}
