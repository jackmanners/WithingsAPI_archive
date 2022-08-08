from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def check_confirmed(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.confirmed is False:
            flash('Please confirm your account!', 'warning')
            return redirect(url_for('user.unconfirmed'))
        return func(*args, **kwargs)

    return decorated_function

def check_admin(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.admin is False:
            flash('Access to this page required an admin!', 'warning')
            return redirect(url_for('home'))
        return func(*args, **kwargs)

    return decorated_function