# Dassana IaC
Supercharge your DevSecOps teams using [Dassana](https://github.com/dassana-io/dassana) to get to production faster.</br><hr/>
Get started with 1-click </br></br>[![](https://cdn.rawgit.com/buildkite/cloudformation-launch-stack-button-svg/master/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://dassana-iac-prod-public.s3.amazonaws.com/deploy.yaml&stackName=Dassana-IaC-Action)

## Example usage
```yaml
on: 
  pull_request:
    paths:
      - 'cloudformation/template.yaml'

jobs:
  dassana-job:
    runs-on: ubuntu-latest
    name: dassana-action
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v2
      - name: python-test
        uses: actions/setup-python@v2.2.2
        with: 
          python-version: 3.8
      - name: Run Dassana IaC Action
        uses: dassana-io/CloudContext@main
        with:
          aws_region: 'us-west-2'
          bucket_name: 'cft-gh'
          stack_name: 'boss-test'
          template_file: './cloudformation/template.yaml'
          github_token: ${{ secrets.GITHUB_TOKEN }}
          aws_access_key_id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws_secret_access_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          api_gateway_endpoint: ${{ secrets.API_GATEWAY_ENDPOINT }}
          api_key: ${{ secrets.API_KEY }}
```
