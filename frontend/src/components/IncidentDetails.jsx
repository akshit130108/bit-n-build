import React, { useState } from 'react';
import RiskBadge from './RiskBadge';

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
  const isWaiting = human_gate.status === 'WAITING_FOR_APPROVAL';
  const isApproved = human_gate.status === 'APPROVED' || human_gate.status === 'AUTO_APPROVED';
  const isRejected = human_gate.status === 'REJECTED';

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
          <div className="details-id-row">
            <span className="event-id">{eventId}</span>
            <span className={`domain-badge ${event.domain}`}>
              {event.domain?.toUpperCase()}
            </span>
          </div>
          <h2 className="details-title">{classification.refined_type || event.event_type}</h2>
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

      {/* Dossier Grid */}
      <div className="dossier-grid">
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
          <h4>Geographic Localization</h4>
          <div className="dossier-row">
            <span className="dossier-label">Coordinates:</span>
            <span className="dossier-val font-mono">
              {localization.lat?.toFixed(4)}, {localization.lon?.toFixed(4)}
            </span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Operational Sector:</span>
            <span className="dossier-val">{localization.sector_name}</span>
          </div>
          <div className="dossier-row">
            <span className="dossier-label">Uncertainty Radius:</span>
            <span className="dossier-val font-mono">±{Math.round(localization.radius_meters || 0)}m</span>
          </div>
          {event.metadata?.protected_area && (
            <div className="dossier-row">
              <span className="dossier-label">Protected Area:</span>
              <span className="dossier-val text-emerald font-semibold">
                {event.metadata?.protected_area_name || 'Designated Sanctuary'}
              </span>
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
