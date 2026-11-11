import type { Holding } from './types.ts'

export type SchwabImportResult = {
  portfolioName: string
  initialCapital: number
  holdings: Holding[]
  skippedCashWeightPercent: number
  notes: string[]
}

/**
 * Expected Charles Schwab Positions export shape (from the Positions table export):
 *
 * Row 1: Positions for account <name> as of <time>, <date>
 * Blank row
 * Header:
 *   Symbol, Description, Qty (Quantity), Price, Price Chng $, Price Chng %,
 *   Mkt Val (Market Value), Day Chng $, Day Chng %, Cost Basis, Gain $, Gain %,
 *   Ratings, Reinvest?, Reinvest Capital Gains?, % of Acct, Security Type
 * Data rows, then Cash & Cash Investments, then Positions Total
 */

const TITLE_PATTERNS = [
  /Positions for account\s+(.+?)\s+as of\s+/i,
  /Positions for\s+(.+?)\s+as of\s+/i,
]

const ACCOUNT_NAME_PATTERN = /^(Individual|Joint|Trust|Roth IRA|Traditional IRA|Rollover IRA|Brokerage|Custodial)\b.*$/i

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let inQuotes = false

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    const next = text[index + 1]
    if (inQuotes) {
      if (char === '"' && next === '"') {
        cell += '"'
        index += 1
      } else if (char === '"') {
        inQuotes = false
      } else {
        cell += char
      }
      continue
    }
    if (char === '"') {
      inQuotes = true
      continue
    }
    if (char === ',' || char === '\t') {
      row.push(cell.trim())
      cell = ''
      continue
    }
    if (char === '\n' || char === '\r') {
      if (char === '\r' && next === '\n') index += 1
      row.push(cell.trim())
      cell = ''
      if (row.some((value) => value.length > 0)) rows.push(row)
      row = []
      continue
    }
    cell += char
  }
  row.push(cell.trim())
  if (row.some((value) => value.length > 0)) rows.push(row)
  return rows
}

function normalizeHeader(value: string): string {
  return value
    .replace(/^\uFEFF/, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

function headerMatches(header: string, alias: string): boolean {
  const left = normalizeHeader(header)
  const right = normalizeHeader(alias)
  return left === right || left.replace(/[.?]/g, '') === right.replace(/[.?]/g, '')
}

function findColumn(headers: string[], aliases: string[]): number {
  for (const alias of aliases) {
    const index = headers.findIndex((header) => headerMatches(header, alias))
    if (index >= 0) return index
  }
  // Fuzzy fallback for "% of Acct" / "% Of Account" variants.
  if (aliases.some((alias) => alias.includes('%'))) {
    const index = headers.findIndex((header) => {
      const value = normalizeHeader(header)
      return value.includes('%') && (value.includes('acct') || value.includes('account'))
    })
    if (index >= 0) return index
  }
  return -1
}

function parseMoney(raw: string): number | null {
  const text = raw.trim()
  if (!text || text === '--' || /^#+$/.test(text) || text.includes('#')) return null
  if (/incomplete|n\/a/i.test(text)) return null
  const cleaned = text.replace(/[$,\s]/g, '')
  const value = Number(cleaned)
  return Number.isFinite(value) ? value : null
}

function parsePercent(raw: string): number | null {
  const text = raw.trim()
  if (!text || text === '--') return null
  const cleaned = text.replace(/%/g, '').replace(/,/g, '')
  const value = Number(cleaned)
  return Number.isFinite(value) ? value : null
}

function parseQuantity(raw: string): number | null {
  const text = raw.trim()
  if (!text || text === '--' || /^#+$/.test(text)) return null
  const cleaned = text.replace(/,/g, '')
  const value = Number(cleaned)
  return Number.isFinite(value) && value > 0 ? value : null
}

function mapSecurityType(raw: string): string | null {
  const value = raw.trim()
  if (!value || value === '--') return null
  const lower = value.toLowerCase()
  if (lower.includes('etf') || lower.includes('closed end')) return 'ETF'
  if (lower.includes('equity') || lower.includes('common stock') || lower.includes('stock')) {
    return 'EQUITY'
  }
  if (lower.includes('mutual')) return 'MUTUAL_FUND'
  if (lower.includes('option')) return 'OPTION'
  if (lower.includes('bond') || lower.includes('fixed income') || lower.includes('treasury')) {
    return 'FIXED_INCOME'
  }
  if (lower.includes('cash') || lower.includes('money market')) return 'CASH'
  return value
}

function isCashRow(symbol: string, securityType: string): boolean {
  const name = symbol.trim().toLowerCase()
  const type = securityType.trim().toLowerCase()
  return (
    name.startsWith('cash & cash') ||
    type === 'cash and money market' ||
    (type.includes('cash') && !type.includes('equity') && !name.match(/^[a-z]/i))
  )
}

function isTotalRow(symbol: string): boolean {
  const value = symbol.trim().toLowerCase()
  return value === 'positions total' || value === 'account total' || value === 'total'
}

function isTickerSymbol(symbol: string): boolean {
  return /^[A-Z][A-Z0-9.\-]{0,14}$/i.test(symbol.trim())
}

function extractPortfolioName(rows: string[][]): string {
  for (const row of rows) {
    for (const cell of row) {
      for (const pattern of TITLE_PATTERNS) {
        const match = cell.match(pattern)
        if (match) {
          const name = match[1].trim()
          // Ignore the generic "CUSTACCS" household title used in some exports.
          if (name && !/^CUSTACCS$/i.test(name)) return name
        }
      }
    }
  }
  for (const row of rows) {
    const first = (row[0] ?? '').trim()
    if (ACCOUNT_NAME_PATTERN.test(first) && !normalizeHeader(first).includes('positions for')) {
      return first
    }
  }
  return ''
}

/**
 * Parse a Charles Schwab Positions CSV into Optify setup fields.
 */
export function parseSchwabPositionsCsv(text: string): SchwabImportResult {
  const rows = parseCsvRows(text.replace(/^\uFEFF/, ''))
  if (rows.length === 0) {
    throw new Error('The CSV file is empty.')
  }

  const portfolioName = extractPortfolioName(rows)

  const headerIndex = rows.findIndex((row) => {
    const hasSymbol = findColumn(row, ['symbol']) >= 0
    const hasWeight =
      findColumn(row, ['% of acct', '% of account', '% of acct.', 'percent of account']) >= 0
    return hasSymbol && hasWeight
  })
  if (headerIndex < 0) {
    throw new Error(
      'Could not find the Schwab Positions header row (Symbol and % of Acct). Export Positions as CSV and try again.',
    )
  }

  const headers = rows[headerIndex]
  const symbolIndex = findColumn(headers, ['symbol'])
  const descriptionIndex = findColumn(headers, ['description'])
  const costIndex = findColumn(headers, ['cost basis', 'cost basis ($)'])
  const marketValueIndex = findColumn(headers, [
    'mkt val (market value)',
    'market value',
    'mkt val',
  ])
  const weightIndex = findColumn(headers, [
    '% of acct',
    '% of account',
    '% of acct.',
    'percent of account',
  ])
  const typeIndex = findColumn(headers, ['security type', 'asset type', 'type'])
  const quantityIndex = findColumn(headers, [
    'qty (quantity)',
    'quantity',
    'qty',
    'shares',
  ])

  if (symbolIndex < 0 || weightIndex < 0) {
    throw new Error('The Schwab header must include Symbol and % of Acct columns.')
  }

  let totalCostBasis: number | null = null
  let totalMarketValue: number | null = null
  const imported: {
    symbol: string
    name: string
    quoteType: string | null
    weightPercent: number
    quantity: number
    costBasis: number | null
  }[] = []
  let skippedCashWeightPercent = 0
  const notes: string[] = []

  for (const row of rows.slice(headerIndex + 1)) {
    // A new account section can appear in multi-account exports.
    if (findColumn(row, ['symbol']) >= 0 && findColumn(row, ['% of acct', '% of account']) >= 0) {
      break
    }

    const symbol = (row[symbolIndex] ?? '').trim()
    if (!symbol) continue

    const securityType = typeIndex >= 0 ? (row[typeIndex] ?? '') : ''

    if (isTotalRow(symbol)) {
      if (costIndex >= 0) {
        const total = parseMoney(row[costIndex] ?? '')
        if (total != null && total > 0) totalCostBasis = total
      }
      if (marketValueIndex >= 0) {
        const total = parseMoney(row[marketValueIndex] ?? '')
        if (total != null && total > 0) totalMarketValue = total
      }
      continue
    }

    if (isCashRow(symbol, securityType)) {
      const cashWeight = parsePercent(row[weightIndex] ?? '')
      if (cashWeight != null) skippedCashWeightPercent += cashWeight
      continue
    }

    if (!isTickerSymbol(symbol)) {
      notes.push(`Skipped "${symbol}" because it is not a ticker symbol.`)
      continue
    }

    const weightPercent = parsePercent(row[weightIndex] ?? '')
    if (weightPercent == null || weightPercent <= 0) {
      notes.push(`Skipped ${symbol.toUpperCase()} because % of Acct was missing.`)
      continue
    }

    const description = descriptionIndex >= 0 ? (row[descriptionIndex] ?? '').trim() : ''
    const costBasis = costIndex >= 0 ? parseMoney(row[costIndex] ?? '') : null
    const quantity =
      quantityIndex >= 0 ? parseQuantity(row[quantityIndex] ?? '') : null
    const quoteType = mapSecurityType(securityType)
    if (quantity == null) {
      notes.push(`Quantity was missing for ${symbol.toUpperCase()}; it was left at 0.`)
    }
    imported.push({
      symbol: symbol.toUpperCase(),
      name: description && description !== '--' ? description : symbol.toUpperCase(),
      quoteType,
      weightPercent,
      quantity: quantity ?? 0,
      costBasis,
    })
  }

  if (imported.length === 0) {
    throw new Error('No importable Symbol rows were found under the Schwab Positions header.')
  }

  // Keep Schwab % of Acct values, then scale after dropping cash so weights total 100%.
  const weightSum = imported.reduce((total, row) => total + row.weightPercent, 0)
  const holdings: Holding[] = imported.map((row) => ({
    symbol: row.symbol,
    name: row.name,
    quoteType: row.quoteType,
    weightPercent:
      weightSum > 0 ? Number(((row.weightPercent / weightSum) * 100).toFixed(4)) : 0,
    quantity: row.quantity,
  }))

  const roundedSum = holdings.reduce((total, holding) => total + holding.weightPercent, 0)
  if (holdings.length > 0 && Math.abs(roundedSum - 100) > 0.0001) {
    holdings[0] = {
      ...holdings[0],
      weightPercent: Number((holdings[0].weightPercent + (100 - roundedSum)).toFixed(4)),
    }
  }

  const summedCost = imported.reduce((total, row) => total + (row.costBasis ?? 0), 0)
  const initialCapital =
    totalCostBasis != null && totalCostBasis > 0
      ? totalCostBasis
      : summedCost > 0
        ? summedCost
        : totalMarketValue != null && totalMarketValue > 0
          ? totalMarketValue
          : 0

  if (!(initialCapital > 0)) {
    notes.push(
      'Positions Total Cost Basis could not be read. Enter the initial portfolio value manually.',
    )
  } else if (totalCostBasis == null && summedCost > 0) {
    notes.push('Used the sum of holding Cost Basis values because Positions Total Cost Basis was missing.')
  } else if (totalCostBasis == null && totalMarketValue != null) {
    notes.push('Used Positions Total market value because Cost Basis was missing.')
  }

  if (skippedCashWeightPercent > 0) {
    notes.push(
      `Skipped Cash & Cash Investments (${skippedCashWeightPercent.toFixed(2)}% of Acct). Remaining Symbol weights were scaled to 100%.`,
    )
  }
  if (!portfolioName) {
    notes.push('Account name was not found in the title line. Enter a portfolio name manually.')
  }

  return {
    portfolioName,
    initialCapital,
    holdings,
    skippedCashWeightPercent,
    notes,
  }
}
