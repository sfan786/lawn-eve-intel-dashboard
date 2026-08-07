import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import CornerBrackets from '../components/common/CornerBrackets'
import EveLoginButton from '../components/common/EveLoginButton'
import WarBarChart from '../components/war/WarBarChart'
import { useAuth } from '../utils/useAuth'
import { formatIsk, timeAgo } from '../utils/formatters'
import {
    sideMeta, share, warDuration, stalenessMinutes, hullTotals,
    orderedHullClasses, buildWarCopyText, formatDuration,
} from '../utils/warHelpers'

// Bloc-war tracker. Unlike the dashboard's kill feed, this reads a *persisted*
// ledger (GET /api/wars/<key>/*) that the war poller fills in, so it can show
// the whole war rather than the last twenty kills.

const mono = { fontFamily: 'Share Tech Mono' }

const RANGES = [
    { key: 1, label: '24H' },
    { key: 7, label: '7D' },
    { key: 30, label: '30D' },
    { key: 0, label: 'WAR' },
]

const btn = (color) => ({
    background: 'transparent', border: `1px solid ${color}`, color,
    fontFamily: 'Share Tech Mono', fontSize: 10, padding: '2px 8px',
    cursor: 'pointer', letterSpacing: 0.5,
})

const headerStyle = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    flexWrap: 'wrap', gap: 12, padding: '10px 16px',
    borderBottom: '1px solid #1a2a3a', background: '#0a1018',
}

const empty = (text) => (
    <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: 10 }}>{text}</div>
)

function Stat({ label, value, sub, color = '#00d4ff' }) {
    return (
        <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1a2a3a', padding: '6px 10px', minWidth: 110 }}>
            <div style={{ fontFamily: 'Orbitron', fontSize: 8, letterSpacing: 1.5, color: '#6a8090' }}>{label}</div>
            <div style={{ ...mono, fontSize: 20, color, lineHeight: 1.2 }}>{value}</div>
            {sub && <div style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{sub}</div>}
        </div>
    )
}

function CopyButton({ text, label = 'COPY' }) {
    const [copied, setCopied] = useState(false)
    const copy = () => {
        const done = () => { setCopied(true); setTimeout(() => setCopied(false), 2000) }
        if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(() => {})
            return
        }
        const ta = document.createElement('textarea')
        ta.value = text
        document.body.appendChild(ta)
        ta.select()
        try { document.execCommand('copy'); done() } catch (_) { /* nothing to do */ }
        document.body.removeChild(ta)
    }
    return (
        <button onClick={copy} style={btn(copied ? '#00ff88' : '#6a8090')}>
            {copied ? 'COPIED!' : label}
        </button>
    )
}

/** Side-vs-side proportional bar — the page's central "who is winning" read. */
function ScoreBar({ a, b, sideA, sideB, format = formatIsk }) {
    const pct = share(a, b)
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: sideA.color }}>{format(a)}</span>
                <span style={{ color: sideB.color }}>{format(b)}</span>
            </div>
            <div style={{ display: 'flex', height: 14, border: '1px solid #1a2a3a', background: '#060a0f' }}>
                <div style={{ width: `${pct}%`, background: sideA.color, opacity: 0.8 }} />
                <div style={{ width: `${100 - pct}%`, background: sideB.color, opacity: 0.8 }} />
            </div>
        </div>
    )
}

export default function WarPage() {
    const auth = useAuth()
    const [password, setPassword] = useState(() => localStorage.getItem('timer_auth') || '')
    const [roster, setRoster] = useState(null)
    const [rosterBusy, setRosterBusy] = useState(null)
    const [rosterError, setRosterError] = useState(null)
    const [wars, setWars] = useState([])
    const [warKey, setWarKey] = useState(null)
    const [days, setDays] = useState(7)
    const [metric, setMetric] = useState('kills')
    const [summary, setSummary] = useState(null)
    const [battles, setBattles] = useState([])
    const [leaderboard, setLeaderboard] = useState(null)
    const [participant, setParticipant] = useState(null)
    const [unclassified, setUnclassified] = useState([])
    const [kills, setKills] = useState([])
    const [status, setStatus] = useState(null)
    const [feedSide, setFeedSide] = useState('')
    const [feedClass, setFeedClass] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        let alive = true
        fetch('/api/wars')
            .then(r => r.ok ? r.json() : [])
            .then(list => {
                if (!alive) return
                setWars(list)
                setWarKey(k => k || list[0]?.key || null)
                if (!list.length) setLoading(false)
            })
            .catch(() => { if (alive) { setError('Could not load wars'); setLoading(false) } })
        return () => { alive = false }
    }, [])

    const load = useCallback(async () => {
        if (!warKey) return
        const q = `days=${days === 0 ? 'all' : days}`
        const get = (path) => fetch(path).then(r => r.ok ? r.json() : null).catch(() => null)
        const [s, b, l, p, u, st, r] = await Promise.all([
            get(`/api/wars/${warKey}/summary?${q}`),
            get(`/api/wars/${warKey}/battles?${q}`),
            get(`/api/wars/${warKey}/leaderboard?${q}`),
            get(`/api/wars/${warKey}/participant?${q}`),
            get(`/api/wars/${warKey}/unclassified?${q}`),
            get(`/api/wars/${warKey}/status`),
            get(`/api/wars/${warKey}/roster`),
        ])
        setSummary(s)
        setBattles(b || [])
        setLeaderboard(l)
        setParticipant(p)
        setUnclassified(u || [])
        setStatus(st)
        setRoster(r)
        setLoading(false)
        if (!s) setError('Could not load war data')
        else setError(null)
    }, [warKey, days])

    useEffect(() => { load() }, [load])

    // The feed reloads on its own filters without re-pulling every aggregate.
    const loadKills = useCallback(async () => {
        if (!warKey) return
        const params = new URLSearchParams({ limit: '40' })
        if (feedSide) params.set('side', feedSide)
        if (feedClass) params.set('class', feedClass)
        const data = await fetch(`/api/wars/${warKey}/kills?${params}`)
            .then(r => r.ok ? r.json() : null).catch(() => null)
        setKills(data?.kills || [])
    }, [warKey, feedSide, feedClass])

    useEffect(() => { loadKills() }, [loadKills])

    // Assign an entity to a side (or to neither, with side === null). The
    // server reclassifies stored history, so the whole page has to reload —
    // a roster change moves the totals, not just this panel.
    const assignSide = useCallback(async (entityId, side, name) => {
        setRosterBusy(entityId)
        setRosterError(null)
        try {
            const headers = { 'Content-Type': 'application/json' }
            if (!auth.ssoEnabled) headers['X-Timer-Auth'] = password
            const res = await fetch(`/api/wars/${warKey}/roster`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ entity_id: entityId, side, name }),
            })
            if (!res.ok) {
                const data = await res.json().catch(() => ({}))
                setRosterError(res.status === 401
                    ? 'Not authorized — log in with EVE or enter the fleet password'
                    : (data.error || `Error ${res.status}`))
                return
            }
            if (!auth.ssoEnabled) localStorage.setItem('timer_auth', password)
            await load()
        } catch (_) {
            setRosterError('Could not reach the server')
        } finally {
            setRosterBusy(null)
        }
    }, [warKey, auth.ssoEnabled, password, load])

    const undoOverride = useCallback(async (entityId, entityType) => {
        setRosterBusy(entityId)
        setRosterError(null)
        try {
            const headers = {}
            if (!auth.ssoEnabled) headers['X-Timer-Auth'] = password
            const res = await fetch(
                `/api/wars/${warKey}/roster/${entityId}?entity_type=${entityType || 'alliance'}`,
                { method: 'DELETE', headers })
            if (!res.ok) {
                setRosterError(res.status === 401 ? 'Not authorized' : `Error ${res.status}`)
                return
            }
            await load()
        } catch (_) {
            setRosterError('Could not reach the server')
        } finally {
            setRosterBusy(null)
        }
    }, [warKey, auth.ssoEnabled, password, load])

    // Poll for new kills only; the aggregates change once per ingest cycle.
    useEffect(() => {
        const id = setInterval(loadKills, 60000)
        return () => clearInterval(id)
    }, [loadKills])

    const war = summary?.war || wars.find(w => w.key === warKey)
    const sideA = useMemo(() => sideMeta(war, 'a'), [war])
    const sideB = useMemo(() => sideMeta(war, 'b'), [war])
    const totals = summary?.totals || {}
    const stale = stalenessMinutes(summary?.coverage?.last_kill)

    const subtitle = () => {
        if (loading) return 'LOADING...'
        if (!war) return 'NO WAR CONFIGURED'
        const bits = [`DAY ${warDuration(war.start_date)}`]
        if (summary?.coverage?.rows) bits.push(`${summary.coverage.rows.toLocaleString()} KILLS LOGGED`)
        if (stale !== null) bits.push(`UPDATED ${stale}M AGO`)
        if (status?.any_gaps) bits.push('⚠ GAPS')
        return bits.join(' · ')
    }

    if (!loading && !wars.length) {
        return (
            <div style={{ minHeight: '100vh', background: '#060a0f', color: '#c0d8e8' }}>
                <div style={headerStyle}>
                    <Link to="/" style={{ ...mono, fontSize: 10, color: '#6a8090', textDecoration: 'none' }}>← DASHBOARD</Link>
                </div>
                <div className="dashboard">
                    <div className="panel panel-wide">
                        <CornerBrackets />
                        <div className="panel-header"><span className="panel-title">War Tracker</span></div>
                        <div style={{ ...mono, fontSize: 11, color: '#6a8090', padding: 10, lineHeight: 1.6 }}>
                            No war is configured. Add a module to <code>private/wars/</code> —
                            see <code>wars/example.py</code> for the template — then restart.
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div style={{ minHeight: '100vh', background: '#060a0f', color: '#c0d8e8' }}>
            <div style={headerStyle}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <Link to="/" style={{ ...mono, fontSize: 10, color: '#6a8090', textDecoration: 'none' }}>
                        ← DASHBOARD
                    </Link>
                    <div>
                        <div style={{ fontFamily: 'Orbitron', fontSize: 14, color: '#00d4ff', letterSpacing: 2 }}>
                            {war?.name?.toUpperCase() || 'WAR TRACKER'}
                        </div>
                        <div style={{ ...mono, fontSize: 10, color: '#6a8090', marginTop: 2 }}>
                            {subtitle()}
                            {error && <span style={{ color: '#ff3355' }}> · {error}</span>}
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    {wars.length > 1 && (
                        <select className="region-picker" value={warKey || ''} onChange={e => setWarKey(e.target.value)}>
                            {wars.map(w => <option key={w.key} value={w.key}>{w.name}</option>)}
                        </select>
                    )}
                    <div className="map-mode-toggle">
                        {RANGES.map(r => (
                            <button key={r.key}
                                className={`map-mode-btn ${days === r.key ? 'active' : ''}`}
                                onClick={() => setDays(r.key)}>
                                {r.label}
                            </button>
                        ))}
                    </div>
                    <EveLoginButton auth={auth} />
                    <button onClick={load} style={btn('#00d4ff')}>↻</button>
                </div>
            </div>

            <div className="dashboard">
                {/* ---- Scoreboard ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Scoreboard</span>
                        <span className="panel-badge">{summary?.bucket === 'week' ? 'weekly' : summary?.bucket || 'daily'}</span>
                        <span style={{ marginLeft: 'auto' }}>
                            <CopyButton text={buildWarCopyText(war, summary)} />
                        </span>
                    </div>
                    <div className="summary-row" style={{ marginBottom: 8 }}>
                        <Stat label={`${sideA.short} KILLS`} value={(totals.a_kills || 0).toLocaleString()}
                            sub={`${totals.a_efficiency || 0}% of ISK destroyed`} color={sideA.color} />
                        <Stat label={`${sideA.short} DESTROYED`} value={formatIsk(totals.a_isk)} color={sideA.color} />
                        <Stat label={`${sideB.short} KILLS`} value={(totals.b_kills || 0).toLocaleString()}
                            sub={`${totals.b_efficiency || 0}% of ISK destroyed`} color={sideB.color} />
                        <Stat label={`${sideB.short} DESTROYED`} value={formatIsk(totals.b_isk)} color={sideB.color} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 10, color: '#6a8090', marginBottom: 2 }}>
                        <span style={{ color: sideA.color }}>{sideA.label}</span>
                        <span style={{ color: sideB.color }}>{sideB.label}</span>
                    </div>
                    <ScoreBar a={totals.a_isk} b={totals.b_isk} sideA={sideA} sideB={sideB} />
                    {status && (
                        <div style={{ ...mono, fontSize: 9, color: '#3a5060', marginTop: 6 }}>
                            Ledger covers {status.coverage_since ? status.coverage_since.slice(0, 10) : '—'} → now
                            across {status.regions?.length || 0} regions
                            {status.any_gaps && <span style={{ color: '#ffaa00' }}> · one or more regions reported a fetch gap</span>}
                        </div>
                    )}
                </div>

                {/* ---- War timeline ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">War Timeline</span>
                        <span className="panel-badge">{summary?.series?.length || 0} periods</span>
                        <div className="map-mode-toggle" style={{ marginLeft: 'auto' }}>
                            <button className={`map-mode-btn ${metric === 'kills' ? 'active' : ''}`} onClick={() => setMetric('kills')}>KILLS</button>
                            <button className={`map-mode-btn ${metric === 'isk' ? 'active' : ''}`} onClick={() => setMetric('isk')}>ISK</button>
                        </div>
                    </div>
                    <WarBarChart series={summary?.series || []} sideA={sideA} sideB={sideB} metric={metric} />
                    <div style={{ display: 'flex', gap: 14, ...mono, fontSize: 9, color: '#6a8090', marginTop: 4 }}>
                        <span><span style={{ color: sideA.color }}>▲</span> {sideA.short} scored</span>
                        <span><span style={{ color: sideB.color }}>▼</span> {sideB.short} scored</span>
                    </div>
                </div>

                {/* ---- Contested systems ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Contested Systems</span>
                        <span className="panel-badge">{summary?.contested_systems?.length || 0}</span>
                    </div>
                    {!summary?.contested_systems?.length && empty('No fighting recorded in this window')}
                    {!!summary?.contested_systems?.length && (
                        <div className="table-scroll-wrapper">
                            <table className="sys-table">
                                <thead>
                                    <tr>
                                        <th>System</th>
                                        {/* War kills vs all kills: a war's regions
                                            contain plenty of unrelated violence. */}
                                        <th title="Kills involving a belligerent / all kills">War / all</th>
                                        <th>ISK</th>
                                        <th>{sideA.short} lost</th><th>{sideB.short} lost</th>
                                        <th>Balance</th><th>Last kill</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {summary.contested_systems.slice(0, 15).map(s => (
                                        <tr key={s.system_id}>
                                            <td className="sys-name">{s.system_name || s.system_id}</td>
                                            <td className="stat-num">
                                                {s.war_kills ?? s.kills}
                                                <span style={{ color: '#3a5060' }}> / {s.kills}</span>
                                            </td>
                                            <td className="stat-num">{formatIsk(s.isk)}</td>
                                            <td className="stat-num" style={{ color: sideA.color }}>{s.a_losses}</td>
                                            <td className="stat-num" style={{ color: sideB.color }}>{s.b_losses}</td>
                                            <td style={{ minWidth: 80 }}>
                                                <div style={{ display: 'flex', height: 8, background: '#060a0f', border: '1px solid #1a2a3a' }}>
                                                    <div style={{ width: `${share(s.a_losses, s.b_losses)}%`, background: sideA.color, opacity: 0.75 }} />
                                                    <div style={{ flex: 1, background: sideB.color, opacity: 0.75 }} />
                                                </div>
                                            </td>
                                            <td style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{timeAgo(s.last_kill)} ago</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* ---- Hull losses ---- */}
                <div className="panel">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Hull Losses</span>
                        <span className="panel-badge">by class</span>
                    </div>
                    {!summary?.ship_classes && empty('No losses recorded')}
                    {summary?.ship_classes && (
                        <table className="sys-table">
                            <thead>
                                <tr><th>Class</th><th>{sideA.short}</th><th>{sideB.short}</th></tr>
                            </thead>
                            <tbody>
                                {orderedHullClasses(summary.ship_classes).map(cls => {
                                    const a = summary.ship_classes.a?.[cls]
                                    const b = summary.ship_classes.b?.[cls]
                                    return (
                                        <tr key={cls}>
                                            <td className="sys-name" style={{ textTransform: 'uppercase' }}>{cls}</td>
                                            <td className="stat-num" style={{ color: sideA.color }}>
                                                {a ? `${a.count} · ${formatIsk(a.isk)}` : '—'}
                                            </td>
                                            <td className="stat-num" style={{ color: sideB.color }}>
                                                {b ? `${b.count} · ${formatIsk(b.isk)}` : '—'}
                                            </td>
                                        </tr>
                                    )
                                })}
                                <tr>
                                    <td className="sys-name" style={{ color: '#00d4ff' }}>TOTAL</td>
                                    <td className="stat-num" style={{ color: sideA.color }}>
                                        {hullTotals(summary.ship_classes, 'a').count} · {formatIsk(hullTotals(summary.ship_classes, 'a').isk)}
                                    </td>
                                    <td className="stat-num" style={{ color: sideB.color }}>
                                        {hullTotals(summary.ship_classes, 'b').count} · {formatIsk(hullTotals(summary.ship_classes, 'b').isk)}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    )}
                </div>

                {/* ---- Our war record ---- */}
                <div className="panel">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Our War Record</span>
                        {participant && <span className="panel-badge">{participant.efficiency}% efficiency</span>}
                    </div>
                    {!participant && empty('Not a belligerent in this war')}
                    {participant && (participant.kills || participant.losses) === 0 &&
                        empty('No kills or losses recorded for us in this window')}
                    {participant && (participant.kills || participant.losses) > 0 && (
                        <>
                            <div className="summary-row" style={{ marginBottom: 6 }}>
                                <Stat label="KILLS" value={participant.kills.toLocaleString()} color="#00ff88" />
                                <Stat label="LOSSES" value={participant.losses.toLocaleString()} color="#ff3355" />
                                <Stat label="DESTROYED" value={formatIsk(participant.isk_killed)} color="#00ff88" />
                                <Stat label="LOST" value={formatIsk(participant.isk_lost)} color="#ff3355" />
                            </div>
                            {!!participant.top_systems?.length && (
                                <div style={{ ...mono, fontSize: 10, color: '#8a9aa0' }}>
                                    Busiest: {participant.top_systems.map(s => `${s.system_name} (${s.n})`).join(' · ')}
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* ---- Battles ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Battles</span>
                        <span className="panel-badge">{battles.length}</span>
                        <span className="panel-badge" style={{ marginLeft: 'auto' }}>30-min clustering</span>
                    </div>
                    {!battles.length && empty('No engagements above the clustering threshold')}
                    {!!battles.length && (
                        <div className="table-scroll-wrapper">
                            <table className="sys-table">
                                <thead>
                                    <tr>
                                        <th>System</th><th>When</th><th>Duration</th><th>Kills</th>
                                        <th>ISK</th><th>{sideA.short}</th><th>{sideB.short}</th>
                                        <th>Caps</th><th>Peak</th><th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {battles.map(b => (
                                        <tr key={`${b.system_id}-${b.start_time}`}>
                                            <td className="sys-name">{b.system_name || b.system_id}</td>
                                            <td style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{timeAgo(b.end_time)} ago</td>
                                            <td className="stat-num">{formatDuration(b.duration_minutes)}</td>
                                            <td className="stat-num">{b.kills}</td>
                                            <td className="stat-num">{formatIsk(b.isk)}</td>
                                            <td className="stat-num" style={{ color: sideA.color }}>-{b.a_losses}</td>
                                            <td className="stat-num" style={{ color: sideB.color }}>-{b.b_losses}</td>
                                            <td className="stat-num" style={{ color: b.cap_losses ? '#ffaa00' : '#3a5060' }}>{b.cap_losses || '—'}</td>
                                            <td className="stat-num">{b.peak_attackers}</td>
                                            <td>
                                                <a href={b.related_url} target="_blank" rel="noopener noreferrer"
                                                    style={{ ...mono, fontSize: 9, color: '#00d4ff' }}>BR ↗</a>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* ---- Leaderboards ---- */}
                <div className="panel">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Heaviest Losses</span>
                        <span className="panel-badge">by alliance</span>
                    </div>
                    {!leaderboard?.bleeders?.length && empty('No losses recorded')}
                    {!!leaderboard?.bleeders?.length && (
                        <table className="sys-table">
                            <thead><tr><th>Alliance</th><th>Lost</th><th>ISK</th></tr></thead>
                            <tbody>
                                {leaderboard.bleeders.map(r => (
                                    <tr key={r.alliance_id}>
                                        <td className="sys-name" style={{ color: sideMeta(war, r.victim_side).color }}>
                                            {r.name || `#${r.alliance_id}`}
                                        </td>
                                        <td className="stat-num">{r.losses}</td>
                                        <td className="stat-num">{formatIsk(r.isk_lost)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                <div className="panel">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Most Active Killers</span>
                        {/* zKill credits every participant on a mail, so this column
                            sums to more than the ISK actually destroyed. */}
                        <span className="panel-badge">involvement, not credit</span>
                    </div>
                    {!leaderboard?.killers?.length && empty('No kills recorded')}
                    {!!leaderboard?.killers?.length && (
                        <table className="sys-table">
                            <thead><tr><th>Alliance</th><th>On kills</th><th>ISK involved</th></tr></thead>
                            <tbody>
                                {leaderboard.killers.map(r => (
                                    <tr key={r.alliance_id}>
                                        <td className="sys-name">{r.name || `#${r.alliance_id}`}</td>
                                        <td className="stat-num">{r.involved_kills}</td>
                                        <td className="stat-num">{formatIsk(r.isk_involved)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* ---- Live feed ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">War Kill Feed</span>
                        <span className="panel-badge">{kills.length}</span>
                        <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', alignItems: 'center' }}>
                            <div className="map-mode-toggle">
                                <button className={`map-mode-btn ${!feedSide ? 'active' : ''}`} onClick={() => setFeedSide('')}>ALL</button>
                                <button className={`map-mode-btn ${feedSide === 'a' ? 'active' : ''}`} onClick={() => setFeedSide('a')}>{sideA.short}</button>
                                <button className={`map-mode-btn ${feedSide === 'b' ? 'active' : ''}`} onClick={() => setFeedSide('b')}>{sideB.short}</button>
                            </div>
                            <div className="map-mode-toggle">
                                <button className={`map-mode-btn ${!feedClass ? 'active' : ''}`} onClick={() => setFeedClass('')}>ANY</button>
                                <button className={`map-mode-btn ${feedClass === 'capital' ? 'active' : ''}`} onClick={() => setFeedClass('capital')}>CAPS</button>
                                <button className={`map-mode-btn ${feedClass === 'structure' ? 'active' : ''}`} onClick={() => setFeedClass('structure')}>STRUCT</button>
                            </div>
                        </div>
                    </div>
                    {!kills.length && empty('No kills match this filter')}
                    {!!kills.length && (
                        <div className="kill-feed">
                            {kills.map(k => {
                                const side = sideMeta(war, k.victim_side)
                                const known = k.victim_side === 'a' || k.victim_side === 'b'
                                return (
                                    <div key={k.killmail_id} className="kill-entry"
                                        style={{ borderLeft: `3px solid ${known ? side.color : '#3a5060'}` }}>
                                        <div className="kill-time">{timeAgo(k.killmail_time)}</div>
                                        <div className="kill-details">
                                            <div className="kill-ship">
                                                {k.ship_name || 'Unknown'}
                                                {k.ship_class !== 'subcap' && (
                                                    <span style={{ ...mono, fontSize: 9, color: '#ffaa00', marginLeft: 6 }}>
                                                        {k.ship_class.toUpperCase()}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="kill-parties">
                                                {k.victim_char_name || 'Unknown'} · {k.victim_alliance_name || k.victim_corp_name || 'Unaffiliated'}
                                            </div>
                                            <div className="kill-system">
                                                {k.system_name} · {k.attacker_count} attackers
                                                {known && <span style={{ color: side.color }}> · {side.short} loss</span>}
                                            </div>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <div className="kill-value">{formatIsk(k.isk_destroyed)}</div>
                                            <a href={`https://zkillboard.com/kill/${k.killmail_id}/`}
                                                target="_blank" rel="noopener noreferrer"
                                                style={{ ...mono, fontSize: 9, color: '#00d4ff' }}>zkill ↗</a>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>

                {/* ---- Roster suggestions ---- */}
                <div className="panel panel-wide">
                    <CornerBrackets />
                    <div className="panel-header">
                        <span className="panel-title">Unaligned in the War Zone</span>
                        <span className="panel-badge">{unclassified.length}</span>
                        <span className="panel-badge" style={{ marginLeft: 'auto' }}>roster suggestions</span>
                    </div>
                    {rosterError && (
                        <div style={{ ...mono, fontSize: 10, color: '#ff3355', padding: '4px 0' }}>
                            {rosterError}
                        </div>
                    )}
                    {!auth.ssoEnabled && (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '4px 0' }}>
                            <input type="password" value={password} placeholder="fleet password"
                                onChange={e => setPassword(e.target.value)}
                                style={{ background: '#060a0f', border: '1px solid #1a3a4a', color: '#c0d8e8', padding: '3px 7px', fontSize: 11, ...mono, width: 150 }} />
                            <span style={{ ...mono, fontSize: 9, color: '#3a5060' }}>needed to edit the roster</span>
                        </div>
                    )}
                    {!unclassified.length && empty('Every active alliance is on a roster')}
                    {!!unclassified.length && (
                        <>
                            <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: '4px 0 6px' }}>
                                Fighting here but on neither roster. The suggested side is whichever
                                they shoot <em>less</em> — confirm before assigning. Assigning
                                reclassifies the war's whole history, not just kills from here on.
                            </div>
                            <div className="table-scroll-wrapper">
                                <table className="sys-table">
                                    <thead>
                                        <tr>
                                            <th>Alliance</th><th>On kills</th><th>ISK</th>
                                            <th>vs {sideA.short}</th><th>vs {sideB.short}</th>
                                            <th>Suggests</th><th>Last seen</th><th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {unclassified.map(u => (
                                            <tr key={u.alliance_id}>
                                                <td className="sys-name">{u.name || `#${u.alliance_id}`}</td>
                                                <td className="stat-num">{u.involved_kills}</td>
                                                <td className="stat-num">{formatIsk(u.isk_involved)}</td>
                                                <td className="stat-num">{u.kills_vs_a}</td>
                                                <td className="stat-num">{u.kills_vs_b}</td>
                                                <td className="stat-num" style={{ color: u.suggested_side ? sideMeta(war, u.suggested_side).color : '#3a5060' }}>
                                                    {u.suggested_side ? sideMeta(war, u.suggested_side).short : '—'}
                                                </td>
                                                <td style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{timeAgo(u.last_seen)} ago</td>
                                                <td>
                                                    <div style={{ display: 'flex', gap: 4 }}>
                                                        <button disabled={rosterBusy === u.alliance_id}
                                                            title={`Add to ${sideA.label}`}
                                                            onClick={() => assignSide(u.alliance_id, 'a', u.name)}
                                                            style={btn(sideA.color)}>→ {sideA.short}</button>
                                                        <button disabled={rosterBusy === u.alliance_id}
                                                            title={`Add to ${sideB.label}`}
                                                            onClick={() => assignSide(u.alliance_id, 'b', u.name)}
                                                            style={btn(sideB.color)}>→ {sideB.short}</button>
                                                        <button disabled={rosterBusy === u.alliance_id}
                                                            title="Not a belligerent — stop suggesting"
                                                            onClick={() => assignSide(u.alliance_id, null, u.name)}
                                                            style={btn('#6a8090')}>✕</button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>

                {/* ---- Roster edits ---- */}
                {!!roster?.overrides?.length && (
                    <div className="panel panel-wide">
                        <CornerBrackets />
                        <div className="panel-header">
                            <span className="panel-title">Roster Edits</span>
                            <span className="panel-badge">{roster.overrides.length}</span>
                            <span className="panel-badge" style={{ marginLeft: 'auto' }}>
                                on top of {war?.short_name || 'the war module'}
                            </span>
                        </div>
                        <div style={{ ...mono, fontSize: 10, color: '#6a8090', padding: '4px 0 6px' }}>
                            Made from this page and stored in the database — the war module on disk
                            is unchanged. Undo reverts to whatever it says.
                        </div>
                        <table className="sys-table">
                            <thead>
                                <tr><th>Entity</th><th>Assigned</th><th>By</th><th>When</th><th></th></tr>
                            </thead>
                            <tbody>
                                {roster.overrides.map(o => {
                                    const side = sideMeta(war, o.side)
                                    return (
                                        <tr key={`${o.entity_type}-${o.entity_id}`}>
                                            <td className="sys-name">{o.name || `#${o.entity_id}`}</td>
                                            <td className="stat-num" style={{ color: side.color }}>
                                                {o.side ? side.short : 'NOT A BELLIGERENT'}
                                            </td>
                                            <td style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{o.added_by || '—'}</td>
                                            <td style={{ ...mono, fontSize: 9, color: '#6a8090' }}>{timeAgo(o.added_at)} ago</td>
                                            <td>
                                                <button disabled={rosterBusy === o.entity_id}
                                                    onClick={() => undoOverride(o.entity_id, o.entity_type)}
                                                    style={btn('#6a8090')}>UNDO</button>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
