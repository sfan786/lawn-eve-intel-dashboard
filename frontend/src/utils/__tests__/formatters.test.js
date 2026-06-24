import { describe, it, expect } from 'vitest'
import { formatIsk, timeAgo, classifyKills } from '../formatters'

// ---------------------------------------------------------------------------
// formatIsk
// ---------------------------------------------------------------------------

describe('formatIsk', () => {
    it('returns "0" for zero', () => {
        expect(formatIsk(0)).toBe('0')
    })

    it('returns "0" for null/undefined', () => {
        expect(formatIsk(null)).toBe('0')
        expect(formatIsk(undefined)).toBe('0')
    })

    it('returns raw integer string for values under 1K', () => {
        expect(formatIsk(500)).toBe('500')
        expect(formatIsk(999)).toBe('999')
    })

    it('returns K suffix for thousands', () => {
        expect(formatIsk(1000)).toBe('1K')
        expect(formatIsk(1500)).toBe('2K')    // Math.round(1.5K)=2
        expect(formatIsk(999999)).toBe('1000K') // just under 1M → still K
    })

    it('returns M suffix for millions', () => {
        expect(formatIsk(1_000_000)).toBe('1.0M')
        expect(formatIsk(1_500_000)).toBe('1.5M')
        expect(formatIsk(999_000_000)).toBe('999.0M')
    })

    it('returns B suffix for billions', () => {
        expect(formatIsk(1_000_000_000)).toBe('1.0B')
        expect(formatIsk(2_000_000_000)).toBe('2.0B')
        expect(formatIsk(12_345_678_901)).toBe('12.3B')
    })
})

// ---------------------------------------------------------------------------
// timeAgo
// ---------------------------------------------------------------------------

describe('timeAgo', () => {
    const isoAgo = (seconds) =>
        new Date(Date.now() - seconds * 1000).toISOString()

    it('returns empty string for null/undefined', () => {
        expect(timeAgo(null)).toBe('')
        expect(timeAgo(undefined)).toBe('')
    })

    it('returns seconds for < 60s ago', () => {
        const result = timeAgo(isoAgo(30))
        expect(result).toMatch(/^\d+s$/)
        expect(parseInt(result)).toBeGreaterThanOrEqual(29)
        expect(parseInt(result)).toBeLessThanOrEqual(30)
    })

    it('returns minutes for < 1h ago', () => {
        const result = timeAgo(isoAgo(5 * 60))
        expect(result).toMatch(/^\d+m$/)
        expect(parseInt(result)).toBe(5)
    })

    it('returns hours for < 24h ago', () => {
        const result = timeAgo(isoAgo(2 * 3600))
        expect(result).toMatch(/^\d+h$/)
        expect(parseInt(result)).toBe(2)
    })

    it('returns days for >= 24h ago', () => {
        const result = timeAgo(isoAgo(3 * 86400))
        expect(result).toMatch(/^\d+d$/)
        expect(parseInt(result)).toBe(3)
    })
})

// ---------------------------------------------------------------------------
// classifyKills
// ---------------------------------------------------------------------------

describe('classifyKills', () => {
    it('returns none for 0', () => {
        expect(classifyKills(0)).toBe('none')
    })

    it('returns low for values below default lower threshold (5)', () => {
        expect(classifyKills(1)).toBe('low')
        expect(classifyKills(4)).toBe('low')
    })

    it('returns medium for values between thresholds (5-19)', () => {
        expect(classifyKills(5)).toBe('medium')
        expect(classifyKills(19)).toBe('medium')
    })

    it('returns high for values at or above upper threshold (20)', () => {
        expect(classifyKills(20)).toBe('high')
        expect(classifyKills(100)).toBe('high')
    })

    it('respects custom thresholds', () => {
        expect(classifyKills(3, [2, 10])).toBe('medium')
        expect(classifyKills(1, [2, 10])).toBe('low')
        expect(classifyKills(10, [2, 10])).toBe('high')
    })
})
