# Withings Web App
This is a web-app to host API requests for Withings data. A large amount of inspiration/initial learnings came from from Miguel Grinberg's [microblog api](https://github.com/miguelgrinberg/microblog-api) - so if anything makes absolutely zero sense, check there for a likely better explanation.
The code to call the data is simple enough, but doing this often or in bulk is cumbersome. Thus, this app provides a very simple GUI & database structure that can make things a little easier (though a nicer version is in the works).

In terms of simply getting data through the Withings API, most of the code you'd be interested in can be found in app/routes.py & app/tasks.py.
Documentation for the Withings API can be found at https://developer.withings.com/api-reference.

This was my first genuine dive into Python programming, so my humblest apologies for the state of the code.
I have learnt a lot since this project was started, and I cringe looking back at some of code - but it does work, so I don't cringe too hard. <br/>
That being said, please reach out if you have any questions or problems. 

## Setup
This project requires a few things to get working.
Make sure to check and update the config.py where necessary - this should be intuitive while following the below steps. 

### Python Script
This was created in Python v3.7. Project requirements can be installed using <br/>
`pip install -r requirements.txt`

### Withings App
A Withings App must be registered on the Withings Public Cloud at https://developer.withings.com/dashboard/welcome.
This will provide you with a **Client ID** and **Client/Customer Secret**, which will need to be included in *config.py* or as an environment variable.

You will also have to define a Callback URL ('**withings_CALLBACK_URI**' in *config.py*). This is where authentication requests will be redirected. 
Importantly: If you redirect to localhost, you will be limited to only 10 linked users. In theory you can unlink these before requesting more, ad infinitum, but in practise I had trouble getting this to work in any convenient way. 

### Web Server
Frustratingly, there is only a very small component of this project that demands an online component. <br/>
Specifically, to avoid the above problem of being limited to 10 users, the callback URL must be hosted at a secure endpoint (*i.e., https://...*). 

This app uses the free package of the web-hosting service [Heroku](https://www.heroku.com/), though this can be done with any hosting service.<br/>
Although inefficient, the simplest setup is to clone this entire project and host it both locally and online. Heroku is configured using the Procfile, see  [microblog-api](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xviii-deployment-on-heroku) for more information.

The only code that requires being online is in app/routes.py, found below:
```python
@app.route("/get_token", methods = ['GET', 'POST'])
def get_token():
    code = request.args.get('code')
    state = request.args.get('state')

    parameters = dict(code=code, state=state)
    from app import ip
    local_url = ('http://localhost:5000/save_token')

    redirect_url = local_url + ('?' + urlencode(parameters) if parameters else "")

    return redirect(redirect_url)
```
In sum; all this is doing is redirecting the code that has been included in the url back to localhost. <br/>
The rest of the web interface was simply out of convenience and to begin prototyping for a proper research dashboard, which is under development.

### SQL Database
This project uses a simple SQL database package ([Flask-SQLalchemy](https://flask-sqlalchemy.palletsprojects.com/) to track linked participants/studies/app-users.
Changing this database properly (i.e., without deleting entries) is done with the [Flask-Migrate](https://flask-migrate.readthedocs.io/) package. 
Each package has good documentation, but the [microblog-api](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-iv-database) has a great section on getting this set up. 

That being said you *should* be able to create/change the database by just running the following.<br/>
This includes creation of an admin account that will be required if using the web app as-is.
```bash
set FLASK_APP=app.py
flask db init

python
>>> from app import db
>>> db.create_all()
>>>
>>> from app.models import User

>>> # The below is adding an admin user which you'll need for the web-app
>>> u = User(email='admin@admin.com', admin=True, confirmed=True) 
>>> User.set_password(u, 'admin')
>>> db.session.add(u)
>>> db.session.commit()


# And if you need to upgrade/change the database at any time...

# flask db migrate
# flask db upgrade

```
Alternatively, this can all be done on other database software, including excel/csv. A proper database structure was, again, largely done for prototyping/learning purposes. 

## Using the App
To run the app, once everything is installed, simply run the app.py script using `flask run`.

You should then be able to view the interface in your web-browser at http://localhost:5000/. <br/>
If you need to login, use the credentials that you added previously (email='admin@admin.com', password='admin').<br/>
Most of the functionality of interest is in the 'Withings' dropdown menu.

**_Note-1:_** You'll have to add a study first - this is just a categorization of participants. This is linked to an account - just use the attached admin account.<br/>
**_Note-2:_** Downloads can be found in *app/static/*<br/>
**_Note-3:_** Downloads are in *.json* format. You can open these in any text editor, though I'd recommend something like https://jsonformatter.org/json-pretty-print to make it more readable. Alternatively you can can use code to convert them to a more palatable format like *.csv* or *.excel* - let me know if you need help with this. 
