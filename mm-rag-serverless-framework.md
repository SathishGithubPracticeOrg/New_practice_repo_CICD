Below is the revised and complete setup using **Serverless Framework**, including OpenSearch **Collection** and **Index Creation**, **SQS for Queue Processing**, and **Lambda Layers** for library dependencies and system utilities like `poppler-utils` and `tesseract-ocr`.

---

### **Folder Structure**

```
serverless-app/
├── serverless.yml
├── resources/
│   ├── opensearch-policies.yml
│   ├── sqs-queue.yml
├── lambdas/
│   ├── indexFiles/
│   │   ├── handler.py
│   ├── processQueue/
│   │   ├── handler.py
├── layers/
│   ├── unstructured-lib/
│   │   ├── requirements.txt
└── requirements.txt
```

---

### **1. `serverless.yml`**

This file defines all the services, including Lambda functions, layers, OpenSearch, and SQS resources.

```yaml
service: multimodal-rag-app

frameworkVersion: '3'

provider:
  name: aws
  runtime: python3.9
  region: us-east-1
  memorySize: 1024
  timeout: 900
  iamRoleStatements:
    - Effect: "Allow"
      Action:
        - "s3:GetObject"
        - "s3:ListBucket"
        - "opensearch:CreateCollection"
        - "opensearch:DescribeCollection"
        - "opensearch:CreateIndex"
        - "opensearch:IndexDocuments"
        - "sqs:*"
      Resource: "*"

functions:
  indexFiles:
    handler: lambdas/indexFiles/handler.index
    events:
      - s3:
          bucket: <YOUR_S3_BUCKET_NAME>
          event: s3:ObjectCreated:*
          existing: true
    environment:
      SQS_QUEUE_URL: { Ref: ProcessQueue }

  processQueue:
    handler: lambdas/processQueue/handler.process
    events:
      - sqs:
          arn:
            Fn::GetAtt:
              - ProcessQueue
              - Arn
    layers:
      - { Ref: UnstructuredLibLayer }
    environment:
      OPENSEARCH_ENDPOINT: <YOUR_OPENSEARCH_ENDPOINT>
      COLLECTION_NAME: multimodal-collection
      INDEX_NAME: multimodal-index

layers:
  unstructuredLibLayer:
    path: layers/unstructured-lib
    compatibleRuntimes:
      - python3.9

resources:
  Resources:
    ProcessQueue:
      Type: AWS::SQS::Queue
      Properties:
        QueueName: ProcessQueue
    OpensearchPolicies:
      Type: AWS::CloudFormation::Stack
      Properties:
        TemplateURL: ./resources/opensearch-policies.yml
```

---

### **2. `resources/opensearch-policies.yml`**

Defines the OpenSearch Collection and its network and access policies.

```yaml
Resources:
  OpenSearchCollection:
    Type: AWS::OpenSearchServerless::Collection
    Properties:
      Name: multimodal-collection
      Type: SEARCH
      Description: "Collection for multimodal RAG app"

  OpenSearchAccessPolicy:
    Type: AWS::OpenSearchServerless::AccessPolicy
    Properties:
      Name: multimodal-access-policy
      Policy:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action:
              - "aoss:*"
            Principal: "*"
            Resource:
              - !GetAtt OpenSearchCollection.Arn
```

---

### **3. `lambdas/indexFiles/handler.py`**

This function gets triggered by new S3 file uploads and adds file paths to the SQS queue.

```python
import boto3
import json
import os

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['SQS_QUEUE_URL']

def index(event, context):
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        file_key = record['s3']['object']['key']

        file_path = f"s3://{bucket_name}/{file_key}"

        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({'file_path': file_path})
        )
        print(f"Sent file {file_path} to SQS. MessageId: {response['MessageId']}")
```

---

### **4. `lambdas/processQueue/handler.py`**

This function processes files, creates embeddings, and adds documents to OpenSearch.

```python
import boto3
import os
import json
from opensearchpy import OpenSearch

OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
COLLECTION_NAME = os.environ['COLLECTION_NAME']
INDEX_NAME = os.environ['INDEX_NAME']

def process(event, context):
    client = OpenSearch(hosts=[OPENSEARCH_ENDPOINT])

    # Ensure OpenSearch index exists
    if not client.indices.exists(INDEX_NAME):
        client.indices.create(INDEX_NAME)
        print(f"Created OpenSearch index: {INDEX_NAME}")

    for record in event['Records']:
        message_body = json.loads(record['body'])
        file_path = message_body['file_path']

        # Parse file and generate embeddings (Placeholder logic)
        # embeddings = generate_embeddings(file_path)

        # Index data into OpenSearch
        document = {
            "file_path": file_path,
            # "embeddings": embeddings,  # Example field
        }
        client.index(index=INDEX_NAME, body=document)
        print(f"Indexed document for {file_path}")
```

---

### **5. `layers/unstructured-lib/requirements.txt`**

Dependencies for the `processQueue` Lambda function.

```
boto3
opensearch-py
unstructured
pdf2image
pytesseract
```

---

### **6. Installing System Utilities (Poppler, Tesseract)**

To include system utilities, you must create a **custom Lambda layer**.

1. Create a new folder for the layer (e.g., `layers/system-utils`).
2. Inside that folder, set up a `Dockerfile`:

   ```dockerfile
   FROM public.ecr.aws/lambda/python:3.9

   RUN yum -y update && \
       yum -y install poppler-utils tesseract-ocr && \
       yum clean all

   RUN mkdir -p /opt/layer
   WORKDIR /opt/layer
   ```

3. Build the layer using Docker:

   ```bash
   docker build -t system-utils .
   docker run --rm -v $(pwd)/system-utils:/opt/layer system-utils
   ```

4. Zip the `/opt/layer` folder and upload it to AWS Lambda as a layer.

---

### **How to Deploy**

1. **Install dependencies**:

   ```bash
   pip install -r layers/unstructured-lib/requirements.txt -t layers/unstructured-lib/
   ```

2. **Deploy the stack**:

   ```bash
   serverless deploy
   ```

3. **Upload Lambda Layers**:

   - Upload the zipped system utilities layer to AWS Lambda.
   - Add this layer to the `processQueue` Lambda function in `serverless.yml`.

---

### **Tracking Indexed Files**

**Approach**:
1. Store file metadata in the OpenSearch index (e.g., file path, upload date).
2. Before processing a file, check if the metadata already exists in the index.

Let me know if you'd like a detailed implementation for this!


---
---
---
# can't the collections and index be created in the serverless framework yaml itself?
---
---
---

The **Serverless Framework YAML file** can indeed create OpenSearch **collections** and **indices** directly as part of the infrastructure setup. This can be achieved using AWS CloudFormation resources. Here's how you can define the OpenSearch collection and index creation in your `serverless.yml` file.  

---

### **Updated `serverless.yml`**

This version adds the creation of an OpenSearch Collection and Index directly via CloudFormation resources.

```yaml
service: multimodal-rag-app

frameworkVersion: '3'

provider:
  name: aws
  runtime: python3.9
  region: us-east-1
  memorySize: 1024
  timeout: 900
  iamRoleStatements:
    - Effect: "Allow"
      Action:
        - "s3:GetObject"
        - "s3:ListBucket"
        - "sqs:*"
        - "opensearch:*"
      Resource: "*"

functions:
  indexFiles:
    handler: lambdas/indexFiles/handler.index
    events:
      - s3:
          bucket: <YOUR_S3_BUCKET_NAME>
          event: s3:ObjectCreated:*
          existing: true
    environment:
      SQS_QUEUE_URL: { Ref: ProcessQueue }

  processQueue:
    handler: lambdas/processQueue/handler.process
    events:
      - sqs:
          arn:
            Fn::GetAtt:
              - ProcessQueue
              - Arn
    layers:
      - { Ref: UnstructuredLibLayer }
    environment:
      OPENSEARCH_COLLECTION_ARN: { Ref: OpenSearchCollection }
      OPENSEARCH_ENDPOINT: { Fn::Join: ["", ["https://", { Fn::GetAtt: ["OpenSearchCollection", "Endpoint"] }]] }
      OPENSEARCH_INDEX_NAME: multimodal-index

layers:
  unstructuredLibLayer:
    path: layers/unstructured-lib
    compatibleRuntimes:
      - python3.9

resources:
  Resources:
    # SQS Queue for processing
    ProcessQueue:
      Type: AWS::SQS::Queue
      Properties:
        QueueName: ProcessQueue

    # OpenSearch Collection
    OpenSearchCollection:
      Type: AWS::OpenSearchServerless::Collection
      Properties:
        Name: multimodal-collection
        Type: SEARCH
        Description: "Collection for multimodal RAG app"

    # OpenSearch Access Policy
    OpenSearchAccessPolicy:
      Type: AWS::OpenSearchServerless::AccessPolicy
      Properties:
        Name: multimodal-access-policy
        Policy:
          Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action:
                - "aoss:*"
              Principal: "*"
              Resource: !GetAtt OpenSearchCollection.Arn

    # OpenSearch Index
    OpenSearchIndex:
      Type: AWS::OpenSearchServerless::Index
      Properties:
        CollectionName: multimodal-collection
        IndexName: multimodal-index
```

---

### **What This Does**

1. **Creates an OpenSearch Collection**:
   - The `OpenSearchCollection` resource creates a new collection named `multimodal-collection` in OpenSearch Serverless.

2. **Defines Access Policies**:
   - The `OpenSearchAccessPolicy` resource ensures that Lambda functions and other services can interact with the OpenSearch collection.

3. **Creates an OpenSearch Index**:
   - The `OpenSearchIndex` resource directly creates the `multimodal-index` for the specified collection.

---

### **Deploying with Serverless Framework**

1. **Install Dependencies**:
   If you haven’t installed the Serverless Framework yet:
   ```bash
   npm install -g serverless
   ```
   Install required plugins:
   ```bash
   serverless plugin install --name serverless-python-requirements
   ```

2. **Install Lambda Layer Dependencies**:
   ```bash
   pip install -r layers/unstructured-lib/requirements.txt -t layers/unstructured-lib/
   ```

3. **Deploy the Stack**:
   ```bash
   serverless deploy
   ```

---

### **Accessing OpenSearch Resources in Lambda**

In the `processQueue` Lambda function, you can access the collection and index as follows:

```python
import boto3
import os
from opensearchpy import OpenSearch

# Get environment variables
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
OPENSEARCH_INDEX_NAME = os.environ['OPENSEARCH_INDEX_NAME']

def process(event, context):
    # OpenSearch client
    client = OpenSearch(hosts=[OPENSEARCH_ENDPOINT])

    # Process each message in the queue
    for record in event['Records']:
        file_path = record['body']
        print(f"Processing file: {file_path}")

        # Placeholder logic for processing and indexing
        document = {"file_path": file_path}
        response = client.index(index=OPENSEARCH_INDEX_NAME, body=document)
        print(f"Indexed document: {response}")
```

---

### **Advantages of CloudFormation for Collection & Index Creation**

1. **Automation**: The collection and index are created as part of the infrastructure deployment, ensuring no manual setup is needed.
2. **Idempotency**: Serverless Framework ensures the resources are only created once, even across multiple deployments.
3. **Environment Consistency**: Consistent infrastructure across development, staging, and production environments.

Let me know if you'd like further refinements!



---
---
---
# Creating the lambda layer using docker and serverless deploy, can it be done using Gitlab ci-cd pipeline? If so, provide the code and folder structure. 
---
---
Yes, you can create a **Lambda Layer using Docker** and deploy it with **Serverless Framework** as part of a **GitLab CI/CD pipeline**. The pipeline can handle building the layer, packaging it, and deploying the infrastructure to AWS.

Here’s how you can set up the project with the necessary GitLab CI/CD configuration.

---

### **Folder Structure**

```
serverless-app/
├── .gitlab-ci.yml
├── serverless.yml
├── layers/
│   ├── unstructured-lib/
│   │   ├── requirements.txt
│   ├── Dockerfile
├── lambdas/
│   ├── indexFiles/
│   │   ├── handler.py
│   ├── processQueue/
│   │   ├── handler.py
└── package.json
```

---

### **1. `serverless.yml`**

Update your `serverless.yml` to include the Lambda Layer built from the Docker process.

```yaml
service: multimodal-rag-app

frameworkVersion: '3'

provider:
  name: aws
  runtime: python3.9
  region: us-east-1
  memorySize: 1024
  timeout: 900
  iamRoleStatements:
    - Effect: "Allow"
      Action:
        - "s3:GetObject"
        - "s3:ListBucket"
        - "sqs:*"
        - "opensearch:*"
      Resource: "*"

functions:
  indexFiles:
    handler: lambdas/indexFiles/handler.index
    events:
      - s3:
          bucket: <YOUR_S3_BUCKET_NAME>
          event: s3:ObjectCreated:*
          existing: true
    environment:
      SQS_QUEUE_URL: { Ref: ProcessQueue }

  processQueue:
    handler: lambdas/processQueue/handler.process
    events:
      - sqs:
          arn:
            Fn::GetAtt:
              - ProcessQueue
              - Arn
    layers:
      - { Ref: UnstructuredLibLayer }
    environment:
      OPENSEARCH_ENDPOINT: { Fn::Join: ["", ["https://", { Fn::GetAtt: ["OpenSearchCollection", "Endpoint"] }]] }
      OPENSEARCH_INDEX_NAME: multimodal-index

layers:
  unstructuredLibLayer:
    path: layers/unstructured-lib/build
    compatibleRuntimes:
      - python3.9

resources:
  Resources:
    ProcessQueue:
      Type: AWS::SQS::Queue
      Properties:
        QueueName: ProcessQueue
```

---

### **2. `layers/Dockerfile`**

A Dockerfile for building the Lambda Layer with system utilities (`poppler-utils` and `tesseract-ocr`) and Python dependencies.

```dockerfile
FROM public.ecr.aws/lambda/python:3.9

# Install required system libraries
RUN yum -y update && \
    yum -y install poppler-utils tesseract-ocr && \
    yum clean all

# Install Python dependencies
COPY unstructured-lib/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt -t /opt/python/

# Set the layer folder for AWS Lambda
WORKDIR /opt
```

---

### **3. GitLab CI/CD: `.gitlab-ci.yml`**

This CI/CD pipeline builds the Lambda Layer using Docker, packages it, and deploys it using Serverless Framework.

```yaml
stages:
  - build
  - deploy

variables:
  DOCKER_IMAGE: lambda-layer-builder
  AWS_ACCESS_KEY_ID: <YOUR_AWS_ACCESS_KEY_ID>
  AWS_SECRET_ACCESS_KEY: <YOUR_AWS_SECRET_ACCESS_KEY>
  AWS_REGION: "us-east-1"

cache:
  paths:
    - node_modules/

build-layer:
  stage: build
  image: docker:latest
  services:
    - docker
  script:
    - echo "Building Lambda Layer..."
    - docker build -t $DOCKER_IMAGE -f layers/Dockerfile layers/
    - mkdir -p layers/unstructured-lib/build
    - docker create --name temp-container $DOCKER_IMAGE
    - docker cp temp-container:/opt layers/unstructured-lib/build
    - docker rm temp-container
  artifacts:
    paths:
      - layers/unstructured-lib/build

deploy:
  stage: deploy
  image: node:16
  before_script:
    - npm install -g serverless
    - serverless config credentials --provider aws --key $AWS_ACCESS_KEY_ID --secret $AWS_SECRET_ACCESS_KEY
  script:
    - echo "Deploying with Serverless Framework..."
    - serverless deploy
  only:
    - main
```

---

### **Key Steps in the CI/CD Pipeline**

1. **Stage: Build (`build-layer`)**:
   - Use Docker to build the Lambda Layer.
   - Install system utilities (`poppler-utils` and `tesseract-ocr`) and Python dependencies.
   - Extract the `/opt` folder from the Docker container (this is where the Lambda Layer contents reside).
   - Save the extracted folder in `layers/unstructured-lib/build` for packaging.

2. **Stage: Deploy (`deploy`)**:
   - Install Serverless Framework in a Node.js environment.
   - Use AWS credentials to deploy the application.
   - Deploy the stack, including the Lambda Layer.

---

### **4. `layers/unstructured-lib/requirements.txt`**

Dependencies for the Lambda Layer.

```
unstructured
pdf2image
pytesseract
boto3
opensearch-py
```

---

### **5. `package.json`**

Manage Node.js dependencies for the Serverless Framework:

```json
{
  "name": "multimodal-rag-app",
  "version": "1.0.0",
  "description": "Serverless framework project for multimodal RAG app",
  "dependencies": {
    "serverless": "^3.0.0"
  }
}
```

---

### **How It Works**

1. **Layer Build (Docker)**:
   - Docker builds the Lambda Layer, including system libraries (`poppler-utils` and `tesseract-ocr`) and Python dependencies.
   - The extracted layer is stored in the `build` folder for packaging.

2. **Deployment (Serverless)**:
   - Serverless Framework packages the Lambda functions and the layer.
   - Deploys the infrastructure, including the SQS queue, OpenSearch resources, and Lambda functions.

3. **GitLab CI/CD**:
   - Automatically triggers the pipeline when you push to the `main` branch.
   - Builds the Lambda Layer and deploys the entire stack.

---

### **Deploying the Pipeline**

1. **Set Up AWS Credentials**:
   - Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables in GitLab CI/CD settings.

2. **Push Changes**:
   - Push the repository to trigger the CI/CD pipeline.

---

This setup ensures your Lambda Layer is built dynamically and seamlessly deployed using GitLab CI/CD. Let me know if you have any questions!
