import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models
from tencentcloud.cbs.v20170312 import cbs_client, models as cbs_models
from tencentcloud.ecm.v20190719 import ecm_client, models as ecm_models


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

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def fetch_unused_eips(project_name, AccountId, client, region):
    unused = []
    req = vpc_models.DescribeAddressesRequest()
    try:
        resp = client.DescribeAddresses(req)
        for addr in resp.AddressSet:
            if not addr.InstanceId:
                resource_name = f"{addr.AddressName} ({addr.AddressId} / {addr.AddressIp})" if addr.AddressName else addr.AddressId
                unused.append(unUsedInfo(
                    CLOUD="TENCENT",
                    PROJECT=project_name,
                    PROJECT_ID=AccountId,
                    RESOURCE_TYPE="IP",
                    RESOURCE=resource_name,
                    REGION=region,
                    USE_O_X=""
                ))
    except TencentCloudSDKException as e:
        print(f"{RED}  EIP 조회 오류: {e}{RESET}")
    return unused

def fetch_unused_security_groups(client, region, project_name, AccountId):
    unused = []
    req = vpc_models.DescribeSecurityGroupsRequest()

    req.Limit = "100"
    req.Offset = "0"

    try:
        while True:
            resp = client.DescribeSecurityGroups(req)

            for sg in resp.SecurityGroupSet:
                if sg.IsDefault or sg.SecurityGroupName.startswith("basic-"):
                    continue

                stat_req = vpc_models.DescribeSecurityGroupAssociationStatisticsRequest()
                stat_req.SecurityGroupIds = [sg.SecurityGroupId]
                stat_resp = client.DescribeSecurityGroupAssociationStatistics(stat_req)

                if stat_resp.SecurityGroupAssociationStatisticsSet:
                    stats = stat_resp.SecurityGroupAssociationStatisticsSet[0]
                    # 모든 리소스 유형의 연결 수 확인
                    if stats.TotalCount == 0:  # 전체 인스턴스 연결 수가 0일 경우 미사용으로 판단
                        resource_name = f"{sg.SecurityGroupName} ({sg.SecurityGroupId})" if sg.SecurityGroupName else sg.SecurityGroupId
                        unused.append(unUsedInfo(
                            CLOUD="TENCENT",
                            PROJECT=project_name,
                            PROJECT_ID=AccountId,
                            RESOURCE_TYPE="SECURITY_GROUP",
                            RESOURCE=resource_name,
                            REGION=region,
                            USE_O_X=""
                        ))

            if len(resp.SecurityGroupSet) < int(req.Limit):
                break

            req.Offset = str(int(req.Offset) + int(req.Limit))

    except TencentCloudSDKException as e:
        print(f"{RED}  보안그룹 조회 실패: {e}{RESET}")

    return unused

def fetch_unused_disks(project_name, AccountId, client, region):
    unused = []
    req = cbs_models.DescribeDisksRequest()
    try:
        resp = client.DescribeDisks(req)
        for disk in resp.DiskSet:
            if not disk.Attached and not disk.DiskName.startswith("pvc-"):
                resource_name = f"{disk.DiskName} ({disk.DiskId} / {disk.DiskSize}GiB / {disk.DiskType})" if disk.DiskName else disk.DiskId
                unused.append(unUsedInfo(
                    CLOUD="TENCENT",
                    PROJECT=project_name,
                    PROJECT_ID=AccountId,
                    RESOURCE_TYPE="DISK",
                    RESOURCE=resource_name,
                    REGION=region,
                    USE_O_X=""
                ))
    except TencentCloudSDKException as e:
        print(f"{RED}  디스크 조회 오류: {e}{RESET}")
    return unused


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
        "ap-hongkong", "ap-seoul",
    ]

    unused_eip_objects = []

    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    for region in region_names:
        cred = credential.Credential(main_account['secret_id'], main_account['secret_key'])
        http_profile = HttpProfile(endpoint="vpc.tencentcloudapi.com")
        client_profile = ClientProfile(httpProfile=http_profile)
        vpc_cli = vpc_client.VpcClient(cred, region, client_profile)
        cbs_cli = cbs_client.CbsClient(cred, region)
        unused_eip_objects.extend(fetch_unused_eips(main_account['AccountName'], main_account['AccountId'], vpc_cli, region))
        unused_eip_objects.extend(fetch_unused_security_groups(client=vpc_cli, region=region, project_name=main_account['AccountName'], AccountId=main_account['AccountId']))
        unused_eip_objects.extend(fetch_unused_disks(main_account['AccountName'], main_account['AccountId'], cbs_cli, region))

    for project_name, project_info in projects.items():
        print(f"{BLUE}{project_name}{RESET}")

        if project_name == "Chinaproject_1":
            cred = credential.Credential(project_info['secret_id'], project_info['secret_key'])
        else:
            cred = credential.STSAssumeRoleCredential(
                main_account['secret_id'],
                main_account['secret_key'],
                f"qcs::cam::uin/{project_info['AccountId']}:roleName/@owner",
                "sts-session",
                7200
            )

        for region in region_names:
            http_profile = HttpProfile(endpoint="vpc.tencentcloudapi.com")
            client_profile = ClientProfile(httpProfile=http_profile)
            vpc_cli = vpc_client.VpcClient(cred, region, client_profile)
            cbs_cli = cbs_client.CbsClient(cred, region)
            unused_eip_objects.extend(fetch_unused_eips(project_name, project_info['AccountId'], vpc_cli, region))
            unused_eip_objects.extend(fetch_unused_security_groups(client=vpc_cli, region=region, project_name=project_name, AccountId=project_info['AccountId']))
            unused_eip_objects.extend(fetch_unused_disks(project_name, project_info['AccountId'], cbs_cli, region))

    unused_eip_objects.sort(key=lambda x: (x.PROJECT, x.RESOURCE_TYPE, x.RESOURCE))

    return unused_eip_objects


if __name__ == "__main__":
    main()
