import os
import asyncio
from openai import AsyncOpenAI
import openai  # For accessing openai.__version__
from flask import Flask, request, render_template_string, redirect, url_for, session

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
    # Access the content attribute directly.
    return response.choices[0].message.content

@app.route('/')
def index():
    # Display the current OpenAI version.
    openai_version = openai.__version__
    return render_template_string("""
    <h1>Welcome to the File-Chat App</h1>
    <p>Current OpenAI version installed: {{ version }}</p>
    <p><a href="{{ url_for('upload') }}">Upload a file to start a conversation</a></p>
    """, version=openai_version)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            content = file.read().decode('utf-8')
            # Initialize the conversation with the file content as context.
            session['conversation'] = [
                {'role': 'system', 'content': f'The following is the file content:\n{content}'}
            ]
            return redirect(url_for('chat'))
        return "No file uploaded", 400

    return render_template_string("""
    <h1>Upload a File</h1>
    <form method="post" enctype="multipart/form-data">
        <p><input type="file" name="file" required></p>
        <p><input type="submit" value="Upload"></p>
    </form>
    """)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    conversation = session.get('conversation', [])
    
    if request.method == 'POST':
        user_message = request.form.get('message')
        if user_message:
            conversation.append({'role': 'user', 'content': user_message})
            try:
                # Run the asynchronous API call using asyncio.run.
                assistant_message = asyncio.run(get_chat_response(conversation))
                conversation.append({'role': 'assistant', 'content': assistant_message})
            except Exception as e:
                error_text = f"Error: {str(e)}"
                conversation.append({'role': 'assistant', 'content': error_text})
            session['conversation'] = conversation

    return render_template_string("""
    <h1>Chat</h1>
    <div style="border:1px solid #ccc; padding: 10px; max-height:300px; overflow:auto;">
      {% for msg in conversation %}
         <p><strong>{{ msg.role.capitalize() }}:</strong> {{ msg.content|e }}</p>
      {% endfor %}
    </div>
    <form method="post">
         <p><input type="text" name="message" placeholder="Type your message" required style="width: 80%;"></p>
         <p><input type="submit" value="Send"></p>
    </form>
    <p><a href="{{ url_for('upload') }}">Upload another file</a></p>
    """, conversation=conversation)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
