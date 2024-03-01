from flask import Flask, request, jsonify, render_template, session
from pdf2image import convert_from_path
import pytesseract
import os
import Bedrock_invoke

app = Flask(__name__)
app.secret_key = 'a_secure_and_persistent_secret_key'  # Set a persistent secret key

@app.route('/')
def index():
    if 'conversation' not in session:
        session['conversation'] = []  # Initialize an empty conversation list
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    combined_text = ""
    for key in request.files:
        file = request.files[key]
        instruction_key = 'instruction' + key.replace('file', '')
        instruction = request.form[instruction_key]

        if file:
            try:
                temp_pdf_path = f'temp_{file.filename}'
                file.save(temp_pdf_path)
                pages = convert_from_path(temp_pdf_path)
                pdf_text = ""
                for page in pages:
                    pdf_text += pytesseract.image_to_string(page)
                combined_text += f"Instruction: {instruction}\nText: {pdf_text}\n\n"
                os.remove(temp_pdf_path)
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                return jsonify({"status": "error", "message": "Failed to process files."})

    response_text = Bedrock_invoke.invoke_model(combined_text)
    session['conversation'].append({"prompt": combined_text, "response": response_text})
    session.modified = True  # Ensure the session is marked as modified

    return render_template('conversation.html', conversation=session['conversation'])

@app.route('/continue_conversation', methods=['POST'])
def continue_conversation():
    user_input = request.form['user_input']
    combined_text = session.get('conversation', [])[-1].get('response', '') + "\n" + user_input

    response_text = Bedrock_invoke.invoke_model(combined_text)
    session['conversation'].append({"prompt": user_input, "response": response_text})
    session.modified = True  # Ensure the session is marked as modified

    return render_template('conversation.html', conversation=session['conversation'])

if __name__ == "__main__":
    app.run(debug=True)
