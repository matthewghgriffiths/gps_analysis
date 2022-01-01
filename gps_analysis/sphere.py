
from typing import NamedTuple

import numpy as np 
from numpy import sin, cos, arctan2, sqrt, pi, radians

class LatLon(NamedTuple):
    latitude: float
    longitude: float 

_AVG_EARTH_RADIUS_KM = 6371.0088


def get_rad_coords(pos):
    try:
        lat, lon = pos.latitude, pos.longitude
        phi, lam = radians(lat), radians(lon)
    except AttributeError: 
        phi, lam = pos 
    return phi, lam


def haversine(pos1, pos2):
    phi1, lam1 = get_rad_coords(pos1)
    phi2, lam2 = get_rad_coords(pos2)
    sindphi = sin((phi2 - phi1)/2)**2
    sindlam = sin((lam2 - lam1)/2)**2
    a = sindphi + cos(phi1) * cos(phi2) * sindlam
    return 2 * arctan2(sqrt(a), sqrt(1 - a))


def haversine_km(pos1, pos2):
    theta = haversine(pos1, pos2)
    return theta * _AVG_EARTH_RADIUS_KM


def rad_bearing(pos1, pos2):
    phi1, lam1 = get_rad_coords(pos1)
    phi2, lam2 = get_rad_coords(pos2)

    y = sin(lam2 - lam1) * cos(phi2)
    x = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(lam2 - lam1)
    return arctan2(y, x)


def bearing(pos1, pos2):
    rad = rad_bearing(pos1, pos2)
    return (rad*180/pi + 360) % 360


def estimate_bearing(positions, pos, tol=0.01):
    dist = haversine_km(positions, pos)
    weights = np.exp( - np.square(dist / tol)/2)
    return np.average(positions.bearing % 180, weights=weights)