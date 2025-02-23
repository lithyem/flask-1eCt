import re

def sanitize_text(text):
	"""
	Remove BOM, unwanted control characters, and Unicode line/paragraph separators.
	"""
	text = text.replace("<", "&lt;").replace(">", "&gt;")
 	text = text.lstrip('\ufeff')
	text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)
	text = re.sub(u'[\u2028\u2029]', '', text)
	return text
