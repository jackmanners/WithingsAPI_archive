from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from app.models import User


class LoginForm(FlaskForm):
    email = StringField('Email: ', validators=[DataRequired()])
    password = PasswordField('Password: ', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    email = StringField('Email: ', validators=[DataRequired(), Email()])
    password = PasswordField('Password: ', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')
        if not '@flinders.edu.au' in email.data:
            raise ValidationError('Please use a valid Flinders email address.')


class EditProfileForm(FlaskForm):
    username = StringField('Username: ', validators=[DataRequired()])
    studies = TextAreaField('About me: ', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')


class dlformWithings(FlaskForm):
    download_id = SelectMultipleField('')
    download_all = BooleanField('Check to download all: ')
    datefrom = DateField('Start date: ', validators=[DataRequired()])
    dateto = DateField('End date: ', validators=[DataRequired()])
    submit = SubmitField('Submit')


class newWithings(FlaskForm):
    study = SelectField('Attached study: ')
    id = StringField('Participant ID: ', validators=[DataRequired()])
    submit = SubmitField('Submit to be redirected to Withings login page (make sure to use correct participant login)')

    def __init__(self, study_choices: list = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if study_choices:
            self.study.choices = study_choices


class assignStudy(FlaskForm):
    users = SelectMultipleField('')
    studies = SelectMultipleField('')
    studies_all = BooleanField('Check to download all: ')
    study_new = StringField('Name of new study: ')
    submit = SubmitField('Submit')


class manageParticipants(FlaskForm):
    participants = SelectMultipleField('')
    delete = BooleanField('Check to delete participants: ')
    study = SelectField('')
    submit = SubmitField('Submit')
