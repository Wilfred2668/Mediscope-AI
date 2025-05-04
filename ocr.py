from PIL import Image
import easyocr
import os

# Initialize EasyOCR reader (this will download the model on first run)
reader = easyocr.Reader(['en'])

def extract_text_from_image(image_path):
    try:
        # Read the image
        result = reader.readtext(image_path)
        
        # Extract text from results
        text = ' '.join([item[1] for item in result])
        
        return text.strip() if text else None
            
    except Exception as e:
        print(f"Error in OCR: {e}")
        return None
