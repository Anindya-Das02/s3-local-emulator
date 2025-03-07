#!/bin/bash

# Create the S3 bucket, folder structure & upload file
awslocal s3api create-bucket --bucket my-test-bucket
awslocal s3api put-object --bucket my-test-bucket --key folder1/folder2/
awslocal s3api put-object --bucket my-test-bucket --key folder1/data/test.txt --body /etc/localstack/init/ready.d/files/test.txt