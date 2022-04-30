# project
EID=tsj7ww
PID=indeed
TYPE=etl
PROJECT=$JOB-$PID

# aws
AWS_REGION=us-east-1
AWS_RGN=useast1
AWS_ACCOUNT=<NUM>
IAM=arn:aws:iam::$AWS_ACCOUNT:role
SNS=arn:aws:sns:$AWS_REGION:$AWS_ACCOUNT
FUNCTION=arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT:function
LAYER=arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT:layer
EVENTS=arn:aws:events:$AWS_REGION:$AWS_ACCOUNT:rule

# email
OWNER=trevsjordan@gmail.com
SENDER=trevsjordan@gmail.com
STAKEHOLDERS=trevsjordan@gmail.com
