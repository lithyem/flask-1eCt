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

talk_bp = Blueprint('talk', __name__)

@talk_bp.route('/talk', methods=['GET'])
def talk():
	return('talk')