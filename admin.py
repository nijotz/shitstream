from flask import redirect, url_for
from flask.ext.admin import Admin, AdminIndexView, expose
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.user import current_user

import db


# Create customized index view class that handles login & registration
class MyAdminIndexView(AdminIndexView):

    @expose('/')
    def index(self):
        if not current_user.is_authenticated():
            return redirect(url_for('user.login'))
        return super(MyAdminIndexView, self).index()


class UserView(ModelView):

    def __init__(self, session, **kwargs):
        super(UserView, self).__init__(db.User, session, **kwargs)

    def is_accessible(self):
        return current_user.is_authenticated()

def setup(app):
    admin = Admin(app, index_view=MyAdminIndexView())
    admin.add_view(UserView(db.db.session))
    
    return admin
