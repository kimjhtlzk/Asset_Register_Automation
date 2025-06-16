import boto3
import os
import re
import json


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class unUsedInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, RESOURCE_TYPE, RESOURCE, REGION, USE_O_X):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.RESOURCE_TYPE = RESOURCE_TYPE
        self.RESOURCE = RESOURCE
        self.REGION = REGION
        self.USE_O_X = USE_O_X

    def __repr__(self):
        return (f"unUsedInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"RESOURCE_TYPE={self.RESOURCE_TYPE}, "
                f"RESOURCE={self.RESOURCE}, "
                f"REGION={self.RESOURCE}, "
                f"USE_O_X={self.USE_O_X})")

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

def fetch_unused_eips(project_name, account_id, client):
    unused_eips = []
    response = client.describe_addresses()

    for address in response['Addresses']:
        # 연결된 인스턴스가 없는 경우만 처리
        if 'InstanceId' not in address and not address.get('AssociationId'):
            print(address)
            name = None
            if 'Tags' in address:
                for tag in address.get('Tags', []):
                    if tag['Key'].lower() == 'name':
                        name = tag['Value']
                        break
            if name:
                resource_name = f"{name} ({address.get('AllocationId')} / {address.get('PublicIp')})"
            else:
                resource_name = f"({address.get('AllocationId')} / {address.get('PublicIp')})"

            unused_eips.append(unUsedInfo(
                CLOUD="AWS",
                PROJECT=project_name,
                PROJECT_ID=account_id,
                RESOURCE_TYPE="IP",
                RESOURCE=resource_name,
                REGION=client.meta.region_name,
                USE_O_X=""
            ))

    return unused_eips

def fetch_unused_security_groups(project_name, account_id, client):
    unused_security_groups = []
    response = client.describe_security_groups()
    for sg in response['SecurityGroups']:
        # 기본 보안 그룹 제외 및 사용 여부 확인
        if (sg['GroupName'] == 'default' or sg['GroupName'] == 'outbound-80-deny'
                or sg['GroupName'].startswith("basic-") or sg['GroupName'].startswith("k8s-")):
            continue

        # 보안 그룹의 연결된 리소스 확인
        sg_usage_response = client.describe_network_interfaces(Filters=[
            {'Name': 'group-id', 'Values': [sg['GroupId']]}
        ])
        if len(sg_usage_response['NetworkInterfaces']) == 0:  # 연결된 리소스가 없는 경우
            resource_name = f"{sg['GroupName']} ({sg['GroupId']})"
            unused_security_groups.append(unUsedInfo(
                CLOUD="AWS",
                PROJECT=project_name,
                PROJECT_ID=account_id,
                RESOURCE_TYPE="SECURITY_GROUP",
                RESOURCE=resource_name,
                REGION=client.meta.region_name,
                USE_O_X=""
            ))
    return unused_security_groups

def fetch_unused_volumes(project_name, account_id, client):
    unused_volumes = []

    response = client.describe_volumes()
    for volume in response['Volumes']:
        if not volume['Attachments']:  # 연결된 리소스가 없는 경우
            name = None
            if 'Tags' in volume:
                for tag in volume.get('Tags', []):
                    if tag['Key'].lower() == 'name':
                        name = tag['Value']
                        break
            if name:
                resource_name = f"{name} ({volume.get('VolumeId')} / {volume.get('Size')}GiB / {volume.get('VolumeType')})"
            else:
                resource_name = f"({volume.get('VolumeId')} / {volume.get('Size')}GiB / {volume.get('VolumeType')})"

            unused_volumes.append(unUsedInfo(
                CLOUD="AWS",
                PROJECT=project_name,
                PROJECT_ID=account_id,
                RESOURCE_TYPE="DISK",
                RESOURCE=resource_name,
                REGION=client.meta.region_name,
                USE_O_X=""
            ))
    return unused_volumes


def main():
    print(f"{UNDERLINE}<AWS>{RESET}")

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

    unused_eip_objects = []

    for project_name in project_names:
        print(f"{ORANGE}{project_name}{RESET}")
        account_id = cred_manager.get_account_id(project_name)
        role_arn = cred_manager.get_role_arn(account_id)

        try:
            credentials = assume_role(role_arn, session_name=project_name)
        except Exception as e:
            print(f"{RED}AssumeRole failed for {project_name}: {e}{RESET}")
            continue

        for REGION in region_names:
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=REGION
            )
            client = session.client('ec2')

            account_client = session.client('sts')
            account_response = account_client.get_caller_identity()
            account_id = account_response["Account"]

            unused_eip_objects.extend(fetch_unused_eips(project_name, account_id, client))
            unused_eip_objects.extend(fetch_unused_security_groups(project_name, account_id, client))
            unused_eip_objects.extend(fetch_unused_volumes(project_name, account_id, client))

    unused_eip_objects.sort(key=lambda x: (x.PROJECT, x.RESOURCE_TYPE, x.RESOURCE))

    return unused_eip_objects


if __name__ == "__main__":
    main()
