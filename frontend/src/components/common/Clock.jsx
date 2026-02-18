import React, { useState, useEffect } from 'react';

const Clock = () => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (date, timeZone) => {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            timeZone: timeZone
        });
    };

    return (
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontFamily: "'Share Tech Mono', monospace", fontSize: '13px' }}>
            <span style={{ color: 'var(--text-primary)' }}>
                <span style={{ color: 'var(--cyan)', marginRight: '6px', fontWeight: 'bold' }}>EVE</span>
                {formatTime(time, 'UTC')}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)', marginRight: '6px' }}>LOC</span>
                {formatTime(time)}
            </span>
        </div>
    );
};

export default Clock;
