import os
import re
import asyncio
import unicodedata
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, Blueprint, request, render_template, redirect, url_for, session, jsonify
import markdown2  # For Markdown to HTML conversion
from docx import Document  # For handling .docx files
from utils import sanitize_text
from talk import talk_bp
from chat import chat_bp
from upload import upload_bp

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

@app.route('/')
def index():
    session.clear()
    return render_template("index.html")

app.register_blueprint(talk_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(upload_bp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
