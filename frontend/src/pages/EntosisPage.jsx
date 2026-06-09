import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import CornerBrackets from '../components/common/CornerBrackets'

const STATUS_META = {
    unclaimed:  { label: 'UNCLAIMED',  color: '#6a8090', bg: 'rgba(106,128,144,0.08)' },
    running:    { label: 'RUNNING',    color: '#00d4ff', bg: 'rgba(0,212,255,0.08)'   },
    contested:  { label: 'CONTESTED',  color: '#ffaa00', bg: 'rgba(255,170,0,0.10)'   },
    captured:   { label: 'CAPTURED',   color: '#00ff88', bg: 'rgba(0,255,136,0.08)'   },
    lost:       { label: 'LOST',       color: '#ff3355', bg: 'rgba(255,51,85,0.08)'   },
}

const NEXT_STATUSES = {
    unclaimed:  ['running', 'contested'],
    running:    ['contested', 'captured', 'lost'],
    contested:  ['running', 'captured', 'lost'],
    captured:   [],
    lost:       [],
}

const btn = (color) => ({
    background: 'transparent',
    border: `1px solid ${color}`,
    color,
    fontFamily: 'Share Tech Mono',
    fontSize: 10,
    padding: '2px 7px',
    cursor: 'pointer',
    letterSpacing: 0.5,
})

export default function EntosisPage() {
    const [nodes, setNodes] = useState([])
    const [config, setConfig] = useState(null)
    const [callsign, setCallsign] = useState(() => localStorage.getItem('entosis_callsign') || '')
    const [callsignInput, setCallsignInput] = useState(() => localStorage.getItem('entosis_callsign') || '')
    const [password, setPassword] = useState(() => localStorage.getItem('timer_auth') || '')
    const [isAuth, setIsAuth] = useState(false)
    const [authError, setAuthError] = useState(false)
    const [showAddForm, setShowAddForm] = useState(false)
    const [addError, setAddError] = useState('')
    const [newSystem, setNewSystem] = useState('')
    const [newLabel, setNewLabel] = useState('')
    const [lastUpdate, setLastUpdate] = useState(null)
    const pollRef = useRef(null)

    const fetchNodes = useCallback(async () => {
        try {
            const res = await fetch('/api/entosis/nodes')
            if (res.ok) { setNodes(await res.json()); setLastUpdate(new Date()) }
        } catch (_) {}
    }, [])

    const fetchConfig = useCallback(async () => {
        try {
            const res = await fetch('/api/config')
            if (res.ok) setConfig(await res.json())
        } catch (_) {}
    }, [])

    useEffect(() => {
        fetchNodes()
        fetchConfig()
        pollRef.current = setInterval(fetchNodes, 5000)
        return () => clearInterval(pollRef.current)
    }, [fetchNodes, fetchConfig])

    // Auto-check auth once on mount using the stored password (not re-run on keystroke)
    useEffect(() => {
        const storedPw = localStorage.getItem('timer_auth')
        if (!storedPw) return
        fetch('/api/auth/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: storedPw }),
        }).then(r => {
            setIsAuth(r.ok)
            if (!r.ok) setAuthError(true)
        }).catch(() => setIsAuth(false))
    }, [])

    const saveCallsign = () => {
        const cs = callsignInput.trim()
        setCallsign(cs)
        localStorage.setItem('entosis_callsign', cs)
    }

    const handleAuth = async (e) => {
        e.preventDefault()
        const res = await fetch('/api/auth/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        })
        if (res.ok) {
            setIsAuth(true); setAuthError(false)
            localStorage.setItem('timer_auth', password)
        } else {
            setIsAuth(false); setAuthError(true)
        }
    }

    const addNode = async (e) => {
        e.preventDefault()
        if (!newSystem) return
        setAddError('')
        try {
            const res = await fetch('/api/entosis/nodes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Timer-Auth': password },
                body: JSON.stringify({ system_name: newSystem, label: newLabel || null }),
            })
            if (!res.ok) {
                const data = await res.json().catch(() => ({}))
                setAddError(res.status === 401 ? 'Auth failed — re-enter FC password' : (data.error || `Error ${res.status}`))
                return
            }
            setNewSystem(''); setNewLabel(''); setShowAddForm(false); setAddError('')
        } catch (err) {
            setAddError('Network error — try again')
            return
        }
        fetchNodes()
    }

    const patchNode = async (id, patch) => {
        await fetch(`/api/entosis/nodes/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        })
        fetchNodes()
    }

    const claimNode = (id) => {
        if (!callsign) return alert('Set your callsign first.')
        patchNode(id, { claimed_by: callsign, status: 'running' })
    }

    const unclaimNode = (id) => {
        patchNode(id, { claimed_by: '', status: 'unclaimed' })
    }

    const deleteNode = async (id) => {
        await fetch(`/api/entosis/nodes/${id}`, {
            method: 'DELETE',
            headers: { 'X-Timer-Auth': password },
        })
        fetchNodes()
    }

    const clearAll = async () => {
        if (!confirm('Clear all command nodes?')) return
        await fetch('/api/entosis/nodes', {
            method: 'DELETE',
            headers: { 'X-Timer-Auth': password },
        })
        fetchNodes()
    }

    // Build primary system list from config for the add-node dropdown
    const primarySystems = config?.constellations ? Object.values(config.constellations)
        .filter(c => c.is_primary ?? c.is_lawn)
        .flatMap(c => Object.values(c.systems || {}).map(s => s.name))
        .sort()
        : []

    const headerStyle = {
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px', background: '#0a1018',
        borderBottom: '1px solid #1a2a3a', gap: 12, flexWrap: 'wrap',
    }

    const inputStyle = {
        background: '#060a0f', border: '1px solid #1a3a4a', color: '#c0d8e8',
        padding: '3px 7px', fontSize: 11, fontFamily: 'Share Tech Mono',
    }

    const counts = nodes.reduce((acc, n) => {
        if (acc[n.status] !== undefined) acc[n.status]++
        return acc
    }, { unclaimed: 0, running: 0, contested: 0, captured: 0, lost: 0 })

    return (
        <div style={{ minHeight: '100vh', background: '#060a0f', color: '#c0d8e8' }}>
            {/* Page header */}
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Link to="/" style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#6a8090', textDecoration: 'none' }}>
                        ← DASHBOARD
                    </Link>
                    <div>
                        <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: '#00d4ff', letterSpacing: 2 }}>
                            ENTOSIS COMMAND NODE BOARD
                        </div>
                        <div style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#6a8090', marginTop: 2 }}>
                            {lastUpdate ? `UPDATED ${lastUpdate.toLocaleTimeString()}` : 'CONNECTING...'}
                            {nodes.length > 0 && ` · ${nodes.length} NODES`}
                        </div>
                    </div>
                </div>

                {/* Summary badges */}
                {nodes.length > 0 && (
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        {Object.entries(counts).filter(([, v]) => v > 0).map(([status, count]) => (
                            <span key={status} style={{
                                fontFamily: 'Share Tech Mono', fontSize: 10,
                                color: STATUS_META[status].color,
                                border: `1px solid ${STATUS_META[status].color}`,
                                padding: '2px 7px', opacity: 0.9,
                            }}>
                                {count} {STATUS_META[status].label}
                            </span>
                        ))}
                    </div>
                )}

                {/* Right controls */}
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    {/* Callsign */}
                    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                        <span style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#6a8090' }}>CALLSIGN</span>
                        <input
                            style={{ ...inputStyle, width: 110 }}
                            value={callsignInput}
                            onChange={e => setCallsignInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && saveCallsign()}
                            placeholder="your handle"
                            maxLength={32}
                        />
                        <button style={btn('#00d4ff')} onClick={saveCallsign}>SET</button>
                        {callsign && (
                            <span style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#00ff88' }}>
                                ✓ {callsign}
                            </span>
                        )}
                    </div>

                    {/* FC auth */}
                    {!isAuth ? (
                        <form onSubmit={handleAuth} style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                            <input
                                type="password"
                                style={{ ...inputStyle, width: 90 }}
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="FC password"
                            />
                            <button type="submit" style={btn(authError ? '#ff3355' : '#ffaa00')}>
                                {authError ? 'WRONG PW' : 'FC LOGIN'}
                            </button>
                        </form>
                    ) : (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            <span style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#00ff88' }}>FC AUTHED</span>
                            <button style={btn('#00d4ff')} onClick={() => { setShowAddForm(f => !f) }}>
                                {showAddForm ? 'CANCEL' : '+ ADD NODE'}
                            </button>
                            {nodes.length > 0 && (
                                <button style={btn('#ff3355')} onClick={clearAll}>CLEAR ALL</button>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Add-node form */}
            {showAddForm && (
                <form onSubmit={addNode} style={{
                    display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
                    padding: '8px 16px', background: '#0a1018', borderBottom: '1px solid #1a2a3a',
                }}>
                    <span style={{ fontFamily: 'Orbitron', fontSize: 10, color: '#00d4ff', letterSpacing: 1 }}>ADD NODE</span>
                    <select
                        style={{ ...inputStyle, minWidth: 130 }}
                        value={newSystem}
                        onChange={e => setNewSystem(e.target.value)}
                        required
                    >
                        <option value="">— system —</option>
                        {primarySystems.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <input
                        style={{ ...inputStyle, width: 120 }}
                        value={newLabel}
                        onChange={e => setNewLabel(e.target.value)}
                        placeholder="label (optional)"
                        maxLength={40}
                    />
                    <button type="submit" style={btn('#00ff88')}>ADD</button>
                    {addError && (
                        <span style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#ff3355' }}>{addError}</span>
                    )}
                </form>
            )}

            {/* Node grid */}
            <div style={{ padding: 12 }}>
                {nodes.length === 0 ? (
                    <div style={{ padding: 10, fontFamily: 'Share Tech Mono', fontSize: 11, color: '#6a8090', textAlign: 'center' }}>
                        No active command nodes — FC adds nodes with [+ ADD NODE] after logging in.
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
                        {nodes.map(node => {
                            const meta = STATUS_META[node.status] || STATUS_META.unclaimed
                            const nextStatuses = NEXT_STATUSES[node.status] || []
                            const isClaimedByMe = callsign && node.claimed_by === callsign

                            return (
                                <div key={node.id} style={{
                                    background: '#0a1018',
                                    border: `1px solid ${meta.color}`,
                                    borderLeft: `3px solid ${meta.color}`,
                                    padding: '10px 12px',
                                    position: 'relative',
                                }}>
                                    <CornerBrackets />

                                    {/* System + label */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                                        <div>
                                            <div style={{ fontFamily: 'Orbitron', fontSize: 12, color: '#c0d8e8', letterSpacing: 1 }}>
                                                {node.system_name}
                                            </div>
                                            {node.label && (
                                                <div style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: '#6a8090', marginTop: 1 }}>
                                                    {node.label}
                                                </div>
                                            )}
                                        </div>
                                        <span style={{
                                            fontFamily: 'Share Tech Mono', fontSize: 10,
                                            color: meta.color,
                                            background: meta.bg,
                                            padding: '2px 6px',
                                            border: `1px solid ${meta.color}`,
                                            animation: node.status === 'contested' ? 'pulse-reffed 2s infinite' : undefined,
                                        }}>
                                            {meta.label}
                                        </span>
                                    </div>

                                    {/* Claimed by */}
                                    <div style={{ fontFamily: 'Share Tech Mono', fontSize: 10, color: node.claimed_by ? '#00ff88' : '#6a8090', marginBottom: 8, minHeight: 16 }}>
                                        {node.claimed_by
                                            ? <>PILOT: <span style={{ color: isClaimedByMe ? '#00ff88' : '#c0d8e8' }}>{node.claimed_by}</span></>
                                            : 'UNCLAIMED'}
                                    </div>

                                    {/* Action buttons */}
                                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                                        {node.status === 'unclaimed' && (
                                            <button style={btn('#00d4ff')} onClick={() => claimNode(node.id)}>
                                                CLAIM
                                            </button>
                                        )}
                                        {node.claimed_by && isClaimedByMe && node.status === 'running' && (
                                            <button style={btn('#6a8090')} onClick={() => unclaimNode(node.id)}>
                                                RELEASE
                                            </button>
                                        )}
                                        {nextStatuses.map(s => (
                                            <button key={s} style={btn(STATUS_META[s].color)} onClick={() => patchNode(node.id, { status: s })}>
                                                {STATUS_META[s].label}
                                            </button>
                                        ))}
                                        {isAuth && (
                                            <button style={{ ...btn('#ff3355'), marginLeft: 'auto' }} onClick={() => deleteNode(node.id)}>
                                                ✕
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
