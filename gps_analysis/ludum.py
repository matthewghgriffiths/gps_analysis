
from datetime import datetime, timedelta 
import shutil 
import urllib 
import json 
from pathlib import Path 

import requests 
import pandas as pd
import numpy as np

from . import geodesy, utils, files 

session_fields = [
    'crews.crew_users.user.crew_user_groups',
    'crews.crew_users.user:fields(id|first_name|last_name|full_name|picture)',
    'crews.gmt_score',
    'crews.inventory.usage_history',
    'participants.user.crew_user_groups',
    'participants.user.user_squads',
    'participants.user:fields(id|first_name|last_name|full_name|picture)',
    'session.structure.pieces.crews.crew_users.user.crew_user_groups',
    'session.structure.pieces.crews.crew_users.user:fields(id|first_name|last_name|full_name|picture)',
    'session.structure.pieces.crews.gmt_score',
    'session.structure.pieces.crews.inventory.usage_history',
    'session.structure.pieces.crews:order(created_at|desc)',
    'session_files.crews.session_crew_files.user',
    'session_files.users:fields(id|full_name)',
    'user_actions'
]


class LudumClient:
    https_base_url = "https://api.ludum.com"
    default_headers = {
        "Accept": "application/json, text/plain, */*",
        # "Content-Type": "application/json",
        "Content-Type":"application/x-www-form-urlencoded",
        "Referer": "https://app.ludum.com/", 
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.67 Safari/537.36"
        ),
    }
    def __init__(self, username, password, client_secret, club_id):
        self.username = username 
        self.password = password 
        self.client_secret = client_secret
        self.club_id = club_id 

        self.session = requests.session()
        self._login_response = None 

    def authenticate(self):
        payload = {
            "username": self.username, 
            "password": self.password, 
            "client_secret": self.client_secret, 
            "client_id": self.club_id, 
            "grant_type": "password"
        }
        headers = self.default_headers
        s = self.session.post(
            self.https_base_url + "/api/v2/login", 
            data=payload, 
            headers=headers
        )
        s.raise_for_status()

        self._login_response = s.json()
        
    @property
    def access_token(self):
        if self._login_response is None:
            self.authenticate()

        return self._login_response['data']['accessToken']['access_token']

    def prepare_headers(self, **kwargs):
        headers={
            "Content-Type":"application/x-www-form-urlencoded",
            "User-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",
            "Referer":"https://app.ludum.com/",
            "club_id": "2", 
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.club_id:
            headers["club_id"] = self.club_id

        headers.update(kwargs)
        return headers

    def post(self, endpt, data=None, json=None, **kwargs):
        kwargs['headers'] = self.prepare_headers(**kwargs.get('headers', {}))
        return self.session.post(
            self.https_base_url + endpt,
            data=data,
            json=json, 
            **kwargs
        )

    
    def get(self, endpt, **kwargs):
        kwargs['headers'] = self.prepare_headers(**kwargs.get('headers', {}))
        return self.session.get(
            self.https_base_url + endpt,
            **kwargs
        )

    def get_session_data(self, session_id):
        fields = ",".join(session_fields)
        endpt = (
            f"/api/v2/session/{session_id}"
            "?fields=id|name|seat_racing|session"
            f"&include={fields}"
        )
        return self.get(endpt).json()

    def get_agenda(self, start_date=None, end_date=None, days=60, **kwargs):
        if end_date:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_datetime = datetime.today()

        if start_date: 
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            if not end_date:
                end_datetime = start_datetime + timedelta(days=days)
        else:
            start_datetime = end_datetime - timedelta(days=days)

        payload = {
            "club_id": self.club_id,
            "start_date": start_datetime.strftime("%Y-%m-%d"),
            "end_date": end_datetime.strftime("%Y-%m-%d"),
            "display": "all-sessions",
        }
        payload.update(kwargs)
        r = self.post(
            "/api/v2/agenda?fields=id|session_id|start_date|end_date|sport|name|all_day_event|attendance_limit|location",
            data=payload
        )
        r.raise_for_status()
        return r.json()

    def load_agenda(self, start_date=None, end_date=None, days=60, **kwargs):
        agenda_data = self.get_agenda(
            start_date=start_date, end_date=end_date, days=days, **kwargs
        )
        return pd.json_normalize(agenda_data['data']['data'])

    def load_sessions(self, start_date=None, end_date=None, days=60, max_workers=10, **kwargs):
        agenda = self.load_agenda(
            start_date=start_date, end_date=end_date, days=days, **kwargs
        )
        sessions = utils.map_concurrent(
            self.get_session_data, 
            dict(zip(agenda.id, zip(agenda.id))), 
            max_workers=max_workers,
        )
        return sessions 


def extract_session_data(sessions):
    session_info = extract_session_info(sessions)

    session_files = (
        (session, session_data['data']['session_files'])
        for session, session_data in sessions.items()
        if 'session_files' in session_data['data'] 
    )
    session_files = pd.concat({
        session: pd.DataFrame.from_records([
            dict(utils.flatten_json(d)) 
            for d in data.get(
                'data', {}
            ).get(
                'users', {}
            ).get(
                'data', {}
            ) if d
        ])
        for session, data in session_files
    }, axis=0, names=['session_id']).droplevel(1).reset_index()

    for c in session_files.columns[
        session_files.columns.str.endswith('id') & 
        ~ session_files.columns.str.endswith('guid') 
    ]:
        session_files[c] = session_files[c].fillna(0).astype(int)

    
    session_files['session_name'] = session_info.name.loc[session_files.session_id].values
    return session_info, session_files 

def extract_session_info(sessions):
    return pd.concat(
        [pd.json_normalize(data['data']) for i, data in sessions.items()], 
        ignore_index=True
    ).set_index('id')

def extract_session_files(sessions):
    session_files = (
        (session, session_data['data']['session_files'])
        for session, session_data in sessions.items()
        if 'session_files' in session_data['data'] 
    )
    session_files = pd.concat({
        session: pd.DataFrame.from_records([
            dict(utils.flatten_json(d)) 
            for d in data.get(
                'data', {}
            ).get(
                'users', {}
            ).get(
                'data', {}
            ) if d
        ])
        for session, data in session_files
    }, axis=0, names=['session_id']).droplevel(1).reset_index()

    for c in session_files.columns[
        session_files.columns.str.endswith('id') & 
        ~ session_files.columns.str.endswith('guid') 
    ]:
        session_files[c] = session_files[c].fillna(0).astype(int)

    return session_files


def download_fit(url):
    return files.parse_fit_data(requests.get(url, stream=True).raw.read())

def download_ludum_data(row, path='ludum_data', overwrite=False):
    data_folder = Path(path)
    file_cols = [
        'session_individual_files_data_gps_file',
        'session_individual_files_data_gps_file_url',
        'session_individual_files_data_hr_file',
        'session_individual_files_data_hr_file_url'
    ]
    paths = []
    for c in file_cols:
        url = row[c]
        out_path = data_folder / urllib.parse.urlparse(row[c]).path.strip("/")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        paths.append(out_path)
        if overwrite or not out_path.exists():
            print("downloading", out_path)
            with requests.get(url, stream=True) as r, open(out_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        else:
            print("skipping")

    return paths

def download_all_ludum_data(session_files, path='ludum_data', overwrite=False):
    return utils.map_concurrent(
        download_ludum_data,
        {
            (row.session_id, row.full_name): (row,)
            for _, row in session_files.iterrows()
        }, 
        max_workers=4,
        overwrite=False 
    )

def read_ludum_data(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)

    
    data.pop('line')

    
    positions = pd.DataFrame.from_dict(
        data.pop('position'), orient='index'
    ).reset_index(drop=True)

    last = positions.index[-1]

    positions['latitude'] = positions.lat
    positions['longitude'] = positions.long
    positions['distance'] /= 1000  
    
    positions['time'] = pd.to_datetime(positions.timestamp, unit='s')
    
    positions['timeElapsed'] = positions.time - positions.time[0]
    positions['distanceDelta'] = - positions.distance.diff(-1)
    positions.loc[last, 'distanceDelta'] = 0

    positions['bearing_r'] = geodesy.rad_bearing(positions, positions.shift(-1))
    positions.loc[last, 'bearing_r'] = positions.bearing_r[1]
    positions['bearing'] = np.rad2deg(positions.bearing_r)

    metadata = pd.json_normalize(data)

    return metadata, positions