import boto3
import json


def invoke_model(prompt_data, history):
    print(history)
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