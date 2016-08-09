"""
Routes and views for the main blueprint.
"""
from flask import render_template, session, redirect, url_for
from . import main


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')
