# pip3 install pytz
# pip3 install google-cloud-resource-manager
from __future__ import annotations
import json
import os
import re
import pytz
from google.oauth2 import service_account
from google.cloud import compute_v1
from google.cloud import resourcemanager_v3
from collections import defaultdict
from datetime import datetime
from google.auth import impersonated_credentials


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

class DiskInfo:
    def __init__(self, project_name, AZ, credentials):
        self.project_name = project_name
        self.AZ = AZ
        self.disk_client = compute_v1.DisksClient(credentials=credentials)
        self.boot_disk = None
        self.non_boot_disks = []
        self.OS = None  # OS 정보를 저장할 변수 추가

    def fetch_disks_info(self, instance):
        self._get_boot_disk_info(instance)
        self._get_non_boot_disks_info(instance)

    def _get_boot_disk_info(self, instance):
        for disk in instance.disks:
            if disk.boot:
                BOOT_DISK_NAME = disk.source.split("/")[-1] if disk.source else None
                BOOT_DISK_SIZE = disk.disk_size_gb
                self.OS = disk.licenses[0].split("/")[-1] if disk.licenses else None  # OS 정보 저장
                if "cos" in self.OS:
                    self.OS = "container-optimized os"
                if BOOT_DISK_NAME:
                    boot_disk_request = compute_v1.GetDiskRequest(
                        disk=BOOT_DISK_NAME,
                        project=self.project_name,
                        zone=self.AZ,
                    )
                    boot_disk_info = self.disk_client.get(request=boot_disk_request)
                    BOOT_DISK_TYPE = boot_disk_info.type.split("/")[-1] if boot_disk_info.type else None
                    self.boot_disk = f"{BOOT_DISK_NAME} : {BOOT_DISK_SIZE}GB : {BOOT_DISK_TYPE}"
                break

    def _get_non_boot_disks_info(self, instance):
        for disk in instance.disks:
            if not disk.boot:
                disk_name = disk.source.split("/")[-1] if disk.source else None
                disk_size = disk.disk_size_gb

                disk_request = compute_v1.GetDiskRequest(
                    disk=disk_name,
                    project=self.project_name,
                    zone=self.AZ,
                )
                disk_info = self.disk_client.get(request=disk_request)
                disk_type = disk_info.type.split("/")[-1] if disk_info.type else None

                self.non_boot_disks.append(f"{disk_name} : {disk_size}GB : {disk_type}")

    def get_disks_summary(self):
        disks_string = "\n".join(self.non_boot_disks) if self.non_boot_disks else "-"
        return self.boot_disk, disks_string, self.OS  # OS 정보도 반환

class ProfileManager:
    def __init__(self, cred_file_path):
        self.cred_file_path = cred_file_path
        self.config = self.load_config()

    def load_config(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

    @property
    def service_account_name(self):
        return self.config.get("service_account")

    @property
    def service_account_key(self):
        return self.config.get("service_account_key")

    @property
    def projects(self):
        return self.config.get("projects", [])

def get_impersonated_credentials(source_credentials, target_service_account):
    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_service_account,
        target_scopes=['https://www.googleapis.com/auth/cloud-platform']
    )

def get_project_info(project_name, credentials):
    pj_client = resourcemanager_v3.ProjectsClient(credentials=credentials)
    pj_request = resourcemanager_v3.GetProjectRequest(
        name=f"projects/{project_name}",
    )
    response = pj_client.get_project(request=pj_request)
    return response

def get_aggregated_instances(project_name, credentials):
    instance_client = compute_v1.InstancesClient(credentials=credentials)
    request = compute_v1.AggregatedListInstancesRequest()
    request.project = project_name
    return instance_client.aggregated_list(request=request)

def all_machine_types(project_name, credentials):
    MachineTypes_client = compute_v1.MachineTypesClient(credentials=credentials)
    request = compute_v1.ListMachineTypesRequest(
        project=project_name,
        zone="us-west1-a",
    )
    return MachineTypes_client.list(request=request)

def find_machine_type(machine_type, machine_types_result):
    vCPUs = None
    RAM = None
    if "custom" in machine_type:
        parts = machine_type.split("-")
        if "custom" in parts:
            custom_index = parts.index("custom")
            if custom_index + 1 < len(parts):
                vCPUs = int(parts[custom_index + 1].strip()) if parts[custom_index + 1].strip().isdigit() else "None Types"
                if custom_index + 2 < len(parts):
                    ram_value = int(parts[custom_index + 2].strip()) if parts[custom_index + 2].strip().isdigit() else None
                    RAM = ram_value // 1024 if ram_value is not None else "None Types"
    else:
        for machine_types in machine_types_result:
            if machine_types.name == machine_type:
                vCPUs_output = float(re.search(r'(\d+(\.\d+)?)\s*vCPUs?', machine_types.description).group(1)) if re.search(
                    r'(\d+(\.\d+)?)\s*vCPUs?', machine_types.description) else "None Types"
                RAM_output = float(re.search(r'(\d+(\.\d+)?)\s*GB\s*RAM', machine_types.description).group(1)) if re.search(
                    r'(\d+(\.\d+)?)\s*GB\s*RAM', machine_types.description) else "None Types"

                vCPUs = int(vCPUs_output) if vCPUs_output.is_integer() else vCPUs_output
                RAM = int(RAM_output) if RAM_output.is_integer() else RAM_output
                break

    return vCPUs, RAM

def extract_instance_info(instance, kst, project_display_name, project_name, machine_types_result, credentials):
    INSTANCE_ID = str(instance.id)
    INSTANCE_NAME = instance.name
    # TAGS = instance.tags.items if instance.tags else []
    # tags_string = "\n".join(f"{tag}" for tag in TAGS)

    REGION = instance.network_interfaces[0].subnetwork.split("/")[-3] if instance.network_interfaces else None
    AZ = instance.zone.split("/")[-1] if instance.zone else None
    if instance.creation_timestamp:
        creation_time_utc = datetime.fromisoformat(instance.creation_timestamp.replace("Z", "+00:00"))
        creation_time_kst = creation_time_utc.astimezone(kst)
        CREATION_TIME = creation_time_kst.strftime('%Y-%m-%d %H:%M')
    else:
        CREATION_TIME = None

    PUBLIC_IP = instance.network_interfaces[0].access_configs[0].nat_i_p if instance.network_interfaces and instance.network_interfaces[0].access_configs else "-"
    PRIVATE_IP = instance.network_interfaces[0].network_i_p if instance.network_interfaces else None
    VPC_NAME = instance.network_interfaces[0].network.split("/")[-1] if instance.network_interfaces else None
    SUBNET_NAME = instance.network_interfaces[0].subnetwork.split("/")[-1] if instance.network_interfaces else None

    MACHINE_TYPE = instance.machine_type.split("/")[-1] if instance.machine_type else None
    HOSTNAME = instance.hostname if instance.hostname else "-"
    CPU_PLATFORM = instance.cpu_platform
    DELETION_PROTECTION = instance.deletion_protection

    disk_info = DiskInfo(project_name, AZ, credentials)
    disk_info.fetch_disks_info(instance)
    BOOT_DISK, DISKS, OS = disk_info.get_disks_summary()
    STATE = instance.status.upper()

    vCPUs, RAM = find_machine_type(MACHINE_TYPE, machine_types_result)

    return InstanceInfo(
        CLOUD="GCP",
        PROJECT=project_display_name,
        PROJECT_ID=project_name,
        INSTANCE_NAME=INSTANCE_NAME,
        INSTANCE_ID=INSTANCE_ID,
        REGION=REGION,
        AZ=AZ,
        MACHINE_TYPE=MACHINE_TYPE,
        vCPUs=vCPUs,
        RAM=RAM,
        BOOT_DISK=BOOT_DISK,
        DISKS=DISKS,
        PRIVATE_IP=PRIVATE_IP,
        PUBLIC_IP=PUBLIC_IP,
        OS=OS,
        STATE=STATE,
        HOSTNAME=HOSTNAME,
        # TAGS=tags_string,
        CPU_PLATFORM=CPU_PLATFORM,
        DELETION_PROTECTION=DELETION_PROTECTION,
        CREATION_TIME=CREATION_TIME,
        VPC_NAME=VPC_NAME,
        SUBNET_NAME=SUBNET_NAME,
    )


def main():
    print(f"{UNDERLINE}<GCP>{RESET}")

    kst = pytz.timezone('Asia/Seoul')
    gcp_cred_file_path = '../auth/cred_gcp.json'

    profile_manager = ProfileManager(gcp_cred_file_path)

    source_credentials = service_account.Credentials.from_service_account_info(
        profile_manager.service_account_key,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    project_names = profile_manager.projects

    instance_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        machine_types_result = all_machine_types(project_name, credentials)
        agg_list = get_aggregated_instances(project_name, credentials)
        all_instances = defaultdict(list)

        for zone, response in agg_list:
            if response.instances:
                all_instances[zone].extend(response.instances)
                for instance in response.instances:
                    instance_info = extract_instance_info(instance, kst, project_display_name, project_name, machine_types_result, credentials)
                    instance_objects.append(instance_info)

    instance_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME, x.INSTANCE_NAME))

    return instance_objects


if __name__ == "__main__":
    main()
