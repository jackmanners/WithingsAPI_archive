from flask import current_app

from app import db, login, app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import flask_admin
import redis
import rq




@login.user_loader
def load_user(id):
    return User.query.get(int(id))


# Association table between Users and Studies
user_studies = db.Table('user_studies',
                        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                        db.Column('study_id', db.Integer(), db.ForeignKey('study.id'))
                        )


# Site users db table
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    admin = db.Column(db.Boolean, default=False)
    confirmed = db.Column(db.Boolean, default=False)
    studies = db.relationship(
        'Study', secondary=user_studies,
        backref=db.backref('user', lazy='dynamic'))

    def __repr__(self):
        return '<User {}>'.format(self.email)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def assign_study(self, study_id):
        study = Study.query.filter_by(id=study_id).first()
        self.studies.append(study)

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()


# Study db table
class Study(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True)
    participants = db.relationship('Participant', backref='study', lazy='dynamic')

    def __repr__(self):
        return '{}'.format(self.name)
        #return self.name


# Participant db table
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)  # The unique backend id of the participant
    lab_id = db.Column(db.String, index=True        )  # The given id of the participant (e.g., LED420), may not be unique
    study_name = db.Column(db.String, db.ForeignKey('study.name', name='fk_study_name'))  # The study the participant is associated with

    withings_id = db.Column(db.String(64), index=True)  # The withings account id
    withings_device_id = db.Column(db.String(128), index=True)
    withings_access_token = db.Column(db.String(128))
    withings_refresh_token = db.Column(db.String(128))
    withings_time_refreshed = db.Column(db.String(32), index=True)

    fitbit_id = db.Column(db.String(64), index=True)  # The fitbit account id
    fitbit_device_id = db.Column(db.String(128), index=True)
    fitbit_access_token = db.Column(db.String(128))
    fitbit_refresh_token = db.Column(db.String(128))
    fitbit_time_refreshed = db.Column(db.String(32), index=True)

    def __repr__(self):
        return '<Participant {}>'.format(self.lab_id)


#  TODO - get tasks working (so that current tasks can be tracked)
#  not urgent
class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True, unique=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100
