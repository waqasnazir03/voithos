#!/usr/bin/env python3
import sys
import subprocess
import json
import boto3
from botocore.exceptions import ClientError

charset = "UTF-8"
aws_region = "ca-central-1"
configuration_set = "health_mon"

def _get_destination(recipient_emails):
    output={"ToAddresses": [recipient_emails]}
    return output

def _get_message(body_text, subject_text):
    output={"Body": {"Html": {"Charset": charset,"Data": body_text},"Text": {"Charset": charset,"Data": body_text}},"Subject": {"Charset": charset,"Data": subject_text}}
    return output

def email_alert(sender_address, recipient_address, subject, body):
    """Trigger email alert to AES"""
    # This address must be verified with Amazon SES.
    client = boto3.client("ses", region_name=aws_region)

    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination = _get_destination(recipient_address),
            Message = _get_message(body, subject),
            Source = sender_address,
            # Optional
            ConfigurationSetName = configuration_set,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response["Error"]["Message"])
    else:
        print("Email sent! Message ID:"),
        print(response["MessageId"])
