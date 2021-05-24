from botocore.exceptions import ClientError
from common import printlog


def put_job_failure(code_pipeline, job, message):

    printlog("FUNC", "put_job_failure", "job: "+str(job)+", message: "+str(message))
    try:
        code_pipeline.put_job_failure_result(jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})
    except ClientError as ce:
        printlog("ERROR", "client_error", str(ce))
        raise Exception(ce)


def put_job_success(code_pipeline, job, message):

    printlog("FUNC", "put_job_success", "job: "+str(job)+", message: "+str(message))
    try:
        code_pipeline.put_job_success_result(jobId=job)
    except ClientError as ce:
        printlog("ERROR", "client_error", str(ce))
        raise Exception(ce)