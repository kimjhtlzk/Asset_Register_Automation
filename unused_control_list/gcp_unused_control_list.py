import json
import os
from google.oauth2 import service_account
from google.cloud import resourcemanager_v3
from google.cloud.compute_v1.services.addresses import AddressesClient
from google.cloud.compute_v1.types import AggregatedListAddressesRequest
from google.cloud.compute_v1.services.firewalls import FirewallsClient
from google.cloud.compute_v1.services.instances import InstancesClient
from google.cloud.compute_v1.types import AggregatedListInstancesRequest
from google.cloud.compute_v1.services.disks import DisksClient
from google.cloud.compute_v1.types import AggregatedListDisksRequest
from google.auth import impersonated_credentials


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

def fetch_unused_addresses(client, project_name, project_display_name):
    unused_addresses = []
    request = AggregatedListAddressesRequest(project=project_name)
    aggregated_list = client.aggregated_list(request=request)

    for zone, addresses_scoped_list in aggregated_list:
        if addresses_scoped_list.addresses:
            region = zone.split("/")[-1]
            for address in addresses_scoped_list.addresses:
                if address.status == "RESERVED":
                    unused_addresses.append(
                        unUsedInfo(
                            CLOUD="GCP",
                            PROJECT=project_display_name,
                            PROJECT_ID=project_name,
                            RESOURCE_TYPE="IP",
                            RESOURCE=f"{address.name} ({address.address})",
                            REGION=region,
                            USE_O_X=""
                        )
                    )
    return unused_addresses

def fetch_unused_firewalls(client, project_name, project_display_name, active_tags):
    unused_firewalls = []
    firewalls = client.list(project=project_name)

    for firewall in firewalls:
        if firewall.target_tags:  # 태그가 있는 방화벽만 처리
            if (firewall.network.split("/")[-1] == 'default' or firewall.name.startswith("k8s-")
                    or firewall.name.startswith("blacklist-")):
                continue

            is_used = any(tag in active_tags for tag in firewall.target_tags)

            if not is_used:  # 태그가 어떤 인스턴스에서도 사용되지 않을 경우 추가
                unused_firewalls.append(
                    unUsedInfo(
                        CLOUD="GCP",
                        PROJECT=project_display_name,
                        PROJECT_ID=project_name,
                        RESOURCE_TYPE="FIREWALL",
                        RESOURCE=firewall.name,
                        REGION="-",
                        USE_O_X=""
                    )
                )
    return unused_firewalls

def fetch_unused_disks(client, project_name, project_display_name):
    unused_disks = []
    request_disks = AggregatedListDisksRequest(project=project_name)
    aggregated_disks = client.aggregated_list(request=request_disks)

    for scope, disks_scoped_list in aggregated_disks:
        if disks_scoped_list.disks:
            if scope.startswith('zones/'):
                zone = scope.split('/')[-1]
                region = '-'.join(zone.split('-')[:-1])  # us-central1-a → us-central1
            elif scope.startswith('regions/'):
                region = scope.split('/')[-1]
            else:
                continue

            for disk in disks_scoped_list.disks:
                if disk.name.startswith("pvc-") or any("k8s" in k or "gke" in k for k in (disk.labels or {})):
                    continue
                if not disk.users:  # 사용자(인스턴스)가 연결되지 않은 경우
                    unused_disks.append(
                        unUsedInfo(
                            CLOUD="GCP",
                            PROJECT=project_display_name,
                            PROJECT_ID=project_name,
                            RESOURCE_TYPE="DISK",
                            RESOURCE=f"{disk.name} ({disk.size_gb}GiB / {disk.type_.split('/')[-1]})",
                            REGION=region,
                            USE_O_X=""
                        )
                    )

    return unused_disks

def fetch_active_tags(client, project_name):
    active_tags = set()
    request_instances = AggregatedListInstancesRequest(project=project_name)
    aggregated_instances = client.aggregated_list(request=request_instances)

    for zone, instances_scoped_list in aggregated_instances:
        if instances_scoped_list.instances:
            for instance in instances_scoped_list.instances:
                active_tags.update(instance.tags.items)
    return active_tags


def main():
    print(f"{UNDERLINE}<GCP>{RESET}")

    gcp_cred_file_path = '../auth/cred_gcp.json'

    profile_manager = ProfileManager(gcp_cred_file_path)

    source_credentials = service_account.Credentials.from_service_account_info(
        profile_manager.service_account_key,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    project_names = profile_manager.projects

    unused_eip_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        addresses_client = AddressesClient(credentials=credentials)
        unused_eip_objects.extend(fetch_unused_addresses(addresses_client, project_name, project_display_name))

        instances_client = InstancesClient(credentials=credentials)
        active_tags = fetch_active_tags(instances_client, project_name)

        firewalls_client = FirewallsClient(credentials=credentials)
        unused_eip_objects.extend(fetch_unused_firewalls(firewalls_client, project_name, project_display_name, active_tags))

        disks_client = DisksClient(credentials=credentials)
        unused_eip_objects.extend(fetch_unused_disks(disks_client, project_name, project_display_name))

    unused_eip_objects.sort(key=lambda x: (x.PROJECT, x.RESOURCE_TYPE, x.RESOURCE))

    return unused_eip_objects


if __name__ == "__main__":
    main()
