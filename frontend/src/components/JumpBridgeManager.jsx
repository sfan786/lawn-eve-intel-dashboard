import React, { useState, useEffect, useCallback } from 'react'
import CornerBrackets from './common/CornerBrackets'

const inputStyle = {
    background: 'var(--bg-deep)', border: '1px solid var(--border-dim)', color: 'var(--text-primary)',
    padding: 4, fontSize: 11, fontFamily: 'Share Tech Mono',
}

const actionBtnStyle = {
    background: 'transparent', border: '1px solid var(--cyan-dim)',
    fontFamily: 'Share Tech Mono', fontSize: 10, padding: '2px 8px', cursor: 'pointer',
}

export default function JumpBridgeManager({ jumpBridges = [], onJbChange }) {
    const [showForm, setShowForm] = useState(false)
    const [newJb, setNewJb] = useState({ system_a: '', system_b: '', label: '' })
    const [password, setPassword] = useState(localStorage.getItem("timer_auth") || "")
    const [isAuthenticated, setIsAuthenticated] = useState(false)
    const [authError, setAuthError] = useState(false)

    const checkAuth = useCallback(async () => {
        if (!password) return
        try {
            const res = await fetch("/api/auth/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password }),
            })
            if (res.ok) {
                setIsAuthenticated(true)
                setAuthError(false)
                localStorage.setItem("timer_auth", password)
            } else {
                setIsAuthenticated(false)
                setAuthError(true)
            }
        } catch {
            setIsAuthenticated(false)
        }
    }, [password])

    useEffect(() => {
        if (password) checkAuth()
    }, [checkAuth, password])

    const handleLogin = (e) => {
        e.preventDefault()
        checkAuth()
    }

    const handleLogout = () => {
        setIsAuthenticated(false)
        setPassword("")
        localStorage.removeItem("timer_auth")
        setShowForm(false)
    }

    const handleAdd = async () => {
        if (!newJb.system_a.trim() || !newJb.system_b.trim()) return
        const res = await fetch("/api/jumpbridges", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Timer-Auth": password },
            body: JSON.stringify(newJb),
        })
        if (res.ok) {
            setShowForm(false)
            setNewJb({ system_a: '', system_b: '', label: '' })
            if (onJbChange) onJbChange()
        } else if (res.status === 401) {
            setIsAuthenticated(false)
            setAuthError(true)
        }
    }

    const handleDelete = async (id) => {
        if (!confirm("Remove this jump bridge?")) return
        const res = await fetch(`/api/jumpbridges/${id}`, {
            method: "DELETE",
            headers: { "X-Timer-Auth": password },
        })
        if (res.ok) {
            if (onJbChange) onJbChange()
        } else if (res.status === 401) {
            setIsAuthenticated(false)
            setAuthError(true)
        }
    }

    return (
        <div className="panel panel-wide">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">JUMP BRIDGES</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {jumpBridges.length > 0 && (
                        <span className="panel-badge">{jumpBridges.length} active</span>
                    )}
                    {isAuthenticated ? (
                        <>
                            <button onClick={() => setShowForm(!showForm)} style={actionBtnStyle}>
                                {showForm ? "CANCEL" : "+ ADD JB"}
                            </button>
                            <button onClick={handleLogout} style={actionBtnStyle}>LOGOUT</button>
                        </>
                    ) : (
                        <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'Share Tech Mono' }}>READ ONLY</span>
                    )}
                </div>
            </div>

            {!isAuthenticated && showForm && (
                <div style={{ padding: 10, background: 'rgba(255,51,85,0.1)', marginBottom: 10, border: '1px solid var(--red-dim)' }}>
                    <form onSubmit={handleLogin} style={{ display: 'flex', gap: 8 }}>
                        <input
                            type="password"
                            placeholder="Enter Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            style={{ ...inputStyle, flex: 1 }}
                        />
                        <button type="submit" style={{ ...actionBtnStyle, background: 'var(--red-dim)', color: '#fff' }}>LOGIN</button>
                    </form>
                    {authError && <div style={{ color: 'var(--red)', fontSize: 10, marginTop: 4 }}>Invalid password</div>}
                </div>
            )}

            {isAuthenticated && showForm && (
                <div style={{ padding: 10, background: 'rgba(204,68,255,0.05)', marginBottom: 10, border: '1px solid rgba(204,68,255,0.2)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
                        <input
                            placeholder="System A (e.g. N-JK02)"
                            value={newJb.system_a}
                            onChange={e => setNewJb({ ...newJb, system_a: e.target.value })}
                            style={inputStyle}
                        />
                        <input
                            placeholder="System B (e.g. IUU3-L)"
                            value={newJb.system_b}
                            onChange={e => setNewJb({ ...newJb, system_b: e.target.value })}
                            style={inputStyle}
                        />
                        <input
                            placeholder="Label (optional)"
                            value={newJb.label}
                            onChange={e => setNewJb({ ...newJb, label: e.target.value })}
                            style={inputStyle}
                        />
                    </div>
                    <button onClick={handleAdd} style={{
                        width: '100%', background: 'rgba(204,68,255,0.15)',
                        color: '#cc44ff', border: '1px solid rgba(204,68,255,0.4)',
                        padding: 6, fontFamily: 'Orbitron', fontSize: 11, cursor: 'pointer',
                    }}>ADD JUMP BRIDGE</button>
                </div>
            )}

            {jumpBridges.length === 0 && !showForm && (
                <div style={{ padding: 10 }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, fontStyle: 'italic' }}>
                        No jump bridges configured. JB connections appear on the map as dashed purple lines.
                    </div>
                    {!isAuthenticated && (
                        <button onClick={() => setShowForm(true)} style={{
                            marginTop: 8, background: 'none', border: '1px solid var(--text-muted)',
                            color: 'var(--text-muted)', fontSize: 10, padding: '2px 8px', cursor: 'pointer',
                        }}>
                            LOGIN TO MANAGE
                        </button>
                    )}
                </div>
            )}

            {jumpBridges.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {jumpBridges.map(jb => (
                        <div key={jb.id} className="campaign-entry-compact" style={{ borderLeft: '3px solid rgba(204,68,255,0.6)' }}>
                            <div style={{ fontWeight: 'bold', color: '#cc44ff', fontFamily: 'Share Tech Mono', fontSize: 12, minWidth: 80 }}>
                                {jb.system_a}
                            </div>
                            <div style={{ color: 'var(--text-muted)', fontSize: 11, margin: '0 6px' }}>↔</div>
                            <div style={{ fontWeight: 'bold', color: '#cc44ff', fontFamily: 'Share Tech Mono', fontSize: 12, minWidth: 80 }}>
                                {jb.system_b}
                            </div>
                            {jb.label && (
                                <div style={{ flex: 1, fontSize: 10, color: 'var(--text-secondary)', fontStyle: 'italic', marginLeft: 8 }}>
                                    {jb.label}
                                </div>
                            )}
                            {!jb.label && <div style={{ flex: 1 }} />}
                            {isAuthenticated && (
                                <button onClick={() => handleDelete(jb.id)} style={{
                                    background: 'none', border: 'none', color: 'var(--text-muted)',
                                    cursor: 'pointer', fontSize: 14, marginLeft: 8,
                                }}>×</button>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
