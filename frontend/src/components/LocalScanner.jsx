import React, { useState, useEffect, useRef } from 'react'
import { AiSummaryButton, AiSummaryBox } from './common/AiSummary'
import CopyButton from './common/CopyButton'
import ShareButton from './common/ShareButton'
import LocalScanResult, { localCounts, StandingCounts } from './parsers/LocalScanResult'
import { buildLocalCopyText } from '../utils/parserCopy'
import { STANDING_ORDER } from '../utils/intelStyles'
import { useAiSummary } from '../utils/useAiSummary'
import { useWriteAuth } from '../utils/useAuth'
import CornerBrackets from './common/CornerBrackets'

function parseNames(raw) {
    if (!raw.trim()) return []
    const names = raw.includes('\n')
        ? raw.split('\n').map(s => s.trim()).filter(Boolean)
        : raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean)
    return [...new Set(names)] // deduplicate
}

export default function LocalScanner() {
    const [rawInput, setRawInput] = useState('')
    const [results, setResults] = useState(null)
    const [riskMap, setRiskMap] = useState({})
    const [scanning, setScanning] = useState(false)
    const [error, setError] = useState(null)
    // canWrite mirrors the backend require_write_auth gate; writeHeaders carries
    // the password credential in deployments where SSO is off.
    const { canWrite, writeHeaders } = useWriteAuth()
    const { summary: aiSummary, generating: generatingAiSummary, error: aiError, generate } = useAiSummary(rawInput)
    const debounceTimer = useRef(null)

    const names = parseNames(rawInput)

    // Auto-scan 800ms after the user stops typing/pasting
    useEffect(() => {
        if (!names.length) return
        clearTimeout(debounceTimer.current)
        debounceTimer.current = setTimeout(() => handleScan(), 800)
        return () => clearTimeout(debounceTimer.current)
    }, [rawInput]) // eslint-disable-line react-hooks/exhaustive-deps

    async function handleScan() {
        if (!names.length) return
        setScanning(true)
        setError(null)
        try {
            const resp = await fetch('/api/local/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names }),
            })
            if (!resp.ok) throw new Error(`Server error: ${resp.status}`)
            const data = await resp.json()
            data.sort((a, b) => (STANDING_ORDER[a.standing] ?? 99) - (STANDING_ORDER[b.standing] ?? 99))
            setResults(data)

            const charIds = data.filter(r => r.character_id).map(r => r.character_id)
            if (charIds.length) {
                fetch('/api/chars/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ char_ids: charIds }),
                }).then(r => r.ok ? r.json() : {}).then(setRiskMap).catch(() => {})
            }
        } catch (e) {
            setError(e.message)
        } finally {
            setScanning(false)
        }
    }

    function handleClear() {
        setRawInput('')
        setResults(null)
        setRiskMap({})
        setError(null)
    }

    function generateAiSummary() {
        if (!results || results.length === 0) return
        const pilotData = results.map(r => {
            const risk = r.character_id ? riskMap[String(r.character_id)] : null
            const corp = r.corporation_name || 'Unknown Corp'
            const alliance = r.alliance_name || 'Unknown Alliance'
            const tier = risk ? risk.label : 'UNRESOLVED'
            const roles = risk && risk.roles && risk.roles.length > 0 ? ` [${risk.roles.join(', ')}]` : ''
            return `${r.name} (${corp} / ${alliance}) - Standing: ${r.standing}, Threat: ${tier}${roles}`
        }).join('\n')

        generate({
            type: 'local',
            data: `Total Pilots: ${results.length}\n${pilotData}`,
        }, writeHeaders)
    }

    const counts = localCounts(results)

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">LOCAL SCANNER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {results && (
                        <span className="panel-badge">
                            <StandingCounts counts={counts} />
                        </span>
                    )}
                    {results && results.length > 0 && (
                        <CopyButton getText={() => buildLocalCopyText(results, riskMap)} />
                    )}
                    {results && results.length > 0 && canWrite && (
                        <ShareButton
                            kind="local"
                            title={`Local — ${results.length} pilots`}
                            writeHeaders={writeHeaders}
                            buildPayload={() => ({ results, riskMap, ai_summary: aiSummary || null })}
                        />
                    )}
                    {(rawInput || results) && (
                        <button
                            onClick={handleClear}
                            style={{
                                background: 'none', border: '1px solid var(--border-dim)',
                                color: 'var(--text-secondary)', cursor: 'pointer',
                                fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                                padding: '2px 8px', letterSpacing: 1,
                            }}
                        >CLEAR</button>
                    )}
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <textarea
                    value={rawInput}
                    onChange={e => setRawInput(e.target.value)}
                    placeholder="Paste pilot names from local chat (one per line or comma-separated)..."
                    style={{
                        flex: 1, minHeight: 72, background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                        fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                        padding: '8px 10px', resize: 'vertical', outline: 'none',
                    }}
                />
                <button
                    onClick={handleScan}
                    disabled={!names.length || scanning}
                    style={{
                        background: names.length && !scanning ? 'rgba(0,212,255,0.1)' : 'rgba(0,0,0,0.2)',
                        border: `1px solid ${names.length && !scanning ? 'var(--cyan-dim)' : 'var(--border-dim)'}`,
                        color: names.length && !scanning ? 'var(--cyan)' : 'var(--text-muted)',
                        cursor: names.length && !scanning ? 'pointer' : 'default',
                        fontFamily: 'Orbitron, sans-serif', fontSize: 10,
                        fontWeight: 600, letterSpacing: 2,
                        padding: '0 16px', height: 72, whiteSpace: 'nowrap',
                        transition: 'all 0.2s',
                    }}
                >
                    {scanning ? 'SCANNING...' : 'SCAN LOCAL'}
                </button>
            </div>

            {canWrite && results && results.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
                    <AiSummaryButton generating={generatingAiSummary} onClick={generateAiSummary} />
                </div>
            )}

            <AiSummaryBox summary={aiSummary} error={aiError} />

            {error && (
                <div style={{
                    marginTop: 8, padding: '6px 10px',
                    background: 'rgba(255,51,85,0.1)', border: '1px solid var(--red)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--red)',
                }}>
                    ERROR: {error}
                </div>
            )}

            <LocalScanResult results={results} riskMap={riskMap} />

        </div>
    )
}
