

import gpxpy
import pandas as pd
import numpy as np

from . import sphere



def load_gpx(filename):
    with open(filename, 'r') as f:
        gpx_data = gpxpy.parse(f)

    return parse_gpx_data(gpx_data)

def parse_gpx_data(gpx_data):
    positions = pd.DataFrame.from_records(
        {
            'latitude': point.latitude, 
            'longitude': point.longitude, 
            'time': point.time
        } 
        for track in gpx_data.tracks 
        for segment in track.segments 
        for point in segment.points
    )
    positions['timeElapsed'] = positions.time - positions.time[0]
    positions['distanceDelta'] = sphere.haversine_km(positions, positions.shift())
    positions.loc[0, 'distanceDelta'] = 0
    positions['distance'] = np.cumsum(positions.distanceDelta)
    positions['bearing_r'] = sphere.rad_bearing(positions, positions.shift())
    positions.loc[0, 'bearing_r'] = positions.bearing_r[1]
    positions['bearing'] = np.rad2deg(positions.bearing_r)

    return positions