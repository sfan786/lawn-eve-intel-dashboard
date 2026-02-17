import React from 'react'

export default function SummaryCard({ label, value, type = "default" }) {
    return (
        <div className="summary-card">
            <div className="summary-label">{label}</div>
            <div className={`summary-value ${type === "danger" ? "danger" : type === "warn" ? "warn" : type === "safe" ? "safe" : ""}`}>
                {value}
            </div>
        </div>
    )
}
