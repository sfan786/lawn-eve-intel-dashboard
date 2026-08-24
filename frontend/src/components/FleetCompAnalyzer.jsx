import React, { useState } from 'react'
import CornerBrackets from './common/CornerBrackets'
import CopyButton from './common/CopyButton'
import ShareButton from './common/ShareButton'
import FleetCompResult, { FleetCounts } from './parsers/FleetCompResult'
import { buildFleetCopyText } from '../utils/parserCopy'
import { useWriteAuth } from '../utils/useAuth'

function parseNames(raw) {
    if (!raw.trim()) return []
    const names = raw.includes('\n')
        ? raw.split('\n').map(s => s.trim()).filter(Boolean)
        : raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean)
    return [...new Set(names)]
}

export default function FleetCompAnalyzer() {
    const [rawInput, setRawInput] = useState('')
    const [result, setResult] = useState(null)
    const [scanning, setScanning] = useState(false)
    const [error, setError] = useState(null)
    // canWrite mirrors the backend require_write_auth gate; writeHeaders carries
    // the password credential in deployments where SSO is off.
    const { canWrite, writeHeaders } = useWriteAuth()

    const names = parseNames(rawInput)

    async function handleAnalyze() {
        if (!names.length) return
        setScanning(true)
        setError(null)
        try {
            const resp = await fetch('/api/fleet/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names }),
            })
            if (!resp.ok) throw new Error(`Server error: ${resp.status}`)
            setResult(await resp.json())
        } catch (e) {
            setError(e.message)
        } finally {
            setScanning(false)
        }
    }

    function handleClear() {
        setRawInput('')
        setResult(null)
        setError(null)
    }

    const s = result?.summary
    const pilots = result?.pilots || []

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">FLEET COMP ANALYZER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {s && (
                        <span className="panel-badge">
                            <FleetCounts summary={s} />
                        </span>
                    )}
                    {s && <CopyButton getText={() => buildFleetCopyText(s)} />}
                    {s && canWrite && (
                        <ShareButton
                            kind="fleet"
                            title={`Fleet — ${pilots.length} pilots`}
                            writeHeaders={writeHeaders}
                            buildPayload={() => ({ result })}
                        />
                    )}
                    {(rawInput || result) && (
                        <button onClick={handleClear} style={{
                            background: 'none', border: '1px solid var(--border-dim)',
                            color: 'var(--text-secondary)', cursor: 'pointer',
                            fontFamily: 'Share Tech Mono, monospace', fontSize: 10,
                            padding: '2px 8px', letterSpacing: 1,
                        }}>CLEAR</button>
                    )}
                </div>
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <textarea
                    value={rawInput}
                    onChange={e => setRawInput(e.target.value)}
                    placeholder="Paste pilot names from local or fleet window (one per line)..."
                    style={{
                        flex: 1, minHeight: 72, background: 'rgba(0,0,0,0.3)',
                        border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
                        fontFamily: 'Share Tech Mono, monospace', fontSize: 11,
                        padding: '8px 10px', resize: 'vertical', outline: 'none',
                    }}
                />
                <button
                    onClick={handleAnalyze}
                    disabled={!names.length || scanning}
                    style={{
                        background: names.length && !scanning ? 'rgba(255,51,85,0.1)' : 'rgba(0,0,0,0.2)',
                        border: `1px solid ${names.length && !scanning ? '#ff3355' : 'var(--border-dim)'}`,
                        color: names.length && !scanning ? '#ff3355' : 'var(--text-muted)',
                        cursor: names.length && !scanning ? 'pointer' : 'default',
                        fontFamily: 'Orbitron, sans-serif', fontSize: 10,
                        fontWeight: 600, letterSpacing: 2,
                        padding: '0 16px', height: 72, whiteSpace: 'nowrap',
                        transition: 'all 0.2s',
                    }}
                >
                    {scanning ? 'ANALYZING...' : 'ANALYZE\nFLEET'}
                </button>
            </div>

            {error && (
                <div style={{
                    marginTop: 8, padding: '6px 10px',
                    background: 'rgba(255,51,85,0.1)', border: '1px solid var(--red)',
                    fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--red)',
                }}>ERROR: {error}</div>
            )}

            <FleetCompResult result={result} />
        </div>
    )
}
