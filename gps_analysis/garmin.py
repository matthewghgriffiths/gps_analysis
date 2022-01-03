
import os 
import getpass
import logging
from datetime import datetime
from typing import Optional 
from io import BytesIO

import pandas as pd
import gpxpy
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

from .utils import map_concurrent, unflatten_json, strfsplit
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

def login(email_address=None, password=None):
    if email_address is None:
        print("please input your Garmin email address: ")
        email_address = input()
    if password is None:
        password = getpass.getpass('Input your Garmin password: ')

    try:
        # API
        ## Initialize Garmin api with your credentials
        api = Garmin(email_address, password)
        api.login()
        global _API
        _API = api 
    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
        logging.error("Error occurred during Garmin Connect communication: %s", err)

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
        activities, activity_data=None, xlpath='garmin_data.xlsx', 
        api=None, max_workers=4, show_progress=True
):
    if activity_data is None:
        activity_data, _ = load_activities(
            activities.activityId, max_workers=max_workers, 
            show_progress=show_progress, api=api)

    activity_td = activities[
        ['activityId', 'startTimeLocal', 'distance']
    ].sort_values(by='startTimeLocal', ascending=False)
    activity_td.columns = ['activityId', 'startTime', 'totalDistance']

    activity_td.totalDistance = (activity_td.totalDistance/1000).round(1)

    activity_best_times = pd.concat({
        actid: splits.find_all_best_times(activity_data[actid])
        for actid in activity_td.activityId
    }, 
        names = ('activityId', 'length', 'distance')
    )

    best_times = activity_best_times.reset_index().join(
        activity_td.set_index('activityId'), on='activityId').set_index(
        ['activityId', 'startTime', 'totalDistance', 'length', 'distance']
    )
    with pd.ExcelWriter(xlpath) as xlf:
        activities.set_index('activityId').to_excel(xlf, "activities")
        best_times.applymap(strfsplit).to_excel(xlf, "best_times")