import React, { useState } from 'react';
import RiskBadge from './RiskBadge';
import AudioEvidencePlayer from './AudioEvidencePlayer';

export default function IncidentDetails({
  incident,
  onApprove,
  onReject,
  onRequestEvidence,
  actionLoading,
}) {
  const [operatorNotes, setOperatorNotes] = useState('');

  if (!incident) {
    return (
      <div className="incident-details-empty">
        <div className="empty-icon">🛰️</div>
        <h3>Select an incident</h3>
        <p>Choose an incident from the map or list to inspect the complete reasoning dossier.</p>
      </div>
    );
  }

  const {
    event = {},
    classification = {},
    verification = {},
    localization = {},
    memory = {},
    risk = {},
    human_gate = {},
    action = {},
  } = incident;

  const eventId = event.id;
  const metadata = event.metadata || {};
  const isWaiting = human_gate.status === 'WAITING_FOR_APPROVAL';
  const isApproved = human_gate.status === 'APPROVED' || human_gate.status === 'AUTO_APPROVED';
  const isRejected = human_gate.status === 'REJECTED';

  // Truthful provenance detection
  const isLive = metadata.data_mode === 'live' || metadata.source === 'global_fishing_watch' || event.sensor_id === 'GFW_AIS';
  const provenanceLabel = isLive ? 'LIVE GFW API DATA' : 'SIMULATED DEMO DATA';
  const provenanceSubtext = isLive
    ? 'Verified observation retrieved from Global Fishing Watch v3 API'
    : 'Simulated demonstration event modeled on EEZ boundary fishing behavior';

  const handleApprove = () => {
    onApprove(eventId, 'ranger_supervisor', operatorNotes || 'Operational clearance granted');
    setOperatorNotes('');
  };

  const handleReject = () => {
    onReject(eventId, 'ranger_supervisor', operatorNotes || 'Dismissed by human operator');
    setOperatorNotes('');
  };

  const handleEvidence = () => {
    onRequestEvidence(eventId, 'ranger_supervisor', operatorNotes || 'Awaiting secondary sensor verification');
    setOperatorNotes('');
  };

  return (
    <div className="incident-details-container">
      {/* Top Banner */}
      <div className="details-header">
        <div>
          <div className="details-id-row" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span className="event-id">{eventId}</span>
            <span className={`domain-badge ${event.domain}`}>
              {event.domain?.toUpperCase()}
            </span>
            <span className={`provenance-badge ${isLive ? 'live' : 'simulated'}`} style={{
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.05em',
              background: isLive ? 'rgba(6, 182, 212, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: isLive ? '#38bdf8' : '#fbbf24',
              border: isLive ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)',
            }}>
              {isLive ? '📡 ' : '🔬 '}{provenanceLabel}
            </span>
          </div>
          <h2 className="details-title">{classification.refined_type || event.event_type}</h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Timestamp: {event.timestamp ? new Date(event.timestamp).toUTCString() : 'N/A'} • Sensor: {event.sensor_id}
          </div>
        </div>
        <div className="details-risk-block">
          <RiskBadge level={risk.level} score={risk.score} />
          <span className="risk-score-caption">{risk.score}/100 Risk Score</span>
        </div>
      </div>

      {/* Human Approval Decision Card */}
      <div className={`gate-decision-card ${isWaiting ? 'pulse-border' : ''}`}>
        <div className="gate-card-header">
          <div className="gate-status-text">
            <span className="gate-icon">
              {isWaiting ? '⚠️' : isApproved ? '✓' : isRejected ? '✕' : 'ℹ️'}
            </span>
            <strong>Human Supervision Gate:</strong>{' '}
            <span className="status-highlight">{human_gate.status}</span>
          </div>
          {action.dispatched && (
            <span className="dispatched-badge">✓ ACTION DISPATCHED</span>
          )}
        </div>

        <p className="gate-rationale">
          {human_gate.reasons?.[0] || 'Safety policy check for response deployment.'}
        </p>

        {isWaiting && (
          <div className="gate-actions-block">
            <input
              type="text"
              placeholder="Operator notes (e.g. Ground patrol unit Charlie dispatched)..."
              value={operatorNotes}
              onChange={(e) => setOperatorNotes(e.target.value)}
              className="operator-notes-input"
              disabled={actionLoading}
            />
            <div className="gate-btn-row">
              <button
                className="gate-btn approve-btn"
                onClick={handleApprove}
                disabled={actionLoading}
              >
                {actionLoading ? 'Processing...' : '✓ APPROVE & DISPATCH'}
              </button>
              <button
                className="gate-btn evidence-btn"
                onClick={handleEvidence}
                disabled={actionLoading}
              >
                ⏳ REQUEST EVIDENCE
              </button>
              <button
                className="gate-btn reject-btn"
                onClick={handleReject}
                disabled={actionLoading}
              >
                ✕ REJECT
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Acoustic Forensics & Live Audio Capture Player */}
      <AudioEvidencePlayer incident={incident} />

      {/* Dossier Grid */}
      <div className="dossier-grid">

        {/* Provenance & Data Origin Card */}
        <div className="dossier-card" style={{ gridColumn: 'span 2' }}>
          <h4>Data Provenance & Sensor Origin</h4>
          <div className="dossier-row">
            <span className="dossier-label">Data Mode:</span>
            <span className="dossier-val font-semibold" style={{ color: isLive ? '#38bdf8' : '#fbbf24' }}>
              {isLive ? 'LIVE OBSERVATION' : 'SIMULATED DEMO'}
            </span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Telemetry Source:</span>
            <span className="dossier-val font-mono">{metadata.source || (isLive ? 'global_fishing_watch' : 'ecosentinel_demo')}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Sensor Identifier:</span>
            <span className="dossier-val font-mono">{event.sensor_id}</span>
          </div>
          {metadata.gfw_event_id && (
            <div className="dossier-row">
              <span className="dossier-label">GFW Event ID:</span>
              <span className="dossier-val font-mono">{metadata.gfw_event_id}</span>
            </div>
          )}
          {metadata.dataset && (
            <div className="dossier-row">
              <span className="dossier-label">GFW Dataset:</span>
              <span className="dossier-val font-mono">{metadata.dataset}</span>
            </div>
          )}
          <div className="reason-item" style={{ marginTop: '8px', fontSize: '12px', fontStyle: 'italic' }}>
            ℹ️ {provenanceSubtext}
          </div>
        </div>

        {/* Ocean Vessel Telemetry Card (when domain is ocean) */}
        {event.domain === 'ocean' && (
          <div className="dossier-card" style={{ gridColumn: 'span 2' }}>
            <h4>Ocean Vessel & Telemetry Intelligence</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <div>
                <span className="dossier-label">Vessel ID / Identifier:</span>
                <div className="dossier-val font-mono font-semibold">{metadata.vessel_id || 'UNKNOWN_VESSEL'}</div>
              </div>
              <div>
                <span className="dossier-label">Vessel Type:</span>
                <div className="dossier-val font-semibold">{metadata.vessel_type || 'FISHING'}</div>
              </div>
              <div>
                <span className="dossier-label">Flag State:</span>
                <div className="dossier-val font-bold" style={{ color: '#38bdf8' }}>🏴 {metadata.flag || 'UNKNOWN'}</div>
              </div>
              <div>
                <span className="dossier-label">AIS Gap Duration:</span>
                <div className="dossier-val font-mono text-amber">
                  {metadata.ais_gap_hours ? `${metadata.ais_gap_hours} hrs` : (metadata.ais_disabled ? 'Gap Detected' : 'No Gap Reported')}
                </div>
              </div>
              <div>
                <span className="dossier-label">Loitering Pattern:</span>
                <div className="dossier-val">{metadata.loitering ? '🚨 Yes (Suspicious)' : 'No'}</div>
              </div>
              <div>
                <span className="dossier-label">Encounter / Transshipment:</span>
                <div className="dossier-val">{metadata.encounter ? '🚨 Yes (Detected)' : 'No'}</div>
              </div>
            </div>
          </div>
        )}

        {/* Classification & Threat */}
        <div className="dossier-card">
          <h4>Classification Refinement</h4>
          <div className="dossier-row">
            <span className="dossier-label">Refined Threat:</span>
            <span className="dossier-val font-semibold">{classification.refined_type}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Threat Category:</span>
            <span className="dossier-val">{classification.category}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Urgency:</span>
            <span className="dossier-val uppercase text-amber">{classification.urgency}</span>
          </div>
          <div className="dossier-reasons">
            {classification.reasons?.map((r, i) => (
              <div key={i} className="reason-item">• {r}</div>
            ))}
          </div>
        </div>

        {/* Verification & Sensor Corroboration */}
        <div className="dossier-card">
          <h4>Sensor Verification</h4>
          <div className="dossier-row">
            <span className="dossier-label">Trust Level:</span>
            <span className="dossier-val uppercase font-semibold">{verification.level}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Trust Score:</span>
            <span className="dossier-val font-mono">{verification.score?.toFixed(2)}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Raw Confidence:</span>
            <span className="dossier-val font-mono">{(event.confidence * 100)?.toFixed(0)}%</span>
          </div>
          <div className="dossier-reasons">
            {verification.reasons?.map((r, i) => (
              <div key={i} className="reason-item">• {r}</div>
            ))}
          </div>
        </div>

        {/* Localization & Spatial Context */}
        <div className="dossier-card">
          <h4>Geographic Localization & Sanctuary</h4>
          <div className="dossier-row">
            <span className="dossier-label">Coordinates:</span>
            <span className="dossier-val font-mono">
              {event.location?.lat?.toFixed(4) || localization.lat?.toFixed(4)}, {event.location?.lon?.toFixed(4) || localization.lon?.toFixed(4)}
            </span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Operational Sector:</span>
            <span className="dossier-val">{localization.sector_name}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Protected Area:</span>
            <span className="dossier-val text-emerald font-semibold">
              {metadata.protected_area_name || (metadata.protected_area ? 'Designated Sanctuary' : 'Outside Reserve')}
            </span>
          </div>
          {metadata.distance_to_boundary_km !== undefined && metadata.distance_to_boundary_km !== null && (
            <div className="dossier-row">
              <span className="dossier-label">Boundary Distance:</span>
              <span className="dossier-val font-mono">{metadata.distance_to_boundary_km} km ({metadata.boundary_source})</span>
            </div>
          )}
          <div className="dossier-reasons">
            {localization.reasons?.map((r, i) => (
              <div key={i} className="reason-item">• {r}</div>
            ))}
          </div>
        </div>

        {/* Spatial-Temporal Memory & Recurrence */}
        <div className="dossier-card">
          <h4>Spatial-Temporal Memory</h4>
          <div className="dossier-row">
            <span className="dossier-label">Historical Incidents:</span>
            <span className="dossier-val font-mono font-bold text-lg">
              {memory.historical_events || 0}
            </span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Recurrence Cluster:</span>
            <span className={`dossier-val font-semibold ${memory.recurrence_detected ? 'text-orange' : 'text-gray'}`}>
              {memory.recurrence_detected ? '🚨 RECURRENCE DETECTED (+24 Risk pts)' : 'Isolated Detection'}
            </span>
          </div>
          <div className="dossier-reasons">
            {memory.reasons?.map((r, i) => (
              <div key={i} className="reason-item">• {r}</div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Recommendation Card */}
      <div className="action-recommendation-card">
        <div className="action-header">
          <div>
            <span className="action-label">RECOMMENDED RESPONSE</span>
            <h3 className="action-name">{action.action}</h3>
          </div>
          <span className={`dispatch-pill ${action.dispatched ? 'dispatched' : 'pending'}`}>
            {action.dispatched ? '✓ DISPATCHED' : '○ PENDING CLEARANCE'}
          </span>
        </div>
        <p className="action-msg">{action.message}</p>
        <div className="action-context">
          {action.reasons?.map((r, i) => (
            <div key={i} className="reason-item">• {r}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
