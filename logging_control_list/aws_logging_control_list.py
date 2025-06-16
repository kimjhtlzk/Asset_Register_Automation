import boto3
import os
import pytz
import re
import json
from datetime import timezone, datetime, timedelta

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class LoggingFirewallInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, SECURITY_GROUP, DIRECTION, RULE_TYPE, PRIORITY,
                 PROTOCOL, PORTS, SOURCE, DESTINATION, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.SECURITY_GROUP = SECURITY_GROUP
        self.DIRECTION = DIRECTION
        self.RULE_TYPE = RULE_TYPE
        self.PRIORITY = PRIORITY
        self.PROTOCOL = PROTOCOL
        self.PORTS = PORTS
        self.SOURCE = SOURCE
        self.DESTINATION = DESTINATION
        self.ACTION_TIME = ACTION_TIME

class LoggingAccountInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, ACCOUNT, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.ACCOUNT = ACCOUNT
        self.ACTION_TIME = ACTION_TIME

class LoggingIamInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, PERMISSION, ACCOUNT, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.PERMISSION = PERMISSION
        self.ACCOUNT = ACCOUNT
        self.ACTION_TIME = ACTION_TIME

class LoggingKeyInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, ACCOUNT, ACCESS_KEY, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.ACCOUNT = ACCOUNT
        self.ACCESS_KEY = ACCESS_KEY
        self.ACTION_TIME = ACTION_TIME

class LoggingInstanceInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, REGION, AZ, INSTANCE_TYPE, INSTANCE, NETWORK,
                 ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.REGION = REGION
        self.AZ = AZ
        self.INSTANCE_TYPE = INSTANCE_TYPE
        self.INSTANCE = INSTANCE
        self.NETWORK = NETWORK
        self.ACTION_TIME = ACTION_TIME

class CredentialManager:
    def __init__(self, cred_json_path):
        self.cred_json_path = cred_json_path
        with open(cred_json_path, 'r') as f:
            self.cred_data = json.load(f)

    def get_projects(self):
        return list(self.cred_data.keys())

    def get_account_id(self, project_name):
        return self.cred_data[project_name]['AccountId']

    def get_role_arn(self, account_id):
        return f"arn:aws:iam::{account_id}:role/@owner"

def assume_role(role_arn, session_name="AssumeRoleSession"):
    sts_client = boto3.client('sts')
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    credentials = response['Credentials']
    return credentials

def calculate_previous_month_dates():
    current_date = datetime.now()
    first_day_previous_month = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_previous_month = current_date.replace(day=1) - timedelta(days=1)
    return first_day_previous_month.strftime('%Y-%m-%dT00:00:00Z'), last_day_previous_month.strftime(
        '%Y-%m-%dT23:59:59Z')

def get_worker_from_identity(user_identity):
    arn = user_identity['arn']
    if 'aws-go-sdk' in arn:
        arn_last_part = 'terraform'
    else:
        arn_last_part = arn.split('/')[-1]

    if user_identity['type'] == 'IAMUser':
        return arn_last_part
    elif user_identity['type'] == 'AssumedRole':
        session_context = user_identity.get('sessionContext', {})
        session_issuer = session_context.get('sessionIssuer', {})
        return f"{arn_last_part}({session_issuer.get('userName', '')})"
    return None

def get_cloudtrail_events(session, region, start_time, end_time, event_filter=None):
    client = session.client('cloudtrail', region_name=region)

    lookup_attributes = [
        {
            'AttributeKey': 'ReadOnly',
            'AttributeValue': 'false'
        }
    ]

    if event_filter:
        lookup_attributes.append(event_filter)

    response = client.lookup_events(
        StartTime=start_time,
        EndTime=end_time,
        LookupAttributes=lookup_attributes,
        MaxResults=50
    )

    all_logs = response['Events']

    while 'NextToken' in response:
        response = client.lookup_events(
            StartTime=start_time,
            EndTime=end_time,
            LookupAttributes=lookup_attributes,
            NextToken=response['NextToken'],
            MaxResults=50
        )
        all_logs.extend(response['Events'])

    return all_logs

def process_account_events(events, project_name, log_objects):
    target_events = ['CreateUser', 'DeleteUser']

    for event in events:
        if event['EventName'] not in target_events:
            continue

        cloud_trail_event = json.loads(event['CloudTrailEvent'])
        if 'errorCode' in cloud_trail_event:
            continue

        action_time = event['EventTime'].strftime('%Y-%m-%d %H:%M:%S')
        user_identity = cloud_trail_event['userIdentity']
        worker = get_worker_from_identity(user_identity)

        log_objects.append(LoggingAccountInfo(
            CLOUD='AWS',
            PROJECT=project_name,
            PROJECT_ID=cloud_trail_event['recipientAccountId'],
            WORKER=worker,
            ACTION=event['EventName'],
            ACCOUNT=cloud_trail_event['requestParameters']['userName'],
            ACTION_TIME=action_time
        ))

def process_iam_permission_events(events, project_name, log_objects):
    target_events = ['AttachUserPolicy', 'DetachUserPolicy']

    for event in events:
        if event['EventName'] not in target_events:
            continue

        cloud_trail_event = json.loads(event['CloudTrailEvent'])
        if 'errorCode' in cloud_trail_event:
            continue

        action_time = event['EventTime'].strftime('%Y-%m-%d %H:%M:%S')
        user_identity = cloud_trail_event['userIdentity']
        worker = get_worker_from_identity(user_identity)

        log_objects.append(LoggingIamInfo(
            CLOUD='AWS',
            PROJECT=project_name,
            PROJECT_ID=cloud_trail_event['recipientAccountId'],
            WORKER=worker,
            ACTION=event['EventName'],
            PERMISSION=cloud_trail_event['requestParameters']['policyArn'].split('/')[-1],
            ACCOUNT=cloud_trail_event['requestParameters']['userName'],
            ACTION_TIME=action_time
        ))

def process_access_key_events(events, project_name, log_objects):
    target_events = ['CreateAccessKey', 'DeleteAccessKey']

    for event in events:
        if event['EventName'] not in target_events:
            continue

        cloud_trail_event = json.loads(event['CloudTrailEvent'])
        if 'errorCode' in cloud_trail_event:
            continue

        action_time = event['EventTime'].strftime('%Y-%m-%d %H:%M:%S')
        user_identity = cloud_trail_event['userIdentity']
        worker = get_worker_from_identity(user_identity)

        if event['EventName'] == 'CreateAccessKey':
            access_key = cloud_trail_event.get('responseElements', {}).get('accessKey', {}).get('accessKeyId', '-')
        else:
            access_key = '-'

        log_objects.append(LoggingKeyInfo(
            CLOUD='AWS',
            PROJECT=project_name,
            PROJECT_ID=cloud_trail_event['recipientAccountId'],
            WORKER=worker,
            ACTION=event['EventName'],
            ACCOUNT=cloud_trail_event['requestParameters']['userName'],
            ACCESS_KEY=access_key,
            ACTION_TIME=action_time
        ))

def process_security_group_events(events, project_name, log_objects):
    target_events = [
        'AuthorizeSecurityGroupIngress', 'AuthorizeSecurityGroupEgress',
        'RevokeSecurityGroupIngress', 'RevokeSecurityGroupEgress'
    ]

    for event in events:
        if event['EventName'] not in target_events:
            continue

        cloud_trail_event = json.loads(event['CloudTrailEvent'])
        if 'errorCode' in cloud_trail_event:
            continue

        action_time = event['EventTime'].strftime('%Y-%m-%d %H:%M:%S')
        user_identity = cloud_trail_event['userIdentity']
        worker = get_worker_from_identity(user_identity)

        sg_resource = next((r for r in event['Resources'] if r['ResourceType'] == 'AWS::EC2::SecurityGroup'), None)
        group_id = sg_resource['ResourceName'] if sg_resource else 'N/A'

        rule_set_key = 'securityGroupRuleSet' if event['EventName'].startswith(
            'Authorize') else 'revokedSecurityGroupRuleSet'
        response_elements = cloud_trail_event.get('responseElements') or {}
        rule_set = response_elements.get(rule_set_key) or {}
        rule_items = rule_set.get('items', [])

        for rule in rule_items:
            description = rule.get('description', '')
            rule_id = rule.get('securityGroupRuleId', '')
            sg_info = f"sg : {group_id} / rule : {description} ({rule_id})"

            from_port = str(rule.get('fromPort', ''))
            to_port = str(rule.get('toPort', ''))
            ports = f"{from_port}~{to_port}" if from_port != to_port else from_port

            direction = 'Ingress' if 'Ingress' in event['EventName'] else 'Egress'
            source = rule.get('cidrIpv4', '-') if direction == 'Ingress' else '-'
            destination = rule.get('cidrIpv4', '-') if direction == 'Egress' else '-'

            log_objects.append(LoggingFirewallInfo(
                CLOUD='AWS',
                PROJECT=project_name,
                PROJECT_ID=cloud_trail_event['recipientAccountId'],
                WORKER=worker,
                ACTION=event['EventName'],
                SECURITY_GROUP=sg_info,
                DIRECTION=direction,
                RULE_TYPE='ACCEPT',
                PRIORITY='-',
                PROTOCOL=rule.get('ipProtocol', 'N/A'),
                PORTS=ports if from_port and to_port else 'N/A',
                SOURCE=source,
                DESTINATION=destination,
                ACTION_TIME=action_time
            ))

def process_instance_events(events, project_name, log_objects):
    target_events = [
        'RunInstances', 'TerminateInstances', 'ModifyInstanceAttribute',
        'ModifyVolume', 'AttachVolume', 'DetachVolume',
        'StartInstances', 'StopInstances'
    ]

    for event in events:
        if event['EventName'] not in target_events:
            continue

        cloud_trail_event = json.loads(event['CloudTrailEvent']) if isinstance(event['CloudTrailEvent'], str) else event['CloudTrailEvent']
        if 'sharedEventID' in cloud_trail_event or 'errorCode' in cloud_trail_event:
            continue

        action_time = event['EventTime'].strftime('%Y-%m-%d %H:%M:%S')
        user_identity = cloud_trail_event.get('userIdentity', {})
        worker = get_worker_from_identity(user_identity)
        if worker.startswith("eks-") or "AutoScaling" in worker or worker.startswith("databricks"):
            continue

        region = cloud_trail_event.get('awsRegion', 'Unknown')
        response_elements = cloud_trail_event.get('responseElements', {})

        if event['EventName'] == 'RunInstances':
            instances = response_elements.get('instancesSet', {}).get('items', [])
            for instance in instances:
                instance_name = instance.get('instanceId', 'Unknown')
                tag_set = instance.get('tagSet', '')

                if tag_set == "HIDDEN_DUE_TO_SECURITY_REASONS" and worker == None:
                    instance_name = f"{tag_set} ({instance.get('instanceId', '')})"
                    worker = "HIDDEN_DUE_TO_SECURITY_REASONS"
                else:
                    if isinstance(tag_set, dict):
                        tags = tag_set.get('items', [])
                        for tag in tags:
                            if tag.get('key', '').lower() == 'name':
                                instance_name = tag.get('value', instance_name)
                                break

                log_objects.append(LoggingInstanceInfo(
                    CLOUD='AWS',
                    PROJECT=project_name,
                    PROJECT_ID=cloud_trail_event.get('recipientAccountId', ''),
                    WORKER=worker,
                    ACTION=event['EventName'],
                    REGION=region,
                    AZ=instance.get('placement', {}).get('availabilityZone', '-'),
                    INSTANCE_TYPE=instance.get('instanceType', '-'),
                    INSTANCE=instance_name,
                    NETWORK=f"{instance.get('vpcId', '')} / {instance.get('subnetId', '')}",
                    ACTION_TIME=action_time
                ))

        elif event['EventName'] == 'TerminateInstances':
            instances = response_elements.get('instancesSet', {}).get('items', [])
            for instance in instances:
                log_objects.append(LoggingInstanceInfo(
                    CLOUD='AWS',
                    PROJECT=project_name,
                    PROJECT_ID=cloud_trail_event.get('recipientAccountId', ''),
                    WORKER=worker,
                    ACTION=event['EventName'],
                    REGION=region,
                    AZ='-',
                    INSTANCE_TYPE='-',
                    INSTANCE=instance.get('instanceId', 'Unknown'),
                    NETWORK='-',
                    ACTION_TIME=action_time
                ))

        elif event['EventName'] == 'ModifyVolume':
            volume_mod = response_elements.get('ModifyVolumeResponse', {}).get('volumeModification', {})
            changes = []

            for field in ['Throughput', 'Iops', 'Size', 'VolumeType']:
                orig = volume_mod.get(f'original{field}', '')
                target = volume_mod.get(f'target{field}', '')
                if orig != target and orig and target:
                    changes.append(f"{field}: {orig} → {target}")

            log_objects.append(LoggingInstanceInfo(
                CLOUD='AWS',
                PROJECT=project_name,
                PROJECT_ID=cloud_trail_event.get('recipientAccountId', ''),
                WORKER=worker,
                ACTION=event['EventName'],
                REGION=region,
                AZ='-',
                INSTANCE_TYPE='\n'.join(changes) if changes else '-',
                INSTANCE=volume_mod.get('volumeId', 'Unknown'),
                NETWORK='-',
                ACTION_TIME=action_time
            ))

        elif event['EventName'] in ['AttachVolume', 'DetachVolume']:
            log_objects.append(LoggingInstanceInfo(
                CLOUD='AWS',
                PROJECT=project_name,
                PROJECT_ID=cloud_trail_event.get('recipientAccountId', ''),
                WORKER=worker,
                ACTION=event['EventName'],
                REGION=region,
                AZ='-',
                INSTANCE_TYPE=response_elements.get('device', '-'),
                INSTANCE=response_elements.get('instanceId', 'Unknown'),
                NETWORK='-',
                ACTION_TIME=action_time
            ))

        elif event['EventName'] in ['StartInstances', 'StopInstances']:
            instances = response_elements.get('instancesSet', {}).get('items', [])
            for instance in instances:
                log_objects.append(LoggingInstanceInfo(
                    CLOUD='AWS',
                    PROJECT=project_name,
                    PROJECT_ID=cloud_trail_event.get('recipientAccountId', ''),
                    WORKER=worker,
                    ACTION=event['EventName'],
                    REGION=region,
                    AZ='-',
                    INSTANCE_TYPE='-',
                    INSTANCE=instance.get('instanceId', 'Unknown'),
                    NETWORK='-',
                    ACTION_TIME=action_time
                ))

def get_all_region_logs(project_name, region_names, start_time, end_time):
    session = boto3.Session(profile_name=project_name)
    all_logs = []

    for region in region_names:
        logs = get_cloudtrail_events(session, region, start_time, end_time)
        all_logs.extend(logs)

    return all_logs


def main():
    print(f"{UNDERLINE}<AWS>{RESET}")

    kst = pytz.timezone('Asia/Seoul')

    cred_json_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_aws.json'
    cred_manager = CredentialManager(cred_json_path)
    project_names = cred_manager.get_projects()

    region_names = [
        "us-east-1", "us-east-2",
        "us-west-1", "us-west-2",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ap-southeast-1", "ap-southeast-2",
        "eu-central-1",
        "eu-west-1", "eu-west-2", "eu-west-3",
    ]

    start_time, end_time = calculate_previous_month_dates()
    # start_time = "2025-02-01T00:00:00Z"
    # end_time = "2025-02-28T23:59:59Z"

    loggingaccount_objects = []
    loggingiam_objects = []
    loggingkey_objects = []
    loggingfirewall_objects = []
    logginginstance_objects = []

    for project_name in project_names:
        print(f"{ORANGE}{project_name}{RESET}")
        account_id = cred_manager.get_account_id(project_name)
        role_arn = cred_manager.get_role_arn(account_id)

        try:
            credentials = assume_role(role_arn, session_name=project_name)
        except Exception as e:
            print(f"{RED}AssumeRole failed for {project_name}: {e}{RESET}")
            continue

        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        iam_region_events = get_cloudtrail_events(session, 'us-east-1', start_time, end_time)

        process_account_events(iam_region_events, project_name, loggingaccount_objects)
        process_iam_permission_events(iam_region_events, project_name, loggingiam_objects)
        process_access_key_events(iam_region_events, project_name, loggingkey_objects)

        for region in region_names:
            region_events = get_cloudtrail_events(session, region, start_time, end_time)
            process_security_group_events(region_events, project_name, loggingfirewall_objects)
            process_instance_events(region_events, project_name, logginginstance_objects)

    loggingfirewall_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingaccount_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingiam_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingkey_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    logginginstance_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))

    return loggingfirewall_objects, loggingaccount_objects, loggingiam_objects, loggingkey_objects, logginginstance_objects

if __name__ == "__main__":
    main()
