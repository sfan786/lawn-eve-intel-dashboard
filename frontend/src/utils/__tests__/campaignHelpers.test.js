import { describe, it, expect } from 'vitest'
import {
    getCampaignPhase,
    formatCountdown,
    formatEveTime,
    formatLocalTime,
    formatVulnWindow,
} from '../campaignHelpers'

// ---------------------------------------------------------------------------
// getCampaignPhase
// ---------------------------------------------------------------------------

describe('getCampaignPhase', () => {
    it('returns nodes phase when start_time is in the past', () => {
        const result = getCampaignPhase({ start_time: '2020-01-01T00:00:00Z' })
        expect(result.phase).toBe('nodes')
        expect(result.nodesSpawnTime).toBeInstanceOf(Date)
    })

    it('returns reinforced phase when start_time is in the future', () => {
        const result = getCampaignPhase({ start_time: '2099-01-01T00:00:00Z' })
        expect(result.phase).toBe('reinforced')
    })

    it('returns reinforced with null nodesSpawnTime when start_time is missing', () => {
        const result = getCampaignPhase({})
        expect(result.phase).toBe('reinforced')
        expect(result.nodesSpawnTime).toBeNull()
    })

    it('returns reinforced when campaign is null', () => {
        const result = getCampaignPhase(null)
        expect(result.phase).toBe('reinforced')
        expect(result.nodesSpawnTime).toBeNull()
    })

    it('returns reinforced for malformed start_time string', () => {
        const result = getCampaignPhase({ start_time: 'not-a-date' })
        expect(result.phase).toBe('reinforced')
        expect(result.nodesSpawnTime).toBeNull()
    })

    it('returns reinforced for null start_time field', () => {
        const result = getCampaignPhase({ start_time: null })
        expect(result.phase).toBe('reinforced')
    })
})

// ---------------------------------------------------------------------------
// formatCountdown
// ---------------------------------------------------------------------------

describe('formatCountdown', () => {
    const future = (ms) => new Date(Date.now() + ms)

    it('returns ACTIVE NOW for past dates', () => {
        expect(formatCountdown(new Date(Date.now() - 1000))).toBe('ACTIVE NOW')
    })

    it('returns minutes for sub-hour future', () => {
        // 45 minutes from now
        const result = formatCountdown(future(45 * 60 * 1000))
        expect(result).toMatch(/^\d+m$/)
        const mins = parseInt(result)
        expect(mins).toBeGreaterThanOrEqual(44)
        expect(mins).toBeLessThanOrEqual(45)
    })

    it('returns hours and minutes for sub-day future', () => {
        // 2h 3m from now
        const result = formatCountdown(future((2 * 60 + 3) * 60 * 1000))
        expect(result).toMatch(/^\d+h \d+m$/)
        expect(result).toContain('2h')
    })

    it('returns days and hours for multi-day future', () => {
        // 2 days and 3 hours from now
        const result = formatCountdown(future((2 * 24 + 3) * 3600 * 1000))
        expect(result).toMatch(/^\d+d \d+h$/)
        expect(result).toContain('2d')
    })
})

// ---------------------------------------------------------------------------
// formatEveTime
// ---------------------------------------------------------------------------

describe('formatEveTime', () => {
    it('formats a known UTC date correctly', () => {
        // 2026-01-15 14:30 UTC
        const date = new Date('2026-01-15T14:30:00Z')
        const result = formatEveTime(date)
        expect(result).toBe('01/15 14:30 EVE')
    })

    it('returns empty string for invalid date', () => {
        expect(formatEveTime(new Date('invalid'))).toBe('')
    })

    it('returns empty string for null', () => {
        expect(formatEveTime(null)).toBe('')
    })

    it('zero-pads single-digit months and days', () => {
        const date = new Date('2026-03-05T09:05:00Z')
        expect(formatEveTime(date)).toBe('03/05 09:05 EVE')
    })
})

// ---------------------------------------------------------------------------
// formatLocalTime
// ---------------------------------------------------------------------------

describe('formatLocalTime', () => {
    it('returns a non-empty string for a valid date', () => {
        const date = new Date('2026-01-15T14:30:00Z')
        const result = formatLocalTime(date)
        expect(result.length).toBeGreaterThan(0)
    })

    it('returns empty string for invalid date', () => {
        expect(formatLocalTime(new Date('invalid'))).toBe('')
    })

    it('returns empty string for null', () => {
        expect(formatLocalTime(null)).toBe('')
    })

    it('includes AM or PM', () => {
        const date = new Date()
        const result = formatLocalTime(date)
        expect(result).toMatch(/AM|PM/)
    })
})

// ---------------------------------------------------------------------------
// formatVulnWindow
// ---------------------------------------------------------------------------

describe('formatVulnWindow', () => {
    it('formats window correctly', () => {
        const result = formatVulnWindow('2026-01-15T10:00:00Z', '2026-01-15T11:00:00Z')
        expect(result).toBe('10:00 - 11:00 EVE')
    })

    it('returns null for missing start', () => {
        expect(formatVulnWindow(null, '2026-01-15T11:00:00Z')).toBeNull()
    })

    it('returns null for missing end', () => {
        expect(formatVulnWindow('2026-01-15T10:00:00Z', null)).toBeNull()
    })

    it('zero-pads hours and minutes', () => {
        const result = formatVulnWindow('2026-01-15T09:05:00Z', '2026-01-15T10:00:00Z')
        expect(result).toBe('09:05 - 10:00 EVE')
    })
})
