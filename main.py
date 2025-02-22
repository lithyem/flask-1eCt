import os
import re
import asyncio
import unicodedata
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import markdown2  # For Markdown to HTML conversion
from docx import Document  # For handling .docx files

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

def sanitize_text(text):
    """
    Sanitize text by:
    1. Removing BOM if present.
    2. Removing unwanted ASCII control characters (except newline, carriage return, and tab).
    3. Removing Unicode line and paragraph separators.
    """
    text = text.lstrip('\ufeff')
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
    text = re.sub(u'[\u2028\u2029]', '', text)
    return text

def split_into_chunks(text, chunk_size=8000):
    """
    Split text into chunks of at most chunk_size characters.
    """
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

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
            filename = file.filename
            # Read file bytes to get size info.
            file_bytes = file.read()
            file_info = f"Uploaded file: {filename}, Size: {len(file_bytes)} bytes"
            # Reset file pointer to beginning.
            file.seek(0)
            # Process .docx files separately.
            if filename.lower().endswith('.docx'):
                document = Document(file)
                content = '\n'.join([para.text for para in document.paragraphs])
            else:
                # For other files, decode as UTF-8.
                content = file.read().decode('utf-8', errors='replace')
            # Sanitize and escape the content.
            content = sanitize_text(content)
            file_info = sanitize_text(file_info)
            content = content.replace("<", "&lt;").replace(">", "&gt;")
            file_info = file_info.replace("<", "&lt;").replace(">", "&gt;")
            
            # Split the full content into chunks of at most 8000 characters.
            chunks = split_into_chunks(content, 8000)
            system_messages = []
            for i, chunk in enumerate(chunks):
                system_messages.append({
                    'role': 'system',
                    'content': f"File chunk {i+1}/{len(chunks)}:\n{chunk}"
                })
            # Also add the file information as a system message.
            system_messages.append({'role': 'system', 'content': file_info})
            
            # Save the conversation (system messages) in session.
            session['conversation'] = system_messages
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
