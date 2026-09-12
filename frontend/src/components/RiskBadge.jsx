import React from 'react';

export default function RiskBadge({ level, score }) {
  const normalizedLevel = (level || 'LOW').toUpperCase();

  const styles = {
    LOW: {
      bg: '#064e3b',
      text: '#34d399',
      border: '#059669',
      dot: '#10b981',
    },
    MEDIUM: {
      bg: '#78350f',
      text: '#fcd34d',
      border: '#d97706',
      dot: '#f59e0b',
    },
    HIGH: {
      bg: '#7c2d12',
      text: '#fdba74',
      border: '#ea580c',
      dot: '#f97316',
    },
    CRITICAL: {
      bg: '#7f1d1d',
      text: '#fca5a5',
      border: '#dc2626',
      dot: '#ef4444',
    },
  }[normalizedLevel] || {
    bg: '#1f2937',
    text: '#9ca3af',
    border: '#374151',
    dot: '#6b7280',
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '2px 8px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: '700',
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        backgroundColor: styles.bg,
        color: styles.text,
        border: `1px solid ${styles.border}`,
        fontFamily: 'var(--font-mono)',
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: styles.dot,
          boxShadow: `0 0 6px ${styles.dot}`,
        }}
      />
      {normalizedLevel}
      {score !== undefined && score !== null && (
        <span style={{ opacity: 0.85, fontWeight: 500 }}>({score})</span>
      )}
    </span>
  );
}
