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
        uses: kloading/CloudContext@main
        with:
          aws_region: 'us-west-2'
          bucket_name: 'cft-bucket'
          stack_name: 'test-stack'
          template_file: './cloudformation/template.yaml'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_PR: ${{ github.event.number }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          API_GATEWAY_ENDPOINT: ${{ secrets.API_GATEWAY_ENDPOINT }}
          API_KEY: ${{ secrets.API_KEY }}
```
