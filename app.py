# app.py
from flask import Flask, render_template, request, send_file, session, redirect, url_for
import google.generativeai as genai
import re
import os
import time
from tts import speak_text
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure Gemini
# Use gemini-2.0-flash for image OCR
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', "AIzaSyDbqPytq3qe7I71KWNmYgKhhEO8Xta9MKo")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Prompt Template
PROMPT_TEMPLATE = """
You are a healthcare assistant. The user will give you a medicine name.
Your job is to return a short but complete usage guide including:
Make unique start (dont start with only "Okay"), give response as a person is speaking

1. Medicine Name
2. Purpose / Condition it treats
3. Dosage (for adults)
4. When to take (before/after food, time of day)
5. Warnings (if any)
6. Common side effects
7. Alternatives (if any)

Give text not as markdown and each point in new line
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
                    try:
                        # Read image as bytes
                        with open(filepath, "rb") as img_file:
                            image_bytes = img_file.read()
                        # Use Gemini to extract text
                        gemini_response = model.generate_content([
                            "Extract all the text from this image.",
                            {"mime_type": f"image/{filename.rsplit('.', 1)[1].lower()}", "data": image_bytes}
                        ])
                        medicine_name = gemini_response.text.strip()
                        if not medicine_name:
                            error = "Could not extract text from the image. Please try again or enter the medicine name manually."
                            return render_template('index.html', result=result, audio_file=audio_file, timestamp=timestamp, error=error)
                    except Exception as e:
                        error = f"Error extracting text from image: {e}"
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

