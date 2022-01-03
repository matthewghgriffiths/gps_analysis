

import zipfile

import gpxpy
import fitparse
import pandas as pd
import numpy as np

from . import geodesy

_SEMICIRCLE_SCALE = 180 / 2**31

def read_gpx(filename):
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
    last = positions.index[-1]
    positions['timeElapsed'] = positions.time - positions.time[0]
    positions['distanceDelta'] = geodesy.haversine_km(positions, positions.shift(-1))
    positions.loc[last, 'distanceDelta'] = 0
    positions['distance'] = np.cumsum(positions.distanceDelta)
    positions['bearing_r'] = geodesy.rad_bearing(positions, positions.shift(-1))
    positions.loc[0, 'bearing_r'] = positions.bearing_r[1]
    positions['bearing'] = np.rad2deg(positions.bearing_r)

    return positions


def read_fit_zipfile(zip_file):
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        fit_file, = (f for f in zipf.filelist if f.filename.endswith("fit"))
        return read_fit_file(fit_file, zipf.open)


def read_fit_file(fit_file, open=open):
    with open(fit_file) as f:
        return parse_fit_data(fitparse.FitFile(f))


def parse_fit_data(fit_data):
    positions = pd.DataFrame.from_records(
        {f.name: f.value for f in record.fields}
        for record in fit_data.get_messages("record")
    ).dropna(subset=['position_lat', 'position_long'])\
        .reset_index(drop=True)\
        .rename(columns={'timestamp': 'time'})

    last = positions.index[-1]

    positions['distance'] /= 1000
    positions['latitude'] = positions.position_lat * _SEMICIRCLE_SCALE
    positions['longitude'] = positions.position_long * _SEMICIRCLE_SCALE

    positions['timeElapsed'] = positions.time - positions.time[0]
    positions['distanceDelta'] = - positions.distance.diff(-1)
    positions.loc[last, 'distanceDelta'] = 0

    positions['bearing_r'] = geodesy.rad_bearing(positions, positions.shift(-1))
    positions.loc[last, 'bearing_r'] = positions.bearing_r[1]
    positions['bearing'] = np.rad2deg(positions.bearing_r)

    return positions

