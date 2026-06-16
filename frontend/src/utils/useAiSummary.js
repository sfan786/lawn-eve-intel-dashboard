import { useState, useEffect, useCallback, useRef } from 'react'

// Shared state + fetch logic for the "AI SUMMARY" feature used by the D-scan
// and Local scanner panels. Posts a {type, data} payload to /api/ai/threat_summary
// and exposes the generated summary, loading, and error state.
//
// `resetKey` clears any existing summary/error whenever it changes (pass the
// raw scan input so editing it invalidates the stale summary). An in-flight
// request is aborted on reset or when a new one starts, so a slow response for
// stale input can't overwrite the current state (race condition).
export function useAiSummary(resetKey) {
    const [summary, setSummary] = useState(null)
    const [generating, setGenerating] = useState(false)
    const [error, setError] = useState(null)
    const abortRef = useRef(null)

    useEffect(() => {
        setSummary(null)
        setError(null)
        if (abortRef.current) {
            abortRef.current.abort()
            abortRef.current = null
        }
    }, [resetKey])

    // `headers` lets callers pass write auth (e.g. X-Timer-Auth in password-only
    // deployments); the SSO session cookie is sent automatically when present.
    const generate = useCallback(async (payload, headers = {}) => {
        if (abortRef.current) abortRef.current.abort()
        const controller = new AbortController()
        abortRef.current = controller

        setGenerating(true)
        setError(null)
        setSummary(null)
        try {
            const resp = await fetch('/api/ai/threat_summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...headers },
                body: JSON.stringify(payload),
                signal: controller.signal,
            })
            const data = await resp.json()
            if (!resp.ok) throw new Error(data.error || 'Server error')
            setSummary(data.summary)
        } catch (e) {
            if (e.name !== 'AbortError') setError(e.message)
        } finally {
            // Only clear loading state if this is still the active request.
            if (abortRef.current === controller) {
                setGenerating(false)
                abortRef.current = null
            }
        }
    }, [])

    return { summary, generating, error, generate }
}
