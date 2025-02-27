from flask import Flask, Blueprint, request, render_template, redirect, url_for, session, jsonify
from docx import Document  # For handling .docx files
from utils import sanitize_text
from PyPDF2 import PdfReader

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():
	
	if request.method == 'POST':
		file = request.files.get('file')
		if file:
			truncate_length = 8000
			filename = file.filename
			file_bytes = file.read()
			file_info = f"Uploaded file: {filename}, Size: {len(file_bytes)} bytes"
			file.seek(0)
			if filename.lower().endswith('.docx'):
				document = Document(file)
				content = '\n'.join([para.text for para in document.paragraphs])
			elif filename.lower().endswith('.pdf'):
				reader = PdfReader(file)
				texts = []
				for page in reader.pages:
					text = page.extract_text()
					if text:
						texts.append(text)
				content = "\n".join(texts)
			else:
				content = file.read().decode('utf-8', errors='replace')
			content = sanitize_text(content)
			file_info = sanitize_text(file_info)
			truncated_content = content[:truncate_length]
			session['conversation'] = [
				{'role': 'system', 'content': f'The following is the file content (truncated to {truncate_length} characters):\n{truncated_content}'},
				{'role': 'system', 'content': file_info}
			]
			return redirect(url_for("chat.chat"))
		return "No file uploaded", 400
	else:
		session.clear()
	return render_template("upload.html")