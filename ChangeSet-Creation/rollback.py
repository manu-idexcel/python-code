from botocore import exceptions
from botocore.exceptions import ClientError
from common import printlog


def rollback_all(cfn, changeset_list):
    
    printlog("FUNC", "rollback_all", str(changeset_list))
    try:
        for stack in changeset_list:
            cfn.delete_change_set(
                ChangeSetName=stack['ChangeSetName'],
                StackName=stack['StackName']
            )
            printlog("INFO", "delete_change_set", "Successfully deleted changeset "+str(stack['ChangesetName']))
    except ClientError as ce:
        printlog("ERROR", "client_error", str(ce))
        raise ClientError(str(ce))


def get_stack_name(config, d):

    printlog("FUNC", "get_stack_name", str(d))
    try:
        for s in config['config_details']:
            if (s['identifier']['Name'] == d):
                return s['stack_name']
    except KeyError as ke:
        printlog("ERROR", "keyerror", str(ke))
        raise KeyError(str(ke))
    except Exception as e:
        printlog("ERROR", "exception", str(e))
        raise KeyError(str(e))

    return "NOT_FOUND"


def check_changeset_created(config, dependency_list, created_changeset_list):

    printlog("FUNC", "check_changeset_created", "config: "+str(config)+", dependency_list: "+str(dependency_list)+", created_changeset_list: "+str(created_changeset_list))    
    created_list = []

    for d in dependency_list:
        stack_name = get_stack_name(config, d)
        if stack_name == "NOT_FOUND":
            raise Exception('Unable to find stack name from configuration file.')

        for c in created_changeset_list:
            if stack_name in c['StackName']:
                created_list.append(c)
    
    return created_list


def check_dependency(config, messagedata, stack_name):

    printlog("FUNC", "check_dependency", "messagedata: "+str(messagedata)+", stack_name: "+str(stack_name))
    for cfn in config['config_details']:
        if (stack_name == cfn['stack_name'] and cfn['dependency']):
            created_list = check_changeset_created(config, cfn['dependency'], messagedata)
            return created_list
        else:
            pass

    return False