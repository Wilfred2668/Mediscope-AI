import json

def fetch_medicine_info(name):
    try:
        with open("meds.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(name.lower())
    except Exception as e:
        print(f"Error reading medicine data: {e}")
        return None
