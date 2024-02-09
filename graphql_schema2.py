import requests
from graphql import graphql_sync, print_schema

# Define the introspection query
introspection_query = '''
    query IntrospectionQuery {
        __schema {
            queryType {
                name
            }
            mutationType {
                name
            }
            subscriptionType {
                name
            }
            types {
                ...FullType
            }
        }
    }

    fragment FullType on __Type {
        kind
        name
        description
        fields(includeDeprecated: true) {
            name
            description
            args {
                ...InputValue
            }
            type {
                ...TypeRef
            }
            isDeprecated
            deprecationReason
        }
        inputFields {
            ...InputValue
        }
        interfaces {
            ...TypeRef
        }
        enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
        }
        possibleTypes {
            ...TypeRef
        }
    }

    fragment InputValue on __InputValue {
        name
        description
        type {
            ...TypeRef
        }
        defaultValue
    }

    fragment TypeRef on __Type {
        kind
        name
        ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                }
            }
        }
    }
'''

introspection_query2 = '''
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                    fields {
                        name
                        type {
                            name
                            kind
                            ofType {
                                name
                                kind
                                ofType {
                                    name
                                    kind
                                }
                            }
                        }
                    }
                }
            }
        }
    '''

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
