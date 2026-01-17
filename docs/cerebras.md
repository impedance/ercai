# Retrieve model

Fetches a model instance, offering key details about the model, including its owner and permissions.

## Path Parameters

<ParamField path="model_id" type="string" required="true">
  The ID of the model to retrieve.

  Available options:

  * `llama3.1-8b`
  * `llama-3.3-70b`
  * `qwen-3-32b`
  * `qwen-3-235b-a22b-instruct-2507` (preview)
  * `gpt-oss-120b`
  * `zai-glm-4.6` (preview)
  * `zai-glm-4.7` (preview)
</ParamField>

## Response

<ResponseField name="id" type="string">
  The model identifier.
</ResponseField>

<ResponseField name="object" type="string">
  The object type, which is always `model`.
</ResponseField>

<ResponseField name="created" type="integer">
  The Unix timestamp (in seconds) of when the model was created.
</ResponseField>

<ResponseField name="owned_by" type="string">
  The organization that owns the model.
</ResponseField>

<RequestExample>
  ```python Python theme={null}
  import os
  from cerebras.cloud.sdk import Cerebras

  client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

  model = client.models.retrieve("zai-glm-4.7")

  print(model)
  ```

  ```javascript Node.js theme={null}
  import Cerebras from '@cerebras/cerebras_cloud_sdk';

  const client = new Cerebras({
    apiKey: process.env['CEREBRAS_API_KEY'],
  });

  async function main() {
    const model = await client.models.retrieve("zai-glm-4.7");
    
    console.log(model);
  }

  main();
  ```

  ```bash cURL theme={null}
  curl https://api.cerebras.ai/v1/models/zai-glm-4.7 \
    -H "Authorization: Bearer $CEREBRAS_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json Response theme={null}
  {
    "id": "zai-glm-4.7",
    "object": "model",
    "created": 1721692800,
    "owned_by": "Cerebras"
  }
  ```
</ResponseExample>


---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://inference-docs.cerebras.ai/llms.txt
