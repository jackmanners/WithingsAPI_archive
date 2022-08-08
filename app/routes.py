import csv
from datetime import datetime
import os
import glob
import requests
from urllib.parse import urlencode
import shutil

import pandas as pd
from flask import request, redirect, url_for, render_template, flash, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from sqlite_web import sqlite_web
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename

import functions as f
from app import app, db, tasks, Config
from app.decorators import check_confirmed, check_admin
from app.forms import LoginForm, newWithings, dlformWithings, RegistrationForm, assignStudy, manageParticipants
from app.models import User, Participant, Study
from app.token import generate_confirmation_token, confirm_token

"""
THINGS DIRECTLY TO DO WITH WITHINGS START FURTHER DOWN (withings_new is the first function)
The rest of this is web-app/GUI stull that was a prototype way to make it all easier.
"""


@app.route("/home")
@app.route("/")
@login_required
def home():
    title = ''
    return render_template("index.html", title=title)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('home')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if '@flinders.edu.au' in form.email.data:
            user = User(email=form.email.data)
            user.set_password(form.password.data)
            user.confirmed = False
            db.session.add(user)
            db.session.commit()

            e = 'jack.manners@flinders.edu.au'  # I currently confirm accounts myself
            token = generate_confirmation_token(user.email)
            confirm_url = url_for('confirm_email', token=token, _external=True)
            html = render_template('user/activate.html', confirm_url=confirm_url)
            subject = "Please confirm the email: " + str(user.email)
            tasks.send_email(e, subject, html)

            login_user(user)

            flash('A confirmation email has been sent via email.', 'success')
            return redirect(url_for('unconfirmed'))
        else:
            return 'Unauthorised email'
    return render_template('register.html', title='Register', form=form)


@app.route('/confirm/<token>')
@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('home'))


@app.route('/resend')
@login_required
def resend_confirmation():
    token = generate_confirmation_token(current_user.email)
    confirm_url = url_for('user.confirm_email', token=token, _external=True)
    html = render_template('user/activate.html', confirm_url=confirm_url)
    subject = "Please confirm your email"
    tasks.send_email(current_user.email, subject, html)
    flash('A new confirmation email has been sent.', 'success')
    return redirect(url_for('user.unconfirmed'))


@app.route('/unconfirmed')
@login_required
def unconfirmed():
    if current_user.confirmed:
        return redirect('home')
    flash('Please confirm your account!', 'warning')
    return render_template('user/unconfirmed.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
@check_confirmed
def profile():
    return """Profile"""


@app.route("/withings_new", methods=['GET', 'POST'])
@login_required
@check_confirmed
def new_withings():
    form = newWithings()
    df = pd.read_sql_table('Study', str(Config.SQLALCHEMY_DATABASE_URI))
    studies = list(df['name'])
    form.study.choices = studies
    message = ''
    study = str(form.study.data)

    id = str(form.id.data)
    if form.validate_on_submit():
        new_user = [study, id]
        with open('new_user', 'w') as f:
            write = csv.writer(f)
            write.writerow(new_user)
            return redirect(url_for('get_code'))
    return render_template('withingsAdd.html', study=study, form=form, message=message, title='Add Withings User')


@app.route("/withings_authorisation")
@login_required
@check_confirmed
def get_code():
    """
    Route to get the permission from an user to take his data.
    This endpoint redirects to a Withings' login page on which
    the user has to identify and accept to share his data
    """
    payload = {'response_type': 'code',  # imposed string by the api
               'client_id': Config.withings_CLIENT_ID,
               'state': Config.withings_STATE,
               'scope': 'user.info,user.activity',  # see docs for enhanced scope
               'redirect_uri': Config.withings_CALLBACK_URI  # URL of this app
               }
    r_auth = requests.get(f'{Config.withings_ACCOUNT_URL}/oauth2_user/authorize2',
                          params=payload)
    return redirect(r_auth.url)


@app.route("/get_token", methods = ['GET', 'POST'])
def get_token():
    """
    Callback route when the user has accepted to share his data.
    Once the auth has arrived Withings servers come back with
    an authentication code and the state code provided in the
    initial call.


    """
    code = request.args.get('code')
    state = request.args.get('state')

    parameters = dict(code=code, state=state)
    from app import ip
    local_url = ('http://localhost:5000/save_token')

    redirect_url = local_url + ('?' + urlencode(parameters) if parameters else "")

    return redirect(redirect_url)


@app.route('/save_token')
@login_required
@check_confirmed
def save_token():
    """
    Using the authorization code (received above) to request access and refresh tokens which are required 
    for all subsequent API requests
    """

    code = request.args.get('code')
    state = request.args.get('state')

    payload = {'action': 'requesttoken',
               'grant_type': 'authorization_code',
               'client_id': Config.withings_CLIENT_ID,
               'client_secret': Config.withings_CUSTOMER_SECRET,
               'code': code,
               'redirect_uri': Config.withings_CALLBACK_URI
               }
    r_token = requests.post(f'{Config.withings_WBSAPI_URL}/v2/oauth2',
                            data=payload).json()

    access_token = (r_token['body']['access_token'])
    headers = {'Authorization': 'Bearer ' + access_token}
    payload_device = {'action': 'getdevice'}

    r_getdevice = requests.get(f'{Config.withings_WBSAPI_URL}/v2/user',
                               headers=headers,
                               params=payload_device).json()

    """
    Saving IDs & tokens into df, and pulling study info and study ID from temp. file.
    This is purely because I don't know an easier way to save it in the session.
    """
    u_id = (r_token['body']['userid'])
    at = (r_token['body']['access_token'])
    rt = (r_token['body']['refresh_token'])

    try:
        print(r_token['body']['access_token'])
    except:
        print('access token not received')

    try:
        d_id = (r_getdevice['body']['devices'][0]['deviceid'])
    except:
        d_id = 'No devices'
    with open('new_user', 'r') as nu:
        reader = csv.reader(nu)
        ls = (list(reader))
        study = ls[0][0]
        s_id = ls[0][1]
    uTime = datetime.strftime(datetime.now(), "%m/%d/%Y, %H:%M:%S")
    wUser = Participant(
        lab_id=s_id,
        withings_id=u_id,
        withings_device_id=d_id,
        withings_access_token=at,
        withings_refresh_token=rt,
        withings_time_refreshed=uTime,
        study_name=study)
    db.session.add(wUser)
    db.session.commit()
    os.remove('new_user')  # remove the new_user file

    return redirect(url_for("home"))


@app.route("/withings_download", methods=['GET', 'POST'])
@login_required
@check_confirmed
def withings_dl():
    """Importing the form and initiating variables"""
    title = 'Download Existing User'
    form = dlformWithings()
    message = ''
    ids = []
    df = pd.read_sql_table('Participant', str(Config.SQLALCHEMY_DATABASE_URI))
    
    """
    # This was oly necessary for us using this across multiple studies

    permissions = []
    for i in current_user.studies:
        permissions.append(str(i))
    print(permissions)
    px = ['You are not linked to any studies - please contact an administrator']
    if (str('|'.join(permissions))) != '':
        df = df.loc[df['study_name'].str.contains('|'.join(permissions))]
    """
        
    px = list(df['lab_id'])
    px.sort()   
    form.download_id.choices = px

    now = datetime.now()
    time = now.strftime("%H%M%S")

    if form.validate_on_submit():
        time_path = ('app/static/' + time)
        os.mkdir(time_path)
        if form.download_all.data:
            selected_ids = px
        else:
            selected_ids = form.download_id.data
        print(selected_ids)
        for i in selected_ids:
            check = str(i)
            if check in px:
                at = tasks.withings_token(check)
                form.download_id.data = ''
                dtFrom = form.datefrom.data
                dtTo = form.dateto.data
                tasks.withings_download(check, dtFrom, dtTo, at, time)
            else:
                message = 'That user does not exist'
        filename = 'withings_download'
        filename_full = (filename + '.zip')
        files = glob.glob(time_path+'/*.json')
        
        """
        # This part zipped files and emailed them to the logged-in user email

        tasks.zip_download(files, filename)
        getuser = current_user.id
        usr = User.query.filter_by(id=getuser).first()
        
        tasks.send_file(file=filename_full, recipient=[usr.email])
        os.remove('app/static/' + filename_full)
        shutil.rmtree('app/static/'+time)
        """

        db.session.commit()

        return redirect(url_for("home"))

    return render_template('withingsDownload.html', ids=ids, form=form, message=message, title=title)


@app.route('/manual_refresh')
@login_required
@check_admin
def man_refresh():
    tasks.refresh_tokens()
    return redirect(url_for('home'))


@app.route('/convert_json_withings', methods=['GET', 'POST'])
@login_required
@check_confirmed
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and f.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('download_file', name=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


@app.route('/uploads/<name>')
@login_required
@check_confirmed
def download_file(name):
    print(app.config['UPLOAD_FOLDER'])
    print(name)
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)


@app.route('/get/<file>')
@login_required
@check_confirmed
def download(file):
    return redirect(url_for("static", filename=file))


@app.route("/assign_studies", methods=['GET', 'POST'])
@login_required
@check_admin
def assign_studies():
    title = 'Assign Studies'
    form = assignStudy()
    message = ''

    users = User.query.all()
    emails = []
    for user in users:
        emails.append(user.email)
    print(emails)

    df_studies = pd.read_sql_table('Study', str(Config.SQLALCHEMY_DATABASE_URI))
    studies = list(df_studies['name'])
    form.studies.choices = studies
    form.users.choices = emails

    if form.validate_on_submit():
        selected_users = []
        if str(form.users.data) != '':
            for i in form.users.data:
                selected_users.append(i)
        else:
            if str(form.study_new.data) != '':
                new_study = Study(name=str(form.study_new.data))
                db.session.add(new_study)
                db.session.commit()
            return redirect(url_for('home'))

        for i in selected_users:
            user = User.query.filter_by(email=i).first()

            selected_studies = []
            if form.studies_all.data:
                selected_studies = studies
            elif str(form.studies.data) != '':
                for i in form.studies.data:
                    selected_studies.append(str(i))

            if str(form.study_new.data) != '':
                selected_studies.append(str(form.study_new.data))
                new_study = Study(name=str(form.study_new.data))
                db.session.add(new_study)
                db.session.commit()

            for i in selected_studies:
                check = str(i)
                if check in studies:
                    study = Study.query.filter_by(name=check).first()
                    user.studies.append(study)

        db.session.commit()
        return redirect(url_for("home"))
    return render_template('admin/assign_study.html', studies=studies, form=form, message=message, title=title)



@app.route("/manage_participants", methods=['GET', 'POST'])
@login_required
@check_admin
def manage_participants():
    title = 'Manage Participants'
    form = manageParticipants()
    message = ''

    participants = Participant.query.all()
    participant_ls = []
    for px in participants:
        participant_ls.append(px.lab_id)

    studies = Study.query.all()
    studies_ls = []
    for sd in studies:
        studies_ls.append(sd.name)

    form.study.choices = studies_ls
    form.participants.choices = participant_ls

    if form.validate_on_submit():
        selected_px = []
        if str(form.participants.data) != '':
            for i in form.participants.data:
                selected_px.append(i)

        if form.delete.data:
            for i in selected_px:
                participant = Participant.query.filter_by(lab_id=i).first()
                db.session.delete(participant)
            db.session.commit()
            return redirect(url_for('home'))

        study = form.study.data

        for i in selected_px:
            participant = Participant.query.filter_by(lab_id=i).first()
            participant.study_name = study

        db.session.commit()
        return redirect(url_for("home"))
    return render_template('admin/manage_participants.html', participants=participants, form=form, message=message, title=title)


"""
@app.route('/admin/database')
@login_required
@check_admin
def database_view():
"""


@app.route('/test', methods=['GET', 'POST'])
@login_required
def test():
    return redirect('http://localhost:5000/')
