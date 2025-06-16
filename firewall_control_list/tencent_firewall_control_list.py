import json
import pytz
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.vpc.v20170312 import vpc_client, models
from datetime import datetime


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

class ProfileManager:
    def __init__(self, cred_file_path):
        self.cred_file_path = cred_file_path

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def process_firewall_rules(policy_set, direction, project_name, AccountId, security_groups_info, firewalls_objects, kst):
    if direction in policy_set:
        for rule in policy_set[direction]:
            # print(f"  PolicyDescription: {rule['PolicyDescription']}")
            if rule['ModifyTime']:
                modify_time = datetime.strptime(rule['ModifyTime'], '%Y-%m-%d %H:%M:%S')
                china_tz = pytz.timezone('Asia/Shanghai')
                modify_time_china = china_tz.localize(modify_time)
                modify_time_kst = modify_time_china.astimezone(kst)
                MODIFY_TIME = modify_time_kst.strftime('%Y-%m-%d %H:%M:%S')
            else:
                MODIFY_TIME = "-"

            firewall_info = FirewallInfo(
                CLOUD="TENCENT",
                PROJECT=project_name,
                PROJECT_ID=AccountId,
                SECURITY_GROUP=security_groups_info["SecurityGroupName"],
                SECURITY_GROUP_ID=security_groups_info["SecurityGroupId"],
                DIRECTION=direction,
                ACTION=rule['Action'],
                SOURCE=rule['CidrBlock'] if direction == "Egress" else "-",
                DESTINATION="-" if direction == "Egress" else rule['CidrBlock'],
                PROTOCOL=rule['Protocol'],
                PORTS=rule['Port'],
                PRIORITY="-",
                TAGS="-",
                VPC="-",
                # TARGET="",
                CREATION_TIME=MODIFY_TIME
            )

            firewalls_objects.append(firewall_info)

def get_security_groups(client, region):
    page = 1
    limit = 100
    security_groups_infos = []

    while True:
        sg_req = models.DescribeSecurityGroupsRequest()
        params = {
            "Region": str(region),
            "Limit": str(limit),
            "Offset": str((page - 1) * limit)
        }
        sg_req.from_json_string(json.dumps(params))

        sg_resp = client.DescribeSecurityGroups(sg_req)

        data = json.loads(sg_resp.to_json_string())

        if data["TotalCount"] > 0:
            for security_group in data["SecurityGroupSet"]:
                security_group_info = {
                    "SecurityGroupId": security_group['SecurityGroupId'],
                    "SecurityGroupName": security_group['SecurityGroupName'],
                    "CreatedTime": security_group['CreatedTime']
                }
                security_groups_infos.append(security_group_info)

        if len(sg_resp.SecurityGroupSet) < limit:
            break

        page += 1

    return security_groups_infos

def get_security_group_policies(client, region, security_group_id):
    rule_req = models.DescribeSecurityGroupPoliciesRequest()
    params = {
        "Region": region,
        "SecurityGroupId": security_group_id
    }
    rule_req.from_json_string(json.dumps(params))

    rule_resp = client.DescribeSecurityGroupPolicies(rule_req)
    rule_results = rule_resp.to_json_string()
    parsed_results = json.loads(rule_results)

    return parsed_results["SecurityGroupPolicySet"]

def fetch_firewall_rules(credentials, project_name, AccountId, region_names, firewalls_objects, role_arn=None):
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
        httpProfile.endpoint = f"vpc.{region}.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = vpc_client.VpcClient(cred, region, clientProfile)

        security_groups_infos = get_security_groups(client, region)

        for security_groups_info in security_groups_infos:
            policy_set = get_security_group_policies(client, region, security_groups_info["SecurityGroupId"])

            # Egress
            process_firewall_rules(policy_set, "Egress", project_name, AccountId, security_groups_info, firewalls_objects, pytz.timezone('Asia/Seoul'))

            # Ingress
            process_firewall_rules(policy_set, "Ingress", project_name, AccountId, security_groups_info, firewalls_objects, pytz.timezone('Asia/Seoul'))


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

    firewalls_objects = []

    # main_account
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    fetch_firewall_rules(main_account, main_account['AccountName'], main_account['AccountId'], region_names, firewalls_objects)

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

        fetch_firewall_rules(credentials, project_name, project_info['AccountId'], region_names, firewalls_objects, role_arn=role_arn)

    firewalls_objects.sort(key=lambda x: (x.PROJECT, x.VPC, x.SECURITY_GROUP, x.DIRECTION, x.ACTION))

    return firewalls_objects


if __name__ == "__main__":
    main()
