import os
import openai
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
# Use an environment variable for the secret key (or default to a fallback, though this is not recommended for production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret')

# Set your OpenAI API key from an environment variable
openai.api_key = "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"

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
            # Read file content (assuming it's a text file) and decode it.
            content = file.read().decode('utf-8')
            # Initialize the conversation with a system message containing the file content.
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
                # Call the OpenAI Chat API with the conversation history.
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=conversation
                )
                assistant_message = response['choices'][0]['message']['content']
                conversation.append({'role': 'assistant', 'content': assistant_message})
            except Exception as e:
                # Log the error and also display it in the chat interface for debugging.
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

    conversation = session.get('conversation', [])
    
    if request.method == 'POST':
        user_message = request.form.get('message')
        if user_message:
            conversation.append({'role': 'user', 'content': user_message})
            # Call the OpenAI Chat API with the conversation history.
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation
            )
            assistant_message = response['choices'][0]['message']['content']
            conversation.append({'role': 'assistant', 'content': assistant_message})
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
    # Railway provides the PORT environment variable. Default to 5000 if not set.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
