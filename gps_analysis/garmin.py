
import os 
import getpass
import logging
from typing import Optional 

from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

from .utils import map_concurrent


logger = logging.getLogger(__name__)

_API: Optional[Garmin] = None

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
    api = api or _API

    gpx_data = api.download_activity(activity_id, dl_fmt=api.ActivityDownloadFormat.GPX)
    path = path or f"./{str(activity_id)}.gpx"
    with open(path, "wb") as fb:
        fb.write(gpx_data)

    return path


def download_activities(activities, folder='./', max_workers=4, api=None, show_progress=True):
    api = api or _API 

    activity_ids = (act["activityId"] for act in activities)
    inputs = {
        act_id: (act_id, os.path.join(folder, f"{str(act_id)}.gpx"))
        for act_id in activity_ids
    }
    return map_concurrent(
        download_activity, inputs, 
        threaded=True, max_workers=max_workers, 
        show_progress=show_progress, raise_on_err=False
    )