
import os 
import sys
import getpass
import logging
from datetime import datetime
from typing import Optional 
from io import BytesIO
import argparse


import pandas as pd
import gpxpy
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

from .utils import (
    map_concurrent, unflatten_json, strfsplit, 
    add_logging_argument, set_logging
)
from .files import parse_gpx_data, read_fit_zipfile
from . import splits


logger = logging.getLogger(__name__)

_API: Optional[Garmin] = None

_ACTIVITY_TYPES = {
    'cycling': {
        "activityType": "cycling",
    },
    'running': {
        "activityType": "running",
    },
    'rowing': {
        "activityType": "other",
        'activitySubType': 'rowing'
    }
}

def get_api(api=None):
    return api or _API or login()

def login(email_address=None, password=None, max_retries=5):
    if email_address is None:
        print("please input your Garmin email address: ")
        email_address = input()
    if password is None:
        password = getpass.getpass('Input your Garmin password: ')

    for i in range(max_retries):
        try:
            # API
            ## Initialize Garmin api with your credentials
            api = Garmin(email_address, password)
            api.login()
            global _API
            _API = api 
            break
        except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
        ) as err:
            logging.error("Error occurred during Garmin Connect communication: %s", err)
    else:
        raise err

    return api


def download_activity(activity_id, path=None, api=None):
    api = get_api(api)

    gpx_data = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.GPX)
    path = path or f"./{str(activity_id)}.gpx"
    with open(path, "wb") as fb:
        fb.write(gpx_data)

    return path


def download_activities(activities, folder='./', max_workers=4, api=None, show_progress=True):
    api = get_api(api)

    activity_ids = (act["activityId"] for act in activities)
    inputs = {
        act_id: (act_id, os.path.join(folder, f"{str(act_id)}.gpx"), api)
        for act_id in activity_ids
    }
    return map_concurrent(
        download_activity, inputs, 
        threaded=True, max_workers=max_workers, 
        show_progress=show_progress, raise_on_err=False
    )

def load_activity(activity_id, api=None):
    api = get_api(api)

    f = api.download_activity(
        activity_id, dl_fmt=api.ActivityDownloadFormat.GPX)
    return parse_gpx_data(gpxpy.parse(f))

def load_activities(activity_ids, max_workers=4, api=None, show_progress=True):
    api = get_api(api)
    inputs = {
        act_id: (act_id, api) for act_id in activity_ids
    }
    return map_concurrent(
        load_activity, inputs, 
        threaded=True, max_workers=max_workers, 
        show_progress=show_progress, raise_on_err=False
    )


def load_fit_activity(activity_id, api=None):
    api = get_api(api)

    zip_data = api.download_activity(
        activity_id, dl_fmt=api.ActivityDownloadFormat.ORIGINAL)
    return read_fit_zipfile(BytesIO(zip_data))

def load_fit_activities(activity_ids, max_workers=4, api=None, show_progress=True):
    api = get_api(api)
    inputs = {
        act_id: (act_id, api) for act_id in activity_ids
    }
    return map_concurrent(
        load_fit_activity, inputs, 
        threaded=True, max_workers=max_workers, 
        show_progress=show_progress, raise_on_err=False
    )

def get_activities(start=0, limit=20, *, api=None, activityType=None, startDate=None, endDate=None, minDistance=None, maxDistance=None, **params):
    if activityType:
        if activityType in _ACTIVITY_TYPES:
            params.update(_ACTIVITY_TYPES[activityType])
        else:
            params['activityType'] = activityType

    if startDate:
        if isinstance(startDate, datetime):
            startDate = startDate.strftime("%Y-%M-%d")
        params['startDate'] = startDate

    if endDate:
        if isinstance(endDate, datetime):
            endDate = endDate.strftime("%Y-%M-%d")
        params['endDate'] = endDate
    
    if minDistance: params['minDistance'] = str(minDistance)
    if maxDistance: params['maxDistance'] = str(maxDistance)

    return activities_to_dataframe(
        _get_activities(start=start, limit=limit, api=api, **params)
    )


def _get_activities(start=0, limit=20, *, api=None, **params):
    api = get_api(api)
    url = api.garmin_connect_activities
    params['start'] = start 
    params['limit'] = limit 

    return api.modern_rest_client.get(url, params=params).json()
    

def activities_to_dataframe(activities):
    df = pd.DataFrame.from_records(
        [dict(unflatten_json(act)) for act in activities]
    )
    depth = max(map(len, df.columns))
    df.columns = pd.MultiIndex.from_tuples([
        k + ('',) * (depth - len(k)) for k in df.columns
    ])
    return df


def activity_data_to_excel(
        activities, activity_data=None, locations=None, 
        xlpath='garmin_data.xlsx', api=None, max_workers=4, 
        show_progress=True
):
    if activity_data is None:
        activity_data, _ = load_activities(
            activities.activityId, max_workers=max_workers, 
            show_progress=show_progress, api=api)

    activity_td = activities[
        ['activityId', 'startTimeLocal', 'distance']
    ].sort_values(by='startTimeLocal', ascending=False)
    activity_td.columns = ['activityId', 'startTime', 'totalDistance']

    # reorder activity_data
    activity_data = {i: activity_data[i] for i in activity_td.activityId}

    activity_td.totalDistance = (activity_td.totalDistance/1000).round(1)

    activity_best_times = pd.concat({
        actid: splits.find_all_best_times(data)
        for actid, data in activity_data.items() if not data.empty
    }, 
        names = ('activityId', 'length', 'distance')
    )

    best_times = activity_best_times.reset_index().join(
        activity_td.set_index('activityId'), on='activityId').set_index(
        ['activityId', 'startTime', 'totalDistance', 'length', 'distance']
    )

    sheet_names = pd.Series(
        activities.startTimeLocal.str.split(" ", expand=True)[0].str.cat(
            activities.activityId.astype(str), sep="_"
        ).values,
        index = activities.activityId
    )
    location_timings = {
        actid: splits.get_location_timings(data, locations)
        for actid, data in activity_data.items() if not data.empty
    }

    with pd.ExcelWriter(xlpath) as xlf:
        activities.set_index('activityId').to_excel(xlf, "activities")
        best_times.applymap(strfsplit).to_excel(xlf, "best_times")
        for actid, timings in location_timings.items():
            timings.applymap(strfsplit).to_excel(
                xlf, sheet_names.loc[actid])


def get_parser():
    def date(s):
        return datetime.strptime(s, '%Y-%m-%d')

    parser = argparse.ArgumentParser(
        description='Analyse recent gps data')
    parser.add_argument(
        'n', 
        type=int, default=5, nargs='?',
        help='maximum number of activities to load')
    parser.add_argument(
        'outfile', 
        type=str, default='garmin.xlsx', nargs='?', 
        help='path of output excel spreadsheet'
    )
    parser.add_argument(
        '-u', '--user', '--email',
        type=str, nargs='?',
        help='Email address to use'
    )
    parser.add_argument(
        '-p', '--password',
        type=str, nargs='?',
        help='Password'
    )
    parser.add_argument(
        '-a', '--activity', 
        type=str, nargs='?',
        help='activity type, options: rowing, cycling, running'
    )
    parser.add_argument(
        '--min-distance',
        type=int, nargs='?',
        help='minimum distance of activity (in km)'
    )
    parser.add_argument(
        '--max-distance',
        type=int, nargs='?',
        help='maximum distance of activity (in km)'
    )
    parser.add_argument(
        '--start-date',
        type=date,
        help='start date to search for activities from in YYYY-MM-DD format'
    )
    parser.add_argument(
        '--end-date',
        type=date,
        help='start date to search for activities from in YYYY-MM-DD format'
    )
    add_logging_argument(parser)
    return parser


def parse_args(args):
    return get_parser().parse_args(args)


def run(args=None):
    options = parse_args(args)
    set_logging(options)

    api = login(options.user, options.password)

    activities = get_activities(
        0, options.n, 
        activityType=options.activity, 
        minDistance=options.min_distance, 
        maxDistance=options.max_distance, 
        startDate=options.start_date, 
        endDate=options.end_date,
        api=api
    )
    activity_data, errors = load_activities(
        activities.activityId,
        api=api
    )

    activity_data_to_excel(
        activities, activity_data, 
        xlpath=options.outfile)


def main():
    run(sys.argv[1:])
    input("Press enter to finish")

if __name__ == "__main__":
    main()