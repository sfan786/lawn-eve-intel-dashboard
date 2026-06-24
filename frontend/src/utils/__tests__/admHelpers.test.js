import { describe, it, expect } from 'vitest'
import {
    getAdmColor,
    getAdmStatus,
    computeGrindingRate,
    compute24hChange,
} from '../admHelpers'

// ---------------------------------------------------------------------------
// getAdmColor
// ---------------------------------------------------------------------------

describe('getAdmColor', () => {
    it('returns red for ADM below 2', () => {
        expect(getAdmColor(0)).toBe('#ff3355')
        expect(getAdmColor(1)).toBe('#ff3355')
        expect(getAdmColor(1.9)).toBe('#ff3355')
    })

    it('returns amber for ADM 2-3.9', () => {
        expect(getAdmColor(2)).toBe('#ffaa00')
        expect(getAdmColor(3)).toBe('#ffaa00')
        expect(getAdmColor(3.9)).toBe('#ffaa00')
    })

    it('returns cyan for ADM 4-5.9', () => {
        expect(getAdmColor(4)).toBe('#00d4ff')
        expect(getAdmColor(5)).toBe('#00d4ff')
        expect(getAdmColor(5.9)).toBe('#00d4ff')
    })

    it('returns green for ADM 6 and above', () => {
        expect(getAdmColor(6)).toBe('#00ff88')
        expect(getAdmColor(10)).toBe('#00ff88')
    })
})

// ---------------------------------------------------------------------------
// getAdmStatus
// ---------------------------------------------------------------------------

describe('getAdmStatus', () => {
    it('returns Safe for ADM >= 4', () => {
        const s = getAdmStatus(5)
        expect(s.label).toBe('Safe')
        expect(s.priority).toBe(0)
    })

    it('returns Caution for ADM 2-3.9', () => {
        const s = getAdmStatus(3)
        expect(s.label).toBe('Caution')
        expect(s.priority).toBe(1)
        expect(s.color).toBe('#ffaa00')
    })

    it('returns Needs Grinding for ADM 0.1-1.9', () => {
        const s = getAdmStatus(1)
        expect(s.label).toBe('Needs Grinding')
        expect(s.priority).toBe(2)
        expect(s.color).toBe('#ff3355')
    })

    it('returns No Sov for ADM 0', () => {
        const s = getAdmStatus(0)
        expect(s.label).toBe('No Sov')
        expect(s.priority).toBe(3)
    })

    it('status object has label, color, priority fields', () => {
        const s = getAdmStatus(5)
        expect(s).toHaveProperty('label')
        expect(s).toHaveProperty('color')
        expect(s).toHaveProperty('priority')
    })
})

// ---------------------------------------------------------------------------
// computeGrindingRate
// ---------------------------------------------------------------------------

describe('computeGrindingRate', () => {
    const now = Date.now()

    const ago = (hours) => new Date(now - hours * 3600 * 1000).toISOString()

    it('returns null for null or empty history', () => {
        expect(computeGrindingRate(null)).toBeNull()
        expect(computeGrindingRate([])).toBeNull()
    })

    it('returns null for single data point', () => {
        expect(computeGrindingRate([{ timestamp: ago(24), adm: 3.0 }])).toBeNull()
    })

    it('returns null when time window is less than 1 hour', () => {
        const history = [
            { timestamp: ago(0.25), adm: 2.0 },  // 15 min ago
            { timestamp: ago(0),    adm: 3.0 },  // now
        ]
        expect(computeGrindingRate(history)).toBeNull()
    })

    it('computes correct rate for 48-hour span', () => {
        // ADM goes from 2.0 to 4.0 over 48h → rate = 2.0 / 2 days = 1.0/day
        const history = [
            { timestamp: ago(48), adm: 2.0 },
            { timestamp: ago(24), adm: 3.0 },
            { timestamp: ago(0),  adm: 4.0 },
        ]
        const rate = computeGrindingRate(history)
        expect(rate).toBeCloseTo(1.0, 1)
    })

    it('returns negative rate when ADM is declining', () => {
        const history = [
            { timestamp: ago(48), adm: 5.0 },
            { timestamp: ago(0),  adm: 3.0 },
        ]
        const rate = computeGrindingRate(history)
        expect(rate).toBeLessThan(0)
    })

    it('falls back to full range when recent window has < 2 points', () => {
        // Both points are older than 48h → filter returns 0 points → fall back to history
        const history = [
            { timestamp: ago(72), adm: 1.0 },
            { timestamp: ago(60), adm: 2.0 },
        ]
        const rate = computeGrindingRate(history)
        // Window is 12h, delta is 1.0 → rate = 1.0 / (12/24) = 2.0/day
        expect(rate).toBeCloseTo(2.0, 1)
    })
})

// ---------------------------------------------------------------------------
// compute24hChange
// ---------------------------------------------------------------------------

describe('compute24hChange', () => {
    const now = Date.now()
    const ago = (hours) => new Date(now - hours * 3600 * 1000).toISOString()

    it('returns 0 for empty history', () => {
        expect(compute24hChange([], 5.0)).toBe(0)
    })

    it('returns 0 for single-point history', () => {
        expect(compute24hChange([{ timestamp: ago(5), adm: 3.0 }], 5.0)).toBe(0)
    })

    it('returns correct delta when oldest point is outside 24h window', () => {
        // history[0] is 30h ago (outside 24h cutoff) and history[1] is 5h ago
        // The function walks until it finds the first entry >= cutoff, then uses
        // history[i-1] as oldPoint. Since history[0] is before cutoff and
        // history[1] is after, oldPoint = history[0].
        const history = [
            { timestamp: ago(30), adm: 3.0 },
            { timestamp: ago(5),  adm: 4.0 },
        ]
        // currentAdm - oldPoint.adm = 5.0 - 3.0 = 2.0
        expect(compute24hChange(history, 5.0)).toBeCloseTo(2.0, 5)
    })

    it('computes negative delta when ADM dropped', () => {
        const history = [
            { timestamp: ago(30), adm: 5.0 },
            { timestamp: ago(1),  adm: 4.0 },
        ]
        expect(compute24hChange(history, 4.0)).toBeCloseTo(-1.0, 5)
    })
})
