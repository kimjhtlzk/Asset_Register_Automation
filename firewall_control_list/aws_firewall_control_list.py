import boto3
import os
import pytz
import re
import json


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class FirewallInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, SECURITY_GROUP, SECURITY_GROUP_ID, DIRECTION, ACTION, SOURCE, DESTINATION, PROTOCOL, PORTS, PRIORITY, TAGS, VPC, CREATION_TIME ):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.SECURITY_GROUP = SECURITY_GROUP
        self.SECURITY_GROUP_ID = SECURITY_GROUP_ID
        self.DIRECTION = DIRECTION
        self.ACTION = ACTION
        self.SOURCE = SOURCE
        self.DESTINATION = DESTINATION
        self.PROTOCOL = PROTOCOL
        self.PORTS = PORTS
        self.PRIORITY = PRIORITY
        self.TAGS = TAGS
        self.VPC = VPC
        # self.TARGET = TARGET
        self.CREATION_TIME = CREATION_TIME


    def __repr__(self):
        return (f"FirewallInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"SECURITY_GROUP={self.SECURITY_GROUP}, "
                f"SECURITY_GROUP_ID={self.SECURITY_GROUP_ID}, "
                f"DIRECTION={self.DIRECTION}, "
                f"ACTION={self.ACTION}, "
                f"SOURCE={self.SOURCE}, "        
                f"DESTINATION={self.DESTINATION}, "
                f"PROTOCOL={self.PROTOCOL}, "
                f"PORTS={self.PORTS}, "
                f"PRIORITY={self.PRIORITY}, "
                f"TAGS={self.TAGS}, "        
                f"VPC={self.VPC}, "
                # f"TARGET={self.TARGET}, "
                f"CREATION_TIME={self.CREATION_TIME})")

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

def process_permissions(security_group, direction, project_name, owner_id, group_name, group_id, vpc_id, firewalls_objects):
    if direction == "Egress":
        permissions = security_group.get('IpPermissionsEgress', [])
    else:
        permissions = security_group.get('IpPermissions', [])

    if not permissions:
        return [{'IpProtocol': '-', 'FromPort': '-', 'ToPort': '-', 'IpRanges': '-'}]

    for permission in permissions:
        entry = {
            'IpProtocol': permission.get('IpProtocol', '-'),
            'FromPort': permission.get('FromPort', '-'),
            'ToPort': permission.get('ToPort', '-'),
            'IpRanges': []
        }
        for ip_range in permission.get('IpRanges', []):
            entry['IpRanges'].append({
                'Description': ip_range.get('Description', '-'),
                'CidrIp': ip_range.get('CidrIp', '-')
            })

        source = '\n'.join([ip['CidrIp'] for ip in permission.get('IpRanges', [{'CidrIp': '-'}])])
        destination = "-" if direction == "Ingress" else '\n'.join(
            [ip['CidrIp'] for ip in permission.get('IpRanges', [{'CidrIp': '-'}])])

        firewall_info = FirewallInfo(
            CLOUD="AWS",
            PROJECT=project_name,
            PROJECT_ID=owner_id,
            SECURITY_GROUP=group_name,
            SECURITY_GROUP_ID=group_id,
            DIRECTION=direction,
            ACTION="ACCEPT",
            SOURCE=source if direction == "Ingress" else "-",
            DESTINATION=destination if direction == "Egress" else "-",
            PROTOCOL=entry['IpProtocol'],
            PORTS=f"{entry['FromPort']}-{entry['ToPort']}" if entry['FromPort'] != '-' else "-",
            PRIORITY="-",
            TAGS="-",
            VPC=vpc_id,
            CREATION_TIME="-"
        )
        firewalls_objects.append(firewall_info)


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

    firewalls_objects = []

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

            response = client.describe_security_groups()

            for security_group in response['SecurityGroups']:

                group_name = security_group['GroupName']
                if group_name == "default":
                    continue

                group_id = security_group['GroupId']
                vpc_id = security_group['VpcId']
                owner_id = security_group['OwnerId']

                # Egress
                process_permissions(security_group, "Egress", project_name, owner_id, group_name, group_id, vpc_id, firewalls_objects)

                # Ingress
                process_permissions(security_group, "Ingress", project_name, owner_id, group_name, group_id, vpc_id, firewalls_objects)

    firewalls_objects.sort(key=lambda x: (x.PROJECT, x.VPC, x.SECURITY_GROUP, x.DIRECTION, x.ACTION))

    return firewalls_objects


if __name__ == "__main__":
    main()
