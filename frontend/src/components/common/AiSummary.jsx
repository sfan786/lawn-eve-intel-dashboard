// Shared UI for the AI threat-summary feature: a compact "AI SUMMARY" button
// and the analysis result box. Used by DscanParser and LocalScanner so the two
// panels stay visually identical. State/fetch lives in utils/useAiSummary.

export function AiSummaryButton({ generating, disabled, onClick }) {
    const inert = generating || disabled
    return (
        <button
            onClick={onClick}
            disabled={inert}
            style={{
                background: generating ? 'rgba(0,212,255,0.2)' : 'none',
                border: '1px solid var(--cyan-dim)',
                color: 'var(--cyan)', cursor: inert ? 'default' : 'pointer',
                fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 1, fontWeight: 600,
                padding: '4px 8px', transition: 'all 0.2s', opacity: disabled ? 0.3 : 1,
            }}
        >
            {generating ? 'ANALYZING...' : 'AI SUMMARY'}
        </button>
    )
}

export function AiSummaryBox({ summary, error }) {
    if (!summary && !error) return null
    return (
        <div style={{
            marginTop: 10, padding: '10px 12px',
            background: error ? 'rgba(255,51,85,0.05)' : 'rgba(0,212,255,0.05)',
            border: `1px solid ${error ? 'var(--red-dim)' : 'var(--cyan-dim)'}`,
            borderLeft: `3px solid ${error ? 'var(--red)' : 'var(--cyan)'}`,
        }}>
            <div style={{
                fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2,
                color: error ? 'var(--red)' : 'var(--cyan)', marginBottom: 6, fontWeight: 700,
            }}>
                TACTICAL AI ANALYSIS
            </div>
            <div style={{
                fontFamily: 'Rajdhani, sans-serif', fontSize: 14, color: 'var(--text-primary)',
                lineHeight: 1.4,
            }}>
                {error ? `ERROR: ${error}` : summary}
            </div>
        </div>
    )
}
