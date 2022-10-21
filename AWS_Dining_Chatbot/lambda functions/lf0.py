import json
import boto3

def lambda_handler(event, context):
    print(event)
    client = boto3.client('lex-runtime')
    # sending request to lex
    response = client.post_text(
    botName='diningBot',
    botAlias='botalias',
    #userId=event.messages[0].["unstructured"].["id"],
    userId='300',
    inputText=event["messages"][0]["unstructured"]["text"]
    #inputText='hello'
    )
    print(response)
    print(response['ResponseMetadata']['HTTPStatusCode'])
    
    # the response to user from lex
    # we check the response status, messages from response
    if response['ResponseMetadata']['HTTPStatusCode'] == 200 :
        return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
       "messages": [
            {
            "type": "unstructured",
            "unstructured": {
                "id": "string",
                "text": response['message'],
                "timestamp": "string"
                }
            }
        ]
        }
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }