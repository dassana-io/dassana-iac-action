import sys
import os
import boto3
import time
import subprocess
import requests
import uuid
import pandas as pd

from json import dumps, loads

GITHUB_REPO = os.environ['GITHUB_REPOSITORY']
GITHUB_SHA = os.environ['GITHUB_SHA']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_PR = os.environ['GITHUB_PR']

API_GATEWAY_ENDPOINT = 'https://yzl8a8ro0a.execute-api.us-east-2.amazonaws.com/v1'
API_KEY = 'rAS4YiYW6s4CyO2h8OJD13RtsiTcRfnB78RZfs6T'

aws_region = 'us-west-2'
s3_bucket_name = 'cft-gh'
cf_stack_name = 'boss-test'
cft_file_name = 'template.yaml'

api_request_headers = {
  'Accept': 'application/json, text/plain, */*',
  'Content-Type': 'application/json',
  'Origin': 'https://editor.dassana.io',
  'Referer': 'https://editor.dassana.io/',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
  'x-api-key': API_KEY,
  'x-dassana-cache': 'false'
}

def stylize_risk(risk):
	if risk == 'high':
		risk = 'High :red_circle:'
	elif risk == 'medium':
		risk = 'Medium :yellow_circle:'
	elif risk == 'low':
		risk = 'Low :white_circle:'
	else:
		risk = ' -'
	return risk

def post_findings_to_github(analysis_table):
	pr_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{GITHUB_PR}/comments"
	headers = {'Content-Type': 'application/json', 'Authorization': f'token {GITHUB_TOKEN}'}
	data_string = f"""<h3>Dassana has detected changes in your tracked CloudFormation template</h3></br>Review the following to avoid service disruptions and/or security risks <hr/></br><details><summary>View Dassana's Change Analysis</summary></br>

{analysis_table}</details>"""
	data = {'body':data_string}
				
	r = requests.post(url = pr_url, data = dumps(data), headers = headers)

def create_analysis_table(decorated_alerts, modified_resources):
	resources = []
	types = []
	policy_names = []
	policies = []
	general_risks = []
	resource_risks = []
	policy_risks = []
	context_urls = []

	base_editor_url = 'https://editor.dassana.io'

	for alert in decorated_alerts:
		alert = alert['dassana']

		general_risk = ' -'
		resource_risk = ' -'
		policy_risk = ' -'

		resource_id = alert['normalize']['output']['resourceId']
		resource_type = alert['normalize']['output']['service'] + ':' + alert['normalize']['output']['resourceType']
		policy_id = alert['normalize']['output']['vendorPolicy']
		vendor_id = alert['normalize']['output']['vendorId']
		alert_id = alert['normalize']['output']['alertId']
		policy_name = ''
		
		for k, v in modified_resources.items():
			if v['physicalResourceId'] == resource_id:
				check_index = 0
				for check in v['check_id']:
					if check == policy_id:
						policy_name = v['check_name'][check_index]
					check_index += 1

		if 'risk' in alert['general-context']:
			general_risk = alert['general-context']['risk']['riskValue']
			general_risk = stylize_risk(stylize_risk)
		
		if 'risk' in alert['resource-context']:
			resource_risk = alert['resource-context']['risk']['riskValue']
			resource_risk = stylize_risk(resource_risk)
		
		if 'risk' in alert['policy-context']:
			policy_risk = alert['policy-context']['risk']['riskValue']
			policy_risk = stylize_risk(policy_risk)

		context_url = f'[View]({base_editor_url}/?alertId={alert_id}&vendorId={vendor_id})'

		resources.append(resource_id)
		types.append(resource_type)
		policies.append(policy_id)
		general_risks.append(general_risk)
		resource_risks.append(resource_risk)
		policy_risks.append(policy_risk)
		policy_names.append(policy_name)
		context_urls.append(context_url)
		
	changes_df = pd.DataFrame({
		"Resource": resources,
		"Type": types,
		"Policy Name": policy_names,
		"Policy ID": policies,
		"General Risk": general_risk,
		"Resource Risk": resource_risk,
		"Policy Risk": policy_risk,
		"Context": context_urls
	}).set_index("Resource")

	return changes_df.to_markdown()


def decorate_alerts(alerts):
	decorated_alerts = []

	for alert in alerts:
		response = requests.request('POST', url=f'{API_GATEWAY_ENDPOINT}/run?includeInputRequest=false&mode=test', headers=api_request_headers, data=dumps(alert))
		decorated_alerts.append(response.json())
	
	return decorated_alerts
	
def create_alerts(resources):
	account = boto3.client('sts').get_caller_identity().get('Account')
	alerts = []

	for resource in resources.keys():
		for i in range(0, len(resources[resource]['check_id'])):
			alert = {}
			alert['Source'] = 'checkov'
			alert['PhysicalResourceId'] = resources[resource]['physicalResourceId']
			alert['LogicalResourceId'] = resource
			alert['ResourceType'] = resources[resource]['resourceType']
			alert['Changes'] = resources[resource]['changes']
			alert['CheckId'] = resources[resource]['check_id'][i]
			alert['CheckName'] = resources[resource]['check_name'][i]
			alert['Account'] = account
			alert['Region'] = aws_region
			alerts.append(dumps(alert))
	
	return alerts


def add_checkov_results(resources):
	checkov_scan = subprocess.Popen(args = ["checkov", "-f", cft_file_name, "--output", "json"], stdout = subprocess.PIPE)

	checkov_results = loads(checkov_scan.communicate()[0])

	failed_checks = checkov_results['results']['failed_checks']

	for check in failed_checks:
		violating_resource = check['resource'].split('.')[1]
		if violating_resource in resources:
			resources[violating_resource]['check_id'].append(check['check_id'])
			resources[violating_resource]['check_name'].append(check['check_name'])

def get_modified_resources(change_set):
	modified_resources = {}
	created_resources = {}

	for change in change_set['Changes']:
		if change['ResourceChange']['Action'] == 'Modify':
			logical_resource = change['ResourceChange']['LogicalResourceId']

			if logical_resource in modified_resources:
				modified_resources[logical_resource]['changes'].append(change)	
			else:
				modified_resources[logical_resource] = {
						'changes': [change], 
						'physicalResourceId': '', 
						'resourceType': change['ResourceChange']['ResourceType'], 
						'check_id': [], 
						'check_name': [],
					}

				if 'PhysicalResourceId' in change['ResourceChange']:
					modified_resources[logical_resource]['physicalResourceId'] = change['ResourceChange']['PhysicalResourceId']
		else:
			logical_resource = change['ResourceChange']['LogicalResourceId']

			if logical_resource in created_resources:
				created_resources[logical_resource]['changes'].append(change)	
			else:
				created_resources[logical_resource] = {
						'changes': [change], 
						'resourceType': change['ResourceChange']['ResourceType'], 
						'check_id': [], 
						'check_name': [],
					}

	return modified_resources

def create_change_set():
	"""
	Uploads CFT to S3 and creates a changeset
	"""
	cft_client = boto3.client('cloudformation', region_name=aws_region)
	s3 = boto3.resource('s3', region_name=aws_region)

	response = s3.meta.client.upload_file(cft_file_name, s3_bucket_name, cft_file_name)
	changeset_name = 'cft-' + str(uuid.uuid4()).replace('-', '')

	response = cft_client.create_change_set(
		StackName=cf_stack_name, 
		TemplateURL=f'https://{s3_bucket_name}.s3.amazonaws.com/{cft_file_name}',
		ChangeSetName=changeset_name,
		ChangeSetType='UPDATE'
	)

	waiter = cft_client.get_waiter('change_set_create_complete')
	
	waiter.wait(
    	ChangeSetName=changeset_name,
    	StackName=cf_stack_name,
    	WaiterConfig={
        	'Delay': 5,
        	'MaxAttempts': 50
    	}
	)

	response = cft_client.describe_change_set(
		ChangeSetName=changeset_name,
		StackName=cf_stack_name
	)

	response = loads(dumps(response, default=str))
	return response

def dassana_is_configured():
	"""
	Checks if API_KEY is valid for a reachable Dassana deployment at API_GATEWAY_ENDPOINT 
	"""
	ping_response = requests.request('GET', url=f'{API_GATEWAY_ENDPOINT}/ping', headers=api_request_headers)
	return ping_response.status_code == 200

def main():
	if not dassana_is_configured():
		sys.exit(-1)
	
	change_set = create_change_set()
	
	modified_resources = get_modified_resources(change_set)
	add_checkov_results(modified_resources)

	alerts = create_alerts(modified_resources)
	decorated_alerts = decorate_alerts(alerts)
	
	analysis_table = create_analysis_table(decorated_alerts, modified_resources)

	post_findings_to_github(analysis_table)

if __name__ == "__main__":
	main()
