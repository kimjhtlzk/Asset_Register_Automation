import pytz
import json
import sys
import gspread
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cvm.v20170312 import cvm_client, models
from datetime import datetime
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
                f"CPU_PLATFORM={self.CPU_PLATFORM}), "
                f"DELETION_PROTECTION={self.DELETION_PROTECTION}, "
                f"CREATION_TIME={self.CREATION_TIME}, "
                f"VPC_NAME={self.VPC_NAME}, "
                f"SUBNET_NAME={self.SUBNET_NAME})")

class ProfileManager:
    def __init__(self, cred_file_path):
        self.cred_file_path = cred_file_path

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def describe_instances(client, REGION, project_name, AccountId, kst, limit=100):
    instance_objects = []
    page = 1

    while True:
        req = models.DescribeInstancesRequest()
        params = {
            "Region": REGION,
            "Limit": limit,
            "Offset": (page - 1) * limit
        }
        req.from_json_string(json.dumps(params))

        resp = client.DescribeInstances(req)

        if resp.TotalCount > 0:
            for instance in resp.InstanceSet:
                BOOT_DISK = f"{instance.SystemDisk.DiskId} : {instance.SystemDisk.DiskSize}GB : {instance.SystemDisk.DiskType}"

                disk_info_list = []
                for disk in instance.DataDisks:
                    disk_info_list.append(f"{disk.DiskId} : {disk.DiskSize}GB : {disk.DiskType}")
                disk_info = "\n".join(disk_info_list)

                created_time_utc = datetime.strptime(instance.CreatedTime, '%Y-%m-%dT%H:%M:%SZ')
                created_time_kst = created_time_utc.replace(tzinfo=pytz.utc).astimezone(kst)
                CREATION_TIME = created_time_kst.strftime('%Y-%m-%d %H:%M:%S')

                PUBLIC_IP = instance.PublicIpAddresses if instance.PublicIpAddresses else "-"
                STATE = instance.InstanceState.upper()

                instance_info = InstanceInfo(
                    CLOUD="TENCENT",
                    PROJECT=project_name,
                    PROJECT_ID=AccountId,
                    INSTANCE_NAME=instance.InstanceName,
                    INSTANCE_ID=instance.InstanceId,
                    REGION=REGION,
                    AZ=instance.Placement.Zone,
                    MACHINE_TYPE=instance.InstanceType,
                    vCPUs=instance.CPU,
                    RAM=instance.Memory,
                    BOOT_DISK=BOOT_DISK,
                    DISKS=disk_info,
                    PRIVATE_IP=instance.PrivateIpAddresses,
                    PUBLIC_IP=PUBLIC_IP,
                    OS=instance.OsName,
                    STATE=STATE,
                    HOSTNAME="-",
                    CPU_PLATFORM="-",
                    DELETION_PROTECTION=instance.DisableApiTermination,
                    CREATION_TIME=CREATION_TIME,
                    VPC_NAME=instance.VirtualPrivateCloud.VpcId,
                    SUBNET_NAME=instance.VirtualPrivateCloud.SubnetId
                )

                instance_objects.append(instance_info)

        if len(resp.InstanceSet) < limit:
            break

        page += 1

    return instance_objects

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
            "\n".join(instance.PRIVATE_IP) if isinstance(instance.PRIVATE_IP, list) else instance.PRIVATE_IP,
            "\n".join(instance.PUBLIC_IP) if isinstance(instance.PUBLIC_IP, list) else instance.PUBLIC_IP,
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

    sheet_id = "1rQ3n3ceYCC-9RR0yFX6NTRapOle75SzTZXB6p9AtNu0"
    worksheet_name = "INSTANCE"
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    header = worksheet.row_values(1)

    delete_existing_project_rows(worksheet, instance_objects)
    upload_new_instances(worksheet, instance_objects)

    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_id_internal = worksheet.id

    sort_request = {
        "sortRange": {
            "range": {
                "sheetId": sheet_id_internal,
                "startRowIndex": 1,
                "endRowIndex": worksheet.row_count,
                "startColumnIndex": 0,
                "endColumnIndex": len(header)
            },
            "sortSpecs": [{
                "dimensionIndex": 1,
                "sortOrder": "ASCENDING"
            }]
        }
    }
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

def fetch_instances(credentials, project_name, AccountId, region_names, instance_objects, role_arn=None):
    kst = pytz.timezone('Asia/Seoul')
    for region in region_names:
        if role_arn:
            cred = credential.STSAssumeRoleCredential(
                credentials['secret_id'],
                credentials['secret_key'],
                role_arn,
                "sts-session",
                7200
            )
        else:
            cred = credential.Credential(
                credentials['secret_id'],
                credentials['secret_key']
            )
        httpProfile = HttpProfile()
        httpProfile.endpoint = f"cvm.{region}.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = cvm_client.CvmClient(cred, region, clientProfile)
        instance_objects.extend(describe_instances(client, region, project_name, AccountId, kst))

def main():
    print(f"{UNDERLINE}<TENCENT>{RESET}")

    kst = pytz.timezone('Asia/Seoul')
    tencent_cred_file_list_path = '../auth/cred_tencent.json'
    profile_manager = ProfileManager(tencent_cred_file_list_path)
    credentials = profile_manager.load_credentials()
    main_account = credentials["main_account"]
    projects = credentials["projects"][0]

    project_names = [main_account['AccountName']] + list(projects.keys())
    project_names.sort(key=lambda x: x[3:] if x.startswith("tc-") else x)

    print(f"\n{GREEN}Available Projects:{RESET}\n")
    for idx, project in enumerate(project_names, start=1):
        display_name = project[3:] if project.startswith("tc-") else project
        print(f"{YELLOW}{idx}.{RESET} {display_name}")

    while True:
        input_str = input(f"\n{GREEN}Enter project numbers separated by {ORANGE}{UNDERLINE}'SPACE'{RESET}{GREEN} (ex, 1 2) (0 to exit):{RESET} ")
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
        "ap-guangzhou", "ap-shanghai",
        "ap-nanjing", "ap-beijing",
        "ap-chengdu", "ap-chongqing",
        "ap-hongkong",
        "ap-singapore", "ap-jakarta",
        "ap-seoul", "ap-tokyo",
        "ap-bangkok", "sa-saopaulo",
        "na-siliconvalley", "na-ashburn",
        "eu-frankfurt",
    ]

    instance_objects = []

    # main_account
    if main_account['AccountName'] in selected_projects:
        print(f"\n{YELLOW}{main_account['AccountName']}{RESET}")
        fetch_instances(main_account, main_account['AccountName'], main_account['AccountId'], region_names, instance_objects)

    # projects
    for project_name in selected_projects:
        if project_name == main_account['AccountName']:
            continue
        print(f"\n{YELLOW}{project_name}{RESET}")
        project_info = projects[project_name]
        if project_name == "Chinaproject_1":
            credentials_proj = {
                "secret_id": project_info['secret_id'],
                "secret_key": project_info['secret_key']
            }
            role_arn = None
        else:
            credentials_proj = {
                "secret_id": main_account['secret_id'],
                "secret_key": main_account['secret_key']
            }
            role_arn = f"qcs::cam::uin/{project_info['AccountId']}:roleName/@owner"

        fetch_instances(credentials_proj, project_name, project_info['AccountId'], region_names, instance_objects, role_arn=role_arn)

    instance_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME, x.INSTANCE_NAME))
    print(f"\n{GREEN}Sheet Synchronizing...{RESET}")
    sync_instances_to_sheet(instance_objects)
    print(f"{GREEN}Sheet Synchronized!{RESET}\n")

if __name__ == "__main__":
    main()
