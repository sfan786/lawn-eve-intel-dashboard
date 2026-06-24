import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import DscanParser from '../DscanParser'

vi.mock('../../utils/useAuth', () => ({
    useAuth: () => ({ authorized: false, ssoEnabled: false }),
}))

vi.mock('../../utils/useAiSummary', () => ({
    useAiSummary: () => ({ summary: null, generating: false, error: null, generate: vi.fn() }),
}))

vi.mock('../common/CornerBrackets', () => ({ default: () => null }))

vi.mock('../common/AiSummary', () => ({
    AiSummaryButton: () => null,
    AiSummaryBox: () => null,
}))

// Tab-separated EVE D-scan: one line per object, columns = name\ttype\tdistance
// (column order doesn't matter — the parser scans every column for a known type)
const DSCAN_WITH_SUPER = [
    'Super Avatar\tAvatar\tTitan\t1,234 km',
    'Tackler One\tMalediction\tInterceptor\t30 km',
    'Purifier Bomb\tPurifier\tStealth Bomber\t40 km',
    'Station Alpha\tAstrahus\tCitadel\t10 km',
    'Factory Beta\tRaitaru\tEngineering Complex\t200 km',
].join('\n')

const DSCAN_BATTLESHIPS_ONLY = [
    'Machariel I\tMachariel\tBattleship\t100 km',
    'Machariel II\tMachariel\tBattleship\t200 km',
].join('\n')

describe('DscanParser', () => {
    describe('initial render', () => {
        it('shows help text when no input is provided', () => {
            render(<DscanParser />)
            expect(screen.getByText(/In EVE: open D-Scan/i)).toBeInTheDocument()
        })

        it('renders a textarea with EVE-specific placeholder', () => {
            render(<DscanParser />)
            expect(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i)
            ).toBeInTheDocument()
        })

        it('does not show a CLEAR button before input', () => {
            render(<DscanParser />)
            expect(screen.queryByText('CLEAR')).not.toBeInTheDocument()
        })
    })

    describe('after pasting D-scan with supercapital', () => {
        it('shows CRITICAL threat tier', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_WITH_SUPER } }
            )
            expect(screen.getByText(/THREAT: CRITICAL/)).toBeInTheDocument()
        })

        it('shows ship count badge with correct count', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_WITH_SUPER } }
            )
            // 3 combat ships in the input
            expect(screen.getByText(/3 ships/)).toBeInTheDocument()
        })

        it('shows the structures section with OBJECTS label', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_WITH_SUPER } }
            )
            expect(screen.getByText(/OBJECTS/i)).toBeInTheDocument()
        })

        it('lists individual structure types in the objects section', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_WITH_SUPER } }
            )
            expect(screen.getAllByText(/Astrahus/).length).toBeGreaterThan(0)
        })

        it('shows CLEAR button after input is added', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_WITH_SUPER } }
            )
            expect(screen.getByText('CLEAR')).toBeInTheDocument()
        })
    })

    describe('CLEAR button', () => {
        it('clicking CLEAR resets output and shows help text again', () => {
            render(<DscanParser />)
            const textarea = screen.getByPlaceholderText(/Paste EVE directional scan output/i)
            fireEvent.change(textarea, { target: { value: DSCAN_WITH_SUPER } })
            expect(screen.getByText(/THREAT: CRITICAL/)).toBeInTheDocument()

            fireEvent.click(screen.getByText('CLEAR'))

            expect(screen.queryByText(/THREAT:/)).not.toBeInTheDocument()
            expect(screen.getByText(/In EVE: open D-Scan/i)).toBeInTheDocument()
        })
    })

    describe('threat tier classification', () => {
        it('shows LOW threat for battleship-only fleet', () => {
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: DSCAN_BATTLESHIPS_ONLY } }
            )
            expect(screen.getByText(/THREAT: LOW/)).toBeInTheDocument()
        })

        it('shows CLEAR threat when scan has no recognized ships', () => {
            // Probes are categorized as PROBE and silently skipped
            const probeOnly = 'Core Scanner Probe I\tScanner Probe\t5 AU'
            render(<DscanParser />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste EVE directional scan output/i),
                { target: { value: probeOnly } }
            )
            expect(screen.getByText(/THREAT: CLEAR/)).toBeInTheDocument()
        })
    })
})
