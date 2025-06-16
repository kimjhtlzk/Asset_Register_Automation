# https://docs.gspread.org/en/latest/user-guide.html
# pip3 install gspread oauth2client
# pip3 install google-cloud-resource-manager
import json
import os
import re
from google.oauth2 import service_account
from google.cloud import compute_v1
from google.cloud import resourcemanager_v3
from google.auth import impersonated_credentials


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

def network_info(PROJECT, REGION):
    subnet_client = compute_v1.SubnetworksClient()

    subnet_request = compute_v1.ListSubnetworksRequest(
        project=PROJECT,
        region=REGION,
    )
    subnet_result = subnet_client.list(request=subnet_request)
    return subnet_result


def main():
    print(f"{UNDERLINE}<GCP>{RESET}")

    gcp_cred_file_path = '../auth/cred_gcp.json'

    profile_manager = ProfileManager(gcp_cred_file_path)

    source_credentials = service_account.Credentials.from_service_account_info(
        profile_manager.service_account_key,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    project_names = profile_manager.projects

    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    subnetwork_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        for region in region_names:
            subnet_client = compute_v1.SubnetworksClient(credentials=credentials)
            subnet_request = compute_v1.ListSubnetworksRequest(
                project=project_name,
                region=region,
            )
            subnetworks = subnet_client.list(request=subnet_request)

            for subnetwork in subnetworks:
                subnetwork_str = str(subnetwork)
                subent_name = re.search(r'name:\s+"([^"]+)"', subnetwork_str).group(1)
                if subent_name == "default":
                    continue
                subnet_cidr = re.search(r'ip_cidr_range:\s+"([^"]+)"', subnetwork_str).group(1)
                region_val = re.search(r'region:\s+"([^"]+)"', subnetwork_str).group(1)
                vpc_name = re.search(r'network:\s+"([^"]+)"', subnetwork_str).group(1)
                if re.search(r'secondary_ip_ranges\s*{', subnetwork_str):
                    secondary_ip_ranges = re.findall(r'secondary_ip_ranges\s*{\s*ip_cidr_range:\s+"([^"]+)"', subnetwork_str)
                else:
                    secondary_ip_ranges = "-"

                subnetwork_info = SubnetworkInfo(
                    CLOUD="GCP",
                    PROJECT=project_display_name,
                    PROJECT_ID=project_name,
                    VPC_NAME=vpc_name.split('/')[-1],
                    VPC_CIDR="-",
                    REGION="GLOBAL",
                    SUBNET_NAME=subent_name,
                    SUBNET_CIDR=subnet_cidr,
                    AZ=region_val.split('/')[-1],
                    SECONDARY_IP_CIDR=secondary_ip_ranges
                )

                subnetwork_objects.append(subnetwork_info)

    subnetwork_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME))

    return subnetwork_objects


if __name__ == "__main__":
    main()
