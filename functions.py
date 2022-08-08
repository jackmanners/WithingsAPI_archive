import datetime as dt
import json
import os
import requests
import shutil
import zipfile
from datetime import datetime

import pandas as pd

from app import Config

pd.options.mode.chained_assignment=None # default='warn'


# Bastien's code to sort withings .json download - not implemented into website yet
def _block_list_to_df(block_list, meas_type='hr', meas_length=60):
    """
    This is just a small function to transform Withings' API measurements (
    rr, HR, snoring) to a pandas Dataframe.

    Parameters
    ----------
    block_list : list
        List of dictionaries

    meas_type : str
        Type of measurement. Must be hr (heart rate), rr (respiration rate) or
        snoring (snoring time).

    meas_length : int
        Length of any given measurement. Withings record data every minutes

    Returns
    -------
    df : pd.DataFrame
        A Dataframe with the following keys: startdate,enddate and the
        measurement value
    """
    h = {k: v for d in block_list for k, v in d.items()}
    df = pd.DataFrame.from_dict(h,orient='index').reset_index()
    df.columns = ['start_date',meas_type]
    df['endate'] = df['start_date'].astype('int').values + meas_length
    return df

#TODO - Implement .json -> df function so that data can be downloaded as .csv
def withings_api_json_to_df(json_file):
    """
    Transform the obtained json_file from Withings getsleep API calls to a
    dataframe. Sleep states, heart rate, respiration rate and snoring are
    extracted.

    Parameters
    ----------
    json_file : dict or str
        If dict, must be the output of Withings API getsleep calls. Otherwise
        must be a valid file path to the saved json object.

    Returns
    -------
    ss_df : pd.DataFrame
        DataFrame containing sleep states values

    hrdf : pd.DataFrame
        DataFrame containing heart rate values

    rrdf : pd.DataFrame
        DataFrame containing respiration rate values

    sndf : pd.DataFrame
        DataFrame containing snoring values

    Returns
    -------
    Startdate and endate are UNIX time (seconds elapsed since 00:00:00 UTC on
    1 January 1970).

    #TODO Check to see if times are zone-aware or not
    """
    if isinstance(json_file, dict):
        data = json_file
    else:
        if os.path.isfile(json_file):
            # Opening JSON file
            f = open(json_file)
            data = json.load(f)
            f.close()
        else:
            raise ValueError("Json must be a valid file path or a dictionnary "
                             "containing Withings' getsleep data")

    sstage = {'startdate':[],
              'sleep_state':[],
              'enddate':[],
              'model':[],
              'hash_deviceid':[]}
    hrs = []
    rrate = []
    snoring = []

    status = data['status'] #Not sure if we need this. We might need it if
    # something goes wrong?
    body = data['body']
    data_series = body['series']
    for block in data_series:
        sstage['startdate'].append(block['startdate'])
        sstage['sleep_state'].append(block['state'])
        sstage['enddate'].append(block['enddate'])
        sstage['model'].append(block['model'])
        sstage['hash_deviceid'].append(block['hash_deviceid'])

        hrs.append(block['hr'])
        rrate.append(block['rr'])
        snoring.append(block['snoring'])

    ss_df = pd.DataFrame.from_dict(sstage)
    hrdf = _block_list_to_df(hrs, meas_type='hr')
    rrdf = _block_list_to_df(rrate, meas_type='rr')
    sndf = _block_list_to_df(snoring, meas_type='snoring')

    return ss_df, hrdf, rrdf, sndf


# Allowed files for upload
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def isNaN(string):
    return string != string
