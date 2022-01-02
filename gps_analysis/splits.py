
import numpy as np
import pandas as pd

from . import geodesy
from .utils import strfmtsplit


_STANDARD_DISTANCES = {
    '250m': 0.25, 
    '500m': 0.5,
    '1km': 1,
    '1.5km': 1.5,
    '2km': 2,
    '3km': 3,
    '5km': 5,
    '7km': 7, 
    '10km': 10, 
}


def find_all_crossing_times(positions, locations, thresh=0.1):
    return pd.concat({
        loc: find_crossing_times(positions, pos)
        for loc, pos in locations.iterrows()
    },
        names = ['location', 'distance']
    ).sort_index(level=1)


def get_location_timings(positions, locations, thresh=0.1):
    loc_times = find_all_crossing_times(positions, locations, thresh=thresh)
    times = loc_times.values
    loc_timings = pd.DataFrame(
        times[None, :] - times[:, None],
        index=loc_times.index, 
        columns=loc_times.index
    )
    distances = loc_times.index.get_level_values(1)
    dist_diffs = 2 * (distances.values[None, :] - distances.values[:, None])
    dist_diffs[np.triu_indices(len(distances))] = 1

    loc_timings /= dist_diffs

    return loc_timings


def find_crossing_times(positions, loc, thresh=0.05):
    close_points = geodesy.haversine_km(positions, loc) < thresh

    close_positions = positions[close_points].copy()
    close_positions.bearing = loc.bearing + 90

    intersections = pd.DataFrame.from_dict(
        geodesy.path_intersections(close_positions, loc)._asdict()
    )
    bearings = geodesy.bearing(intersections, loc)
    sgns = np.sign(np.cos(np.radians(bearings - loc.bearing)))
    if not sgns.size:
        return pd.Series([])

    crossings = bearings.index[sgns != sgns.shift(fill_value=sgns.iloc[0])]
        
    def weight(*ds):
        return ds[0] / sum(ds)

    crossing_weights = pd.Series([
        weight(*geodesy.haversine(intersections.loc[i:i+2], loc))
        for i in crossings
    ], 
        index=crossings
    )

    time_deltas = (
        positions.time[crossings + 1].values - positions.time[crossings].values
    )
    crossing_times = (
        positions.time[crossings] + time_deltas * crossing_weights 
    )
    distance_deltas = (
        positions.distance[crossings + 1].values 
        - positions.distance[crossings].values
    )
    crossing_distances = (
        positions.distance[crossings] + distance_deltas * crossing_weights 
    )
    crossing_times.index = crossing_distances.round(3)
    crossing_times.index.name = 'distance'


    return crossing_times


def find_best_times(positions, distance):
    total_distance = positions.distance.iloc[-1]
    time_elapsed = positions.timeElapsed.dt.total_seconds()
    sel = positions.distance + distance < total_distance
    distances = positions.distance[sel]
    end_distances = distances + distance

    dist_elapsed = np.interp(
        end_distances, positions.distance, time_elapsed    
    )

    dist_times = dist_elapsed - time_elapsed[sel] 
    best_ordering = dist_times.argsort().values

    best = []
    unblocked = np.ones_like(best_ordering, dtype=bool)
    while unblocked.any():
        next_best = best_ordering[unblocked[best_ordering]][0]
        best.append(next_best)
        i0 = end_distances.searchsorted(distances[next_best])
        i1 = distances.searchsorted(end_distances[next_best])
        unblocked[i0:i1] = False
    
    best_times = pd.to_timedelta(dist_times[best], 'S')
    best_timesplits = pd.DataFrame.from_dict({
        'time': best_times,
        'split': best_times / distance / 2
    })
    best_timesplits.index = distances[best].round(3)
    return best_timesplits


def find_all_best_times(positions, distances=None):
    distances = distances or _STANDARD_DISTANCES
    return pd.concat({
        name: find_best_times(positions, distance)
        for name, distance in distances.items()
    },
        names = ('length', 'distance'),
    )