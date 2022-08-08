import pandas as pd
import requests
from flask_mail import Message
from app import app, mail, db, Config
from celery import Celery
import datetime as dt
import json
import os
import requests
import shutil
import zipfile
from datetime import datetime, timedelta

from app.models import Participant


def make_celery(app):
    """
    This function can be called with
        @celery.task()
        def <FUNCTION NAME>():

    This allows the decorated function to run as a background process, 
    rather than requiring the user stay on a loading screen while
    the function runs.
    """
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)

@celery.task()
def withings_token(p_id):
    """
    This gets or refreshes the participant's access token/
    The p_id that is fed in is used to query the associated participant in the 
    database and gather their token.
    If it has been >2hrs since it was last refreshed, a request is sent for a new one.
    (Access tokens expire after 3 hours)
    """
    px = Participant.query.filter_by(lab_id=p_id).first()
    t = px.withings_time_refreshed
    try:
        t = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        t = datetime.strptime(t, "%m/%d/%Y, %H:%M:%S")
    print(px)

    at = px.withings_access_token
    rt = px.withings_refresh_token
    print(at)

    try:
        time_test = (datetime.now() - t) < timedelta(hours=2)
    except:
        time_test = False

    if not time_test:
        try:
            print('Refreshing Token')
            payload = {'action': 'requesttoken',
                       'grant_type': 'refresh_token',
                       'client_id': Config.withings_CLIENT_ID,
                       'client_secret': Config.withings_CUSTOMER_SECRET,
                       'refresh_token': rt
                       }
            r_token = requests.post(f'{Config.withings_WBSAPI_URL}/v2/oauth2',
                                    data=payload).json()

            rt = r_token['body']['refresh_token']
            at = r_token['body']['access_token']
            t = datetime.strftime(datetime.now(), "%m/%d/%Y, %H:%M:%S")

        except:
            print(px.lab_id + ' could not be refreshed')

    px.withings_access_token = at
    px.withings_refresh_token = rt
    px.withings_time_refreshed = t

    return at


@celery.task()
def withings_download(uid, dtFrom, dtTo, at, time):
    """
    Function for requesting sleep data from the Withings API.
    This sends a request for both the raw sleep data (r_getsleep), as well as the sleep
    summaries (r_getsleepsummary) for each requested night.
    It then saves it into .json files that are zipped and moved to app/static/ to then be
    downloaded in the browser.

    This process takes a while as it has to iterate over each day.

    Parameters
        uid:  the user_id (In practise this is the lab_id), used only for naming the file.
        dtFrom: the beginning date of sleeps to be requested
        dfTo: the end date of sleeps to be requested
        at: the Withings access_token of the requested participant
    """

    headers = {'Authorization': 'Bearer ' + at}
    delta = dt.timedelta(days=1)
    while dtFrom <= dtTo:
        date = int(round((datetime.combine(dtFrom, dt.time(12, 0, 0))).timestamp()))
        payload_sleep = {'action': 'get',
                         'startdate': date,
                         'enddate': date+86400,
                         'data_fields': 'hr,rr,snoring,sdnn_1,rmssd'
                         }
        r_getsleep = requests.get(f'{Config.withings_WBSAPI_URL}/v2/sleep',
                                  headers=headers,
                                  params=payload_sleep).json()
        with open('app/static/'+time+'/'+(str(uid)+'_sleep_'+str(dtFrom))+'.json', 'w') as outfile:
            json.dump(r_getsleep, outfile)

        payload_sleepSummary = {'action': 'getsummary',
                                'startdateymd': dtFrom.strftime('%Y-%m-%d'),
                                'enddateymd': (dtFrom + delta).strftime('%Y-%m-%d'),
                                'data_fields': 'sleep_efficiency,total_sleep_time,total_timeinbed,sleep_latency,'
                                               'wakeup_latency,waso,apnea_hypopnea_index,'
                                               'breathing_disturbances_intensity,asleepduration,lightsleepduration,'
                                               'deepsleepduration,remsleepduration,nb_rem_episodes,hr_average,hr_max,'
                                               'hr_min,rr_average,rr_max,rr_min,sleep_score,snoring,'
                                               'snoringepisodecount,out_of_bed_count,wakeupcount,wakeupduration,'
                                }
        r_getsleepsummary = requests.get(f'{Config.withings_WBSAPI_URL}/v2/sleep',
                                  headers=headers,
                                  params=payload_sleepSummary).json()
        with open('app/static/'+time+'/'+(str(uid)+'_sleepSummary_'+str(dtFrom))+'.json', 'w') as outfile:
            json.dump(r_getsleepsummary, outfile)

        print('Downloading ' + str(uid) + ' ' + str(dtFrom) + '...')
        dtFrom += delta


@celery.task()
def zip_download(filepaths, dir_name):
    """
    Used for zipping up files before download.

    Parameters
        filePaths: the files to be zipped.
        dir_name: Placeholder, currently just names it 'withings_download'.
    """

    print('The following list of files will be zipped:')
    for fileName in filepaths:
        print(fileName)

    # writing files to a zipfile
    zip_file = zipfile.ZipFile('app/static/' + dir_name + '.zip', 'w')
    with zip_file:
        for file in filepaths:
            zip_file.write(file)

    print(dir_name + '.zip created successfully!')


@celery.task()
def send_file(file, recipient):
    """
    A simple function to send the file to an email once complete.
    Since the download can be slow this was added to make it more 
    hands-off. 
    """
    msg = Message('Test send!', sender=Config.MAIL_USERNAME, recipients=recipient)
    msg.body = "Your requested download is attached"
    with app.open_resource('static/' + file) as fp:
        msg.attach(file, 'application/zip', fp.read())
    mail.send(msg)
    return "Message sent!"

@celery.task()
def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_USERNAME']
    )
    mail.send(msg)