from datetime import datetime
import os 
import json
import uuid

import azure.functions as func
import azure.durable_functions as df
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceExistsError
from openai import AzureOpenAI
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="orchestrators/orchestrator_function")
@app.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client):
    """
    HTTP trigger to start the orchestration.
    """
    
    # Get user prompt
    user_prompt = ""
    try:
        req_body = req.get_json()
    except Exception as e:
        print(f"An error occurred: {e}")
    else:
        user_prompt = req_body.get("prompt")
    
    # Start the orchestration
    instance_id = await client.start_new("orchestrator_function", client_input=user_prompt)
    response = client.create_check_status_response(req, instance_id)
    
    return response

@app.orchestration_trigger(context_name="context")
def orchestrator_function(context):
    """
    Orchestrator function to call models in parallel and evaluate responses.
    """
    system_prompt = """You are a helpful assistant in STEM."""
    user_prompt = context.get_input()
    
    if not user_prompt:
        raise ValueError("Please provide a question to ask the models.")
    
    # Set retry options for activity calls
    retry_interval_in_milliseconds = 2000
    max_number_of_attempts = 3
    retry_options = df.RetryOptions(retry_interval_in_milliseconds, max_number_of_attempts)
    
    # Run all tasks in parallel
    tasks = [
        context.call_activity_with_retry("get_gpt35_result", retry_options, [user_prompt, system_prompt]),
        context.call_activity_with_retry("get_gpt4omini_result", retry_options, [user_prompt, system_prompt]),
        context.call_activity_with_retry("get_phi4_result", retry_options, [user_prompt, system_prompt])
    ]
    
    # Wait for all the parallel tasks to complete before continuing
    results = yield context.task_all(tasks)
    
    # Evaluate responses 
    model_responses = "\n".join(f"Response #{i+1}. {result}" for i, result in enumerate(results))
    evaluation_result = yield context.call_activity_with_retry("get_gpt4o_result", retry_options, [model_responses, user_prompt])
    
    # Store results in Azure Blob Storage
    blob_content = f"PROMT: {user_prompt}\n"
    
    for result in results:
        blob_content += f"\nMODEL: {result[1]}\nTIMESTAMP: {result[2]}\nRESPONSE: {result[0]}\n"
        
    blob_content += f"\nEVALUATION MODEL: {evaluation_result[1]}\nTIMESTAMP: {evaluation_result[2]}\n=== EVALUATION RESULT ===\n\n{evaluation_result[0]}\n"
    blob_url = yield context.call_activity("copy_to_blob", blob_content)

    return f"Evaluation result stored at: {blob_url}"

@app.activity_trigger(input_name='content')
def copy_to_blob(content: str):
    # Create the BlobServiceClient object  
    blob_service_client = BlobServiceClient.from_connection_string(os.environ.get("BLOB_STORAGE_ENDPOINT"))
    
    # Create name for the container and blob
    container_name = "results"
    blob_name = "model-evaluation-" + str(uuid.uuid4()) + ".txt"
    
    # Create the container if it does not exist
    try:
        blob_service_client.create_container(container_name)
    except ResourceExistsError:
        pass
    
    # Create a container client to help upload file
    container_client = blob_service_client.get_container_client(container_name)
    container_client.upload_blob(name=blob_name, data=content)
        
    return container_client.get_blob_client(blob_name).url

@app.activity_trigger(input_name="prompts")
def get_gpt35_result(prompts: list):
    user_prompt, system_prompt = prompts[0], prompts[1]
    
    client = ChatCompletionsClient(
        endpoint=os.environ["MODELS_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_API_KEY"]),
    )
    response = client.complete(
        model="gpt-35-turbo", # model deployment name
        messages=[
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt)
        ],
        temperature=0
    )
    
    return [response.choices[0].message.content, "gpt-35-turbo", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

@app.activity_trigger(input_name="prompts")
def get_gpt4omini_result(prompts: list):  
    user_prompt, system_prompt = prompts[0], prompts[1]
 
    client = ChatCompletionsClient(
        endpoint=os.environ["MODELS_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_API_KEY"]),
    )
    response = client.complete(
        model="gpt-4o-mini", # model deployment name
        messages=[
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt)
        ],
        temperature=0
    )

    return [response.choices[0].message.content, "gpt-4omini", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

@app.activity_trigger(input_name="prompts")
def get_phi4_result(prompts: list): 
    user_prompt, system_prompt = prompts[0], prompts[1]
       
    client = ChatCompletionsClient(
        endpoint=os.environ["MODELS_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_API_KEY"]),
    )
    response = client.complete(
        model="Phi-4", # model deployment name
        messages=[
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt)
        ],
        temperature=0
    )

    return [response.choices[0].message.content, "phi4", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

@app.activity_trigger(input_name="inputData")
def get_gpt4o_result(inputData: list):
    system_prompt = """
    You have been provided with a set of responses from various language models to a user query. 
    Your task is to use the specified rubric to score the responses and return scores in a specific format.   
    
    The rubric is as follows: 
    - Clarity: The response is easy to understand and free of ambiguity. 
    - Conciseness: The response is brief and to the point, without unnecessary information. 
    - Relevance: The response is directly related to the user query and provides useful information. 
    - Creativity: The response demonstrates original thinking and provides unique insights.
    
    Format your response strictly as follows:
    Model Name: overall score written as a fraction, out of the max total score. For example, 15/20.
    - Clarity: Rank from 1 to 5, where 1 is very unclear and 5 is very clear. Written as a fraction, like 1/5. Provide a brief explanation.
    - Conciseness: Rank from 1 to 5, where 1 is very verbose and 5 is very concise. Written as a fraction, like 1/5. Provide a brief explanation.
    - Relevance: Rank from 1 to 5, where 1 is not relevant and 5 is very relevant. Written as a fraction, like 1/5. Provide a brief explanation.
    - Creativity: Rank from 1 to 5, where 1 is not creative and 5 is very creative. Written as a fraction, like 1/5. Provide a brief explanation.

    Responses from models:"""
    
    client = ChatCompletionsClient(
        endpoint=os.environ["MODELS_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_API_KEY"]),
    )
    
    model_responses, user_prompt = inputData[0], inputData[1]
    complete_system_prompt = system_prompt + "\n" + model_responses
        
    response = client.complete(
        model="gpt-4o", # model deployment name
        messages=[
            SystemMessage(content=complete_system_prompt),
            UserMessage(content=user_prompt)
        ],
        temperature=0
    )
    
    return [response.choices[0].message.content, "gpt-4o", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

