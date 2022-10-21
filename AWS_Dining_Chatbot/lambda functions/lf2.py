import boto3
import json
import requests
import random
from requests_aws4auth import AWS4Auth

def receiveMsgFromSqsQueue():
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/522704846529/DiningbotSqs'
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['SentTimestamp'],
        MaxNumberOfMessages=5,
        MessageAttributeNames=['All'],
        VisibilityTimeout=10,
        WaitTimeSeconds=0
        )
    print(response)
    return response

# The function return list of business id
def findRestaurantFromElasticSearch(cuisine):
    region = 'us-east-1'
    service = 'es'
    credentials = boto3.Session(aws_access_key_id="",
                          aws_secret_access_key="", 
                          region_name="us-east-1").get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    host = 'search-dining-nipwtaplonagx66movjisfr3wi.us-east-1.es.amazonaws.com'
    index = 'restaurants'
    url = 'https://' + host + '/' + index + '/_search'
    # i am just getting 3 buisiness id from es but its not random rn
    query = {
        "size": 1300,
        "query": {
            "query_string": {
                "default_field": "cusine",
                "query": cuisine
            }
        }
    }
    headers = { "Content-Type": "application/json" }
    response = requests.get(url,auth=awsauth, headers=headers, data=json.dumps(query))
    #res = json.loads(response.content.decode('utf-8'))
    res = response.json()
    print(res)
    # noOfHits = res['hits']['total']
    hits = res['hits']['hits']
    # print(noOfHits)
    # print(hits[0]['_id'])
    restaurant_id = []
    for hit in hits:
        print(hit)
        restaurant_id.append(str(hit['_source']['restaurant_id']))
    print(len(restaurant_id))
    return restaurant_id

# function returns detail of all resturantids as a list(working)
def getRestaurantFromDb(restaurantIds):
    res = []
    client = boto3.resource('dynamodb')
    table = client.Table('yelp-restaurants')
    for id in restaurantIds:
        response = table.get_item(Key={'Business ID': id})
        res.append(response)
    return res

def getMsgToSend(restaurantDetails,message):
    noOfPeople = message['MessageAttributes']['people_count']['StringValue']
    date = message['MessageAttributes']['date']['StringValue']
    time = message['MessageAttributes']['time_open']['StringValue']
    cuisine = message['MessageAttributes']['cuisine']['StringValue']
    separator = ', '
    resOneName = restaurantDetails[0]['Item']['name']
    resOneAdd = separator.join(restaurantDetails[0]['Item']['address'])
    resTwoName = restaurantDetails[1]['Item']['name']
    resTwoAdd = separator.join(restaurantDetails[1]['Item']['address'])
    resThreeName = restaurantDetails[2]['Item']['name']
    resThreeAdd = separator.join(restaurantDetails[2]['Item']['address'])
    msg = 'Hello! Here are my {0} restaurant suggestions for {1} people, for {2} at {3} : 1. {4}, located at {5}, 2. {6}, located at {7},3. {8}, located at {9}. Enjoy your meal!'.format(cuisine,noOfPeople,date,time,resOneName,resOneAdd,resTwoName,resTwoAdd,resThreeName,resThreeAdd)
    return msg
    
def sendEmail(msgToSend,EmailAddress):
    client = boto3.client("ses")
    verifiedResponse = client.list_verified_email_addresses()
    email_id = EmailAddress
    if email_id not in verifiedResponse['VerifiedEmailAddresses']:
        verifyEmailResponse = client.verify_email_identity(EmailAddress= email_id)
    # sample phone number shown PhoneNumber="+12223334444"
    client.send_email(
        Destination={
            "ToAddresses": [
                email_id,
                
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": "UTF-8",
                    "Data": msgToSend,
                }
            },
            "Subject": {
                "Charset": "UTF-8",
                "Data": "Dining Recommendations!",
            },
        },
        Source='jp6207@nyu.edu',
    )
    
def deleteMsg(receipt_handle):
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/522704846529/DiningbotSqs'
    sqs.delete_message(QueueUrl=queue_url,
    ReceiptHandle=receipt_handle
    )

def lambda_handler(event, context):
    # getting response from sqs queue
    sqsQueueResponse = receiveMsgFromSqsQueue()
    if "Messages" in sqsQueueResponse.keys():
        for message in sqsQueueResponse['Messages']:
            cuisine = message['MessageAttributes']['cuisine']['StringValue']
            restaurantIds = findRestaurantFromElasticSearch(cuisine)
            # Assume that it returns a list of restaurantsIds
            # call some random function to select 3 from the list
            restaurantIds = random.sample(restaurantIds, 3)
            restaurantDetails = getRestaurantFromDb(restaurantIds)
            # now we have all required details to send the sms
            # now we will create the required message using the details
            msgToSend = getMsgToSend(restaurantDetails,message)
            print(msgToSend)
            # dont uncomment below line until required. There is max limit on msg
            EmailAddress = message['MessageAttributes']['email']['StringValue']
            sendEmail(msgToSend,EmailAddress)
            #now delete message from queue
            receipt_handle = message['ReceiptHandle']
            deleteMsg(receipt_handle)