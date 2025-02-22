import os
import re
import asyncio
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import markdown2  # For Markdown to HTML conversion
from docx import Document  # For handling .docx files

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

def sanitize_text(text):
    # Remove BOM, unwanted control characters, and Unicode separators.
    text = text.lstrip('\ufeff')
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
    text = re.sub(u'[\u2028\u2029]', '', text)
    return text

def split_into_chunks(text, chunk_size=8000):
    # Split text into blocks of up to chunk_size characters.
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# Initialize AsyncOpenAI with your API key.
aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
            # Split the content into 8000-character chunks.
            chunks = split_into_chunks(content, 8000)
            # Store chunks and initialize chunk pointer.
            session['file_chunks'] = chunks
            session['chunk_index'] = 0
            # Initialize conversation with the file info message.
            session['conversation'] = [{'role': 'system', 'content': file_info}]
            return redirect(url_for('chat'))
        return "No file uploaded", 400
    return render_template("upload.html")

@app.route('/send_chunk', methods=['POST'])
def send_chunk():
    file_chunks = session.get('file_chunks', [])
    chunk_index = session.get('chunk_index', 0)
    conversation = session.get('conversation', [])
    if chunk_index < len(file_chunks):
        chunk = file_chunks[chunk_index]
        # Append the next file chunk as a system message.
        conversation.append({
            'role': 'system',
            'content': f"File chunk {chunk_index+1}/{len(file_chunks)}:\n{chunk}"
        })
        try:
            assistant_message = asyncio.run(get_chat_response(conversation))
            conversation.append({'role': 'assistant', 'content': assistant_message})
        except Exception as e:
            conversation.append({'role': 'assistant', 'content': f"Error: {str(e)}"})
        session['chunk_index'] = chunk_index + 1
        session['conversation'] = conversation
        return jsonify({
            'conversation': conversation,
            'chunk_remaining': len(file_chunks) - session['chunk_index']
        })
    else:
        return jsonify({
            'conversation': conversation,
            'chunk_remaining': 0
        })

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
            conversation.append({'role': 'assistant', 'content': f"Error: {str(e)}"})
        session['conversation'] = conversation
    return jsonify({'conversation': conversation})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
