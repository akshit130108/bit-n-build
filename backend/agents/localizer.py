from schemas.event import LocalizationResult, NormalizedEvent


def localize_event(event: NormalizedEvent) -> LocalizationResult:
    """
    Localization Agent: Resolves geographical coordinates, accuracy radius,
    and assigned sector for spatial tracking and memory clustering.
    """
    meta = event.metadata or {}
    sensor_locs = meta.get("multi_sensor_locations")
    reasons = []

    # Check if multiple reporting sensors provide coordinate sets
    if sensor_locs and isinstance(sensor_locs, list) and len(sensor_locs) > 1:
        avg_lat = sum(p["lat"] for p in sensor_locs) / len(sensor_locs)
        avg_lon = sum(p["lon"] for p in sensor_locs) / len(sensor_locs)
        lat = round(avg_lat, 6)
        lon = round(avg_lon, 6)
        radius = 120.0  # Tight centroid radius
        loc_conf = 0.92
        reasons.append(f"Estimated centroid from {len(sensor_locs)} cooperating sensor locations")
    else:
        lat = event.location.lat
        lon = event.location.lon
        # Use sensor precision or standard default radius
        radius = meta.get("accuracy_radius_meters", 250.0)
        loc_conf = 0.85
        reasons.append(f"Direct coordinates from sensor {event.sensor_id}")

    sector_name = meta.get("cluster_sector") or meta.get("sector") or f"Sector-{abs(int(lat * 10)) % 100}"
    reasons.append(f"Mapped to operational zone '{sector_name}' (approx. +/-{int(radius)}m precision)")

    return LocalizationResult(
        lat=lat,
        lon=lon,
        confidence=loc_conf,
        radius_meters=radius,
        sector_name=sector_name,
        reasons=reasons,
    )
