from . import deezer_service
from flask import (
    session, render_template, redirect, request, url_for, send_file
)

@deezer_service.route('/')
def index():
    return 'deezer'
