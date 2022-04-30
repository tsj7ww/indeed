source $PWD/artifacts/project.env

SRC() {
  # zip source py code
  (cd $1 && zip -r $2/src.zip ./*)
  # s3 put
  aws s3api put-object --region $AWS_REGION \
  --bucket $EID-artifacts-$AWS_RGN --key $TYPE/$PID/src.zip \
  --body $2/src.zip --acl bucket-owner-full-control \
  --storage-class REDUCED_REDUNDANCY
}

LAMBDA() {
  aws lambda update-function-code \
  --function-name $TYPE-$PID \
  --s3-bucket $EID-artifacts-$AWS_RGN \
  --s3-key $TYPE/$PID/src.zip \
  --publish
}

LAYER() {
  PKG=$1/layers/webscrape
  # install reqs
  pip install -r $PKG/requirements.txt -t $PKG/python/lib/python3.8/site-packages
  # zip layer
  (cd $PKG && zip -r $1/webscrape.zip ./*)
  # s3 put
  aws s3api put-object --region $AWS_REGION \
  --bucket $EID-artifacts-$AWS_RGN --key layers/python/webscrape.zip \
  --body $1/webscrape.zip --acl bucket-owner-full-control \
  --storage-class REDUCED_REDUNDANCY
  # publish layer
  aws lambda publish-layer-version \
  --layer-name python-webscrape \
  --compatible-runtimes "python3.8" \
  --description "Python web scraping packages. Includes: bs4, requests." \
  --content S3Bucket=$EID-artifacts-$AWS_RGN,S3Key=layers/python/webscrape.zip
  # update lambda
  aws lambda update-function-configuration \
  --function-name $TYPE-$PID \
  --layers "$LAYER:python-webscrape:2"

}

PROJECT() {
  zip project.zip ./* src/* src/env/* artifacts/*.json artifacts/*.env
  # s3 put
  aws s3api put-object --region $AWS_REGION \
  --bucket $EID-artifacts-$AWS_RGN --key $TYPE/$PID/project.zip \
  --body $PWD/project.zip --acl bucket-owner-full-control \
  --storage-class REDUCED_REDUNDANCY
}

UPDATE() {
  SRC=$PWD/src
  ART=$PWD/artifacts

  SRC $SRC $ART
  LAMBDA

  # LAYER $ART

  PROJECT
}

UPDATE
