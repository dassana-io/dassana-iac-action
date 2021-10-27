import os
import boto3
import time
import subprocess
import requests
import uuid

from json import dumps, loads

GITHUB_REPO = os.environ['GITHUB_REPOSITORY']
GITHUB_SHA = os.environ['GITHUB_SHA']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_PR = os.environ['GITHUB_PR']
API_GATEWAY_ENDPOINT = os.environ['API_GATEWAY_ENDPOINT']
API_KEY = os.environ['API_KEY']

cft_client = boto3.client('cloudformation', region_name='us-west-2')
s3 = boto3.resource('s3', region_name='us-west-2')

aws_region = 'us-west-2'
resources = {}

response = s3.meta.client.upload_file('template.yaml', 'cft-gh', 'template.yaml')
changeset_name = 'cft-' + str(uuid.uuid4()).replace('-', '')

response = cft_client.create_change_set(
    StackName='boss-test',
    TemplateURL='https://cft-gh.s3.amazonaws.com/template.yaml',
    ChangeSetName=changeset_name,
    ChangeSetType='UPDATE'
)

time.sleep(10)

response = cft_client.describe_change_set(
    ChangeSetName=changeset_name,
    StackName='boss-test'
)

response = loads(dumps(response, default=str))

for change in response['Changes']:
	logical_resource = change['ResourceChange']['LogicalResourceId']
	if logical_resource in resources:
		resources[logical_resource]['changes'].append(change)	
	else:
		resources[logical_resource] = {'changes': [change], 'physicalResourceId': change['ResourceChange']['PhysicalResourceId'], 'resourceType': change['ResourceChange']['ResourceType'], 'check_id': '', 'check_name': '', }

x = {'ChangeSetName': 'changeset4-test', 'ChangeSetId': 'arn:aws:cloudformation:us-west-2:032584774331:changeSet/changeset4-test/014e648e-30da-4c18-91df-5319d319b88c', 'StackId': 'arn:aws:cloudformation:us-west-2:032584774331:stack/boss-test/56b4d250-2d2a-11ec-9922-0abb512a1f57', 'StackName': 'boss-test', 'CreationTime': '2021-10-26 05:14:17.403000+00:00', 'ExecutionStatus': 'AVAILABLE', 'Status': 'CREATE_COMPLETE', 'NotificationARNs': [], 'RollbackConfiguration': {}, 'Capabilities': [], 'Changes': [{'Type': 'Resource', 'ResourceChange': {'Action': 'Modify', 'LogicalResourceId': 'HelloBucket', 'PhysicalResourceId': 'boss-test-hellobucket-q99jlx0g35p4', 'ResourceType': 'AWS::S3::Bucket', 'Replacement': 'False', 'Scope': ['Properties'], 'Details': [{'Target': {'Attribute': 'Properties', 'Name': 'AccessControl', 'RequiresRecreation': 'Never'}, 'Evaluation': 'Static', 'ChangeSource': 'DirectModification'}]}}], 'IncludeNestedStacks': False, 'ResponseMetadata': {'RequestId': '37cadf22-147a-4b5a-8f48-1ab6e9dbb0d9', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amzn-requestid': '37cadf22-147a-4b5a-8f48-1ab6e9dbb0d9', 'content-type': 'text/xml', 'content-length': '1793', 'date': 'Tue, 26 Oct 2021 05:15:20 GMT'}, 'RetryAttempts': 0}}

y = subprocess.Popen(args = ["checkov", "-f", "template.yaml", "--output", "json"], stdout = subprocess.PIPE)

a = loads(y.communicate()[0])

failed_checks = a['results']['failed_checks']

for check in failed_checks:
	violating_resource = check['resource'].split('.')[1]
	resources[violating_resource]['check_id'] = check['check_id']
	resources[violating_resource]['check_name'] = check['check_name']
	
account = boto3.client('sts').get_caller_identity().get('Account')
print(account)
alerts = []

for resource in resources.keys():
	alert = {}
	alert['Source'] = 'checkov'
	alert['PhysicalResourceId'] = resources[resource]['physicalResourceId']
	alert['LogicalResourceId'] = resource
	alert['ResourceType'] = resources[resource]['resourceType']
	alert['Changes'] = resources[resource]['changes']
	alert['CheckId'] = resources[resource]['check_id']
	alert['CheckName'] = resources[resource]['check_name']
	alert['Account'] = account
	alert['Region'] = aws_region
	alerts.append(dumps(alert))

alert = {"Source": "checkov", "PhysicalResourceId": "boss-test-hellobucket-q99jlx0g35p4", "LogicalResourceId": "HelloBucket", "ResourceType": "AWS::S3::Bucket", "Changes": [{"Type": "Resource", "ResourceChange": {"Action": "Modify", "LogicalResourceId": "HelloBucket", "PhysicalResourceId": "boss-test-hellobucket-q99jlx0g35p4", "ResourceType": "AWS::S3::Bucket", "Replacement": "False", "Scope": ["Properties"], "Details": [{"Target": {"Attribute": "Properties", "Name": "AccessControl", "RequiresRecreation": "Never"}, "Evaluation": "Static", "ChangeSource": "DirectModification"}]}}], "CheckId": "CKV_AWS_56", "CheckName": "Ensure S3 bucket has 'restrict_public_bucket' enabled", "Account": "032584774331", "Region": "us-west-2"}

headers = {
  'Accept': 'application/json, text/plain, */*',
  'Content-Type': 'application/json',
  'Origin': 'https://editor.dassana.io',
  'Referer': 'https://editor.dassana.io/',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
  'x-api-key': API_KEY,
  'x-dassana-cache': 'false'
}

print(headers)

response = requests.request("POST", f'{API_GATEWAY_ENDPOINT}/run', headers=headers, data=dumps(alert))

print(response.text)
