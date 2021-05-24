import json
import boto3
import os
import time


from botocore.exceptions import ClientError


try:
    
    # s3 location where configuration file is stored
    CONFIG_BUCKET_NAME = os.environ['CONFIG_BUCKET_NAME']
    CONFIG_KEY_NAME = os.environ['CONFIG_KEY_NAME']
    
    # s3 location of the deploy stage artifact
    ARTIFACT_BUCKET_NAME = os.environ['ARTIFACT_BUCKET_NAME']
    ARTIFACT_KEY_NAME = os.environ['ARTIFACT_KEY_PATH']

    SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
except KeyError as ke:
    raise ke

try:
    cfn = boto3.client('cloudformation')
    s3  = boto3.resource('s3')
    sns = boto3.client('sns')
except ClientError as e:
    raise e


def get_file_content(bucket_name, object_key):

    printlog("FUNC", "get_file_content", "bucket_name: "+str(bucket_name)+", object_key: "+str(object_key))
    if not s3:
        return False
    else:
        try:
            obj = s3.Object(bucket_name, object_key)
            body = obj.get()['Body'].read()
            return body
        except ClientError as ce:
            printlog("ERROR", "client_error", str(ce))
            return False


def deploy_change_set(change_set_name, stack_name):

    printlog("FUNC", "get_file_content", "change_set_name: "+str(change_set_name)+", stack_name: "+str(stack_name))
    process_list = ["CREATE_COMPLETE", "ROLLBACK_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE", 
        "REVIEW_IN_PROGRESS", "IMPORT_COMPLETE", "IMPORT_ROLLBACK_COMPLETE"]
    
    try:
        stack_status = cfn.describe_stacks(StackName=stack_name)["Stacks"]
        stack_curr_status = stack_status[0]['StackStatus']

        printlog("INFO", "stack_curr_status", str(stack_curr_status))
        if stack_curr_status in process_list:
            cfn.execute_change_set(
                ChangeSetName=change_set_name,
                StackName=stack_name
            )
            return True
    except ClientError as ce:
        printlog("ERROR", "client_error", str(ce))
        return False


def check_status(lc_stack_name):

    printlog("FUNC", "check_status", "lc_stack_name: "+str(lc_stack_name))
    status = ['ROLLBACK_IN_PROGRESS','ROLLBACK_FAILED','ROLLBACK_COMPLETE','DELETE_IN_PROGRESS','DELETE_FAILED',
        'DELETE_COMPLETE','UPDATE_ROLLBACK_IN_PROGRESS','UPDATE_ROLLBACK_COMPLETE']

    try:
        lo_stacks = cfn.describe_stacks(StackName=lc_stack_name)["Stacks"]
        la_stack = lo_stacks[0]
        lc_cur_status = la_stack["StackStatus"]
        printlog("INFO", "lc_cur_status", str(lc_cur_status))

        for ln_loop in range(1, 9999):
            if "IN_PROGRESS" in lc_cur_status:
                printlog("INFO", "wait", "Waiting for status update(" + str(ln_loop) + ")...",)
                time.sleep(10) # pause 10 seconds

                try:
                    lo_stacks = cfn.describe_stacks(StackName=lc_stack_name)["Stacks"]
                except:
                    printlog("INFO", "wait", "Stack " + lc_stack_name + " no longer exists")
                    lc_cur_status = "STACK_DELETED"
                    break

                la_stack = lo_stacks[0]

                if la_stack["StackStatus"] != lc_cur_status:
                    lc_cur_status = la_stack["StackStatus"]
                    printlog("INFO", "update_status", "Updated status of stack " + la_stack["StackName"] + ": " + lc_cur_status)
            elif lc_cur_status in status:
                return False
            else:
                break
    except ClientError as ce:
        printlog("ERROR", "client_error", ce)
        return False
    except Exception as e:
        printlog("ERROR", "exception", e)
        return False

    return True


def printlog(logType, scope, Message):
    
    try:
        message = {
            'logType': logType,
            'scope': scope,
            'message' : Message
        }
        print(json.dumps(message))
    except Exception as e:
        message = {
            'logType': 'Error',
            'scope' : 'An error occured while printing logs',
            'message': str(e)   
        }
        print(json.dumps(message))


def check_dependency(exec_list, config_data, curr_stack_name):

    pass


def main():
    printlog("FUNC", "main", "Inside main function")

    pipeline_exec_id = os.environ['CODE_EXEC_ID']
    printlog("INFO", "pipeline_exec_id", str(pipeline_exec_id))

    object_key = ARTIFACT_KEY_NAME+pipeline_exec_id+'.txt'
    deploy_details = get_file_content(ARTIFACT_BUCKET_NAME, object_key)
    body_str = deploy_details.decode("utf-8")
    body_str = body_str.replace("\'", "\"")
    deploy_list = json.loads(body_str)
    printlog("INFO", "deploy_list", str(deploy_list))

    config_data = get_file_content(CONFIG_BUCKET_NAME, CONFIG_KEY_NAME)
    config_data = json.loads(config_data)
    printlog("INFO", "config_data", str(config_data))

    exec_list = []
    copy_exec_list = []
    for data in config_data["config_details"]:
        for cs in deploy_list["details"]:
            if data['stack_name'] == cs['StackName']:
                exec_list.insert(int(data['execution_order']), cs)
            
    printlog("INFO", "exec_list", str(exec_list))
    for exec in exec_list:
        cs_status = deploy_change_set(exec['ChangeSetName'], exec['StackName'])
        if cs_status:
            if not check_status(exec['StackName']):
                check_dependency(exec_list, config_data, exec['StackName'])
                
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Message="Unable to create/execute cloudformation stack",
                    Subject="Cloudformation Execution Failure"
                )
                raise Exception("Unable to create stack")
            else:
                printlog("INFO", "", "")


main()

#check if the failed stack has a dependency
#if dependency found with other change sets