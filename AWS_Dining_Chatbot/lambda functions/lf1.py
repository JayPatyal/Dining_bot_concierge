from botocore.vendored import requests
import json
import os
import time
import dateutil.parser
import logging
import datetime
import urllib
import sys
import boto3
# import argparse
# import pprint


# API constants, you shouldn't have to change these.
# API_HOST = 'https://api.yelp.com'
# SEARCH_PATH = '/v3/businesses/search'
# API_KEY = 'FwvSHuQvLmxSzez1ogD__zbTdClGrflCD329AXUXqnlXri84dT8aP5FEh1t0a5tkyQnc67_rBIvm035HcSnEUABdrPeiQ5Ej_yx_fU8wT8R1O-LtjEW-T_lBizJKY3Yx'
# ENDPOINT = 'https://api.yelp.com/v3/businesses/search'
# HEADERS = {
#     'Authorization': 'Bearer %s' % API_KEY
# }




try:
    # For Python 3.0 and later
    from urllib.error import HTTPError
    from urllib.parse import quote
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2 and urllib
    from urllib2 import HTTPError
    from urllib import quote
    from urllib import urlencode

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    return dispatch(event)

def dispatch(intent_request):

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':
        return greet(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return suggest_places(intent_request)
    elif intent_name == 'ThanksIntent':
        return thank_you(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

def greet(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitIntent',
            'message': {
                'contentType': 'PlainText',
                'content': 'Hello there, how can I help?'
            }
        }
    }
    return response

def thank_you(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
            session_attributes,
            'Fulfilled',
            {
                'contentType': 'PlainText',
                'content': 'Thank you. Hope you enjoyed our service.'
            }
        )

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': {'contentType':'PlainText', 'content':message}
        }
    }

    return response

def suggest_places(intent_request):
    slots = intent_request['currentIntent']['slots']
    cuisine_type = slots['cuisine']
    people_count = slots['numberOfpeople']
    city = slots['city']
    date = slots['date']
    # phone='+17323971296'
    phone = str(slots['phone'])
    email=slots['email']
    # time = int(datetime.datetime.strptime(slots['Time']))
    time_open = slots['time']
    if phone[:2] != '+1':
        phone = '+1'+phone
    print(date, time_open)

    # print(date)
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    if intent_request['invocationSource'] == 'DialogCodeHook':
        validation_result = validate_suggest_place(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            # print(validation_result['message'])
            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        return delegate(session_attributes, intent_request['currentIntent']['slots'])
    request_time = str(int(time.mktime(datetime.datetime.strptime((date+' '+time_open), '%Y-%m-%d %H:%M').timetuple())))
    PARAMETERS={'term':'dinner',
                'limit':5,
                'open_at':request_time,
                'radius':1000,
                'sort_by':'best_match',
                'categories':cuisine_type,
                'location':city}
    
    sqsmessage= cuisine_type+' '+phone+' '+email
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/522704846529/DiningbotSqs'
    response = sqs.send_message(
            QueueUrl=queue_url,
            MessageAttributes={
                'cuisine': {
                    'DataType': 'String',
                    'StringValue': cuisine_type
                },
                'phone': {
                    'DataType': 'String',
                    'StringValue': phone

                },
                'email':{
                    'DataType':'String',
                    'StringValue':email
                },
                'city':{
                    'DataType':'String',
                    'StringValue':city
                },
                'time_open':{
                   'DataType':'String',
                    'StringValue':time_open 
                },
                'people_count':{
                    'DataType':'Number',
                    'StringValue':people_count
                },
                'date':{
                    'DataType':'String',
                    'StringValue':date
                }
                
                
              },
            MessageBody=(
               sqsmessage
               )
              )
   
    return close(
        session_attributes,
        'Fulfilled',
        'I have sent my suggestions to the following phone number: \n'+phone+'& email:'+ email
    )

def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n

def isvalid_city(city):
    valid_cities = ['new york', 'los angeles', 'chicago', 'houston', 'philadelphia', 'phoenix', 'san antonio',
                    'san diego', 'dallas', 'san jose', 'austin', 'jacksonville', 'san francisco', 'indianapolis',
                    'columbus', 'fort worth', 'charlotte', 'detroit', 'el paso', 'seattle', 'denver', 'washington dc',
                    'memphis', 'boston', 'nashville', 'baltimore', 'portland']
    return city.lower() in valid_cities

def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def isvalid_cuisine_type(cuisine_type):
    cuisines = ['japanese', 'chinese', 'indian', 'italian']
    return cuisine_type.lower() in cuisines

def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_suggest_place(slots):
    v_city = slots['city']
    v_date = slots['date']
    v_time = slots['time']
    v_peoplecount = safe_int(slots['numberOfpeople'])
    v_cuisine_type = slots['cuisine']

    if v_city and not isvalid_city(v_city):
        return build_validation_result(
            False,
            'city',
            'We currently do not support {} as a valid destination.  Can you try a different city?'.format(pickup_city)
        )

    if v_date:
        if not isvalid_date(v_date):
            return build_validation_result(False, 'date', 'I did not understand the data you provided. Can you please tell me what date are you planning to go?')
        if datetime.datetime.strptime(v_date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'date', 'Suggestions cannot be made for date earlier than today.  Can you try a different date?')

    if v_peoplecount is not None and v_peoplecount < 1 and v_peoplecount > 20:
        return build_validation_result(
            False,
            'numberOfpeople',
            'Total number of people going should be between 1 and 20.  Can you provide a different count of people?'
        )

    if v_cuisine_type and not isvalid_cuisine_type(v_cuisine_type):
        return build_validation_result(
            False,
            'cuisine',
            'I did not recognize that cuisine.  What cuisine would you like to try?  '
            'Popular cuisines are Japanese, Indian, or Italian')

    return {'isValid': True}

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }