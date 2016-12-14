"""
Contains the SQLAlchemy classes for the Role and User models
"""
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from . import db, login_manager, recipe_imgs
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from datetime import datetime
import hashlib
import os
from faker import Faker
from random import randint, choice

class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_RECIPES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x08


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')


    def __repr__(self):
        return '<Role %r>' % self.name

    
    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_RECIPES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_RECIPES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()


class Recipe(db.Model):
    __tablename__ = 'recipes'
    INGREDIENT_LIMIT = 10
    STEP_LIMIT = 10

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    img_filename = db.Column(db.String(256))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy='dynamic')
    steps = db.relationship('RecipeStep', backref='recipe', lazy='dynamic')
    prep_time = db.Column(db.Interval)
    cook_time = db.Column(db.Interval)
    description = db.Column(db.Text)


    @property
    def img_src(self):
        return recipe_imgs.url(self.img_filename)
    

    @property
    def img_path(self):
        return recipe_imgs.path(self.img_filename)


    def delete_img(self):
        if self.img_filename != current_app.config['STOCKPOT_DEFAULT_IMG']:
            os.remove(self.img_path)


    def update_img(self, filename):
        if filename != self.img_filename:
            self.delete_img()
        self.img_filename = filename


    @classmethod
    def generate_fake(cls, count=100):
        fake = Faker()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count-1)).first()
            
            ingredients = []
            for j in range(randint(1, cls.INGREDIENT_LIMIT)):
                ingredients.append(RecipeIngredient(
                    amount=randint(1,10),
                    units=choice(current_app.config['RECIPE_UNITS']),
                    ingredient=Ingredient(name=fake.word())
                ))

            steps = []
            for k in range(randint(1, cls.STEP_LIMIT)):
                steps.append(RecipeStep(body=fake.text()))

            r = Recipe(
                title=fake.word(),
                ingredients=ingredients,
                steps=steps,
                author=u,
                img_filename=current_app.config['STOCKPOT_DEFAULT_IMG'],
                description=fake.text()
            )


# clean up function for Recipe instance before deletion
@event.listens_for(Recipe, 'before_delete')
def recipe_before_delete(mapper, connection, target):
    target.delete_img()


class RecipeStep(db.Model):
    __tablename__ = 'recipesteps'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'))


class RecipeIngredient(db.Model):
    __tablename__ = 'recipeingredients'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    units = db.Column(db.String(64))
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'))
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'))


class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    recipe_ingredients = db.relationship('RecipeIngredient', backref='ingredient', lazy='dynamic')


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), 
                           primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                           primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    recipes = db.relationship('Recipe', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')


    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['STOCKPOT_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        self.follow(self)


    def __repr__(self):
        return '<User %r>' % self.username
    
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')


    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)


    @property
    def followed_recipes(self):
        # join recipe rows with follow table by matching followed_id to author_id
        # then select the rows where the follower is the user instance
        return Recipe.query.join(Follow, Follow.followed_id == Recipe.author_id)\
                .filter(Follow.follower_id == self.id)


    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})


    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True


    def can(self, permissions):
        return self.role is not None and \
                (self.role.permissions & permissions) == permissions


    def is_administrator(self):
        return self.can(Permission.ADMINISTER)


    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)


    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hashed = self.avatar_hash or hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hashed}?s={size}&d={default}&r={rating}'.format(
            url=url, hashed=hashed, size=size, default=default, rating=rating)


    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)


    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)


    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None


    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None


    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()


    @staticmethod
    def generate_fake(count=100):
        fake = Faker()

        for i in range(count):
            u = User(
                email=fake.email(),
                username=fake.user_name(),
                password=fake.word(),
                confirmed=True,
                name=fake.name(),
                location=fake.city(),
                about_me=fake.text(),
                member_since=fake.date_time_this_century(
                    before_now=True,after_now=False, tzinfo=None))
            db.session.add(u)
            try:
                db.session.commit()
            except:
                db.session.rollback()



class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False


    def is_administrator(self):
        return False


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


login_manager.anonymous_user = AnonymousUser
