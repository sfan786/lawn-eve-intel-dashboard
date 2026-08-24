/**
 * Plain-text renderings of the parser results, for pasting into fleet chat.
 *
 * These lived inside their component files, which made them untestable and
 * unavailable to the shared read-only page. Exported here alongside the same
 * pattern already used by buildWarCopyText (warHelpers) and
 * buildCampaignCopyText (campaignHelpers).
 *
 * The output is deliberately ASCII-plain — "x3" rather than "×3" — because it
 * is going into EVE chat and Discord.
 */

import { CATEGORY_LABELS, formatTypes, shipCatRows, structureCounts } from './dscanCategories'

export function buildDscanCopyText(result) {
    if (!result) return ''
    const catRows = shipCatRows(result)
    const structures = structureCounts(result)

    const lines = [`THREAT: ${result.threat.tier}`]
    lines.push(`${result.ships} combat ships · ${result.structures.length} structures`)
    lines.push('')
    for (const { cat, count, types } of catRows) {
        lines.push(`${CATEGORY_LABELS[cat]}: ${count}  (${formatTypes(types, 'x')})`)
    }
    if (Object.keys(structures).length > 0) {
        lines.push('')
        lines.push('Objects: ' + Object.entries(structures)
            .map(([t, n]) => n > 1 ? `${t} x${n}` : t).join(', '))
    }
    return lines.join('\n')
}

export function buildLocalCopyText(results, riskMap = {}) {
    if (!results) return ''
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

export function buildFleetCopyText(s) {
    if (!s) return ''
    const total = (s.unknown || 0) + (s.friendly || 0) + (s.lawn || 0) + (s.unresolved || 0)
    const lines = [`FLEET ANALYSIS — ${total} pilots`]
    lines.push(`Threat: ${s.avg_danger ?? 0}% avg danger | Caps: ${s.capitals || 0}`)
    const dist = s.risk_distribution || {}
    const distParts = []
    if (dist.very_dangerous) distParts.push(`${dist.very_dangerous} VERY DANGEROUS`)
    if (dist.dangerous) distParts.push(`${dist.dangerous} DANGEROUS`)
    if (dist.moderate) distParts.push(`${dist.moderate} MODERATE`)
    if (dist.snuggly) distParts.push(`${dist.snuggly} SNUGGLY`)
    if (dist.newbie) distParts.push(`${dist.newbie} NEWBIE`)
    if (distParts.length) lines.push(`Risk: ${distParts.join(', ')}`)
    const roles = Object.entries(s.role_counts || {})
    if (roles.length) lines.push(`Roles: ${roles.map(([r, n]) => n > 1 ? `${r} ×${n}` : r).join(', ')}`)
    const fleetRoles = Object.entries(s.fleet_role_counts || {})
    if (fleetRoles.length) lines.push(`Fleet roles: ${fleetRoles.map(([r, n]) => n > 1 ? `${r} ×${n}` : r).join(', ')}`)
    const topAlliances = (s.top_alliances || []).slice(0, 5)
    if (topAlliances.length) lines.push(`Top alliances: ${topAlliances.map(a => `${a.name} (${a.count})`).join(', ')}`)
    return lines.join('\n')
}

/** Copy text for a share payload of the given kind. Used by SharePage. */
export function buildShareCopyText(kind, payload) {
    if (kind === 'dscan') return buildDscanCopyText(payload.result)
    if (kind === 'local') return buildLocalCopyText(payload.results, payload.riskMap)
    if (kind === 'fleet') return buildFleetCopyText(payload.result?.summary)
    return ''
}
