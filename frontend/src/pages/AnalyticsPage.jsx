import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import CornerBrackets from '../components/common/CornerBrackets'
import EveLoginButton from '../components/common/EveLoginButton'
import { useAuth } from '../utils/useAuth'
import { ANALYTICS_AUTH_KEY, ANALYTICS_SEEN_KEY } from '../utils/analyticsAuth'

// Operator-facing usage stats: how many distinct people load the dashboard,
// how often they come back, and when. Backed by GET /api/analytics/summary,
// which is write-auth gated — the same SSO session / TIMER_PASSWORD that gates
// timers and entosis nodes.

const mono = { fontFamily: 'Share Tech Mono' }

const RANGES = [7, 30, 90]

const btn = (color) => ({
    background: 'transparent',
    border: `1px solid ${color}`,
    color,
    fontFamily: 'Share Tech Mono',
    fontSize: 10,
    padding: '2px 8px',
    cursor: 'pointer',
    letterSpacing: 0.5,
})

const inputStyle = {
    background: '#060a0f', border: '1px solid #1a3a4a', color: '#c0d8e8',
    padding: '3px 7px', fontSize: 11, fontFamily: 'Share Tech Mono',
}

const headerStyle = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    flexWrap: 'wrap', gap: 12, padding: '10px 16px',
    borderBottom: '1px solid #1a2a3a', background: '#0a1018',
}

function Stat({ label, value, sub, color = '#00d4ff' }) {
    return (
        <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1a2a3a', padding: '6px 10px', minWidth: 110 }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: 8, letterSpacing: 1.5, color: '#6a8090' }}>{label}</div>
            <div style={{ ...mono, fontSize: 20, color, lineHeight: 1.2 }}>{value}</div>
            {sub && <div style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{sub}</div>}
        </div>
    )
}

/** Vertical bar chart. values: [{ key, value, title }] */
function BarChart({ values, color = '#00d4ff', height = 90, emptyLabel = 'No data yet' }) {
    const max = Math.max(1, ...values.map(v => v.value))
    if (!values.length) {
        return <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: 10 }}>{emptyLabel}</div>
    }
    return (
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height, padding: '4px 0' }}>
            {values.map(v => (
                <div
                    key={v.key}
                    title={v.title}
                    style={{
                        flex: 1, minWidth: 2,
                        height: `${Math.max(2, (v.value / max) * 100)}%`,
                        background: v.value ? color : '#16222c',
                        opacity: v.value ? 0.85 : 1,
                    }}
                />
            ))}
        </div>
    )
}

function PathList({ title, rows, color }) {
    const max = Math.max(1, ...rows.map(r => r.views))
    return (
        <div className="panel">
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">{title}</span>
                <span className="panel-badge">{rows.length}</span>
            </div>
            {!rows.length && <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: 10 }}>No traffic recorded</div>}
            {rows.map(r => (
                <div key={r.path} style={{ position: 'relative', padding: '2px 4px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                    <div style={{
                        position: 'absolute', top: 0, left: 0, bottom: 0,
                        width: `${(r.views / max) * 100}%`, background: color, opacity: 0.12,
                    }} />
                    <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                        <span style={{ ...mono, fontSize: 10, color: '#c0d8e8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.path}</span>
                        <span style={{ ...mono, fontSize: 10, color }}>{r.views.toLocaleString()}</span>
                    </div>
                </div>
            ))}
        </div>
    )
}

export default function AnalyticsPage() {
    const auth = useAuth()
    const [days, setDays] = useState(30)
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [needsAuth, setNeedsAuth] = useState(false)
    const [unconfigured, setUnconfigured] = useState(null)
    const [gate, setGate] = useState(null)
    // Two separate values on purpose. `draft` is what the input holds while you
    // type; `credential` is what actually gets sent. Fetching keys off
    // `credential` only, so typing a password does not fire a request per
    // keystroke — that burned the whole rate-limit budget before the user ever
    // clicked UNLOCK, and put partial passwords on the wire.
    // The storage key is its own: the analytics credential is not the
    // fleet-wide timer password, and sharing that slot would conflate them.
    const [draft, setDraft] = useState(() => localStorage.getItem(ANALYTICS_AUTH_KEY) || '')
    const [credential, setCredential] = useState(() => localStorage.getItem(ANALYTICS_AUTH_KEY) || '')
    const [authError, setAuthError] = useState(null)

    const load = useCallback(async () => {
        setLoading(true)
        setAuthError(null)
        try {
            const res = await fetch(`/api/analytics/summary?days=${days}`, {
                headers: credential ? { 'X-Analytics-Auth': credential } : {},
            })
            if (res.status === 401 || res.status === 503 || res.status === 429) {
                setData(null)
                setNeedsAuth(res.status !== 503)
                setUnconfigured(res.status === 503 ? (await res.json()).detail : null)
                // Stop advertising the page in the header once access is gone.
                localStorage.removeItem(ANALYTICS_SEEN_KEY)
                if (res.status === 429) {
                    // Already throttled — don't spend the other endpoint's budget
                    // on a probe that can't help.
                    setAuthError('Too many attempts. Wait a minute, then try again.')
                } else {
                    setGate(await fetch('/api/analytics/auth').then(r => r.json()).catch(() => null))
                }
            } else if (res.ok) {
                setNeedsAuth(false)
                setUnconfigured(null)
                setData(await res.json())
                localStorage.setItem(ANALYTICS_SEEN_KEY, '1')
            } else {
                setAuthError('Could not load usage stats.')
            }
        } catch {
            setAuthError('Could not load usage stats.')
        } finally {
            setLoading(false)
        }
    }, [days, credential])

    useEffect(() => { if (auth.loaded) load() }, [auth.loaded, load])

    const submitPassword = (e) => {
        e.preventDefault()
        const value = draft.trim()
        if (!value) return
        localStorage.setItem(ANALYTICS_AUTH_KEY, value)
        // Setting the credential re-runs load() through the effect. When the
        // value is unchanged (retrying after a throttle) that dependency does
        // not change, so ask for the reload explicitly.
        if (value === credential) load()
        else setCredential(value)
    }

    const lock = () => {
        localStorage.removeItem(ANALYTICS_AUTH_KEY)
        localStorage.removeItem(ANALYTICS_SEEN_KEY)
        setDraft('')
        setCredential('')
        setData(null)
        setNeedsAuth(true)
    }

    const totals = data?.totals || {}
    const daily = data?.daily || []
    // Median-ish read of "a typical day" — the mean is skewed by op nights.
    const activeDays = daily.filter(d => d.visitors > 0)
    const avgVisitors = activeDays.length
        ? (activeDays.reduce((s, d) => s + d.visitors, 0) / activeDays.length).toFixed(1)
        : '0'
    const regulars = (data?.visitor_frequency || [])
        .filter(f => f.days_seen >= 5)
        .reduce((s, f) => s + f.visitors, 0)

    return (
        <div style={{ minHeight: '100vh', background: '#060a0f', color: '#c0d8e8' }}>
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Link to="/" style={{ ...mono, fontSize: 10, color: '#6a8090', textDecoration: 'none' }}>
                        ← DASHBOARD
                    </Link>
                    <div>
                        <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: '#00d4ff', letterSpacing: 2 }}>
                            USAGE ANALYTICS
                        </div>
                        <div style={{ ...mono, fontSize: 10, color: '#6a8090', marginTop: 2 }}>
                            {loading ? 'LOADING...' : data ? `LAST ${data.days} DAYS · UTC` : 'NO DATA'}
                        </div>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {RANGES.map(r => (
                            <button key={r} style={btn(r === days ? '#00d4ff' : '#1a3a4a')} onClick={() => setDays(r)}>
                                {r}D
                            </button>
                        ))}
                    </div>
                    <button style={btn('#00d4ff')} onClick={load} disabled={loading}>↻</button>
                    {data && credential && (
                        <button style={btn('#6a8090')} onClick={lock} title="Forget the analytics password on this browser">
                            LOCK
                        </button>
                    )}
                    <EveLoginButton auth={auth} />
                </div>
            </div>

            <div className="dashboard">
                {unconfigured && (
                    <div className="panel panel-wide">
                        <CornerBrackets />
                        <div className="panel-header">
                            <span className="panel-title">Access Not Configured</span>
                        </div>
                        <div style={{ padding: 10, ...mono, fontSize: 11, color: '#6a8090' }}>
                            <div style={{ color: '#ffaa00', marginBottom: 6 }}>{unconfigured}</div>
                            Traffic is still being recorded — it just can&apos;t be read until an
                            operator opts in. Set one of these in <code>.env</code> and restart:
                            <div style={{ marginTop: 6, color: '#c0d8e8' }}>
                                <div>ANALYTICS_ALLOWED_CHARACTER_IDS=&lt;your EVE character id&gt;</div>
                                <div>ANALYTICS_PASSWORD=&lt;a password you don&apos;t share with the fleet&gt;</div>
                            </div>
                        </div>
                    </div>
                )}

                {needsAuth && (
                    <div className="panel panel-wide">
                        <CornerBrackets />
                        <div className="panel-header">
                            <span className="panel-title">Authorization Required</span>
                        </div>
                        <div style={{ padding: 10 }}>
                            <div style={{ ...mono, fontSize: 11, color: '#6a8090', marginBottom: 8 }}>
                                Usage stats are operator-only — separate from the fleet timer password.
                            </div>
                            {gate?.sso && (
                                <div style={{ marginBottom: 8 }}>
                                    {auth.loggedIn ? (
                                        <span style={{ ...mono, fontSize: 11, color: '#ffaa00' }}>
                                            {auth.characterName} is not on the analytics allowlist.
                                        </span>
                                    ) : (
                                        <button style={btn('#00d4ff')} onClick={auth.login}>⛛ LOG IN WITH EVE</button>
                                    )}
                                </div>
                            )}
                            {/* Default to showing the form when the probe hasn't
                                answered (e.g. we're throttled) — otherwise a
                                rate-limited user sees an error with no way to
                                retry once the window clears. */}
                            {(gate?.password ?? true) && (
                                <form onSubmit={submitPassword} style={{ display: 'flex', gap: 8, maxWidth: 340 }}>
                                    <input
                                        type="password"
                                        placeholder="Analytics password"
                                        value={draft}
                                        onChange={e => setDraft(e.target.value)}
                                        style={{ ...inputStyle, flex: 1 }}
                                    />
                                    <button type="submit" style={btn('#00d4ff')}>UNLOCK</button>
                                </form>
                            )}
                            {authError && (
                                <div style={{ ...mono, fontSize: 10, color: '#ff3355', marginTop: 6 }}>{authError}</div>
                            )}
                        </div>
                    </div>
                )}

                {authError && !needsAuth && (
                    <div className="panel panel-wide">
                        <div style={{ ...mono, fontSize: 11, color: '#ff3355', padding: 10 }}>{authError}</div>
                    </div>
                )}

                {data && (
                    <>
                        <div className="panel panel-wide">
                            <CornerBrackets />
                            <div className="panel-header">
                                <span className="panel-title">Is Anyone Using This?</span>
                                <span className="panel-badge">{totals.active_days || 0} days with traffic</span>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                <Stat
                                    label="Unique Visitors"
                                    value={(totals.unique_visitors || 0).toLocaleString()}
                                    sub={`${avgVisitors}/active day`}
                                    color={totals.unique_visitors ? '#00ff88' : '#ff3355'}
                                />
                                <Stat
                                    label="Regulars"
                                    value={regulars}
                                    sub="seen 5+ days"
                                    color={regulars ? '#00ff88' : '#6a8090'}
                                />
                                <Stat
                                    label="Returning"
                                    value={totals.returning_visitors || 0}
                                    sub="seen 2+ days"
                                />
                                <Stat label="Page Loads" value={(totals.page_views || 0).toLocaleString()} />
                                <Stat label="API Calls" value={(totals.api_calls || 0).toLocaleString()} color="#6a8090" />
                                <Stat label="Peak Day" value={totals.peak_daily_visitors || 0} sub="visitors" color="#ffaa00" />
                                <Stat label="Bot Hits" value={(totals.bot_hits || 0).toLocaleString()} sub="not counted above" color="#6a8090" />
                            </div>
                        </div>

                        <div className="panel panel-wide">
                            <CornerBrackets />
                            <div className="panel-header">
                                <span className="panel-title">Daily Visitors</span>
                                <span className="panel-badge">{daily.length} days recorded</span>
                            </div>
                            <BarChart
                                values={daily.map(d => ({
                                    key: d.day,
                                    value: d.visitors,
                                    title: `${d.day}: ${d.visitors} visitors, ${d.page_views} page loads, ${d.api_calls} API calls`,
                                }))}
                                emptyLabel="No visits recorded yet — stats start accumulating from first deploy."
                            />
                            {daily.length > 0 && (
                                <div style={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 9, color: '#6a8090' }}>
                                    <span>{daily[0].day}</span>
                                    <span>{daily[daily.length - 1].day}</span>
                                </div>
                            )}
                        </div>

                        <div className="panel panel-wide">
                            <CornerBrackets />
                            <div className="panel-header">
                                <span className="panel-title">Hour of Day</span>
                                <span className="panel-badge">EVE time · page loads</span>
                            </div>
                            <BarChart
                                values={(data.hourly || []).map(h => ({
                                    key: h.hour,
                                    value: h.views,
                                    title: `${String(h.hour).padStart(2, '0')}:00 — ${h.views} page loads`,
                                }))}
                                color="#ffaa00"
                                height={70}
                            />
                            <div style={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 9, color: '#6a8090' }}>
                                <span>00</span><span>06</span><span>12</span><span>18</span><span>23</span>
                            </div>
                        </div>

                        <div className="panel-pair">
                            <PathList title="Pages" rows={data.top_pages || []} color="#00d4ff" />
                            <PathList title="API Endpoints" rows={data.top_api || []} color="#6a8090" />
                        </div>

                        <div className="panel panel-wide">
                            <CornerBrackets />
                            <div className="panel-header">
                                <span className="panel-title">Known Pilots</span>
                                <span className="panel-badge">{(data.pilots || []).length} logged in</span>
                            </div>
                            {!(data.pilots || []).length && (
                                <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: 10 }}>
                                    No SSO logins recorded — visitors are counted anonymously.
                                </div>
                            )}
                            {(data.pilots || []).length > 0 && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 6 }}>
                                    {data.pilots.map(p => (
                                        <div key={p.character_name} style={{
                                            display: 'flex', justifyContent: 'space-between', gap: 8,
                                            background: 'rgba(0,0,0,0.3)', border: '1px solid #1a2a3a', padding: '3px 7px',
                                        }}>
                                            <span style={{ ...mono, fontSize: 11, color: '#00ff88' }}>{p.character_name}</span>
                                            <span style={{ ...mono, fontSize: 10, color: '#6a8090' }}>{p.days_seen}d</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="panel panel-wide">
                            <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: 6 }}>
                                Visitors are counted by a salted hash of IP + browser, never stored raw.
                                One person on two devices counts twice; a shared corp office IP with the
                                same browser counts once. Bot and crawler hits are excluded from visitor counts.
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
