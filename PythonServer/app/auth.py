from flask import Blueprint, render_template, redirect, url_for, request, flash


authEndPoint = Blueprint('auth', __name__)
@authEndPoint.route('/login')
def login():
    return render_template('login.html')