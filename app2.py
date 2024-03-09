from flask import Flask, request, jsonify, render_template, session
from flask_session import Session  # Import Session
from pdf2image import convert_from_path
import pytesseract
import os
import json
import boto3
from openai import OpenAI
from botocore.config import Config

app = Flask(__name__)
app.secret_key = 'a_secure_and_persistent_secret_key'

# Configure server-side session storage
app.config["SESSION_TYPE"] = "filesystem"  # Options include redis, memcached, filesystem, etc.
Session(app)

def invoke_model_claude2(prompt_data, history_messages):
    config = Config(read_timeout=1000)
    bedrock = boto3.client(service_name="bedrock-runtime", config=config)
    # Ensure history_messages is a list. If it's not, initialize as an empty list.
    if not isinstance(history_messages, list):
        history_messages = []  # Correctly initialize history_messages if it was not a list

    prompt_data = prompt_data + """------Please provide your answer in well-structured HTML format suitable to be inserted within a <div> element on a webpage. 
                Your response should include appropriate HTML tags for formatting, such as <p> for paragraphs, <h1>, <h2> for headings, <ul>, <ol> with <li> for lists, 
                <a> for links, and <strong>, <em> for text emphasis. Specifically, include a table element <table> with headers <th> and rows <tr> containing data cells 
                <td>. Ensure the HTML is clean and ready for web presentation-----"""
    
    messages = history_messages + [{ "role": "user","content": prompt_data}]
    
    payload = {
        "messages": messages,
        "anthropic_version": "bedrock-2023-05-31", 
        "max_tokens": 4096,
        "temperature": 0.8,
        "top_p": 0.8,
    }


    body = json.dumps(payload)
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
#    print(body)
    response = bedrock.invoke_model(
        body=body,
        modelId=model_id,
#        accept="application/json",
#        contentType="application/json",
    )

    print(response)
    response_body = json.loads(response.get("body").read())
    print(response_body)
    response_text = response_body['content'][0]['text']

    # Update history_messages with the latest user and assistant messages
    history_messages.append({
        "role": "user", "content": prompt_data
    })
    history_messages.append({
        "role": "assistant", "content": response_text
    })

    return response_text, history_messages

def invoke_model_openai(prompt_data, history):
    # Ensure your OpenAI API key is set correctly
    client = OpenAI(
        # This is the default and can be omitted
        api_key="the key",
        )

    # Adjust the prompt format as needed
    messages = [
        {
            "role": "assistant",
                "content": f"""{history}user: Please provide your answer in well-structured HTML format suitable to be inserted within a <div> element on a webpage. 
                Your response should include appropriate HTML tags for formatting, such as <p> for paragraphs, <h1>, <h2> for headings, <ul>, <ol> with <li> for lists, 
                <a> for links, and <strong>, <em> for text emphasis. Specifically, include a table element <table> with headers <th> and rows <tr> containing data cells 
                <td>. Ensure the HTML is clean and ready for web presentation  {prompt_data}\n\nassistant:""",
        }
    ]
#    prompt = f"{history}Human: {prompt_data}\n\nAssistant:"

    response = client.chat.completions.create(
        model="gpt-4-0125-preview",  # Use the appropriate model for your needs
        messages=messages,
        temperature=0.8,
        max_tokens=4096,
        top_p=0.8,
        n=1,  # Generate one completion for the given prompt
        stop=None  # You can define stop sequences if necessary
    )

    # Extract the response text
    response_text = response.choices[0].message.content


    # Update the history to include the latest exchange
    updated_history = f"{history}User: {prompt_data}\n\nAssistant: {response_text}\n\n"
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
                combined_text += f"My context: {pdf_text}\n\My Question for teh context: {instruction}\n"

                # Clean up: remove the temporary file
                os.remove(temp_pdf_path)

            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                return jsonify({"status": "error", "message": "Failed to process files."})

    response_text, updated_history = invoke_model_claude2(combined_text, session.get('history', ''))
    session['conversation'].append({"prompt": combined_text, "response": response_text})
    session['history'] = updated_history  # Update the session history with the new exchange

    return render_template('conversation.html', conversation=session['conversation'])

@app.route('/continue_conversation', methods=['POST'])
def continue_conversation():
    user_input = request.form['user_input']
    combined_text = user_input  # Directly use user input as the new prompt

    response_text, updated_history = invoke_model_claude2(combined_text, session.get('history', ''))
    session['conversation'].append({"prompt": user_input, "response": response_text})
    session['history'] = updated_history  # Update the session history with the new exchange

    return render_template('conversation.html', conversation=session['conversation'])

if __name__ == "__main__":
    app.run(debug=True)
