import boto3
import os
import pytz
import re
import sys
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class InstanceInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, INSTANCE_NAME, INSTANCE_ID, REGION, AZ, MACHINE_TYPE, vCPUs, RAM, BOOT_DISK, DISKS, PRIVATE_IP, PUBLIC_IP, OS, STATE, HOSTNAME, CPU_PLATFORM, DELETION_PROTECTION, CREATION_TIME, VPC_NAME, SUBNET_NAME, ):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.INSTANCE_NAME = INSTANCE_NAME
        self.INSTANCE_ID = INSTANCE_ID
        self.REGION = REGION
        self.AZ = AZ
        self.MACHINE_TYPE = MACHINE_TYPE
        self.vCPUs = vCPUs
        self.RAM = RAM
        self.BOOT_DISK = BOOT_DISK
        self.DISKS = DISKS
        self.PRIVATE_IP = PRIVATE_IP
        self.PUBLIC_IP = PUBLIC_IP
        self.OS = OS
        self.STATE = STATE
        self.HOSTNAME = HOSTNAME
        # self.TAGS = TAGS
        self.CPU_PLATFORM = CPU_PLATFORM
        self.DELETION_PROTECTION = DELETION_PROTECTION
        self.CREATION_TIME = CREATION_TIME
        self.VPC_NAME = VPC_NAME
        self.SUBNET_NAME = SUBNET_NAME

    def __repr__(self):
        return (f"InstanceInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"INSTANCE_NAME={self.INSTANCE_NAME}, "
                f"INSTANCE_ID={self.INSTANCE_ID}, "
                f"REGION={self.REGION}, "
                f"AZ={self.AZ}, "
                f"MACHINE_TYPE={self.MACHINE_TYPE}, "
                f"vCPUs={self.vCPUs}, "
                f"RAM={self.RAM}, "        
                f"BOOT_DISK={self.BOOT_DISK}, "
                f"DISKS={self.DISKS}, "
                f"PRIVATE_IP={self.PRIVATE_IP}, "
                f"PUBLIC_IP={self.PUBLIC_IP}, "
                f"OS={self.OS}, "
                f"STATE={self.STATE}, "
                f"HOSTNAME={self.HOSTNAME}, "
                # f"TAGS={self.TAGS}, "
                f"CPU_PLATFORM={self.CPU_PLATFORM}), "
                f"DELETION_PROTECTION={self.DELETION_PROTECTION}, "
                f"CREATION_TIME={self.CREATION_TIME}, "
                f"VPC_NAME={self.VPC_NAME}, "
                f"SUBNET_NAME={self.SUBNET_NAME})")

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

def describe_instance_types(client):
    instance_types = []
    next_token = None

    while True:
        if next_token:
            response = client.describe_instance_types(NextToken=next_token)
        else:
            response = client.describe_instance_types()
        instance_types.extend(response['InstanceTypes'])
        next_token = response.get('NextToken')
        if not next_token:
            break
    return instance_types

def describe_instances(credentials, REGION, kst, instance_objects, project_name):
    session = boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=REGION
    )
    client = session.client('ec2')

    instances = client.describe_instances()

    instance_types = describe_instance_types(client)

    if len(instances['Reservations']) > 0:
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                INSTANCE_NAME = None
                vCPUs = None
                RAM = None
                boot_ebs_volume = None

                ebs_volumes = []
                for instance_type in instance_types:
                    if instance['InstanceType'] == instance_type['InstanceType']:
                        vCPUs = instance_type['VCpuInfo']['DefaultVCpus']
                        RAM = instance_type['MemoryInfo']['SizeInMiB'] // 1024

                        for block_device in instance['BlockDeviceMappings']:
                            if block_device['DeviceName'] != instance['RootDeviceName']:
                                volume_info = client.describe_volumes(VolumeIds=[block_device['Ebs']['VolumeId']])['Volumes'][0]
                                ebs_volumes.append(f"{volume_info['VolumeId']} : {volume_info['Size']}GB : {volume_info['VolumeType']}")
                            else:
                                boot_volume = client.describe_volumes(VolumeIds=[block_device['Ebs']['VolumeId']])['Volumes'][0]
                                boot_ebs_volume = f"{boot_volume['VolumeId']} : {boot_volume['Size']}GB : {boot_volume['VolumeType']}"

                ebs_volumes_str = "\n".join(ebs_volumes) if ebs_volumes else "-"

                PUBLIC_IP = instance.get('PublicIpAddress', '-')

                STATE = instance['State']['Name'].upper()
                # tags_list = []
                for tag in instance['Tags']:
                    key = tag['Key']
                    value = tag['Value']
                    # tags_list.append(f"{key} : {value}")
                    if key == 'Name' or key == 'NAME':
                        INSTANCE_NAME = value
                # tags_string = "\n".join(tags_list)

                describe_dp_option = client.describe_instance_attribute(InstanceId=instance['InstanceId'], Attribute='disableApiTermination')
                dp_option = describe_dp_option['DisableApiTermination']['Value']

                created_time_utc = instance['LaunchTime']
                created_time_kst = created_time_utc.replace(tzinfo=pytz.UTC).astimezone(kst)
                CREATION_TIME = created_time_kst.strftime('%Y-%m-%d %H:%M:%S')

                instance_info = InstanceInfo(
                    CLOUD="AWS",
                    PROJECT=project_name,
                    PROJECT_ID=instance['NetworkInterfaces'][0]['OwnerId'],
                    INSTANCE_NAME=INSTANCE_NAME,
                    INSTANCE_ID=instance['InstanceId'],
                    REGION=REGION,
                    AZ=instance['Placement']['AvailabilityZone'],
                    MACHINE_TYPE=instance['InstanceType'],
                    vCPUs=vCPUs,
                    RAM=RAM,
                    BOOT_DISK=boot_ebs_volume,
                    DISKS=ebs_volumes_str,
                    PRIVATE_IP=instance['PrivateIpAddress'],
                    PUBLIC_IP=PUBLIC_IP,
                    OS=instance['PlatformDetails'],
                    STATE=STATE,
                    HOSTNAME="-",
                    # TAGS=tags_string,
                    CPU_PLATFORM="-",
                    DELETION_PROTECTION=dp_option,
                    CREATION_TIME=CREATION_TIME,
                    VPC_NAME=instance['VpcId'],
                    SUBNET_NAME=instance['SubnetId']
                )

                instance_objects.append(instance_info)

def delete_existing_project_rows(worksheet, instance_objects):
    project_ids_to_delete = {obj.PROJECT_ID for obj in instance_objects}

    all_data = worksheet.get_all_values()

    rows_to_delete = []
    for idx, row in enumerate(all_data[1:], start=2):
        if len(row) >= 3 and row[2] in project_ids_to_delete:
            rows_to_delete.append(idx)

    requests = []
    for row_idx in reversed(rows_to_delete):
        requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "ROWS",
                    "startIndex": row_idx - 1,
                    "endIndex": row_idx
                }
            }
        })

    if requests:
        body = {"requests": requests}
        worksheet.spreadsheet.batch_update(body)

def upload_new_instances(worksheet, instance_objects):
    if not instance_objects:
        return

    new_rows = [
        [
            instance.CLOUD,
            instance.PROJECT,
            instance.PROJECT_ID,
            instance.INSTANCE_NAME,
            instance.INSTANCE_ID,
            instance.REGION,
            instance.AZ,
            instance.MACHINE_TYPE,
            instance.vCPUs,
            instance.RAM,
            instance.BOOT_DISK,
            instance.DISKS,
            instance.PRIVATE_IP,
            instance.PUBLIC_IP,
            instance.OS,
            instance.STATE,
            instance.HOSTNAME,
            instance.CPU_PLATFORM,
            instance.DELETION_PROTECTION,
            instance.CREATION_TIME,
            instance.VPC_NAME,
            instance.SUBNET_NAME,
        ]
        for instance in instance_objects
    ]

    worksheet.append_rows(new_rows, table_range="A2")

def sync_instances_to_sheet(instance_objects):
    key_file_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/gcp.json'
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file_path, scopes=scope)
    client = gspread.authorize(credentials)
    service = build('sheets', 'v4', credentials=credentials)

    sheet_id = "1rQ3*******************"
    worksheet_name = "INSTANCE"
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    header = worksheet.row_values(1)

    delete_existing_project_rows(worksheet, instance_objects)

    upload_new_instances(worksheet, instance_objects)

    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_internal = worksheet.id

    # 정렬
    sort_request = {
        "sortRange": {
            "range": {
                "sheetId": sheet_id_internal,
                "startRowIndex": 1,  # 헤더 제외, 데이터만 정렬
                "endRowIndex": worksheet.row_count,
                "startColumnIndex": 0,
                "endColumnIndex": len(header)
            },
            "sortSpecs": [{
                "dimensionIndex": 1,  # B열 (PROJECT)
                "sortOrder": "ASCENDING"
            }]
        }
    }

    # 필터
    filter_request = {
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id_internal,
                    "startRowIndex": 0,
                    "endRowIndex": worksheet.row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(header)
                }
            }
        }
    }

    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': [sort_request, filter_request]}
    ).execute()


def main():
    print(f"{UNDERLINE}<AWS>{RESET}")

    kst = pytz.timezone('Asia/Seoul')

    cred_json_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_aws.json'
    cred_manager = CredentialManager(cred_json_path)
    project_names = cred_manager.get_projects()
    project_names.sort()

    print(f"\n{GREEN}Available Projects:{RESET}\n")
    for idx, project in enumerate(project_names, start=1):
        print(f"{ORANGE}{idx}.{RESET} {project}")

    selected_projects = None
    while True:
        input_str = input(f"\n{GREEN}Enter project numbers separated by {BLUE}{UNDERLINE}'SPACE'{RESET}{GREEN} (ex, 1 2) (0 to exit):{RESET} ")
        if input_str == "0":
            sys.exit(0)

        try:
            selected_project_indices = [int(num) - 1 for num in input_str.split()]
            if any(idx < 0 or idx >= len(project_names) for idx in selected_project_indices):
                print(f"{RED}Invalid project number.{RESET}")
                continue
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")
            continue

        selected_projects = [project_names[idx] for idx in selected_project_indices]
        break

    region_names = [
        "us-east-1", "us-east-2",
        "us-west-1", "us-west-2",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ap-southeast-1", "ap-southeast-2",
        "eu-central-1",
        "eu-west-1", "eu-west-2", "eu-west-3",
    ]

    instance_objects = []

    for project_name in selected_projects:
        print(f"\n{YELLOW}ListUp Processing Project: {project_name}{RESET}")
        account_id = cred_manager.get_account_id(project_name)
        role_arn = cred_manager.get_role_arn(account_id)
        try:
            credentials = assume_role(role_arn, session_name=project_name)
        except Exception as e:
            print(f"{RED}AssumeRole failed for {project_name}: {e}{RESET}")
            continue

        for REGION in region_names:
            describe_instances(credentials, REGION, kst, instance_objects, project_name)

    instance_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME, x.INSTANCE_NAME))

    print(f"\n{GREEN}Sheet Synchronizing...{RESET}")
    sync_instances_to_sheet(instance_objects)
    print(f"{GREEN}Sheet Synchronized!{RESET}\n")


if __name__ == "__main__":
    main()
