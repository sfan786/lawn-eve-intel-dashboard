import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import LocalScanner from '../LocalScanner'

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

const MOCK_SCAN_RESPONSE = [
    {
        name: 'Hostile Pilot',
        character_id: 123,
        corporation_name: 'Bad Corp',
        alliance_name: 'Bad Alliance',
        standing: 'unknown',
    },
    {
        name: 'Friendly Pilot',
        character_id: 456,
        corporation_name: 'LAWN HC',
        alliance_name: 'Get Off My Lawn',
        standing: 'lawn',
    },
]

function makeFetchMock(response = MOCK_SCAN_RESPONSE, ok = true) {
    return vi.fn().mockResolvedValue({
        ok,
        status: ok ? 200 : 500,
        json: vi.fn().mockResolvedValue(response),
    })
}

describe('LocalScanner', () => {
    afterEach(() => {
        vi.restoreAllMocks()
    })

    describe('initial render', () => {
        it('renders textarea for pilot paste input', () => {
            render(<LocalScanner />)
            expect(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i)
            ).toBeInTheDocument()
        })

        it('renders a SCAN LOCAL button', () => {
            render(<LocalScanner />)
            expect(screen.getByText('SCAN LOCAL')).toBeInTheDocument()
        })

        it('SCAN LOCAL button is disabled when no names are entered', () => {
            render(<LocalScanner />)
            expect(screen.getByText('SCAN LOCAL')).toBeDisabled()
        })
    })

    describe('scan button interaction', () => {
        it('button is enabled after entering pilot names', () => {
            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Pilot Alpha\nPilot Beta' } }
            )
            expect(screen.getByText('SCAN LOCAL')).not.toBeDisabled()
        })

        it('calls POST /api/local/scan when button is clicked', async () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            // Use a newline-separated name so it's not split on spaces
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'PilotAlpha' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            expect(global.fetch).toHaveBeenCalledWith(
                '/api/local/scan',
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
                    body: expect.stringContaining('PilotAlpha'),
                })
            )
        })

        it('shows SCANNING... on button while request is in flight', async () => {
            // fetch never resolves — keeps scanning=true indefinitely
            global.fetch = vi.fn(() => new Promise(() => {}))

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Pilot Alpha' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            expect(screen.getByText('SCANNING...')).toBeInTheDocument()
        })
    })

    describe('results display', () => {
        it('displays classification rows after successful scan', async () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Hostile Pilot\nFriendly Pilot' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            await waitFor(() => {
                expect(screen.getByText('Hostile Pilot')).toBeInTheDocument()
                expect(screen.getByText('Friendly Pilot')).toBeInTheDocument()
            })
        })

        it('shows UNKNOWN standing label for unknown pilots', async () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Hostile Pilot' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            await waitFor(() => {
                expect(screen.getByText('UNKNOWN')).toBeInTheDocument()
            })
        })

        it('shows LAWN standing label for own pilots', async () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Friendly Pilot' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            await waitFor(() => {
                expect(screen.getByText('LAWN')).toBeInTheDocument()
            })
        })
    })

    describe('error handling', () => {
        it('shows error message when fetch fails', async () => {
            global.fetch = vi.fn().mockRejectedValue(new Error('Network down'))

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Pilot Alpha' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            await waitFor(() => {
                expect(screen.getByText(/ERROR:/i)).toBeInTheDocument()
            })
        })

        it('shows error message for non-ok server response', async () => {
            global.fetch = makeFetchMock([], false)

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Pilot Alpha' } }
            )

            await act(async () => {
                fireEvent.click(screen.getByText('SCAN LOCAL'))
            })

            await waitFor(() => {
                expect(screen.getByText(/ERROR:/i)).toBeInTheDocument()
            })
        })
    })

    describe('auto-scan debounce', () => {
        beforeEach(() => {
            vi.useFakeTimers()
        })

        afterEach(() => {
            vi.useRealTimers()
        })

        it('auto-scans 800ms after user stops typing', async () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Auto Pilot' } }
            )

            // Advance timers to trigger 800ms debounce
            await act(async () => {
                vi.advanceTimersByTime(800)
            })

            expect(global.fetch).toHaveBeenCalledWith(
                '/api/local/scan',
                expect.objectContaining({ method: 'POST' })
            )
        })

        it('does not auto-scan before 800ms', () => {
            global.fetch = makeFetchMock()

            render(<LocalScanner />)
            fireEvent.change(
                screen.getByPlaceholderText(/Paste pilot names from local chat/i),
                { target: { value: 'Auto Pilot' } }
            )

            vi.advanceTimersByTime(799)
            expect(global.fetch).not.toHaveBeenCalled()
        })
    })
})
