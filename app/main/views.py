"""
Routes and views for the main blueprint.
"""
from flask import (render_template, session, redirect, url_for, flash, request, 
                   current_app, abort, make_response)
from . import main
from ..models import (User, Permission, Recipe, Role, RecipeIngredient, Ingredient, 
                      RecipeStep, Comment)
from .. import db, recipe_imgs
from .forms import EditProfileForm, EditProfileAdminForm, RecipeForm, CommentForm
from flask_login import login_required, current_user
from flask_uploads import UploadNotAllowed
from ..decorators import admin_required, permission_required
from datetime import timedelta
from math import ceil


@main.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_recipes
    else:
        query = Recipe.query
    pagination = query.order_by(Recipe.timestamp.desc()).paginate(
        page, per_page=current_app.config['STOCKPOT_RECIPES_PER_PAGE'], 
        error_out=False)
    recipes = pagination.items
    return render_template('index.html', recipes=recipes,
                          show_followed=show_followed, pagination=pagination)


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp 


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = user.recipes.order_by(Recipe.timestamp.desc()).paginate(
        page, per_page=current_app.config['STOCKPOT_RECIPES_PER_PAGE'], 
        error_out=False)
    recipes = pagination.items
    return render_template('user.html', user=user, recipes=recipes,
                           pagination=pagination)


@main.route('/user/<username>/follow')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s' % username)
    return redirect(url_for('.user', username=username))



@main.route('/user/<username>/unfollow')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))



@main.route('/user/<username>/followers')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['STOCKPOT_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/user/<username>/followed-by')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['STOCKPOT_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/recipes/create', methods=['GET', 'POST'])
@login_required
def create_recipe(): 
    form = RecipeForm()
    default_img = current_app.config['STOCKPOT_DEFAULT_IMG']
    if request.method == 'POST':
        if current_user.can(Permission.WRITE_RECIPES) and \
            form.validate_on_submit():
            amounts = [ing.amount.data for ing in form.ingredients] 
            units = [ing.units.data for ing in form.ingredients] 
            names = [Ingredient(name=ing.ingredient.data['name']) for ing in form.ingredients]
            recipe_ings = []
            for item in zip(amounts, units, names):
                recipe_ings.append(RecipeIngredient(
                    amount=item[0],
                    units=item[1],
                    ingredient=item[2]
                ))
            steps = [RecipeStep(body=step.body.data) for step in form.steps]
            img = form.image.data
            filename = default_img
            # if the user didn't upload a file, use default filename
            # otherwise try to upload image
            if img.filename != '':
                try:
                    filename = recipe_imgs.save(img)
                except UploadNotAllowed:
                    flash('The upload was not allowed') 
                    return render_template('create_recipe.html', form=form)
            print(form.prep_time.data)
            recipe = Recipe(
                title=form.title.data,
                ingredients=recipe_ings,
                steps=steps, 
                author=current_user._get_current_object(),
                img_filename=filename, 
                prep_time=form.prep_time.data,
                cook_time=form.cook_time.data,
                description=form.description.data
            )
            db.session.add(recipe)
            return redirect(url_for('.user', username=current_user.username))
    return render_template('create_recipe.html', form=form, 
                          default_img=recipe_imgs.url(default_img))


@main.route('/recipes/<int:id>', methods=['GET', 'POST'])
def show_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                         recipe=recipe,
                         author=current_user._get_current_object())
        db.session.add(comment)
        flash('Your comment has been published.')
        return redirect(url_for('.show_recipe', id=recipe.id, page=-1))

    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = ceil(recipe.comments.count() / current_app.config['STOCKPOT_COMMENTS_PER_PAGE'])
    pagination = recipe.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['STOCKPOT_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('show_recipe.html', recipe=recipe, form=form,
                          comments=comments, pagination=pagination)


@main.route('/recipes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    if current_user != recipe.author and \
       not current_user.can(Permission.ADMINISTER):
        abort(403)

    form = RecipeForm(obj=recipe)
    if form.validate_on_submit():
        form.populate_obj(recipe)
        img = form.image.data
        filename = recipe.img_filename
        # if the user didn't upload a file, default to old filename
        # otherwise try to upload image
        if img.filename != '':
            try:
                filename = recipe_imgs.save(img)
            except UploadNotAllowed:
                flash('The upload was not allowed') 
                return render_template('edit_recipe.html', form=form, recipe=recipe)
        recipe.update_img(filename)
        db.session.add(recipe)
        flash('Recipe was successfully updated.')
        return redirect(url_for('.show_recipe', id=id))
    return render_template('edit_recipe.html', form=form, recipe=recipe)


@main.route('/recipes/<int:id>/delete')
@login_required
def delete_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    if current_user == recipe.author:
        db.session.delete(recipe)
    return redirect(request.referrer)


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['STOCKPOT_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                          pagination=pagination, page=page)


@main.route('/moderate/comment/<int:id>/enable')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/comment/<int:id>/disable')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
