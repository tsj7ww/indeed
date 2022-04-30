# Indeed ETL
Python web scraper running on AWS Lambda to pull job postings data from Indeed.com.

### AWS
- Lambda: compute for the web scraper
- IAM: Lambda & Events custom roles
- DynamoDB: store scraped job postings for future use
- S3: store source code & Lambda layer packages
- Events: automate job kickoff with CRON event
- SNS: notification of job success / failure
- SES: send email summary of scraped job postings

### [Python](./src/main.py)
- Features
  - Concurrency
  - RegEx text cleaning
  - Logging

### Shell
- [Build](./build.sh): load source code to S3 & build AWS services (Lambda, DynamoDB, IAM, SNS, Events)
- [Update](./update.sh): update source code in S3 & Lambda, update Lambda layer
- [Cleanup](./cleanup.sh): delete AWS services (Lambda, DynamoDB, SNS, Events)

### ToDo
1. AWS API Gateway with query params for job title & location
1. Create Docker environment for local testing
1. Finish Makefile for quick maintenance
