import os
import asyncio
from openai import AsyncOpenAI
from flask import Flask, Blueprint, request, render_template, redirect, url_for, session, jsonify
import markdown2  # For Markdown to HTML conversion

chat_bp = Blueprint('chat', __name__)

# Initialize AsyncOpenAI with your API key.
aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def get_chat_response(messages):
	response = await aclient.chat.completions.create(
		model="gpt-4o",
		messages=messages,
	)
	content = response.choices[0].message.content
	# If the content starts with # or contains any Markdown tags, convert it to HTML.
	if content.startswith('#') or any(tag in content for tag in ['*', '-', '`']):
		content = markdown2.markdown(content, extras=["tables"])
	return content

@chat_bp.route('/chat', methods=['GET'])
def chat():
	conversation = session.get('conversation', [])
	return render_template("chat.html", conversation=conversation)

@chat_bp.route('/chat', methods=['POST'])
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