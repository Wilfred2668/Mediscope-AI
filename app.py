from flask import Flask, render_template, request, send_file, session, redirect, url_for, jsonify
import google.generativeai as genai
import re
import os
import time
from tts import speak_text, text_to_speech
from ocr import extract_text_from_image
from werkzeug.utils import secure_filename
import json
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY', "AIzaSyDbqPytq3qe7I71KWNmYgKhhEO8Xta9MKo"))
model = genai.GenerativeModel("gemini-1.5-flash")

# Prompt Template
PROMPT_TEMPLATE = """
You are a healthcare assistant. The user will give you a medicine name.
Your job is to return a short but complete usage guide including:
Make unique start (dont start with only "Okay"), give responses like you are speaking

1. Medicine Name
2. Purpose / Condition it treats
3. Dosage (for adults)
4. When to take (before/after food, time of day)
5. Warnings (if any)
6. Common side effects

Keep it under 100 words and very clear. Respond in plain, spoken English.
Medicine: {}
"""

# Remove Markdown for TTS
def clean_markdown_for_tts(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    audio_file = 'static/audio.mp3'
    timestamp = None
    error = None

    if request.method == 'POST':
        medicine_name = None
        
        # Check if an image was uploaded
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:  # Check if a file was actually selected
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Extract text from image using OCR
                    medicine_name = extract_text_from_image(filepath)
                    if not medicine_name:
                        error = "Could not extract text from the image. Please try again or enter the medicine name manually."
                        return render_template('index.html', result=result, audio_file=audio_file, timestamp=timestamp, error=error)
                else:
                    error = "Invalid file type. Please upload a PNG, JPG, or JPEG image."
                    return render_template('index.html', result=result, audio_file=audio_file, timestamp=timestamp, error=error)
        
        # If no image was uploaded or OCR failed, check for text input
        if not medicine_name and 'medicine' in request.form:
            medicine_name = request.form['medicine'].strip()
        
        if not medicine_name:
            error = "Please enter a medicine name or upload an image."
            return render_template('index.html', result=result, audio_file=audio_file, timestamp=timestamp, error=error)

        # Process the medicine name
        prompt = PROMPT_TEMPLATE.format(medicine_name)
        response = model.generate_content(prompt)
        result = response.text.strip()

        # Clean the response to be suitable for TTS (text-to-speech)
        cleaned_result = clean_markdown_for_tts(result)
        speak_text(cleaned_result)

        # Create a unique timestamp to force browser to reload audio
        timestamp = int(time.time())

    return render_template('index.html', result=result, audio_file=audio_file, timestamp=timestamp, error=error)

@app.route('/audio')
def audio():
    return send_file('static/audio.mp3', mimetype='audio/mpeg')

@app.route('/search', methods=['POST'])
def search():
    try:
        medicine_name = None
        
        # Check for image upload
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    image.save(temp_file.name)
                    medicine_name = extract_text_from_image(temp_file.name)
                    os.unlink(temp_file.name)  # Clean up the temporary file
                
                if not medicine_name:
                    return jsonify({'error': 'Could not extract text from image. Please try again or enter the medicine name manually.'})
        
        # If no image or image processing failed, check for text input
        if not medicine_name and 'medicine' in request.form:
            medicine_name = request.form['medicine'].strip()
        
        if not medicine_name:
            return jsonify({'error': 'Please enter a medicine name or upload an image.'})
        
        # Search in medicine data
        medicine_info = None
        with open('meds.json', 'r', encoding='utf-8') as f:
            medicine_data = json.load(f)
        
        for med in medicine_data:
            if medicine_name.lower() in med['name'].lower():
                medicine_info = med
                break
        
        if not medicine_info:
            return jsonify({'error': f'No information found for {medicine_name}.'})
        
        # Generate detailed instructions using Gemini
        prompt = f"""Generate detailed usage instructions for {medicine_info['name']} based on this information:
        Category: {medicine_info['category']}
        Description: {medicine_info['description']}
        Usage: {medicine_info['usage']}
        
        Include:
        1. Proper dosage instructions
        2. When to take the medicine
        3. Important precautions
        4. Possible side effects
        5. Storage instructions
        6. What to do if a dose is missed
        
        Format the response in clear, easy-to-understand language."""
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        detailed_instructions = response.text
        
        # Generate audio
        audio_path = text_to_speech(detailed_instructions)
        
        return jsonify({
            'name': medicine_info['name'],
            'category': medicine_info['category'],
            'description': medicine_info['description'],
            'usage': medicine_info['usage'],
            'detailed_instructions': detailed_instructions,
            'audio_path': audio_path
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
