import os
import asyncio
import logging
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import markdown2  # Add this import for Markdown to HTML conversion
from docx import Document  # Add this import for handling .docx files

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize AsyncOpenAI with your API key.
aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Async helper function to get chat response using the new OpenAI API interface.
async def get_chat_response(messages):
    response = await aclient.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    content = response.choices[0].message.content
    # Check if the response is in Markdown format
    if content.startswith('#') or any(tag in content for tag in ['*', '-', '`']):
        content = markdown2.markdown(content, extras=["tables"])
    return content

@app.route('/')
def index():
    # Display the current OpenAI version.
    session.clear()
    openai_version = openai.__version__
    logger.debug("Index page loaded, OpenAI version: %s", openai_version)
    return render_template("index.html", version=openai_version)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Clear the session to start a new conversation
    logger.debug("Session cleared")  # Debug statement
    session.clear()
    logger.debug("Upload page loaded, session cleared")
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = file.filename
            file_info = f"Uploaded file: {filename}, Size: {len(file.read())} bytes"
            file.seek(0)  # Reset file pointer to the beginning
            if filename.endswith('.docx'):
                document = Document(file)
                content = '\n'.join([para.text for para in document.paragraphs])
            else:
                content = file.read().decode('utf-8')
            # Initialize the conversation with the file content as context.
            session['conversation'] = [
                {'role': 'system', 'content': f'The following is the file content:\n{content}'},
                {'role': 'system', 'content': file_info}
            ]
            logger.debug("New conversation initialized with file info: %s", file_info)  # Debug statement
            #return redirect(url_for('chat'))
        return "No file uploaded", 400

    return render_template("upload.html")

@app.route('/chat', methods=['GET'])
def chat():
    conversation = session.get('conversation', [])
    logger.debug("Current conversation: %s", conversation)  # Debug statement
    return render_template("chat.html", conversation=conversation)

@app.route('/chat', methods=['POST'])
def chat_post():
    conversation = session.get('conversation', [])
    user_message = request.form.get('message')
    if user_message:
        conversation.append({'role': 'user', 'content': user_message})
        logger.debug("User message added: %s", user_message)  # Log user message
        try:
            # Run the asynchronous API call using asyncio.run.
            assistant_message = asyncio.run(get_chat_response(conversation))
            conversation.append({'role': 'assistant', 'content': assistant_message})
            logger.debug("Assistant message added: %s", assistant_message)  # Log assistant message
        except Exception as e:
            error_text = f"Error: {str(e)}"
            conversation.append({'role': 'assistant', 'content': error_text})
            logger.error("Error occurred: %s", error_text)  # Log error
        session['conversation'] = conversation
        logger.debug("Updated conversation: %s", conversation)  # Log updated conversation
    return jsonify(conversation)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
