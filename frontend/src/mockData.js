// EcoSentinel High-Fidelity Mock Pipeline Data for Offline / Fallback Demo Mode
export function createMockLandIncident() {
  const id = 'evt_land_' + Math.random().toString(36).substring(2, 9);
  return {
    event: {
      id,
      domain: 'land',
      event_type: 'chainsaw',
      confidence: 0.93,
      sensor_id: 'S07-ACOUSTIC',
      timestamp: new Date().toISOString(),
      location: { lat: 11.83 + (Math.random() - 0.5) * 0.05, lon: 76.12 + (Math.random() - 0.5) * 0.05 },
      metadata: { protected_area: true, snr_db: 19.4, nearby_confirmations: 2, acoustic_signature: 'two_stroke_engine' }
    },
    classification: {
      refined_type: 'chainsaw',
      domain: 'land',
      is_high_risk: true,
      rationale: 'High-frequency acoustic signature matches illegal logging equipment.'
    },
    verification: {
      verified: true,
      confidence_score: 0.95,
      evidence: ['Corroborated by node S08 (18.2 dB SNR)', 'Audio frequency spectrum 2.45 kHz harmonic match']
    },
    localization: {
      lat: 11.832,
      lon: 76.125,
      radius_meters: 140,
      region_name: 'Bandipur Forest Corridor (Sector-4)'
    },
    memory: {
      historical_matches_count: 2,
      recurrence_detected: true,
      pattern_summary: '2 similar logging acoustic incidents recorded within 15 km in the last 48 hours.'
    },
    risk: {
      score: 88,
      level: 'HIGH',
      factors: ['Illegal logging in core buffer zone', 'Rapid recurrence cluster', 'High acoustic confidence']
    },
    human_gate: {
      status: 'WAITING_FOR_APPROVAL',
      required: true,
      reviewer: null,
      notes: 'Requires ranger supervisor authorization before motorized patrol unit dispatch.'
    },
    action: {
      recommended_action: 'DISPATCH_ANTI_LOGGING_PATROL',
      status: 'PENDING_APPROVAL',
      rationale: 'Rapid intervention required to intercept mechanized deforestation equipment.'
    },
    pipeline_trajectory: [
      { stage: '1. Ingestion', status: 'COMPLETED', detail: 'Acoustic sensor S07 captured 93% confidence chainsaw audio.' },
      { stage: '2. Classification', status: 'COMPLETED', detail: 'Refined to illegal forestry threat (Land Domain).' },
      { stage: '3. Verification', status: 'COMPLETED', detail: 'Acoustic cross-validation confirmed by adjacent node S08.' },
      { stage: '4. Localization', status: 'COMPLETED', detail: 'Triangulated to Bandipur Forest Corridor (Radius: 140m).' },
      { stage: '5. Spatial Memory', status: 'COMPLETED', detail: 'Historical cluster match: 2 previous events in Sector-4.' },
      { stage: '6. Risk Engine', status: 'COMPLETED', detail: 'Risk escalated to HIGH (88/100) due to recurrence.' },
      { stage: '7. Human Gate', status: 'ACTIVE', detail: 'Awaiting supervisor sign-off for dispatch.' },
      { stage: '8. Action Dispatch', status: 'PENDING', detail: 'Anti-logging patrol team placed on tactical standby.' }
    ]
  };
}

export function createMockOceanIncident() {
  const id = 'evt_ocean_' + Math.random().toString(36).substring(2, 9);
  return {
    event: {
      id,
      domain: 'ocean',
      event_type: 'suspicious_vessel',
      confidence: 0.91,
      sensor_id: 'GFW-AIS-TRACKER',
      timestamp: new Date().toISOString(),
      location: { lat: -0.45 + (Math.random() - 0.5) * 0.08, lon: -90.65 + (Math.random() - 0.5) * 0.08 },
      metadata: { ais_disabled: true, loitering_detected: true, protected_area: true, vessel_mmsi: '412389104' }
    },
    classification: {
      refined_type: 'dark_vessel_loitering',
      domain: 'ocean',
      is_high_risk: true,
      rationale: 'Commercial fishing trawler went dark (AIS gap 14h) inside Marine Protected Area.'
    },
    verification: {
      verified: true,
      confidence_score: 0.92,
      evidence: ['AIS transponder disabled for >12 hours', 'Synthetic Aperture Radar (SAR) detection confirms vessel presence']
    },
    localization: {
      lat: -0.452,
      lon: -90.655,
      radius_meters: 650,
      region_name: 'Galapagos Marine Sanctuary (Zone Bravo)'
    },
    memory: {
      historical_matches_count: 1,
      recurrence_detected: false,
      pattern_summary: 'Previous transponder gap flagged 3 weeks ago along MPA perimeter.'
    },
    risk: {
      score: 92,
      level: 'CRITICAL',
      factors: ['Illegal dark vessel inside sanctuary boundary', 'Potential longline poaching', 'Transponder tampering']
    },
    human_gate: {
      status: 'WAITING_FOR_APPROVAL',
      required: true,
      reviewer: null,
      notes: 'Requires naval coast guard liaison sign-off for interception intercept.'
    },
    action: {
      recommended_action: 'SCRAMBLE_MARITIME_PATROL_CUTTER',
      status: 'PENDING_APPROVAL',
      rationale: 'Intercept dark trawler before catch retrieval in protected nursery waters.'
    },
    pipeline_trajectory: [
      { stage: '1. Ingestion', status: 'COMPLETED', detail: 'GFW AIS ingest detected transponder blackout from MMSI 412389104.' },
      { stage: '2. Classification', status: 'COMPLETED', detail: 'Classified as illegal dark vessel loitering in sanctuary waters.' },
      { stage: '3. Verification', status: 'COMPLETED', detail: 'SAR satellite radar corroborated physical vessel position.' },
      { stage: '4. Localization', status: 'COMPLETED', detail: 'Fixed to Galapagos Marine Reserve Zone Bravo.' },
      { stage: '5. Spatial Memory', status: 'COMPLETED', detail: 'Flagged vessel has prior perimeter violations.' },
      { stage: '6. Risk Engine', status: 'COMPLETED', detail: 'Surged to CRITICAL (92/100) due to no-take zone intrusion.' },
      { stage: '7. Human Gate', status: 'ACTIVE', detail: 'Awaiting Coast Guard liaison authorization.' },
      { stage: '8. Action Dispatch', status: 'PENDING', detail: 'Fast response cutter primed for interception.' }
    ]
  };
}

export function createInitialDemoIncidents() {
  return [createMockOceanIncident(), createMockLandIncident()];
}