source $PWD/artifacts/project.env

PROJECT() {
  zip project.zip ./* src/* src/env/* artifacts/*.json artifacts/*.env
  # s3 put
  aws s3api put-object --region $AWS_REGION \
  --bucket $EID-artifacts-$AWS_RGN --key $TYPE/$PID/project.zip \
  --body $PWD/project.zip --acl bucket-owner-full-control \
  --storage-class REDUCED_REDUNDANCY
}

DELETE() {
  # lambda
  aws lambda delete-function \
  --function-name $TYPE-$PID
  # layer
  # VER=4
  # for i in (seq 1 $VER);
  # do aws lambda delete-layer-version \
  # --layer-name "python-$TYPE-$PID" \
  # --version-number i;
  # done;
  # sns
  aws sns delete-topic --topic-arn $SNS:$TYPE-$PID
  # dynamodb
  aws dynamodb delete-table --table-name $TYPE-$PID
  # event
  aws events delete-rule --name lambda-$TYPE-$PID
}

PROJECT
DELETE
