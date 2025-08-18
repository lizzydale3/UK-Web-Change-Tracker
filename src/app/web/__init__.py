from __future__ import annotations
from flask import Blueprint, render_template

bp = Blueprint("web", __name__, template_folder="templates")

@bp.get("/")
def index():
    return render_template("index.html")

@bp.get("/dashboard")
def dashboard():
    return render_template("pages/dashboard.html")

@bp.get("/http")
def http_page():
    return render_template("pages/http_page.html")

@bp.get("/l3")
def l3_page():
    return render_template("pages/l3_page.html")

@bp.get("/ooni")
def ooni_page():
    return render_template("pages/ooni_page.html")

@bp.get("/bot")
def bot_page():
    return render_template("pages/bot_page.html")

@bp.get("/domains")
def domains_page():
    return render_template("pages/domains_page.html")

@bp.get("/trends")
def trends_page():
    return render_template("pages/trends_page.html")

def register_web(app):
    app.register_blueprint(bp)
