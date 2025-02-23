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

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

# Initialize AsyncOpenAI with your API key.
aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Async helper function to get chat response using the new OpenAI API interface.
async def get_chat_response(messages):
    response = await aclient.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    content = response.choices[0].message.content
    if content.startswith('#') or any(tag in content for tag in ['*', '-', '`']):
        content = markdown2.markdown(content, extras=["tables"])
    return content

@app.route('/')
def index():
    session.clear()
    return render_template("index.html")

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    session.clear()
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            truncate_length = request.form.get('truncate_length', default=8000, type=int)
            filename = file.filename
            file_bytes = file.read()
            file_info = f"Uploaded file: {filename}, Size: {len(file_bytes)} bytes"
            file.seek(0)
            if filename.lower().endswith('.docx'):
                document = Document(file)
                content = '\n'.join([para.text for para in document.paragraphs])
            else:
                content = file.read().decode('utf-8', errors='replace')
            content = sanitize_text(content)
            file_info = sanitize_text(file_info)
            content = content.replace("<", "&lt;").replace(">", "&gt;")
            file_info = file_info.replace("<", "&lt;").replace(">", "&gt;")
            # Truncate content to the first 1000 characters.
            truncated_content = content[:truncate_length]
            session['conversation'] = [
                {'role': 'system', 'content': f'The following is the file content (truncated to {truncate_length} characters):\n{truncated_content}'},
                {'role': 'system', 'content': file_info}
            ]
            return redirect(url_for('chat'))
        return "No file uploaded", 400

    return render_template("upload.html")

@app.route('/chat', methods=['GET'])
def chat():
    conversation = session.get('conversation', [])
    return render_template("chat.html", conversation=conversation)

@app.route('/chat', methods=['POST'])
def chat_post():
    conversation = session.get('conversation', [])
    user_message = request.form.get('message')
    if user_message:
        conversation.append({'role': 'user', 'content': user_message})
        try:
            assistant_message = asyncio.run(get_chat_response(conversation))
            conversation.append({'role': 'assistant', 'content': assistant_message})
        except Exception as e:
            error_text = f"Error: {str(e)}"
            conversation.append({'role': 'assistant', 'content': error_text})
        session['conversation'] = conversation
    return jsonify({
        'conversation': conversation
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
