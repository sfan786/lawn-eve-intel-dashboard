import { useState, useEffect, useCallback } from 'react'

// Shared state + fetch logic for the "AI SUMMARY" feature used by the D-scan
// and Local scanner panels. Posts a {type, data} payload to /api/ai/threat_summary
// and exposes the generated summary, loading, and error state.
//
// `resetKey` clears any existing summary/error whenever it changes (pass the
// raw scan input so editing it invalidates the stale summary).
export function useAiSummary(resetKey) {
    const [summary, setSummary] = useState(null)
    const [generating, setGenerating] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        setSummary(null)
        setError(null)
    }, [resetKey])

    // `headers` lets callers pass write auth (e.g. X-Timer-Auth in password-only
    // deployments); the SSO session cookie is sent automatically when present.
    const generate = useCallback(async (payload, headers = {}) => {
        setGenerating(true)
        setError(null)
        setSummary(null)
        try {
            const resp = await fetch('/api/ai/threat_summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...headers },
                body: JSON.stringify(payload),
            })
            const data = await resp.json()
            if (!resp.ok) throw new Error(data.error || 'Server error')
            setSummary(data.summary)
        } catch (e) {
            setError(e.message)
        } finally {
            setGenerating(false)
        }
    }, [])

    return { summary, generating, error, generate }
}
