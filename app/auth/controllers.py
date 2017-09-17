# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  redirect, url_for
from app.auth.forms import LoginForm, RegistrationForm
from app.auth.models import User, Role, roles_users
from flask_admin.contrib import sqla
from flask_admin import helpers
import flask_login as login
from app import db
from werkzeug.security import generate_password_hash
from app.site.models import Themes

auth = Blueprint('auth', __name__, url_prefix='/auth')

class MyModelView(sqla.ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated


@auth.route('/')
def index():
    if not login.current_user.is_authenticated:
        return redirect(url_for('auth.login_view'))
    return redirect(url_for('site.index'))


@auth.route('/login', methods=['GET', 'POST'])
def login_view():
    form = LoginForm(request.form)
    if helpers.validate_form_on_submit(form):
        user = form.validate_login()
        if user:
            login.login_user(user)

            if login.current_user.is_authenticated:
                return redirect(url_for('site.index'))
    template_path = Themes.get_active('auth')
    return render_template(template_path + '/auth/login.html', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def registration_view():
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            if form.validate_registration():
                user = User()

                form.populate_obj(user)
                user.password = generate_password_hash(form.password.data)
                
                db.session.add(user)
                db.session.commit()

                login.login_user(user)

                return redirect(url_for('auth.index'))
        template_path = Themes.get_active('auth')
        return render_template(template_path + '/auth/register.html', form=form)


@auth.route('/logout')
def logout_view():
    login.logout_user()
    return redirect(url_for('auth.index'))
