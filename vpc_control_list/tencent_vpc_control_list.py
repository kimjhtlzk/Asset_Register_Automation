import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.vpc.v20170312 import vpc_client, models


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
    def __init__(self, secret_id, secret_key, region, role_arn=None):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.role_arn = role_arn
        self.client = self.create_client()

    def create_client(self):
        if self.role_arn:
            sts_cred = credential.STSAssumeRoleCredential(
                self.secret_id, self.secret_key, self.role_arn, "sts-session", 7200
            )
            cred = sts_cred
        else:
            cred = credential.Credential(self.secret_id, self.secret_key)

        http_profile = HttpProfile()
        http_profile.endpoint = "vpc.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        return vpc_client.VpcClient(cred, self.region, client_profile)

    def get_subnetworks(self):
        subnet_req = models.DescribeSubnetsRequest()
        subnet_params = {}
        subnet_req.from_json_string(json.dumps(subnet_params))
        subnet_resp = self.client.DescribeSubnets(subnet_req)
        return subnet_resp

    def get_vpcs(self, vpc_id):
        vpc_req = models.DescribeVpcsRequest()
        vpc_params = {
            "VpcIds": [vpc_id]
        }
        vpc_req.from_json_string(json.dumps(vpc_params))
        vpc_resp = self.client.DescribeVpcs(vpc_req)
        return vpc_resp

class ProfileManager:
    def __init__(self, cred_file_path):
        self.cred_file_path = cred_file_path

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def fetch_subnetworks(networks, project_name, project_id):
    subnetwork_objects = []
    try:
        subnet_resp = networks.get_subnetworks()

        if subnet_resp.TotalCount > 0:
            for subnet in subnet_resp.SubnetSet:
                VPC_ID = subnet.VpcId
                vpc_resp = networks.get_vpcs(VPC_ID)

                subnetwork_info = SubnetworkInfo(
                    CLOUD="TENCENT",
                    PROJECT=project_name,
                    PROJECT_ID=project_id,
                    VPC_NAME=vpc_resp.VpcSet[0].VpcName,
                    VPC_CIDR=vpc_resp.VpcSet[0].CidrBlock,
                    REGION=networks.region,
                    SUBNET_NAME=subnet.SubnetName,
                    SUBNET_CIDR=subnet.CidrBlock,
                    AZ=subnet.Zone,
                    SECONDARY_IP_CIDR="-"
                )
                subnetwork_objects.append(subnetwork_info)

    except Exception as e:
        print(f"Error fetching subnetworks: {e}")

    return subnetwork_objects


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

    subnetwork_objects = []

    # main_account
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    for region in region_names:
        networks = NetworkInfo(
            secret_id=main_account['secret_id'],
            secret_key=main_account['secret_key'],
            region=region,
            role_arn=None
        )
        subnetwork_objects.extend(fetch_subnetworks(networks, main_account['AccountName'], main_account['AccountId']))

    # projects
    for project_name, project_info in projects.items():
        print(f"{BLUE}{project_name}{RESET}")
        if project_name == "Chinaproject_1":
            secret_id = project_info['secret_id']
            secret_key = project_info['secret_key']
            role_arn = None
        else:
            secret_id = main_account['secret_id']
            secret_key = main_account['secret_key']
            role_arn = f"qcs::cam::uin/{project_info['AccountId']}:roleName/@owner"

        for region in region_names:
            networks = NetworkInfo(
                secret_id=secret_id,
                secret_key=secret_key,
                region=region,
                role_arn=role_arn
            )
            subnetwork_objects.extend(fetch_subnetworks(networks, project_name, project_info['AccountId']))

    subnetwork_objects.sort(key=lambda x: (x.PROJECT, x.VPC_NAME, x.SUBNET_NAME))

    return subnetwork_objects


if __name__ == "__main__":
    main()
