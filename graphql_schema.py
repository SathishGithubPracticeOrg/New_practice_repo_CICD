# pip install graphql-core-next requests

import requests
from graphql import graphql_sync, introspection_query, print_schema

# Define the GraphQL endpoint URL
endpoint_url = 'https://your-graphql-endpoint.com/graphql'

def fetch_schema(endpoint_url):
    # Send introspection query to fetch the schema
    response = requests.post(endpoint_url, json={'query': introspection_query})
    response_json = response.json()

    # Check if the response contains errors
    if 'errors' in response_json:
        raise Exception(response_json['errors'])

    # Extract and return the schema from the response
    return response_json['data']

def save_schema(schema_json, file_path):
    # Write the schema JSON to a file
    with open(file_path, 'w') as schema_file:
        schema_file.write(schema_json)

def main():
    # Fetch the schema from the endpoint
    schema_data = fetch_schema(endpoint_url)

    # Convert the schema data to JSON format
    schema_json = print_schema(schema_data)

    # Save the schema to a file
    save_schema(schema_json, 'schema.graphql')

    print('Schema saved successfully.')

if __name__ == '__main__':
    main()
