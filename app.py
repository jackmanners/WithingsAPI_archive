from app import app
from app import db
from app.models import User, Participant
from app import Config


@app.shell_context_processor
def make_shell_context():
    # I can't remember what this does, but it's necessary.
    return {'db': db, 'User': User, 'Participant': Participant}


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.

    This was needed as downloads were being cached indefinitely.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "10"
    r.headers['Cache-Control'] = 'public, max-age=10'
    return r


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)

