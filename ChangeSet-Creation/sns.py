from common import printlog
from botocore.exceptions import ClientError


def send_message(sns, sns_arn, subject, message):

    printlog("FUNC", "send_message", "sns_arn: "+str(sns_arn)+", subject: "+str(subject)+", message: "+str(message))
    try:
        sns.publish(
            TopicArn=sns_arn,
            Message=message,
            Subject=subject
        )
    except ClientError as ce:
        printlog("ERROR", "client_error", str(ce))
        return False