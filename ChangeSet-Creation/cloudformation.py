from common import printlog
import time

from botocore.exceptions import ClientError
from s3 import get_file_content


def describe_change_set(cf, changeset_name, stack_name):

    changeset_status = ["CREATE_IN_PROGRESS"]
    printlog("FUNC", "describe_change_set", "changeset_name: "+str(changeset_name)+", stack_name: "+str(stack_name))
    try:
        response = cf.describe_change_set(ChangeSetName=changeset_name, StackName=stack_name)
        lc_cur_status = response['Status']
        
        for ln_loop in range(1, 9999):
            if lc_cur_status in changeset_status:
                printlog("INFO", "wait", "Waiting for status update(" + str(ln_loop) + ")...",)
                time.sleep(10) # pause 10 seconds

                try:
                    response = cf.describe_change_set(ChangeSetName=changeset_name, StackName=stack_name)
                    lc_cur_status = response['Status']
                    printlog("INFO", "wait", "Stack Status: " + response['Status'])
                except:
                    printlog("INFO", "wait", "Stack " + stack_name + " no longer exists")
                    lc_cur_status = "STACK_DELETED"
                    break
            elif "FAILED" in lc_cur_status:
                return False
            elif "CREATE_COMPLETE" in lc_cur_status:
                return True
            elif "CREATE_PENDING" in lc_cur_status:
                return True
            else:
                break
        return False
    except ClientError as ce:
        printlog("ERROR", "client_error", ce)
        return False


def create_change_set(cf, stack_name, template_url, params, changeset_name, changeset_type):

    message = "stack_name: "+str(stack_name)+", template_url: "+str(template_url)+", params: "+str(params)
    message = message+", changeset_name: "+str(changeset_name)+", changeset_type: "+str(changeset_type)
    printlog("FUNC", "create_change_set", message)
    changeset = {}
    try:
        cf.create_change_set(
            StackName=stack_name,
            TemplateURL=template_url,
            Parameters=params,
            Capabilities=[
                'CAPABILITY_IAM',
                'CAPABILITY_NAMED_IAM',
                'CAPABILITY_AUTO_EXPAND'
            ],
            ChangeSetName=changeset_name,
            ChangeSetType=changeset_type
        )

        changeset["status"] = changeset_type
        changeset["ChangeSetName"] = changeset_name
        changeset["StackName"] = stack_name
        
        return changeset
    except ClientError as e:
        if e.response['Error']['Code'] == 'ValidationError':
            printlog("WARNING", "validation_error", str(e))
            return "VALIDATION_ERROR"
        else:
            printlog("ERROR", "client_error", str(e))
            return "ROLLBACK"


def stack_exists(cf, stack):

    printlog("FUNC", "stack_exists", "stack: "+str(stack))
    try:
        cf.describe_stacks(StackName=stack)
        return True
    except ClientError as e:
        if "does not exist" in e.response['Error']['Message']:
            return False
        else:
            printlog("ERROR", "client_error", str(e))
            raise Exception(str(e))


def get_parameters_list(bucket_name, key_name, file):

    printlog("FUNC", "get_parameters_list", "bucket_name: "+str(bucket_name)+" "+"key_name: "+str(key_name)+" "+"file: "+str(file))
    la_parameters_data = get_file_content(bucket_name, key_name+file)

    if not la_parameters_data:
        return "ROLLBACK"

    try:    
        la_create_stack_parameters = []
        for lc_key in la_parameters_data.keys():
            la_create_stack_parameters.append({"ParameterKey": str(lc_key), "ParameterValue": str(la_parameters_data[lc_key])})

        printlog("INFO", "parameters", la_create_stack_parameters)
        return la_create_stack_parameters
    except Exception as e:
        printlog("ERROR", "exception", str(e))
        return "ROLLBACK"