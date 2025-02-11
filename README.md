<!--
---
description: This Python sample shows how to use Durable Functions for model evaluation. 
page_type: sample
products:
- azure-functions
languages:
- python
- bicep
- azdeveloper
---
-->

# Model evaluation using Durable Functions (Python)

## About sample
This sample demonstrates how to use Durable Functions to call multiple models in parallel to quickly get the best response to a user's query. It uses three models - GPT-3.5-turbo, GPT-4o-mini, and Phi-4 - to answer a query. After getting the responses, it uses GPT-4 to evaluate and select the simplest and most intuitive response.

There's no particular reason for choosing the models used in this sample - the key is to demonstrate how to leverage Durable Function's fan-out/fan-in pattern to easily realize this scenario. 

### About Durable Functions 
[Durable Functions](https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview) is part of [Azure Functions](https://learn.microsoft.com/azure/azure-functions/functions-overview) offering. It helps  orchestrate stateful logic that is long-running and provides reliable execution. For example, when there's infrastructure failure (network connectivity dropped, VM crashed, etc.), the framework rebuilds application state and start from the point of failure instead of the beginning. This helps save time and money, especially for expensive operations like LLM calls. Common scenarios where Durable Functions is useful include agentic workflows, data processing, asynchronous APIs, batch processing, and infrastructure management.

Durable Functions needs a [backend provider](https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-storage-providers) to persist application states. This sample uses the Azure Storage backend. 

> [!IMPORTANT]
> This sample creates several resources. Delete the resource group after testing to minimize charges.


## Run in your local environment

The project is designed to run on your local computer, provided you have met the  [required prerequisites](#prerequisites). You can run the project locally in these environments:

+ [Using Visual Studio Code](#using-visual-studio-code)
+ [Using Azure Functions Core Tools (CLI)](#using-azure-functions-core-tools-cli)

### Prerequisites
+ [Python 3.11](https://www.python.org/downloads/) 
+ [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local?tabs=v4%2Cmacos%2Ccsharp%2Cportal%2Cbash#install-the-azure-functions-core-tools)
+ Install [Azurite storage emulator](https://learn.microsoft.com/azure/storage/common/storage-use-azurite). 
+ Clone the repo
+ Deploy the models needed by sample:
  - [GPT-4](https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-openai)
  - [GPT-3.5-turbo](https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-openai)
  - [GPT-4o-mini](https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-openai)
  - [Phi-4](https://learn.microsoft.com/azure/ai-studio/how-to/deploy-models-phi-4?pivots=programming-language-python) (pick the deploy the model as a serverless API option)

### Get endpoints and keys for models 
You'll need the model endpoints and keys for the next step.

#### GPT models 
Get the connection information by going to the "Deployments" tab on Azure AI Foundry portal and clicking into the name of the model. For example, here's how to get the information for GTP-3.5-turbo: 
  ![Getting connection info example](img/gpt-35-connection.png)

#### Phi-4
[Phi-4](https://techcommunity.microsoft.com/blog/aiplatformblog/introducing-phi-4-microsoft%E2%80%99s-newest-small-language-model-specializing-in-comple/4357090) is a small language model by Microsoft that has advanced reasoning capabilities in areas like math and science.

Phi-4 is not an OpenAI model. To find the connection information, go to the "Home" page of the project where this model is deployed. 
  ![Phi 4 connection info](img/phi-4-connection.png)


### Using Visual Studio Code
1. Open this folder in a new terminal 
2. Open VS Code by entering `code .` in the terminal
3. In the root folder (**app**), create a file named `local.settings.json` with the following, filling in connection information from the previous step:
    ```json
    {
      "IsEncrypted": false,
      "Values": {
          "AzureWebJobsStorage": "UseDevelopmentStorage=true",
          "GPT35_ENDPOINT": "https://<resource name>.openai.azure.com/openai/deployments/<deployment name>/chat/completions?api-version=2024-08-01-preview",
          "GPT35_API_KEY": "model api key",
          "GPT4_ENDPOINT": "https://<resource name>.openai.azure.com/openai/deployments/<deployment name>/chat/completions?api-version=2024-08-01-preview",
          "GPT4_API_KEY": "model api key",
          "GPT4O_MINI_ENDPOINT": "https://<resource name>.openai.azure.com/openai/deployments/<deployment name>/chat/completions?api-version=2024-08-01-preview",
          "GPT4O_MINI_API_KEY": "model api key",
          "PHI4_ENDPOINT": "https://<resource name>.services.ai.azure.com/models",
          "PHI4_API_KEY": "model api key",
          "FUNCTIONS_WORKER_RUNTIME": "python"
      }
    }
    ```
4. Start Azurite by opening the command template and searching for `Azurite: Start`

5. Run project with debugging (F5)

6. You can test easily by going to the `test.http` file and click "Send Request". This file has an example query asking:
  
   *"In a room of 10 people, how many handshakes are needed so that everyone has shaken hands with everyone else exactly once?"*

    The http request returns a 202 with the following:
    ```json
    {
      "id": "e59b4988a8d04105ae5b75907a8202f6",
      "statusQueryGetUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6?taskHub=TestHubName&connection=Storage&code=<code>",
      "sendEventPostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/raiseEvent/{eventName}?taskHub=TestHubName&connection=Storage&code=<code>",
      "terminatePostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/terminate?reason={text}&taskHub=TestHubName&connection=Storage&code=<code>",
      "rewindPostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/rewind?reason={text}&taskHub=TestHubName&connection=Storage&code=<code>",
      "purgeHistoryDeleteUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6?taskHub=TestHubName&connection=Storage&code=<code>",
      "restartPostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/restart?taskHub=TestHubName&connection=Storage&code=<code>",
      "suspendPostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/suspend?reason={text}&taskHub=TestHubName&connection=Storage&code=<code>",
      "resumePostUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/e59b4988a8d04105ae5b75907a8202f6/resume?reason={text}&taskHub=TestHubName&connection=Storage&code=<code>"
    }
    ```

7. Go the `statusQueryGetUri` to get the result of the orchestration instance. It should show the final answer picked by the evaluation model:

    ```json
    {
      "name": "orchestrator_function",
      "instanceId": "292e739b69ca4b3cb00c8dcdc499e6ae",
      "runtimeStatus": "Completed",
      "input": "\"In a room of 10 people, how many handshakes are needed so that everyone has shaken hands with everyone else exactly once?\"",
      "customStatus": null,
      "output": "The simplest and most intuitive response is:\n\nTo solve this problem, we can use the formula for the number of handshakes in a group of n people, which is:\n\nn(n-1)/2\n\nIn this case, we have 10 people, so we can substitute n=10 into the formula:\n\n10(10-1)/2 = 45\n\nTherefore, 45 handshakes are needed so that everyone has shaken hands with everyone else exactly once.",
      "createdTime": "2025-02-10T20:35:55Z",
      "lastUpdatedTime": "2025-02-10T20:37:03Z"
    }
    ```

### Inspect the solution 

Take a look at the `orchestrator_function` to see how Durable Functions allows you to write code that runs in parallel. This function simply adds the activity functions that make calls to language models to a list and then call `context.task_all(tasks)`, which would signal the activity functions to run in parallel. Note that you don't have to worry about when each activity functions finishes or if any fail in the middle - Durable Functions handles the "fan in" and the automatic retries. Simply take the result and continue with your business logic.

```python
@app.orchestration_trigger(context_name="context")
def orchestrator_function(context):
  # Previous logic
  
  tasks = [
      context.call_activity("get_gpt35_result", user_prompt),
      context.call_activity("get_gpt4omini_result", user_prompt),
      context.call_activity("get_phi4_result", user_prompt)
  ]
  
  results = yield context.task_all(tasks)

  # Other business logic
```

#### Responses from language models
The sample added a print statement to print out the prompt to the evaluation model, which shows the responses from the three different language models: 

![Evaluation model prompt](img/evaluation-model-prompt.png)

All three responses returned `45` as the answer. However, the first one does seem to be the simplest of all. 


### Using Azure Functions Core Tools (CLI)
1. Make sure Azurite is started before proceeding.

2. Open the cloned repo in a new terminal and navigate to the `app` directory: 
```bash
cd app
```

3. Create and activate the virtual environment:
```bash
python3 -m venv venv_name
```
```bash
source .venv/bin/activate
```
4. Install required packages:
```bash
python3 -m pip install -r requirements.txt
```

5. [Add `local.settings.json`](#using-visual-studio-code) to root directory (**app**)

6. Start function app 
```bash
func start
```


## Resources

For more information on Durable Functions, see the following:

* [Durable Functions overview](https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-overview)
* Order processing workflow with Durable Functions [Python sample](https://github.com/Azure-Samples/durable-functions-order-processing-python), [C# sample](https://github.com/Azure-Samples/Durable-Functions-Order-Processing) 
