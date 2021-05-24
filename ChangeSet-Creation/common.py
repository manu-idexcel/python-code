import json

from botocore import exceptions


def get_byte_to_list(file_data):

    printlog("FUNC", "get_byte_to_list", str(file_data))
    file_list = []
    buffer_list = []

    try:
        for c in file_data:
            if c == '\n':
                file_list.append(''.join(buffer_list))
                buffer_list = []
            else:
                buffer_list.append(c)
        else:
            if buffer_list:
                file_list.append(''.join(buffer_list))
    except Exception as e:
        printlog("ERROR", "exception". str(e))
        return False

    return file_list


def format_message(message):

    printlog("FUNC", "format_message", str(message))
    header = "CloudFormation Changeset Details"
    header = header+"\n"
    header = header+"==================================="
    update = ""
    create = ""
    
    try:
        for detail in message:
            if (detail != None and detail['status'] == 'UPDATE'):
                update = update + '\n'
                update = update + "StackName: "+detail['StackName']+'\n'
                update = update + "ChangeSetName: "+detail['ChangeSetName']+'\n'
                update = update + '\n'
            elif (detail != None and detail['status'] == 'CREATE'):
                create = create + '\n'
                create = create + "StackName: "+detail['StackName']+'\n'
                create = create + "ChangeSetName: "+detail['ChangeSetName']+'\n'
                create = create + '\n'

        custom_message = header+update+create
        return custom_message
    except Exception as e:
        printlog("ERROR", "exception", str(e))
        return False


def write_to_file(file_name, message):
    
    printlog("FUNC", "write_to_file", "file_name: "+str(file_name)+", message: "+str(message))
    try:
        f = open(file_name, "a")
        f.write(str(message))
        f.close()
        return True
    except Exception as e:
        printlog("ERROR", "exception", e)
        return "ROLLBACK"


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