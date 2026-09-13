import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom SVG icon generator for Land vs Ocean events
function createCustomIcon(domain, riskLevel, isSelected) {
  const isLand = domain === 'land';
  const level = (riskLevel || 'LOW').toUpperCase();

  const colorMap = {
    LOW: '#10b981',
    MEDIUM: '#f59e0b',
    HIGH: '#f97316',
    CRITICAL: '#ef4444',
  };

  const color = colorMap[level] || '#3b82f6';
  const size = isSelected ? 42 : 34;

  const iconSvg = isLand
    ? `<svg xmlns="http://www.w3.org/2000/svg" width="${size - 12}" height="${size - 12}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2L3 9h3v10h12V9h3L12 2z"/>
        <path d="M12 12v6"/>
      </svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" width="${size - 12}" height="${size - 12}" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 21c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.5 0 2.5 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>
        <path d="M19.38 20A11.6 11.6 0 0 0 21 14l-9-4-9 4c0 2.9.94 5.34 2.81 7.12"/>
        <path d="M12 10V4"/>
        <path d="M8 7h8"/>
      </svg>`;

  const html = `
    <div style="
      width: ${size}px;
      height: ${size}px;
      background-color: ${color};
      border: ${isSelected ? '3px solid #ffffff' : '2px solid rgba(255,255,255,0.85)'};
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 ${isSelected ? '16px' : '8px'} ${color};
      cursor: pointer;
      transition: transform 0.2s ease;
    ">
      ${iconSvg}
    </div>
  `;

  return L.divIcon({
    className: 'custom-map-marker',
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

export default function MapView({ incidents = [], selectedIncident, onSelectIncident }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  // Initialize Leaflet Map once
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Create map centered on tropical/global view
      const map = L.map(mapContainerRef.current, {
        center: [5.0, 30.0],
        zoom: 3,
        zoomControl: true,
        minZoom: 2,
        maxZoom: 18,
      });

      // High-resolution satellite imagery (free, unwatermarked, high fidelity for land & ocean)
      const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics',
        maxZoom: 18,
      });

      const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      });

      // Default to satellite layer
      satellite.addTo(map);

      // Layer switcher control
      L.control.layers({
        '🛰️ Satellite': satellite,
        '🗺️ Street Map': streetMap,
      }, null, { position: 'topright' }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;

      // Force size recalculation after layout settles
      const invalidate = () => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      };
      setTimeout(invalidate, 100);
      setTimeout(invalidate, 400);
      setTimeout(invalidate, 1000);

      // Responsive observer: guarantees map fills container on window/layout resize
      let ro = null;
      if (window.ResizeObserver && mapContainerRef.current) {
        ro = new ResizeObserver(() => {
          invalidate();
        });
        ro.observe(mapContainerRef.current);
      }

      return () => {
        if (ro) ro.disconnect();
        if (mapInstanceRef.current) {
          mapInstanceRef.current.remove();
          mapInstanceRef.current = null;
        }
      };
    }
  }, []);

  // Update Markers when incidents or selectedIncident change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();
    const bounds = [];

    incidents.forEach((inc) => {
      const loc = inc.event?.location || inc.localization;
      if (!loc || loc.lat === undefined || loc.lon === undefined) return;

      const lat = parseFloat(loc.lat);
      const lon = parseFloat(loc.lon);
      bounds.push([lat, lon]);

      const isSelected = selectedIncident?.event?.id === inc.event?.id;
      const domain = inc.event?.domain || 'land';
      const riskLevel = inc.risk?.level || 'LOW';

      const icon = createCustomIcon(domain, riskLevel, isSelected);
      const marker = L.marker([lat, lon], { icon });

      const popupContent = `
        <div style="font-family: sans-serif; color: #111827; min-width: 180px;">
          <div style="font-weight: 700; font-size: 13px; text-transform: uppercase; color: #1f2937;">
            ${inc.event?.event_type || 'Incident'}
          </div>
          <div style="font-size: 11px; color: #6b7280; margin-bottom: 6px;">
            Domain: <strong>${domain.toUpperCase()}</strong> • Risk: <strong>${riskLevel}</strong>
          </div>
          <div style="font-size: 12px; margin-bottom: 8px;">
            Action: <strong>${inc.action?.action || 'MONITOR'}</strong>
          </div>
          <div style="font-size: 10px; color: #9ca3af;">
            Lat: ${lat.toFixed(4)}, Lon: ${lon.toFixed(4)}
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);

      marker.on('click', () => {
        if (onSelectIncident) {
          onSelectIncident(inc);
        }
      });

      marker.addTo(markersLayer);
    });

    // Auto fit bounds if multiple points exist and no specific selection
    if (bounds.length > 0 && !selectedIncident) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 6 });
    }
  }, [incidents, selectedIncident, onSelectIncident]);

  // Pan to selected incident smoothly
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedIncident) return;

    map.invalidateSize();
    const loc = selectedIncident.event?.location || selectedIncident.localization;
    if (loc && loc.lat !== undefined && loc.lon !== undefined) {
      map.flyTo([parseFloat(loc.lat), parseFloat(loc.lon)], Math.max(map.getZoom(), 8), {
        duration: 1.2,
      });
    }
  }, [selectedIncident]);

  return (
    <div className="map-wrapper">
      <div ref={mapContainerRef} className="map-container" />
      <div className="map-legend">
        <span className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#10b981' }} /> Land Detection
        </span>
        <span className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#06b6d4' }} /> Marine AIS Vessel
        </span>
        <span className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#ef4444' }} /> High/Critical Threat
        </span>
      </div>
    </div>
  );
}
