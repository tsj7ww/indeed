source $PWD/artifacts/project.env

DYNAMO() {
    aws dynamodb create-table --table-name $TYPE-$PID \
    --attribute-definitions AttributeName=indeed_id,AttributeType=S \
    --key-schema AttributeName=indeed_id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
    # --sse-specification Enabled=true SSEType=AES256
    # aws dynamodb delete-table --table-name $PID

    # attach policy???
}

SNS() {
  # create topic
  aws sns create-topic --name $TYPE-$PID
  # subscribe stakeholders (a.k.a. me)
  aws sns subscribe --topic-arn "$SNS:$TYPE-$PID" --protocol email --notification-endpoint $SENDER

  # allow invoke from lambda -> only need for cross account
  # aws sns add-permission --topic-arn $SNS
}

IAM() {
  ### lambda
  # role + trust policy
  aws iam create-role \
  --role-name lambda-$TYPE-$PID \
  --assume-role-policy-document file://$PWD/artifacts/iam-lambda-trust.json \
  --description "IAM role for Indeed $TYPE Lambda function."

  # policy - exec, dynamodb crud, sns publish, ses send
  aws iam put-role-policy \
  --role-name lambda-$TYPE-$PID \
  --policy-name lambda-$TYPE-$PID \
  --policy-document file://$PWD/artifacts/iam-lambda-policy.json

  ### events
  # role + trust
  aws iam create-role \
  --role-name events-$TYPE-$PID \
  --assume-role-policy-document file://$PWD/artifacts/iam-events-trust.json \
  --description "IAM role for $TYPE Indeed cron event."

  # policy - event target role
  aws iam attach-role-policy \
  --role-name events-$TYPE-$PID \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSBatchServiceEventTargetRole"
}

LAMBDA() {
  # publish layer
  aws lambda publish-layer-version \
  --layer-name python-webscrape \
  --compatible-runtimes "python3.8" \
  --description "Python web scraping packages. Includes: bs4, requests." \
  --content S3Bucket=$EID-artifacts-$AWS_RGN,S3Key=layers/python/webscrape.zip
  # update lambda
  aws lambda create-function \
  --function-name $TYPE-$PID \
  --runtime "python3.8" \
  --role "$IAM/lambda-$TYPE-$PID" \
  --handler main.HANDLER \
  --code S3Bucket=$EID-artifacts-$AWS_RGN,S3Key=$TYPE/$PID/src.zip \
  --description "Function for intaking queries and responding with postings from Indeed.com" \
  --publish --timeout 120 \
  --layers "$LAYER:python-webscrape:1"
  #--environment $PWD/src/env/prod

  # allow invoke from events
  aws lambda add-permission \
  --function-name $TYPE-$PID \
  --statement-id sns \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn "$EVENTS/$TYPE-$PID"

}

EVENTS() {
  # setup event
  aws events put-rule \
  --name $TYPE-$PID \
  --schedule-expression "cron(59 8 ? * SUN *)" \
  --state ENABLED --description "$TYPE Indeed.com cron" \
  --role-arn "$IAM/events-$TYPE-$PID"
  # set target
  aws events put-targets --rule $TYPE-$PID --targets "Id"="1","Arn"="$FUNCTION:$TYPE-$PID"
  # --role-arn $IAM/event-$TYPE-$PID
}

COMPILE() { # TODO: build src env files from build env??
  SRC=$PWD/src
  ART=$PWD/artifacts
  # zip source py code
  (cd $SRC && zip -r $ART/src.zip ./*)
  # s3 put
  aws s3api put-object --region $AWS_REGION --bucket $EID-artifacts-$AWS_RGN --key $TYPE/$PID/src.zip --body $ART/src.zip --acl bucket-owner-full-control --storage-class REDUCED_REDUNDANCY
  # install reqs
  PKG=$ART/layers/webscrape
  pip install -r $LAYER/requirements.txt -t $PKG/python/lib/python3.8/site-packages
  # zip layer
  (cd $PKG && zip -r $ART/webscrape.zip ./*)
  # s3 put
  aws s3api put-object --region $AWS_REGION --bucket $EID-artifacts-$AWS_RGN --key layers/python/webscrape.zip --body $ART/webscrape.zip --acl bucket-owner-full-control --storage-class REDUCED_REDUNDANCY
}

PROJECT() {
  zip project.zip ./* src/* src/env/* artifacts/*.json artifacts/*.env
  # s3 put
  aws s3api put-object --region $AWS_REGION \
  --bucket $EID-artifacts-$AWS_RGN --key $TYPE/$PID/project.zip \
  --body $PWD/project.zip --acl bucket-owner-full-control \
  --storage-class REDUCED_REDUNDANCY
}

BUILD() {
  # dev
  if $1;
    then
      DYNAMO;
      SNS; # SES -> no setup
  fi;
  # prod
  if $2;
    then
      COMPILE;
      IAM;
      LAMBDA;
      EVENTS;
      PROJECT;
  fi;
}

BUILD true true
