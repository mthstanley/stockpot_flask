from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, FormField, FieldList, IntegerField, FloatField, FileField
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from ..models import Role, User, RecipeStep, RecipeIngredient, Ingredient
from .fields import DurationField, TIME_REGEX
from datetime import timedelta
from flask import current_app


class EditProfileForm(Form):
    name = StringField('Real Name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          'Usernames must have only letters, '
                                          'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class IngredientForm(Form):
    name = StringField('Name', validators=[Required(), Length(1, 64)], render_kw={'placeholder':'e.g. Carrots'})


class RecipeIngredientForm(Form):
    amount = FloatField('Amount', validators=[Required()], render_kw={'placeholder':'e.g. 1'})
    units = SelectField(
        'Units', 
        choices=[(unit, unit) for unit in current_app.config['RECIPE_UNITS']]
    )
    ingredient = FormField(IngredientForm)


class StepForm(Form):
    body = TextAreaField('Step')


class RecipeForm(Form):
    title = StringField('What are we cooking?', validators=[Required(), Length(1, 64)])
    image = FileField('Upload an image')
    prep_time = DurationField('Prep Time', default=timedelta())
    cook_time = DurationField('Cook Time', default=timedelta())
    description = TextAreaField('Description')
    # define defualt factory functions for ingredients and steps so that when
    # they are appended to the form wtforms knows how to add them to the
    # sqlalchemy object and then populate them
    ingredients = FieldList(FormField(
        RecipeIngredientForm, 
        default=lambda: RecipeIngredient(ingredient=Ingredient())
    ), min_entries=1)
    steps = FieldList(FormField(StepForm, default=lambda: RecipeStep()), min_entries=1)
    submit = SubmitField('Submit')


    def validate_cook_time(self, field):
        # if field data is none then field's process_formdata
        # time regex did not match meaning the field has invalid input
        if field.data is None:
            raise ValidationError('Enter valid cook time.')


    def validate_prep_time(self, field):
        # if field data is none then field's process_formdata
        # time regex did not match meaning the field has invalid input
        if field.data is None:
            raise ValidationError('Enter valid prep time.')


class CommentForm(Form):
    body = StringField('', validators=[Required()])
    submit = SubmitField('Submit')
