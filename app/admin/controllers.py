# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for
from app import db
from app.admin.forms import CreatePostForm, EditPostForm, \
                            CreatePageForm, EditPageForm, \
                            CreateUserForm, EditUserForm, \
                            CreateRoleForm, EditRoleForm, \
                            CreateCommentForm, EditCommentForm, EditProfileForm
from app.site.models import Themes, PostComment
from app.admin.models import Post, Page
from app.auth.models import User, Role, roles_users
from flask_admin import helpers
import flask_login as login
from app import check_login, check_admin, has_role
from werkzeug.security import generate_password_hash
import codecs
import translitcodec
import difflib
from datetime import datetime
import re
from app.site.models import Themes

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

# Create blog blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Create the blog routes
@admin.route('/blog', methods=['GET'])
@check_login
@has_role('editor')
def blog_list():
    posts = Post.all()
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/blog/list.html", posts=posts)


@admin.route('/blog/create', methods=['GET', 'POST'])
@check_login
@has_role('writer')
def create_post():
    form = CreatePostForm(request.form)
    if helpers.validate_form_on_submit(form):
        post = Post()
        form.populate_obj(post)
        post.slug = slugify(post.title)
        post.writen_by = login.current_user.id
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('admin.blog_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/blog/post.html", form=form)


@admin.route('/blog/edit/<int:post_id>', methods=['GET', 'POST'])
@check_login
@has_role('editor')
def edit_post(post_id):
    post = Post.query.get(post_id)
    form = EditPostForm(request.form, obj=post)
    if helpers.validate_form_on_submit(form):
        form.populate_obj(post)
        post.slug = slugify(post.title)
        post.writen_by = login.current_user.id
        db.session.merge(post)
        db.session.commit()
        return redirect(url_for('admin.blog_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/blog/post.html", form=form)


@admin.route('/blog/delete/<int:post_id>', methods=['POST'])
@check_login
@check_admin
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin.blog_list'))


# Create the page routes
@admin.route('/page', methods=['GET'])
@check_login
@has_role('editor')
def page_list():
    pages = Page.all()
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/pages/list.html", pages=pages)


@admin.route('/page/create', methods=['GET', 'POST'])
@check_login
@has_role('writer')
def create_page():
    form = CreatePageForm(request.form)
    if helpers.validate_form_on_submit(form):
        page = Page()
        form.populate_obj(page)
        page.slug = slugify(page.title)
        page.history = "{} created at {}".format(str(login.current_user.email), datetime.now().strftime('%m-%d-%Y %I:%M %p'))
        db.session.add(page)
        db.session.commit()
        return redirect(url_for('admin.page_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/pages/page.html", form=form)


@admin.route('/page/edit/<int:page_id>', methods=['GET', 'POST'])
@check_login
@has_role('editor')
def edit_page(page_id):
    page = Page.query.get(page_id)
    last_edit = page.html
    form = EditPageForm(request.form, obj=page)
    if helpers.validate_form_on_submit(form):
        form.populate_obj(page)
        page.slug = slugify(page.title)
        page.history = str(login.current_user.email) \
                       + ' updated site at ' \
                       + datetime.now().strftime('%m-%d-%Y %I:%M %p') \
                       + '\n' + _unidiff_output(last_edit, page.html) \
                       + '\n\n' + page.history
        db.session.merge(page)
        db.session.commit()
        return redirect(url_for('admin.page_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/pages/page.html", form=form)


@admin.route('/page/delete/<int:page_id>', methods=['POST'])
@check_login
@check_admin
def delete_page(page_id):
    page = Page.query.get_or_404(post_id)
    db.session.delete(page)
    db.session.commit()
    return redirect(url_for('admin.page_list'))


# Create the user routes
@admin.route('/user', methods=['GET'])
@check_login
@check_admin
def user_list():
    users = User.all()
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/users/list.html", users=users)


@admin.route('/user/create', methods=['GET', 'POST'])
@check_login
@check_admin
def create_user():
    form = CreateUserForm(request.form)
    if helpers.validate_form_on_submit(form):
        user = User()
        form.populate_obj(user)
        user.password = generate_password_hash(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('admin.user_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/users/user.html", form=form)


@admin.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
@check_login
@check_admin
def edit_user(user_id):
    user = User.query.get(user_id)
    old_pass = user.password
    user.password = None
    last_login = user.last_login_ip
    form = EditUserForm(request.form, obj=user)
    if helpers.validate_form_on_submit(form):
        
        form.populate_obj(user)

        if user.password == '':
            user.password = old_pass
        else:
            user.password = generate_password_hash(user.password)

        db.session.merge(user)
        db.session.commit()

        return redirect(url_for('admin.user_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/users/user.html", form=form, last_login=last_login)


@admin.route('/user/delete/<int:user_id>', methods=['POST'])
@check_login
@check_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin.user_list'))


# Create the role routes
@admin.route('/role', methods=['GET'])
@check_login
@check_admin
def role_list():
    roles = Role.all()
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/roles/list.html", roles=roles)

@admin.route('/role/create', methods=['GET', 'POST'])
@check_login
@check_admin
def create_role():
    form = CreateRoleForm(request.form)
    if helpers.validate_form_on_submit(form):
        role = Role()
        form.populate_obj(role)
        db.session.add(role)
        db.session.commit()
        return redirect(url_for('admin.role_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/roles/role.html", form=form)


@admin.route('/role/edit/<int:role_id>', methods=['GET', 'POST'])
@check_login
@check_admin
def edit_role(role_id):
    role = Role.query.get(role_id)
    form = EditRoleForm(request.form, obj=role)
    if helpers.validate_form_on_submit(form):
        form.populate_obj(role)
        db.session.merge(role)
        db.session.commit()
        return redirect(url_for('admin.role_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/roles/role.html", form=form)


@admin.route('/role/delete/<int:role_id>', methods=['POST'])
@check_login
@check_admin
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()
    return redirect(url_for('admin.role_list'))


# Create the comment routes
@admin.route('/comment', methods=['GET'])
@check_login
@has_role('editor')
def comment_list():
    comments = PostComment.all()
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/comments/list.html", comments=comments)

@admin.route('/comment/create', methods=['GET', 'POST'])
@check_login
@has_role('writer')
def create_comment():
    form = CreateCommentForm(request.form)
    if helpers.validate_form_on_submit(form):
        comment = PostComment()
        form.populate_obj(comment)
        comment.viewed = 1
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('admin.comment_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/comments/comment.html", form=form)


@admin.route('/comment/edit/<int:comment_id>', methods=['GET', 'POST'])
@check_login
@has_role('editor')
def edit_comment(comment_id):
    comment = PostComment.query.get(comment_id)
    form = EditCommentForm(request.form, obj=comment)
    if request.method == 'GET':
        comment.viewed = 1
        db.session.merge(comment)
        db.session.commit()
    if helpers.validate_form_on_submit(form):
        form.populate_obj(comment)
        db.session.merge(comment)
        db.session.commit()
        return redirect(url_for('admin.comment_list'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/comments/comment.html", form=form)


@admin.route('/comment/delete/<int:comment_id>', methods=['POST'])
@check_login
@check_admin
def delete_comment(comment_id):
    comment = PostComment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('admin.comment_list'))


@admin.route('/profile', methods=['GET', 'POST'])
@check_login
def edit_profile():
    user = login.current_user
    old_pass = user.password
    user.password = None
    form = EditProfileForm(request.form, obj=user)
    if helpers.validate_form_on_submit(form):
        form.populate_obj(user)

        if user.password == '':
            user.password = old_pass
        else:
            user.password = generate_password_hash(user.password)

        db.session.merge(user)
        db.session.commit()
        return redirect(url_for('site.index'))
    template_path = Themes.get_active('admin')
    return render_template(template_path + "/admin/edit_profile.html", form=form)


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = codecs.encode(word, 'translit/long')
        if word:
            result.append(word)
    return str(delim.join(result))

def _unidiff_output(expected, actual):
    """
    Helper function. Returns a string containing the unified diff of two multiline strings.
    """
    expected=expected.splitlines(1)
    actual=actual.splitlines(1)

    diff=difflib.unified_diff(expected, actual)

    return ''.join(diff)
