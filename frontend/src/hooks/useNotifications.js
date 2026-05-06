import { useState, useCallback, useRef } from 'react'

const STORAGE_KEY = 'lawn-notif-settings'
const DEFAULTS = {
    enabled: false,
    campaigns: true,
    pvp: true,
    pvpThreshold: 3,
    admCritical: true,
}

function supported() {
    return typeof window !== 'undefined' && 'Notification' in window
}

export function useNotifications() {
    const [settings, setSettings] = useState(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY)
            return stored ? { ...DEFAULTS, ...JSON.parse(stored) } : DEFAULTS
        } catch { return DEFAULTS }
    })

    const [permStatus, setPermStatus] = useState(() =>
        supported() ? Notification.permission : 'unsupported'
    )

    // Snapshot of previous poll data for change detection
    const prevRef = useRef(null)

    const saveSettings = useCallback((updater) => {
        setSettings(prev => {
            const next = typeof updater === 'function' ? updater(prev) : updater
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch {}
            return next
        })
    }, [])

    const requestPermission = useCallback(async () => {
        if (!supported()) return
        const result = await Notification.requestPermission()
        setPermStatus(result)
        if (result === 'granted') {
            saveSettings(prev => ({ ...prev, enabled: true }))
        }
    }, [saveSettings])

    const sendNotif = useCallback((title, body, tag) => {
        if (!supported() || Notification.permission !== 'granted') return
        try {
            const n = new Notification(title, {
                body,
                tag,
                icon: '/static/logo.png',
                silent: false,
            })
            // Auto-close after 8s
            setTimeout(() => n.close(), 8000)
        } catch (e) {
            console.warn('[Notif] failed:', e)
        }
    }, [])

    // Call after each non-init data fetch.
    // Compares new data vs last snapshot and fires notifications for changes.
    // `allianceShort` is the active deployment's alliance ticker — used in the
    // notification copy so alerts read correctly for any alliance.
    const checkAndNotify = useCallback((campaigns, sovereignty, activity, primarySysIds, sysNames, allianceShort = 'PRIMARY') => {
        // Build current snapshot
        const campaignIds = new Set(campaigns.map(c => c.campaign_id))
        const admBySystem = {}
        primarySysIds.forEach(id => {
            const sov = sovereignty[id]
            if (sov && sov.is_friendly) admBySystem[id] = sov.adm
        })
        let primaryPVP = 0
        primarySysIds.forEach(id => {
            const a = activity[id] || {}
            primaryPVP += (a.ship_kills || 0) + (a.pod_kills || 0)
        })

        const prev = prevRef.current

        if (prev && settings.enabled && supported() && Notification.permission === 'granted') {
            // 1. New sov campaigns
            if (settings.campaigns) {
                campaigns.forEach(c => {
                    if (!prev.campaignIds.has(c.campaign_id)) {
                        const label = c.event_type === 'ihub_defense' ? 'IHUB' :
                                      c.event_type === 'tcu_defense' ? 'TCU' :
                                      c.event_type === 'station_defense' ? 'STATION' :
                                      (c.event_type || 'STRUCTURE').toUpperCase()
                        const isPrimaryCampaign = c.is_primary ?? c.is_lawn
                        const tag = isPrimaryCampaign ? ` — ${allianceShort} SPACE` : ''
                        sendNotif(
                            `⚠ SOV CAMPAIGN — ${c.system_name}`,
                            `${label} contested${tag}`,
                            `campaign-${c.campaign_id}`
                        )
                    }
                })
            }

            // 2. Primary-space PVP spike
            if (settings.pvp) {
                const delta = primaryPVP - prev.primaryPVP
                if (delta >= settings.pvpThreshold) {
                    sendNotif(
                        `💀 PVP IN ${allianceShort} SPACE — ${delta} kills`,
                        `${primaryPVP} total ship kills this hour in ${allianceShort} sov`,
                        'primary-pvp-spike'
                    )
                }
            }

            // 3. ADM critical drop (system crosses below 2.0)
            if (settings.admCritical) {
                primarySysIds.forEach(id => {
                    const prevAdm = prev.admBySystem[id]
                    const newAdm = admBySystem[id]
                    if (prevAdm !== undefined && prevAdm >= 2.0 && newAdm !== undefined && newAdm < 2.0) {
                        const name = sysNames[id] || id
                        sendNotif(
                            `🚨 ADM CRITICAL — ${name}`,
                            `ADM dropped to ${newAdm.toFixed(1)} — priority grinding needed`,
                            `adm-critical-${id}`
                        )
                    }
                })
            }
        }

        // Always update snapshot (including on init)
        prevRef.current = { campaignIds, admBySystem, primaryPVP }
    }, [settings, sendNotif])

    return { settings, saveSettings, permStatus, requestPermission, checkAndNotify }
}
