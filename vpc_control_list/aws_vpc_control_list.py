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


class SubnetworkInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, VPC_NAME, VPC_CIDR, REGION, SUBNET_NAME, SUBNET_CIDR, AZ, SECONDARY_IP_CIDR):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.VPC_NAME = VPC_NAME
        self.VPC_CIDR = VPC_CIDR
        self.REGION = REGION
        self.SUBNET_NAME = SUBNET_NAME
        self.SUBNET_CIDR = SUBNET_CIDR
        self.AZ = AZ
        self.SECONDARY_IP_CIDR = SECONDARY_IP_CIDR

    def __repr__(self):
        return (f"SubnetworkInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"VPC_NAME={self.VPC_NAME}, "
                f"VPC_CIDR={self.VPC_CIDR}, "
                f"REGION={self.REGION}, "
                f"SUBNET_NAME={self.SUBNET_NAME}, "
                f"SUBNET_CIDR={self.SUBNET_CIDR}, "
                f"AZ={self.AZ}, "
                f"SECONDARY_IP_CIDR={self.SECONDARY_IP_CIDR})")

class NetworkInfo:
    def __init__(self, client):
        self.client = client

    def get_vpcs(self):
        vpc_response = self.client.describe_vpcs()
        vpc_data = []

        for vpc in vpc_response['Vpcs']:
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] in ['Name', 'NAME']:
                        vpc_info = {
                            'OwnerId': vpc['OwnerId'],
                            'VPC_NAME': tag['Value'],
                            'VPC_CIDR': vpc['CidrBlock'],
                            'VpcId': vpc['VpcId'],
                            'Subnets': self.get_subnets(vpc['VpcId'])
                        }
                        vpc_data.append(vpc_info)
        return vpc_data

    def get_subnets(self, vpc_id):
        subnet_response = self.client.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id],
                },
            ],
        )

        subnet_data = []
        for subnet in subnet_response['Subnets']:
            if 'Tags' in subnet:
                for tag in subnet['Tags']:
                    if tag['Key'] in ['Name', 'NAME']:
                        subnet_info = {
                            'SUBNET_NAME': tag['Value'],
                            'SUBNET_CIDR': subnet['CidrBlock'],
                            'AZ': subnet['AvailabilityZone']
                        }
                        subnet_data.append(subnet_info)
        return subnet_data

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

    subnetwork_objects = []

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

            networks = NetworkInfo(client)
            vpc_data = networks.get_vpcs()

            for vpc in vpc_data:
                for subnet in vpc['Subnets']:
                    subnetwork_info = SubnetworkInfo(
                        CLOUD="AWS",
                        PROJECT=project_name,
                        PROJECT_ID=vpc['OwnerId'],
                        VPC_NAME=vpc['VPC_NAME'],
                        VPC_CIDR=vpc['VPC_CIDR'],
                        REGION=REGION,
                        SUBNET_NAME=subnet['SUBNET_NAME'],
                        SUBNET_CIDR=subnet['SUBNET_CIDR'],
                        AZ=subnet['AZ'],
                        SECONDARY_IP_CIDR="-"
                    )
                    subnetwork_objects.append(subnetwork_info)

    subnetwork_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME))

    return subnetwork_objects

if __name__ == "__main__":
    main()
