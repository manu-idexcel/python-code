import json
import tempfile
import zipfile
import boto3 

from botocore.exceptions import ClientError
from common import printlog


def get_file_content(bucket_name, object_key):

    printlog("FUNC", "get_file_content", "bucket_name: "+str(bucket_name)+", object_key: "+str(object_key))
    s3 = boto3.resource('s3')
    if not s3:
        return False
    else:
        try:
            obj = s3.Object(bucket_name, object_key)
            body = obj.get()['Body'].read()
            return json.loads(body)
        except ClientError as ce:
            printlog("ERROR", "client_error", str(ce))
            return False


def get_artifact_file_content(s3, artifacts):
    printlog("FUNC", "get_artifact_file_content", "artifacts: "+str(artifacts))
    try:
        bucket_name = artifacts[0]['location']['s3Location']['bucketName']
        key_name = artifacts[0]['location']['s3Location']['objectKey']

        tmp_file = tempfile.NamedTemporaryFile()

        with tempfile.NamedTemporaryFile() as tmp_file:
            s3.download_file(bucket_name, key_name, tmp_file.name)
            with zipfile.ZipFile(tmp_file.name, 'r') as zip:
                file_body = zip.read('check-code/list.txt')
                return file_body.decode("utf-8")
    except Exception as ce:
        printlog("ERROR", "exception", str(ce))
        return False


def upload_artifact(s3, file_name, bucket, object_name=None):

    printlog("FUNC", "upload_artifact", "file_name: "+str(file_name)+", bucket: "+str(bucket)+", object_name: "+str(object_name))
    if object_name is None:
        object_name = file_name
        
    try:
        return s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        printlog("ERROR", "client_error", str(e))
        return "ROLLBACK"