"""Reusable geospatial helpers - real point-to-point distance (Haversine,
never naive lat/lon subtraction) plus approximate reference coordinates for
the app's existing serviced blocks, so the hyper-local radius schematic on
the frontend has real coordinates to draw from.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a)), 3)


# Approximate town-centre coordinates for each serviced block - general
# public geographic knowledge (not a per-user GPS pin, and not surveyed to
# sub-block precision). Used only to draw the 5km/10km radius schematic;
# every population/competitor figure in city_data.py is already a
# block-level aggregate rather than something computed from these
# coordinates, so this never overstates precision beyond what the
# underlying data actually supports.
BLOCK_CENTROIDS: dict[str, tuple[float, float]] = {
    "Latur": (18.4088, 76.5604),
    "Ausa": (18.2500, 76.5000),
    "Nilanga": (18.1167, 76.7500),
    "Renapur": (18.5333, 76.6167),
    "Chakur": (18.5833, 76.8000),
    "Biswan": (27.4975, 80.9975),
    "Mahmoodabad": (27.3167, 81.1167),
    "Sidhauli": (27.2833, 80.8333),
    "Laharpur": (27.7167, 80.9000),
    "Machhrehta": (27.5667, 80.6500),
    "Sanwer": (22.9833, 75.9167),
    "Depalpur": (22.8500, 75.5500),
    "Mhow": (22.5500, 75.7667),
    "Hatod": (22.8167, 75.7167),
    "Rau": (22.6333, 75.7833),
}


def get_block_centroid(block_name: str) -> tuple[float, float] | None:
    return BLOCK_CENTROIDS.get(block_name)
