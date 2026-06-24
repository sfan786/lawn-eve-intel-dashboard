import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
import SystemTable from '../SystemTable'

// UpgradeBadges has no complex deps but mock it to keep tests isolated
vi.mock('../common/UpgradeBadges', () => ({ default: () => null }))

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const SYSTEMS = [
    { system_id: 1, name: 'Sys-Alpha', security_status: '-0.9' },
    { system_id: 2, name: 'Sys-Beta',  security_status: '-1.0' },
    { system_id: 3, name: 'Sys-Gamma', security_status: '-0.8' },
]

const SOVEREIGNTY = {
    1: { alliance_name: 'Get Off My Lawn', is_friendly: true, adm: 1.5 }, // CRITICAL
    2: { alliance_name: 'Get Off My Lawn', is_friendly: true, adm: 3.0 }, // GRIND
    3: { alliance_name: 'Get Off My Lawn', is_friendly: true, adm: 5.0 }, // safe
}

const ACTIVITY = {
    1: { ship_kills: 10, pod_kills: 2, npc_kills: 200, jumps: 50 },
    2: { ship_kills: 0,  pod_kills: 0, npc_kills: 50,  jumps: 10 },
    3: { ship_kills: 0,  pod_kills: 0, npc_kills: 20,  jumps: 5  },
}

// System 1 has most kills → sorts first despite identical faction membership
const LAWN_SYSTEM_IDS = new Set(['1', '2', '3'])

const DEFAULT_PROPS = {
    systems: SYSTEMS,
    sovereignty: SOVEREIGNTY,
    activity: ACTIVITY,
    selectedSystem: null,
    onSelectSystem: vi.fn(),
    lawnSystemIds: LAWN_SYSTEM_IDS,
    config: { system_upgrades: {} },
    annotations: {},
}

function renderTable(overrides = {}) {
    return render(<SystemTable {...DEFAULT_PROPS} {...overrides} />)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SystemTable', () => {
    describe('table structure', () => {
        it('renders a table with expected column headers', () => {
            renderTable()
            expect(screen.getByText('System')).toBeInTheDocument()
            expect(screen.getByText('ADM')).toBeInTheDocument()
            expect(screen.getByText('PVP')).toBeInTheDocument()
            expect(screen.getByText('Jumps')).toBeInTheDocument()
            expect(screen.getByText('Sov Holder')).toBeInTheDocument()
        })

        it('renders one row per system', () => {
            renderTable()
            SYSTEMS.forEach(sys => {
                expect(screen.getByText(sys.name)).toBeInTheDocument()
            })
        })

        it('shows system security status', () => {
            renderTable()
            // Security status for Sys-Alpha
            expect(screen.getByText('-0.9')).toBeInTheDocument()
        })
    })

    describe('ADM status badges', () => {
        it('shows ⚠ CRITICAL badge for system with ADM below 2', () => {
            renderTable()
            // Sys-Alpha has ADM 1.5
            const badges = screen.getAllByText(/CRITICAL/)
            expect(badges.length).toBeGreaterThan(0)
        })

        it('shows ⚠ GRIND badge for system with ADM 2-4', () => {
            renderTable()
            // Sys-Beta has ADM 3.0
            const badges = screen.getAllByText(/GRIND/)
            expect(badges.length).toBeGreaterThan(0)
        })

        it('shows no grinding badge for system with ADM >= 4', () => {
            renderTable()
            // Sys-Gamma has ADM 5.0 — safe, no badge
            // There should be exactly one CRITICAL (Sys-Alpha) and one GRIND (Sys-Beta)
            expect(screen.queryAllByText(/CRITICAL/)).toHaveLength(1)
            expect(screen.queryAllByText(/GRIND/)).toHaveLength(1)
        })
    })

    describe('ADM values', () => {
        it('displays ADM value formatted to one decimal place', () => {
            renderTable()
            expect(screen.getByText('1.5')).toBeInTheDocument()
            expect(screen.getByText('3.0')).toBeInTheDocument()
            expect(screen.getByText('5.0')).toBeInTheDocument()
        })

        it('shows — for systems with no ADM data', () => {
            const noAdmSov = { 1: { alliance_name: null, is_friendly: false, adm: 0 } }
            renderTable({
                systems: [SYSTEMS[0]],
                sovereignty: noAdmSov,
                activity: { 1: {} },
                lawnSystemIds: new Set(),
            })
            // Both the ADM cell and sov-holder cell render "—" → at least 2
            expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
        })
    })

    describe('row selection', () => {
        it('calls onSelectSystem with string id when a row is clicked', () => {
            const onSelect = vi.fn()
            renderTable({ onSelectSystem: onSelect })
            // Click on the first system name
            fireEvent.click(screen.getByText('Sys-Alpha'))
            expect(onSelect).toHaveBeenCalledWith('1')
        })

        it('adds selected class to the currently selected row', () => {
            renderTable({ selectedSystem: '2' })
            // The tr for system 2 should have class 'selected'
            const betaCell = screen.getByText('Sys-Beta')
            const row = betaCell.closest('tr')
            expect(row).toHaveClass('selected')
        })
    })

    describe('empty states', () => {
        it('renders an empty table body for empty systems array', () => {
            renderTable({ systems: [], lawnSystemIds: new Set() })
            // Headers still present
            expect(screen.getByText('System')).toBeInTheDocument()
            // No system names in body
            SYSTEMS.forEach(sys => {
                expect(screen.queryByText(sys.name)).not.toBeInTheDocument()
            })
        })
    })

    describe('annotations', () => {
        it('displays annotation note for a system', () => {
            renderTable({
                annotations: { 'Sys-Alpha': { note: 'Watch this gate', updated_at: '' } },
            })
            expect(screen.getByText('Watch this gate')).toBeInTheDocument()
        })
    })

    describe('sorting logic', () => {
        it('places hostile systems first, then sorts friendly systems by PVP kills then jumps', () => {
            const sov = {
                1: { alliance_name: 'Get Off My Lawn', is_friendly: true,  adm: 5.0 },
                2: { alliance_name: 'Hostile Alliance', is_friendly: false, adm: 3.0 },
                3: { alliance_name: 'Get Off My Lawn', is_friendly: true,  adm: 1.5 },
            }
            const act = {
                1: { ship_kills: 10, pod_kills: 5,  npc_kills: 100, jumps: 50  }, // PVP=15
                2: { ship_kills: 2,  pod_kills: 1,  npc_kills: 50,  jumps: 10  }, // hostile
                3: { ship_kills: 20, pod_kills: 5,  npc_kills: 200, jumps: 100 }, // PVP=25
            }
            renderTable({ sovereignty: sov, activity: act })
            const rows = screen.getAllByRole('row').slice(1) // skip header
            expect(rows[0]).toHaveTextContent('Sys-Beta')   // hostile → first
            expect(rows[1]).toHaveTextContent('Sys-Gamma')  // friendly, PVP=25
            expect(rows[2]).toHaveTextContent('Sys-Alpha')  // friendly, PVP=15
        })
    })
})
