import os
import time
import json
import uuid
import boto3
import requests

GITHUB_REPO = os.environ['GITHUB_REPOSITORY']
GITHUB_SHA = os.environ['GITHUB_SHA']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_PR = os.environ['GITHUB_PR']

from json import dumps, loads
s3 = boto3.resource('s3', region_name='us-west-2')
cft_client = boto3.client('cloudformation', region_name='us-west-2')

response = s3.meta.client.upload_file('template.yaml', 'cft-gh', 'template.yaml')
changeset_name = 'cft-' + str(uuid.uuid4()).replace('-', '')

response = cft_client.create_change_set(
    StackName='boss-test',
    TemplateURL='https://cft-gh.s3.amazonaws.com/template.yaml',
    ChangeSetName=changeset_name,
    ChangeSetType='UPDATE'
)

time.sleep(10) # Replace with waiter object on create changeset completion

response = cft_client.describe_change_set(
    ChangeSetName=changeset_name,
    StackName='boss-test'
)

response = loads(dumps(response, default=str))
print(response)

try:
    response = response['Changes'][0]['ResourceChange']
    
    pr_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{GITHUB_PR}/comments"
    headers = {'Content-Type': 'application/json', 'Authorization': f'token {GITHUB_TOKEN}'}
    context = "\tBucket Size: 100 GB\n"
    data_string = f"<h3>Resources Affected by Cloudformation Changeset</h3></br>\n<strong>:rotating_light: Critical Resources</strong></br>------------------------</br>{response['ResourceType']} - {response['PhysicalResourceId']}\n<details><summary>View resource context</summary>\n\n{context}"
    data = {'body':data_string}
            
    r = requests.post(url = pr_url, data = json.dumps(data), headers = headers)
    
except Exception:
    pr_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{GITHUB_PR}/comments"
    headers = {'Content-Type': 'application/json', 'Authorization': f'token {GITHUB_TOKEN}'}
            
    data_string = 'No resource modifications are being made'
    data = {'body':data_string}
            
    r = requests.post(url = pr_url, data = json.dumps(data), headers = headers)

