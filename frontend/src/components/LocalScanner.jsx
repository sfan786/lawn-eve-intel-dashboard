import React, { useState, useEffect, useRef } from 'react'
import { AiSummaryButton, AiSummaryBox } from './common/AiSummary'
import { useAiSummary } from '../utils/useAiSummary'
import { useAuth } from '../utils/useAuth'
import CornerBrackets from './common/CornerBrackets'

const STANDING_CONFIG = {
    unknown:    { label: 'UNKNOWN',    color: '#6a8090', bg: 'rgba(106,128,144,0.08)' },
    friendly:   { label: 'FRIENDLY',   color: '#00d4ff', bg: 'rgba(0,212,255,0.08)' },
    lawn:       { label: 'LAWN',       color: '#00ff88', bg: 'rgba(0,255,136,0.08)' },
    unresolved: { label: '?',          color: '#ffaa00', bg: 'rgba(255,170,0,0.08)' },
}

const STANDING_ORDER = { unknown: 0, friendly: 1, lawn: 2, unresolved: 3 }

const RISK_COLOR = {
    very_dangerous: '#ff2244',
    dangerous:      '#ff3355',
    moderate:       '#ffaa00',
    snuggly:        '#00d4ff',
    newbie:         '#6a8090',
    nodata:         '#334455',
}

const ROLE_COLOR = {
    TITAN:   '#ff2244',
    SUPER:   '#ff5500',
    DREAD:   '#ff7744',
    CARRIER: '#ffaa44',
    FAX:     '#ffdd00',
    BLOPS:   '#cc44ff',
    RECON:   '#aa55ff',
    BOMBER:  '#8855dd',
    T3C:     '#7755cc',
    COVOPS:  '#6644aa',
}

function parseNames(raw) {
    if (!raw.trim()) return []
    const names = raw.includes('\n')
        ? raw.split('\n').map(s => s.trim()).filter(Boolean)
        : raw.split(/[\s,]+/).map(s => s.trim()).filter(Boolean)
    return [...new Set(names)] // deduplicate
}

function buildLocalCopyText(results, riskMap) {
    const unknownCount = results.filter(r => r.standing === 'unknown').length
    const lines = [`LOCAL SCAN — ${results.length} pilots, ${unknownCount} unknown`]
    lines.push('')
    for (const r of results) {
        const risk = r.character_id ? riskMap[String(r.character_id)] : null
        const corp = r.corporation_name || 'Unknown Corp'
        const alliance = r.alliance_name ? ` / ${r.alliance_name}` : ''
        const standing = (r.standing || '').toUpperCase()
        const tier = risk ? risk.label : ''
        const roles = risk?.roles?.length ? ` [${risk.roles.join(', ')}]` : ''
        lines.push(`${r.name} (${corp}${alliance}) [${standing}]${tier ? ` ${tier}` : ''}${roles}`)
    }
    return lines.join('\n')
}

export default function LocalScanner() {
    const [rawInput, setRawInput] = useState('')
    const [results, setResults] = useState(null)
    const [riskMap, setRiskMap] = useState({})
    const [scanning, setScanning] = useState(false)
    const [error, setError] = useState(null)
    const [copied, setCopied] = useState(false)
    const { authorized, ssoEnabled } = useAuth()
    // Show the AI button when the session can write (SSO) or when SSO is off
    // (demo / no-SSO) — matches the backend require_write_auth gate.
    const canUseAi = authorized || !ssoEnabled
    // In password-only deployments the AI endpoint is authed via X-Timer-Auth,
    // same as the other write features; under SSO the session cookie carries it.
    const writeHeaders = ssoEnabled ? {} : { 'X-Timer-Auth': localStorage.getItem('timer_auth') || '' }
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

    const counts = results ? {
        unknown: results.filter(r => r.standing === 'unknown').length,
        friendly: results.filter(r => r.standing === 'friendly').length,
        lawn: results.filter(r => r.standing === 'lawn').length,
        unresolved: results.filter(r => r.standing === 'unresolved').length,
    } : null

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">LOCAL SCANNER</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {results && (
                        <span className="panel-badge">
                            {counts.unknown > 0 && <span style={{ color: STANDING_CONFIG.unknown.color }}>{counts.unknown} unknown</span>}
                            {counts.unknown > 0 && (counts.friendly > 0 || counts.lawn > 0) && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.friendly > 0 && <span style={{ color: STANDING_CONFIG.friendly.color }}>{counts.friendly} friendly</span>}
                            {counts.friendly > 0 && counts.lawn > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.lawn > 0 && <span style={{ color: STANDING_CONFIG.lawn.color }}>{counts.lawn} lawn</span>}
                            {counts.unresolved > 0 && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                            {counts.unresolved > 0 && <span style={{ color: STANDING_CONFIG.unresolved.color }}>{counts.unresolved} unresolved</span>}
                        </span>
                    )}
                    {results && results.length > 0 && (
                        <button
                            onClick={async () => {
                                const text = buildLocalCopyText(results, riskMap)
                                try { await navigator.clipboard.writeText(text) } catch {
                                    const el = document.createElement('textarea')
                                    el.value = text
                                    document.body.appendChild(el)
                                    el.select()
                                    document.execCommand('copy')
                                    document.body.removeChild(el)
                                }
                                setCopied(true)
                                setTimeout(() => setCopied(false), 2000)
                            }}
                            style={{
                                background: 'none', border: '1px solid var(--border-dim)',
                                color: copied ? 'var(--green)' : 'var(--cyan)',
                                cursor: 'pointer', fontFamily: 'Share Tech Mono, monospace',
                                fontSize: 10, padding: '2px 8px', letterSpacing: 1,
                                transition: 'color 0.2s',
                            }}
                        >{copied ? 'COPIED' : 'COPY'}</button>
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

            {canUseAi && results && results.length > 0 && (
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

            {results && results.length > 0 && (
                <div style={{ marginTop: 10 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                <th style={{ padding: '4px 8px', textAlign: 'left', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>PILOT</th>
                                <th style={{ padding: '4px 8px', textAlign: 'left', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>CORP / ALLIANCE</th>
                                <th style={{ padding: '4px 8px', textAlign: 'right', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>STANDING</th>
                                <th style={{ padding: '4px 8px', textAlign: 'right', fontFamily: 'Orbitron, sans-serif', fontSize: 9, letterSpacing: 2, color: 'var(--text-muted)', fontWeight: 500 }}>RISK</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.map((r, i) => {
                                const cfg = STANDING_CONFIG[r.standing] || STANDING_CONFIG.unknown
                                return (
                                    <tr key={i} style={{ borderBottom: '1px solid var(--border-dim)', background: cfg.bg }}>
                                        <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 11, color: 'var(--text-primary)' }}>
                                            {r.character_id ? (
                                                <a
                                                    href={`https://zkillboard.com/character/${r.character_id}/`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{ color: cfg.color, textDecoration: 'none' }}
                                                >
                                                    {r.name}
                                                </a>
                                            ) : r.name}
                                        </td>
                                        <td style={{ padding: '5px 8px', fontFamily: 'Share Tech Mono, monospace', fontSize: 10, color: 'var(--text-secondary)' }}>
                                            {r.corporation_name && <span>{r.corporation_name}</span>}
                                            {r.corporation_name && r.alliance_name && <span style={{ color: 'var(--text-muted)' }}> · </span>}
                                            {r.alliance_name && <span style={{ color: r.standing === 'unknown' ? '#ff9966' : 'var(--text-secondary)' }}>{r.alliance_name}</span>}
                                            {!r.corporation_name && !r.alliance_name && (
                                                <span style={{ color: 'var(--text-muted)' }}>—</span>
                                            )}
                                        </td>
                                        <td style={{ padding: '5px 8px', textAlign: 'right' }}>
                                            <span style={{
                                                fontFamily: 'Orbitron, sans-serif', fontSize: 9,
                                                fontWeight: 600, letterSpacing: 2, color: cfg.color,
                                            }}>{cfg.label}</span>
                                        </td>
                                        <td style={{ padding: '5px 8px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                                            {(() => {
                                                const risk = r.character_id ? riskMap[String(r.character_id)] : null
                                                if (!risk) return <span style={{ color: '#334455', fontFamily: 'Share Tech Mono, monospace', fontSize: 9 }}>—</span>
                                                const rc = RISK_COLOR[risk.tier] ?? '#334455'
                                                const kills = risk.kills >= 1000 ? `${(risk.kills/1000).toFixed(1)}k` : String(risk.kills)
                                                const roles = risk.roles || []
                                                return (
                                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                                                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 9, fontWeight: 700, letterSpacing: 1, color: rc }}>{risk.label}</span>
                                                            {roles.map(role => (
                                                                <span key={role} style={{
                                                                    fontFamily: 'Orbitron, sans-serif', fontSize: 7, fontWeight: 700,
                                                                    letterSpacing: 1, color: ROLE_COLOR[role] ?? '#aaaaaa',
                                                                    border: `1px solid ${ROLE_COLOR[role] ?? '#aaaaaa'}44`,
                                                                    padding: '0 3px', borderRadius: 2,
                                                                }}>{role}</span>
                                                            ))}
                                                        </div>
                                                        {risk.tier !== 'nodata' && risk.tier !== 'newbie' && (
                                                            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: '#6a8090' }}>
                                                                {kills} kills · {risk.isk_eff}% eff · {risk.danger}% danger
                                                            </span>
                                                        )}
                                                        {risk.tier === 'newbie' && (
                                                            <span style={{ fontFamily: 'Share Tech Mono, monospace', fontSize: 8, color: '#6a8090' }}>{kills} kills</span>
                                                        )}
                                                    </div>
                                                )
                                            })()}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {results && results.length === 0 && (
                <div style={{ padding: '8px 0', color: 'var(--text-muted)', fontFamily: 'Share Tech Mono, monospace', fontSize: 11 }}>
                    No pilots resolved.
                </div>
            )}
        </div>
    )
}
