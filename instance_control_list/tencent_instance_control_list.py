import pytz
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cvm.v20170312 import cvm_client, models
from datetime import datetime


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

                # tags_info = []
                # if instance.Tags:
                #     for tag in instance.Tags:
                #         tags_info.append(f"{tag.Key} : {tag.Value}")
                # TAGS = "\n".join(tags_info) if tags_info else "-"

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
                    # TAGS=TAGS,
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

def fetch_instances(credentials, project_name, AccountId, region_names, instance_objects, role_arn=None):
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

        instance_objects.extend(describe_instances(client, region, project_name, AccountId, pytz.timezone('Asia/Seoul')))


def main():
    print(f"{UNDERLINE}<TENCENT>{RESET}")

    tencent_cred_file_list_path = '../auth/cred_tencent.json'

    profile_manager = ProfileManager(tencent_cred_file_list_path)
    credentials = profile_manager.load_credentials()
    main_account = credentials["main_account"]
    projects = credentials["projects"][0]

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
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    fetch_instances(main_account, main_account['AccountName'], main_account['AccountId'], region_names, instance_objects)

    # projects
    for project_name, project_info in projects.items():
        print(f"{BLUE}{project_name}{RESET}")

        if project_name == "Chinaproject_1":
            credentials = {
                "secret_id": project_info['secret_id'],
                "secret_key": project_info['secret_key']
            }
            role_arn = None
        else:
            credentials = {
                "secret_id": main_account['secret_id'],
                "secret_key": main_account['secret_key']
            }
            role_arn = f"qcs::cam::uin/{project_info['AccountId']}:roleName/@owner"

        fetch_instances(credentials, project_name, project_info['AccountId'], region_names, instance_objects, role_arn=role_arn)

    instance_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME, x.INSTANCE_NAME))

    return instance_objects


if __name__ == "__main__":
    main()
