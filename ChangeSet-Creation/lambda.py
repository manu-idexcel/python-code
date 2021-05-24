import boto3
import traceback
import os


from botocore.exceptions import ClientError
from common import format_message, get_byte_to_list, write_to_file, printlog
from cloudformation import create_change_set, get_parameters_list, stack_exists, describe_change_set
from codepipeline import put_job_failure, put_job_success
from s3 import get_file_content, get_artifact_file_content, upload_artifact
from sns import send_message
from rollback import check_dependency, rollback_all


try:
    # s3 location where cfn templates are stored
    TEMPLATE_BUCKET_NAME = os.environ['TEMPLATE_BUCKET_NAME']
    TEMPLATE_KEY_PREFIX = os.environ['TEMPLATE_KEY_PREFIX'] # Enter only the prefix of the filename eg: /foldername/
    
    # s3 location where configuration file is stored
    CONFIG_BUCKET_NAME = os.environ['CONFIG_BUCKET_NAME']
    CONFIG_KEY_NAME = os.environ['CONFIG_KEY_NAME']
    
    # s3 location of the deploy stage artifact
    ARTIFACT_BUCKET_NAME = os.environ['ARTIFACT_BUCKET_NAME']
    ARTIFACT_KEY_NAME = os.environ['ARTIFACT_KEY_PATH']

    # s3 location where cfn parameters are stored
    PARAMETERS_BUCKET_NAME = os.environ['PARAMETERS_BUCKET_NAME']
    PARAMETERS_KEY_NAME = os.environ['PARAMETERS_KEY_NAME'] # Enter only the prefix of the filename eg: /foldername/

    INPUT_ARTIFACT_FILE = os.environ['CHANGE_FILE_NAME']
    SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
except KeyError as ke:
    # s3 location where cfn templates are stored
    TEMPLATE_BUCKET_NAME = 'pipeline-shared-codebuild-manu-nvirginia-561880438739'
    TEMPLATE_KEY_PREFIX  = '/templates/'
    
    # s3 location where configuration file is stored
    CONFIG_BUCKET_NAME = 'pipeline-shared-codebuild-manu-nvirginia-561880438739'
    CONFIG_KEY_NAME    = 'configuration/config.json'
    
    # s3 location of the deploy stage artifact
    ARTIFACT_BUCKET_NAME = 'manu-prathapan-test-bucket'
    ARTIFACT_KEY_NAME    = 'test-cfn-pipeline/Changeset/'

    # s3 location where cfn parameters are stored
    PARAMETERS_BUCKET_NAME = 'pipeline-shared-codebuild-manu-nvirginia-561880438739'
    PARAMETERS_KEY_NAME    = 'parameters/'

    SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:561880438739:nginx-process-check'
    # raise ke


try:
    cf = boto3.client('cloudformation')
    cp = boto3.client('codepipeline')
    s3 = boto3.client('s3')
    sns = boto3.client('sns')
except ClientError as e:
    raise e


def lambda_handler(event, context):

    #printlog("INFO", "event", event)
    try:
        details = {}
        changeset = {}
        messagedata = []
        
        pipeline_exec_id = event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters']
        job_id = event['CodePipeline.job']['id']
        job_data = event['CodePipeline.job']['data']
        artifacts = job_data['inputArtifacts']

        file_data = get_artifact_file_content(s3, artifacts)
        if not file_data:
            raise Exception('Unable to get artifact file')

        file_data_list = get_byte_to_list(file_data)
        if not file_data_list:
            raise Exception('Unable to convert byte to string')

        config_data = get_file_content(CONFIG_BUCKET_NAME, CONFIG_KEY_NAME)
        if not config_data:
            raise Exception('Unable to download config file')

        for filename in file_data_list:
            for det in config_data['config_details']:
                if (filename == det['template']):
                    stack_name = det['stack_name']
                    parameters_filename = det['parameters']

                    params = get_parameters_list(PARAMETERS_BUCKET_NAME, PARAMETERS_KEY_NAME, parameters_filename)

                    if params == "ROLLBACK" and messagedata:
                        dependency_list = check_dependency(config_data, messagedata, stack_name)
                        
                        if dependency_list:
                            rollback_all(cf, dependency_list)

                    if stack_exists(cf, stack_name):
                        template_url = "https://"+TEMPLATE_BUCKET_NAME+".s3.amazonaws.com"+TEMPLATE_KEY_PREFIX+filename
                        changeset_name = stack_name+"-"+job_id
                        changeset_type = "UPDATE"
                        
                        changeset = create_change_set(cf, stack_name, template_url, params, changeset_name, changeset_type)
                        printlog("INFO", "changeset", str(changeset))

                        if changeset == "VALIDATION_ERROR":
                            pass
                        elif changeset == "ROLLBACK":
                            dependency_list = check_dependency(config_data, messagedata, stack_name)
                        
                            if dependency_list:
                                rollback_all(cf, dependency_list)

                        elif changeset != None:
                            if not describe_change_set(cf, changeset_name, stack_name):
                                raise Exception('Unable to create changeset ' + str(changeset_name))
                            else:
                                messagedata.append(changeset)
                        else:
                            raise Exception('Unable to create changeset ' + str(changeset_name))
                    else:
                        template_url = "https://"+TEMPLATE_BUCKET_NAME+".s3.amazonaws.com"+TEMPLATE_KEY_PREFIX+filename
                        changeset_name = stack_name+"-"+job_id
                        changeset_type = "CREATE"
                        
                        changeset = create_change_set(cf, stack_name, template_url, params, changeset_name, changeset_type)
                        printlog("INFO", "changeset", str(changeset))

                        if changeset == "VALIDATION_ERROR":
                            pass
                        elif changeset == "ROLLBACK":
                            dependency_list = check_dependency(config_data, messagedata, stack_name)
                        
                            if dependency_list:
                                rollback_all(cf, dependency_list)
                                
                        elif changeset != None:
                            if not describe_change_set(cf, changeset_name, stack_name):
                                raise Exception('Unable to create changeset ' + str(changeset_name))
                            else:
                                messagedata.append(changeset)
                        else:
                            raise Exception('Unable to create changeset ' + str(changeset_name))
                else:
                    pass
        
        if not messagedata:
            raise Exception('There are no change sets created')

        job_file_name = str(pipeline_exec_id)+'.txt'
        # job_file_name = '/tmp/'+str(pipeline_exec_id)+'.txt'
        details["details"] = messagedata
        if write_to_file(job_file_name, details) == "ROLLBACK":
            pass

        upload_response = upload_artifact(s3, job_file_name, ARTIFACT_BUCKET_NAME, ARTIFACT_KEY_NAME+str(pipeline_exec_id)+'.txt')
        if upload_response == "ROLLBACK":
            pass
        
        formatted_message = format_message(messagedata)
        if not formatted_message:
            message="There was a error while formatting the message. Raw data appended to this message\n"
            message=message+str(messagedata)
            send_message(sns, SNS_TOPIC_ARN, "Cloudformation Changeset Approval Details", message)
        else:
            send_message(sns, SNS_TOPIC_ARN, "Cloudformation Changeset Approval Details", formatted_message)

        #put_job_success(cp, job_id, 'Stack update complete')
        printlog("INFO", "complete", "Function executed successfully")
    except KeyError as ke:
        printlog("ERROR", "keyerror", 'Function failed due to keyerror exception')
        #put_job_failure(cp, job_id, 'Function exception: ' + str(ke))
    except Exception as e:
        printlog("ERROR", "exception", 'Function failed due to exception')
        #put_job_failure(cp, job_id, 'Function exception: ' + str(e))

    return True


event = {
  "CodePipeline.job": {
    "id": "0556ea88-fccf-4a47-867f-826547d2ed7c",
    "accountId": "561880438739",
    "data": {
      "actionConfiguration": {
        "configuration": {
          "FunctionName": "codepipeline-cfn",
          "UserParameters": "2deb8702-2207-47e4-b148-8825ffc80c18"
        }
      },
      "inputArtifacts": [
        {
          "name": "BuildArtifactOne",
          "revision": "None",
          "location": {
            "type": "S3",
            "s3Location": {
              "bucketName": "manu-prathapan-test-bucket",
              "objectKey": "test-cfn-pipeline/BuildArtif/ZaqyUVc"
            }
          }
        }
      ],
      "outputArtifacts": [
        {
          "name": "LambdaArtifacts",
          "revision": "None",
          "location": {
            "type": "S3",
            "s3Location": {
              "bucketName": "manu-prathapan-test-bucket",
              "objectKey": "test-cfn-pipeline/LambdaArti/97CLUoZ"
            }
          }
        }
      ],
      "artifactCredentials": {
        "accessKeyId": "ASIAYFUVPC7JZ4FUPK6F",
        "secretAccessKey": "GBVFkgg+VzaivUGB4YzTvsxQCQjT6MZbKUKaoPCb",
        "sessionToken": "IQoJb3JpZ2luX2VjEKj//////////wEaCXVzLWVhc3QtMSJIMEYCIQCBlqwMUKQ/ncPQwnI2ZBM+oa7MVtOjd7cC2ubIaHhDgwIhAL4w5Kc0otgyQe1b2IvgqdkaQfm8YbMBWK0kKMXl8iDEKpoFCEAQAhoMNTYxODgwNDM4NzM5Igw+d5KE8tEwOt5Zvz0q9wSF9/POLwmPVq3cE3riIJ7GODvdzrmERMxcrNmTFVmIkLYbetIotIdVyYrMxiyzlgM9WsJKsFhUbUO/cXBoKS8T/kMpUDH9YQXvdzMwgo/nqU/7tluL5UJh0tSJQVEF9CJbcjzAzvhMx1N69lC0Mw2TK+V7/g0SE+Wfw2ahWfB7ylOvogI+M8zjANrE4SpUaE+3/mjL3wLrchyIDCyHOgamydRLjlG80r+QxBSMHm7eIy8763mOzGbIjf4UG39qIq1oVf2IkhVqz/XPWbRfQxB+EtY5XaeBW6Ys6m5t+8LzgICyJ+i/tv8UvFI0d9B5QdHeLb1zVybv9fl9onp0ETSV3L5UcAYTNydFQQK/l7Srtekk6cYCrpt2CWWg6AXpreVOheDKL9f3/SNxP6AexXo+ePCl2IvlgSSBwzlna8+xGMBhWZ8FORb8HASu61Nlhypbir8cXraCFqIaiU716CwkkTwat3HLHx4nM5THxeRjI5weeMSKLNryT6tKTNaJemnOcXUd01Ge+y4rUhO7GMtBx54VTghNbqB5z4s1O2u/nixFgbemBmQ4Gr8W2RteIwr2DTeV+8QrbkNfX6zL35K3Sdu2PKb/YkQSqk2G+VFoodwt3JhuhXtUTmiK3To09aTopO+QIGv9w1dSS5UdUI2yo/wTKaP6rEyzLMpf0Ay90T452IvGA9A6KRQ521Xq2WnsnHDfHFCPLnPjxjB30Lk39crhM2QMRQ0Y9FdBf0wvC7nnqd61jTgBJ0XRC7MrlvvQ88wuVgiHzvUhgF45G7mpIMbm088UnUgOf5tFvxpXj4qoFhSzbykDbwT7AB+h82aImEMzwojYMLiyiIUGOr4BBd4+37Io6VEYkx1x8G+vV9p5qqQLYfhYjcLpnJNeHLdrij1FQue8Dn6JiYh3K5m8il8xpKFq2hBtjNkrRNjP3i/nPlSaC2czrGY59uNEbYpbnyl4Uf6OoAFf0tx86y1ysq0F2Uxsdk+meyq8JtnIxI4qSxtFqqzZtn+4FfWl5iXe7Ya8BZVPtLQq0ZmG25NhHlcPa2PCiAPQmEhlpNyos5iY6vfd9Hqd05cN5rM3TbvCtVz60BlJ5gq7uHzcYQ==",
        "expirationTime": 1621236924000
      }
    }
  }
}


lambda_handler(event, 0)