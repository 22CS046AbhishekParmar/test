from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import spacy
import urllib.parse
import os
import re
import requests

app = Flask(__name__)


spacy.cli.download("en_core_web_lg")

# Load the pretrained model
nlp = spacy.load("en_core_web_lg")

# Define the path to the patterns file
skills_pattern_file = "jz_skill_patterns.jsonl"

# Create an EntityRuler instance with a unique name
ruler = nlp.add_pipe("entity_ruler", name="my_entity_ruler")

# Load patterns from disk
ruler.from_disk(skills_pattern_file)

# Regular expression pattern for matching email addresses
email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Regular expression pattern for matching phone numbers (supports various formats)
phone_pattern = r'\b(?:\+\d{1,2}\s*)?(?:(?:\d{1,3}[\s.-]*)?\d{3}[\s.-]*\d{3}[\s.-]*\d{4})\b'


@app.route('/spacy_extract_skills', methods=['POST'])
def extract_skills():
    print("Received request")
    if not request.is_json:
        print("Request is not JSON")
        return jsonify({"error": "Request content type must be application/json"}), 415

    try:
        # Receive file URL from the request
        file_url = request.json.get('file_url')
        print("File URL:", file_url)
        
        if file_url:
            # Append the base URL to the file URL
            file_url = "https://pmsdemo.topiatech.co.uk/VacancyPDFs/" + file_url
            
            # Assume the file URL is a remote URL
            response = requests.get(file_url)
            
            if response.status_code == 200:
                text = extract_text_from_pdf_from_bytes(response.content)
                return process_text(text)
            else:
                return jsonify({"error": f"Failed to fetch PDF from URL: {file_url}"}), response.status_code
        else:
            print("No file URL received")
            return jsonify({"error": "No file URL received."}), 400

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

def extract_text_from_pdf_from_bytes(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            text += page.get_text()
    return text

def process_text(text):
    # Check if "dotnet" or ".net" is present in the text
    dotnet_present = "dotnet" in text.lower()
    dot_net_present = ".net" in text.lower()
    java_present = "java" in text.lower()

    # Process text to extract skills 
    doc = nlp(text)
    skills = set()
    for ent in doc.ents:
        if ent.label_ == 'SKILL':
            skills.add(ent.text.lower().capitalize())

    # Include "dotnet" and ".net" in the extracted skills if present
    if dotnet_present:
        skills.add("Dotnet")
    if dot_net_present:
        skills.add(".Net")
    if java_present:
        skills.add("Java")

    # Extract email addresses and phone numbers using regular expressions
    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)

    # Convert the lists of emails and phones to strings
    emails_str = ", ".join(emails)
    phones_str = ", ".join(phones)

    print("Skills extracted:", skills)
    print("Emails extracted:", emails_str)
    print("Phone numbers extracted:", phones_str)

    return jsonify({"skills": list(skills), "emails": emails_str, "phones": phones_str})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
