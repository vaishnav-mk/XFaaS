from azure.storage.queue import QueueClient
import json
from python.src.utils.classes.commons.serwo_objects import SerWOObject
import os, uuid
import logging
import boto3

connect_str = "CONNECTION_STRING"
queue_name = "QUEUE_NAME"
csp = "COLL_CSP"

if csp == "aws":
    queue = boto3.client("sqs")
elif csp == "azure":
    queue = QueueClient.from_connection_string(
        conn_str=connect_str, queue_name=queue_name
    )


def user_function(serwoObject) -> SerWOObject:
    try:
        fin_dict = dict()
        data = serwoObject.get_body()
        logging.info("Data to push - "+str(data))
        metadata = serwoObject.get_metadata()
        fin_dict["data"] = data
        fin_dict["metadata"] = metadata
        logging.info("Fin dict - "+str(fin_dict))
        if csp == "azure":
            queue.send_message(json.dumps(fin_dict))
        elif csp == "aws":
            queue.send_message(MessageBody=json.dumps(fin_dict), QueueUrl=connect_str)
        # data = {"body": "success: OK"}
        return SerWOObject(body=serwoObject.get_body())
    except Exception as e:
        return SerWOObject(error=True)
