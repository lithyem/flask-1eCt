from flask import Flask, Blueprint, request, render_template, redirect, url_for, session, jsonify
from docx import Document  # For handling .docx files
from utils import sanitize_text

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['GET', 'POST'])
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
            return redirect(url_for("chat.chat"))
        return "No file uploaded", 400

    return render_template("upload.html")