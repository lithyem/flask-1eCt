import os
import asyncio
import openai
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')
openai.api_key = os.environ.get("OPENAI_API_KEY")

@app.route('/')
def index():
    return render_template_string("""
    <h1>Welcome to the File-Chat App</h1>
    <p><a href="{{ url_for('upload') }}">Upload a file to start a conversation</a></p>
    """)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            content = file.read().decode('utf-8')
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
                # Use asyncio.run to call the asynchronous acreate method
                response = asyncio.run(
                    openai.ChatCompletion.acreate(
                        model="gpt-3.5-turbo",
                        messages=conversation
                    )
                )
                assistant_message = response['choices'][0]['message']['content']
                conversation.append({'role': 'assistant', 'content': assistant_message})
            except Exception as e:
                conversation.append({'role': 'assistant', 'content': f"Error: {str(e)}"})
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
