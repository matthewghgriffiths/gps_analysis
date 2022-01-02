
from typing import NamedTuple

import numpy as np 
from numpy import sin, cos, arcsin, arccos, arctan2, sqrt, pi, radians

class LatLon(NamedTuple):
    latitude: float
    longitude: float 

class LatLonBear(NamedTuple):
    latitude: float
    longitude: float 
    bearing: float

class RadCoords(NamedTuple):
    phi: float
    lam: float 

class RadBearing(NamedTuple):
    phi: float
    lam: float 
    theta: float 

def cross(a, b):
    a1, a2, a3 = a 
    b1, b2, b3 = b 
    return Vector(a2 * b3 - a3 * b2, a3 * b1  - a1 * b3, a1 * b2 - a2 * b1)

class Vector(NamedTuple):
    x: float 
    y: float
    z: float

    cross = cross # type: ignore

_AVG_EARTH_RADIUS_KM = 6371.0088


def get_rad_coords(pos):
    try:
        lat, lon = pos.latitude, pos.longitude
        phi, lam = radians(lat), radians(lon)
    except AttributeError: 
        try: 
            phi, lam = pos.phi, pos.lam
        except AttributeError: 
            phi, lam = pos 
            
    return RadCoords(phi, lam)

def get_rad_bearing(pos):
    try:
        lat, lon, bearing = pos.latitude, pos.longitude, pos.bearing
        phi, lam, bearing = radians(lat), radians(lon), radians(bearing)
    except AttributeError: 
        try: 
            phi, lam, bearing = pos.phi, pos.lam, pos.theta
        except AttributeError: 
            phi, lam, bearing = pos 

    return RadBearing(phi, lam, bearing)

def to_n_vector(pos):
    phi, lam = get_rad_coords(pos)
    cosp = cos(phi)
    return Vector(cosp * cos(lam), cosp * sin(lam), sin(phi))

def from_n_vector(vec):
    x, y, z = vec 
    phi = arctan2(z, np.sqrt(x**2 + y**2))
    lam = arctan2(y, x)
    return RadCoords(phi, lam)

def to_axis(pos):
    phi, lam, theta = get_rad_bearing(pos)
    sinp = sin(phi)
    cosp = cos(phi)
    sinl = sin(lam)
    cosl = cos(lam)
    sint = sin(theta)
    cost = cos(theta)
    x = sinl * cost - sinp * cosl * sint
    y = - cosl * cost - sinp * sinl * sint
    z = cosp * sint 
    return Vector(x, y, z)

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


def path_intersections(pos1, pos2):
    gc1s = to_axis(pos1)
    gc2s = to_axis(pos2)
    intersections = cross(gc1s, gc2s)
    return from_n_vector(intersections)