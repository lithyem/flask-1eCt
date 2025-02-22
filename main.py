import os
import re
import asyncio
import logging
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import markdown2  # For Markdown to HTML conversion
from docx import Document  # For handling .docx files

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create an in-memory logging handler to store debug logs.
class InMemoryHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_records = []

    def emit(self, record):
        log_entry = self.format(record)
        self.log_records.append(log_entry)
        # Limit stored logs to the most recent 100 entries
        if len(self.log_records) > 100:
            self.log_records.pop(0)

# Initialize and add the in-memory handler to our logger.
in_memory_handler = InMemoryHandler()
in_memory_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
in_memory_handler.setFormatter(formatter)
logger.addHandler(in_memory_handler)

# Revised function to sanitize text:
# 1. Removes BOM if present.
# 2. Removes control characters (ASCII 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F) except newline (\n), carriage return (\r) and tab (\t).
# 3. Removes Unicode line and paragraph separators (U+2028 and U+2029) that can break JavaScript.
def sanitize_text(text):
    # Remove Byte Order Mark (BOM)
    text = text.lstrip('\ufeff')
    # Remove unwanted ASCII control characters.
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
    # Remove Unicode line separator and paragraph separator.
    text = re.sub(u'[\u2028\u2029]', '', text)
    return text

# Initialize AsyncOpenAI with your API key.
aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Async helper function to get chat response using the new OpenAI API interface.
async def get_chat_response(messages):
    response = await aclient.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    content = response.choices[0].message.content
    # Check if the response is in Markdown format.
    if content.startswith('#') or any(tag in content for tag in ['*', '-', '`']):
        content = markdown2.markdown(content, extras=["tables"])
    return content

@app.route('/')
def index():
    # Display the current OpenAI version.
    session.clear()
    openai_version = openai.__version__
    logger.debug("Index page loaded, OpenAI version: %s", openai_version)
    app.logger.debug("Index page loaded, OpenAI version: %s", openai.__version__)
    return render_template("index.html", version=openai_version)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Clear the session to start a new conversation.
    logger.debug("Session cleared")
    session.clear()
    logger.debug("Upload page loaded, session cleared")
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = file.filename
            # Read file content once to determine file size.
            file_bytes = file.read()
            file_info = f"Uploaded file: {filename}, Size: {len(file_bytes)} bytes"
            file.seek(0)  # Reset file pointer to beginning.
            # Process file based on its type.
            if filename.lower().endswith('.docx'):
                document = Document(file)
                content = '\n'.join([para.text for para in document.paragraphs])
            else:
                content = file.read().decode('utf-8', errors='replace')
            # Sanitize the file content and file_info.
            content = sanitize_text(content)
            file_info = sanitize_text(file_info)
            # Escape HTML characters.
            content = content.replace("<", "&lt;").replace(">", "&gt;")
            file_info = file_info.replace("<", "&lt;").replace(">", "&gt;")
            # Initialize the conversation with the sanitized file content as context.
            session['conversation'] = [
                {'role': 'system', 'content': f'The following is the file content:\n{content}'},
                {'role': 'system', 'content': file_info}
            ]
            logger.debug("New conversation initialized with file info: %s", file_info)
            return redirect(url_for('chat'))
        return "No file uploaded", 400

    return render_template("upload.html")

@app.route('/chat', methods=['GET'])
def chat():
    conversation = session.get('conversation', [])
    logger.debug("Current conversation: %s", conversation)
    return render_template("chat.html", conversation=conversation)

@app.route('/chat', methods=['POST'])
def chat_post():
    conversation = session.get('conversation', [])
    user_message = request.form.get('message')
    if user_message:
        conversation.append({'role': 'user', 'content': user_message})
        logger.debug("User message added: %s", user_message)
        try:
            # Run the asynchronous API call using asyncio.run.
            assistant_message = asyncio.run(get_chat_response(conversation))
            conversation.append({'role': 'assistant', 'content': assistant_message})
            logger.debug("Assistant message added: %s", assistant_message)
        except Exception as e:
            error_text = f"Error: {str(e)}"
            conversation.append({'role': 'assistant', 'content': error_text})
            logger.error("Error occurred: %s", error_text)
        session['conversation'] = conversation
        logger.debug("Updated conversation: %s", conversation)
    # Retrieve the latest debug logs (last 20 entries).
    debug_logs = in_memory_handler.log_records[-20:]
    return jsonify({
        'conversation': conversation,
        'debug_logs': debug_logs
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
