from flask import Flask, request, jsonify, render_template, session
from flask_session import Session  # Import Session
from pdf2image import convert_from_path
import pytesseract
import os
import json
import boto3

app = Flask(__name__)
app.secret_key = 'a_secure_and_persistent_secret_key'

# Configure server-side session storage
app.config["SESSION_TYPE"] = "filesystem"  # Options include redis, memcached, filesystem, etc.
Session(app)

def invoke_model(prompt_data, history):
    bedrock = boto3.client(service_name="bedrock-runtime")
    payload = {
        "prompt": f"{history}Human: {prompt_data}\n\nAssistant:",
        "max_tokens_to_sample": 1024,
        "temperature": 0.8,
        "top_p": 0.8,
    }

    body = json.dumps(payload)
    model_id = "anthropic.claude-v2:1"
    response = bedrock.invoke_model(
        body=body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json",
    )

    response_body = json.loads(response.get("body").read())
    response_text = response_body.get("completion")

    # Update the history to include the latest exchange
    updated_history = f"{history}Human: {prompt_data}\n\nAssistant: {response_text}\n\n"
    print(response_text)

    return response_text, updated_history

@app.route('/')
def index():
    session['conversation'] = []  # Initialize an empty conversation list
    session['history'] = ""  # Initialize an empty history string
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    combined_text = ""  # Initialize an empty string for the combined text

    for key in request.files:
        file = request.files[key]
        instruction_key = 'instruction' + key.replace('file', '')
        instruction = request.form[instruction_key]

        if file:
            try:
                # Save the uploaded PDF file temporarily
                temp_pdf_path = f'temp_{file.filename}'
                file.save(temp_pdf_path)

                # Convert PDF pages to images
                pages = convert_from_path(temp_pdf_path)

                # Initialize a variable to store text from all pages
                pdf_text = ""

                # Use pytesseract to extract text from each image
                for page in pages:
                    pdf_text += pytesseract.image_to_string(page)

                # Append the instruction and its associated text to the combined_text string
                combined_text += f"Instruction: {instruction}\nText: {pdf_text}\n\n"

                # Clean up: remove the temporary file
                os.remove(temp_pdf_path)

            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                return jsonify({"status": "error", "message": "Failed to process files."})

    response_text, updated_history = invoke_model(combined_text, session.get('history', ''))
    session['conversation'].append({"prompt": combined_text, "response": response_text})
    session['history'] = updated_history  # Update the session history with the new exchange

    return render_template('conversation.html', conversation=session['conversation'])

@app.route('/continue_conversation', methods=['POST'])
def continue_conversation():
    user_input = request.form['user_input']
    combined_text = user_input  # Directly use user input as the new prompt

    response_text, updated_history = invoke_model(combined_text, session.get('history', ''))
    session['conversation'].append({"prompt": user_input, "response": response_text})
    session['history'] = updated_history  # Update the session history with the new exchange

    return render_template('conversation.html', conversation=session['conversation'])

if __name__ == "__main__":
    app.run(debug=True)
