import unittest
from flask import current_app, url_for, session
from app.models import User
from app import create_app, db
from flask_login import current_user, login_user


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    
    def register(self, email, username, password, password2):
        with self.app.test_request_context():
            return self.client.post(url_for('auth.register'), data=dict(
                email=email,
                username=username,
                password=password,
                password2=password2
            ))


    def login(self, email, password):
        with self.app.test_request_context():
            return self.client.post(url_for('auth.login'), data=dict(
                email=email,
                password=password
            ), follow_redirects=True)


    def logout(self):
        with self.app.test_request_context():
            return self.client.get(url_for('auth.logout'), follow_redirects=True)


    def test_register_login_logout_user(self):
        username = 'test'
        password = 'test'
        email = 'test@example.com'
        
        # test user registration
        response = self.register(email, username, password, password)
        self.assertEqual(response.status_code, 302)
        
        # test user login
        response = self.login(email, password)
        data = response.get_data(as_text=True)
        self.assertTrue('Log Out' in data)

        # test user logout
        response = self.logout()
        data = response.get_data(as_text=True)
        self.assertTrue('You have been logged out' in data)


    def test_register_existant_user(self):
        username = 'test'
        email = 'test@example.com'
        password = 'test'
        u = User(username=username, email=email, password=password)
        db.session.add(u)
        db.session.commit()
        response = self.register(email, username, password, password)
        data = response.get_data(as_text=True)
        self.assertTrue('Email already registered' in data)
        self.assertTrue('Username already in use' in data)


    def test_register_different_passwords(self):
        username = 'test'
        email = 'test@example.com'
        password = 'test'
        password2 = 'something else'
        u = User(username=username, email=email, password=password)
        db.session.add(u)
        db.session.commit()
        response = self.register(email, username, password, password2)
        data = response.get_data(as_text=True)
        self.assertTrue('Passwords must match' in data)

