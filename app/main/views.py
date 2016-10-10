"""
Routes and views for the main blueprint.
"""
from flask import render_template, session, redirect, url_for, flash, request
from . import main
from ..models import User, Permission, Recipe, Role, RecipeIngredient, Ingredient, \
        RecipeStep
from .. import db
from .forms import EditProfileForm, EditProfileAdminForm, RecipeForm
from flask_login import login_required, current_user
from ..decorators import admin_required


@main.route('/', methods=['GET', 'POST'])
def index():
    recipes = Recipe.query.order_by(Recipe.timestamp.desc()).all()
    return render_template('index.html', recipes=recipes)


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    recipes = user.recipes.order_by(Recipe.timestamp.desc()).all()
    return render_template('user.html', user=user, recipes=recipes)


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
        recipe = Recipe(
            title=form.title.data,
            ingredients=recipe_ings,
            steps=steps, 
            author=current_user._get_current_object()
        )
        db.session.add(recipe)
        return redirect(url_for('.user', username=current_user.username))
    return render_template('create_recipe.html', form=form)


@main.route('/recipes/<int:id>')
def show_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    return render_template('show_recipe.html', recipe=recipe)


@main.route('/recipes/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    form = RecipeForm(obj=recipe)
    if form.validate_on_submit() and current_user == recipe.author:
        form.populate_obj(recipe)
        db.session.add(recipe)
        flash('Recipe was successfully updated.')
        return redirect(url_for('.show_recipe', id=id))
    return render_template('edit_recipe.html', form=form)


@main.route('/recipes/<int:id>/delete')
@login_required
def delete_recipe(id):
    recipe = Recipe.query.get_or_404(id)
    if current_user == recipe.author:
        db.session.delete(recipe)
    return redirect(request.referrer)
