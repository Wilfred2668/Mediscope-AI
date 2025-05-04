import requests

def extract_text_from_image(filename, api_key = 'K88961227488957', language='eng'):
    try:
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': language,
        }
        with open(filename, 'rb') as f:
            r = requests.post(
                'https://api.ocr.space/parse/image',
                files={filename: f},
                data=payload,
            )
        result = r.json()
        return result['ParsedResults'][0]['ParsedText']
     
    except Exception as e:
        print(f"Error in OCR: {e}")
        return None
