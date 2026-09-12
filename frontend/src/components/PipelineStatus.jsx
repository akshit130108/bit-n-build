import React from 'react';

export default function PipelineStatus({ incident }) {
  if (!incident) {
    return (
      <div className="pipeline-empty">
        <p>Select an incident to view its 8-stage agentic reasoning trajectory.</p>
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

  // Determine stage status
  const gateStatus = human_gate.status || 'PENDING';
  const isWaitingApproval = gateStatus === 'WAITING_FOR_APPROVAL';
  const isApproved = gateStatus === 'APPROVED' || gateStatus === 'AUTO_APPROVED';
  const isRejected = gateStatus === 'REJECTED';
  const isEvidenceRequested = gateStatus === 'REQUEST_MORE_EVIDENCE';

  const stages = [
    {
      id: 1,
      name: 'Detection',
      status: 'completed',
      badge: event.domain?.toUpperCase() || 'DOMAIN',
      summary: `${event.event_type || 'Unknown'} (${Math.round((event.confidence || 0) * 100)}% raw confidence)`,
      detail: `Sensor ${event.sensor_id || 'N/A'} • ${event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'N/A'}`,
    },
    {
      id: 2,
      name: 'Classification',
      status: 'completed',
      badge: classification.category || 'TERRESTRIAL',
      summary: classification.refined_type || 'Refining signature...',
      detail: classification.reasons?.[0] || 'Domain-agnostic threat refinement',
    },
    {
      id: 3,
      name: 'Verification',
      status: 'completed',
      badge: `${verification.level?.toUpperCase() || 'EVAL'} (${Math.round((verification.score || 0) * 100)}%)`,
      summary: verification.reasons?.[1] || verification.reasons?.[0] || 'Signal corroborated',
      detail: verification.reasons?.slice(0, 2).join(' • ') || 'Evidence evaluation complete',
    },
    {
      id: 4,
      name: 'Localization',
      status: 'completed',
      badge: localization.sector_name || 'ZONE',
      summary: `${localization.lat?.toFixed(4)}, ${localization.lon?.toFixed(4)} (±${Math.round(localization.radius_meters || 0)}m)`,
      detail: localization.reasons?.[0] || 'Spatial coordinates resolved',
    },
    {
      id: 5,
      name: 'Memory',
      status: 'completed',
      badge: memory.recurrence_detected ? 'RECURRENCE SPIKE' : 'ISOLATED',
      summary: `${memory.historical_events || 0} historical incident(s) in sector (48h window)`,
      detail: memory.reasons?.[0] || 'Spatial-temporal memory checked',
      highlight: memory.recurrence_detected,
    },
    {
      id: 6,
      name: 'Risk',
      status: 'completed',
      badge: `${risk.score || 0}/100 ${risk.level || ''}`,
      summary: risk.reasons?.[0] || 'Multi-factor risk computed',
      detail: `Base: ${risk.factors?.base_threat || 0} | Evidence: ${risk.factors?.evidence_score || 0} | Recurrence: ${risk.factors?.historical_recurrence || 0}`,
    },
    {
      id: 7,
      name: 'Human Gate',
      status: isWaitingApproval ? 'waiting' : (isApproved ? 'completed' : 'waiting'),
      badge: gateStatus,
      summary: isWaitingApproval
        ? '⏳ Human operator approval required'
        : isApproved
        ? '✓ Clearance authorized for dispatch'
        : isRejected
        ? '✕ Response dismissed by operator'
        : isEvidenceRequested
        ? '⏳ Awaiting secondary sensor evidence'
        : 'Passive monitoring approved',
      detail: human_gate.reasons?.[0] || 'Safety policy check',
    },
    {
      id: 8,
      name: 'Action',
      status: action.dispatched ? 'completed' : (isWaitingApproval ? 'pending' : 'completed'),
      badge: action.action || 'MONITORING',
      summary: action.action || 'Action recommendation',
      detail: action.dispatched
        ? `✓ DISPATCHED: ${action.message || ''}`
        : `○ PENDING APPROVAL: ${action.message || ''}`,
    },
  ];

  return (
    <div className="pipeline-container">
      <div className="pipeline-header">
        <h4>Agentic Reasoning Pipeline (8 Stages)</h4>
        <span className="pipeline-indicator">
          {isWaitingApproval ? '⚠️ Action Held at Gate' : '✓ Pipeline Resolved'}
        </span>
      </div>

      <div className="pipeline-steps">
        {stages.map((st, idx) => (
          <div
            key={st.id}
            className={`pipeline-step ${st.status} ${st.highlight ? 'step-highlight' : ''}`}
          >
            <div className="step-rail">
              <div className="step-node">
                {st.status === 'completed' && '✓'}
                {st.status === 'waiting' && '⏳'}
                {st.status === 'pending' && '○'}
              </div>
              {idx < stages.length - 1 && <div className="step-connector" />}
            </div>

            <div className="step-content">
              <div className="step-meta">
                <span className="step-name">{st.id}. {st.name}</span>
                <span className="step-badge">{st.badge}</span>
              </div>
              <div className="step-summary">{st.summary}</div>
              <div className="step-detail">{st.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
