import React, { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import CornerBrackets from '../components/common/CornerBrackets'
import CopyButton from '../components/common/CopyButton'
import EveLoginButton from '../components/common/EveLoginButton'
import { AiSummaryBox } from '../components/common/AiSummary'
import DscanResult from '../components/parsers/DscanResult'
import LocalScanResult, { localCounts, StandingCounts } from '../components/parsers/LocalScanResult'
import FleetCompResult, { FleetCounts } from '../components/parsers/FleetCompResult'
import { buildShareCopyText } from '../utils/parserCopy'
import { eveTime, timeAgo } from '../utils/formatters'
import { useAuth } from '../utils/useAuth'

// Read-only view of a shared parser snapshot (/s/<token>).
//
// Everything here is replayed from what the sender's browser had on screen —
// no scanning, no ESI, no zKill. That is the whole point: a local scan's
// standings and risk tiers are only true as of when they were taken, so the
// page states its age prominently rather than passing stale intel off as live.

const mono = { fontFamily: 'Share Tech Mono, monospace' }

const KIND_TITLE = {
    dscan: 'D-SCAN',
    local: 'LOCAL SCAN',
    fleet: 'FLEET COMP',
}

/**
 * Colour the age so staleness is legible without doing arithmetic.
 *
 * Fifteen minutes is roughly how long a D-scan or local list stays actionable
 * before a fleet has moved; past a couple of hours it is history, not intel.
 */
function ageColorFor(isoTime) {
    const minutes = (Date.now() - new Date(isoTime).getTime()) / 60000
    if (!Number.isFinite(minutes)) return 'var(--text-muted)'
    if (minutes < 15) return 'var(--green)'
    if (minutes < 120) return 'var(--amber)'
    return 'var(--red)'
}

function Notice({ title, children }) {
    return (
        <div className="panel panel-wide" style={{ maxWidth: 640, margin: '80px auto' }}>
            <CornerBrackets />
            <div className="panel-header">
                <span className="panel-title">{title}</span>
            </div>
            <div style={{ ...mono, fontSize: 12, color: 'var(--text-secondary)', padding: '10px 0' }}>
                {children}
            </div>
            <Link to="/" style={{ ...mono, fontSize: 11, color: 'var(--cyan)', textDecoration: 'none' }}>
                ← BACK TO DASHBOARD
            </Link>
        </div>
    )
}

/** The panel-header badge for each kind, so a share reads like its live panel. */
function ShareBadge({ kind, payload }) {
    if (kind === 'dscan' && payload.result) {
        return <span className="panel-badge">{payload.result.ships} ships · {payload.result.total} total</span>
    }
    if (kind === 'local' && payload.results) {
        return <span className="panel-badge"><StandingCounts counts={localCounts(payload.results)} /></span>
    }
    if (kind === 'fleet' && payload.result?.summary) {
        return <span className="panel-badge"><FleetCounts summary={payload.result.summary} /></span>
    }
    return null
}

function ShareBody({ kind, payload }) {
    if (kind === 'dscan') {
        return (
            <DscanResult
                result={payload.result}
                summarySlot={payload.ai_summary ? <AiSummaryBox summary={payload.ai_summary} /> : null}
            />
        )
    }
    if (kind === 'local') {
        return (
            <>
                {payload.ai_summary && <AiSummaryBox summary={payload.ai_summary} />}
                <LocalScanResult results={payload.results} riskMap={payload.riskMap || {}} />
            </>
        )
    }
    if (kind === 'fleet') {
        return <FleetCompResult result={payload.result} />
    }
    return (
        <div style={{ ...mono, fontSize: 11, color: 'var(--text-muted)', padding: '8px 0' }}>
            This share is of a type this dashboard does not know how to render.
        </div>
    )
}

export default function SharePage() {
    const { token } = useParams()
    const auth = useAuth()
    const [report, setReport] = useState(null)
    const [status, setStatus] = useState('loading')

    useEffect(() => {
        let cancelled = false
        async function load() {
            try {
                const res = await fetch(`/api/share/${encodeURIComponent(token)}`)
                if (cancelled) return
                if (res.status === 403) { setStatus('forbidden'); return }
                if (!res.ok) { setStatus('missing'); return }
                setReport(await res.json())
                setStatus('ok')
            } catch {
                if (!cancelled) setStatus('error')
            }
        }
        load()
        return () => { cancelled = true }
        // auth.authorized is a dependency: logging in is exactly what fixes a
        // 403, so the page should reload itself once the session changes.
    }, [token, auth.authorized])

    if (status === 'loading') {
        return <Notice title="LOADING">Fetching shared report…</Notice>
    }

    if (status === 'forbidden') {
        return (
            <Notice title="ALLIANCE ONLY">
                <p style={{ marginBottom: 10 }}>
                    Whoever shared this restricted it to alliance members. Log in with your
                    EVE character to view it.
                </p>
                <EveLoginButton auth={auth} />
                {!auth.ssoEnabled && (
                    <p style={{ color: 'var(--amber)' }}>
                        SSO is not configured on this deployment, so this share cannot be opened here.
                    </p>
                )}
            </Notice>
        )
    }

    if (status !== 'ok' || !report) {
        return (
            <Notice title="NOT FOUND">
                This share link has expired or does not exist. Shares are deliberately
                short-lived — ask whoever sent it for a fresh one.
            </Notice>
        )
    }

    const { kind, payload, title, created_by: createdBy, created_at: createdAt, expires_at: expiresAt, visibility } = report
    const ageColor = ageColorFor(createdAt)

    return (
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '16px 12px' }}>
            <div className="panel panel-wide">
                <CornerBrackets />
                <div className="panel-header">
                    <span className="panel-title">{KIND_TITLE[kind] || 'SHARED REPORT'}</span>
                    <ShareBadge kind={kind} payload={payload} />
                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <CopyButton getText={() => buildShareCopyText(kind, payload)} />
                        <Link to="/" style={{ ...mono, fontSize: 10, color: 'var(--text-secondary)', textDecoration: 'none', letterSpacing: 1 }}>
                            DASHBOARD →
                        </Link>
                    </span>
                </div>

                {/* Age is not decoration. A D-scan read as live when it is three
                    hours old is worse than no D-scan at all.
                    The absolute EVE time leads and the relative age follows it:
                    "3h ago" is the glance, but the timestamp is what gets compared
                    against a fleet ping or a timer — and unlike the relative age,
                    it does not quietly rot while the tab sits open. */}
                <div style={{
                    ...mono, fontSize: 10, color: 'var(--text-muted)',
                    display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'baseline',
                    borderBottom: '1px solid var(--border-dim)', paddingBottom: 6, marginBottom: 2,
                }}>
                    <span style={{ color: 'var(--amber)' }}>SNAPSHOT — not live</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                        {eveTime(createdAt, { withSeconds: true })} EVE
                    </span>
                    <span style={{ color: ageColor }}>{timeAgo(createdAt)} old</span>
                    {createdBy && <span>by {createdBy}</span>}
                    {title && <span style={{ color: 'var(--text-secondary)' }}>{title}</span>}
                    {visibility === 'alliance' && <span style={{ color: 'var(--cyan)' }}>alliance only</span>}
                    <span style={{ marginLeft: 'auto' }}>expires {eveTime(expiresAt)} EVE</span>
                </div>

                <ShareBody kind={kind} payload={payload} />
            </div>
        </div>
    )
}
