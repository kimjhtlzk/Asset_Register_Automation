import json
import pytz
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.clb.v20180317 import clb_client, models
from datetime import datetime

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"

class LoadbalancerInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, LOADBALANCER_NAME, LOADBALANCER_ID, LOADBALANCER_TYPE, LOADBALANCER_DOMAIN, VIPS, VIP_ISP, REGION, MASTER_ZONE, BACKUP_ZONE, SNAT, SECURITY_GROUPS, SLA_TYPE, INTERNET_MAX_BANDWIDTH_OUT, NETWORK, PASS_TO_TARGET, LISTENER_PROTOCOL, LISTENER, HEALTH_CHECK, CREATION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.LOADBALANCER_NAME = LOADBALANCER_NAME
        self.LOADBALANCER_ID = LOADBALANCER_ID
        self.LOADBALANCER_TYPE = LOADBALANCER_TYPE
        self.LOADBALANCER_DOMAIN = LOADBALANCER_DOMAIN
        self.VIPS = VIPS
        self.VIP_ISP = VIP_ISP
        self.REGION = REGION
        self.MASTER_ZONE = MASTER_ZONE
        self.BACKUP_ZONE = BACKUP_ZONE
        self.SNAT = SNAT
        self.SECURITY_GROUPS = SECURITY_GROUPS
        self.SLA_TYPE = SLA_TYPE
        self.INTERNET_MAX_BANDWIDTH_OUT = INTERNET_MAX_BANDWIDTH_OUT
        self.NETWORK = NETWORK
        self.PASS_TO_TARGET = PASS_TO_TARGET
        self.LISTENER_PROTOCOL = LISTENER_PROTOCOL
        self.LISTENER = LISTENER
        self.HEALTH_CHECK = HEALTH_CHECK
        self.CREATION_TIME = CREATION_TIME

    def __repr__(self):
        return (f"LoadbalancerInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"LOADBALANCER_NAME={self.LOADBALANCER_NAME}, "
                f"LOADBALANCER_ID={self.LOADBALANCER_ID}, "
                f"LOADBALANCER_TYPE={self.LOADBALANCER_TYPE}, "
                f"LOADBALANCER_DOMAIN={self.LOADBALANCER_DOMAIN}, "
                f"VIPS={self.VIPS}, "
                f"VIP_ISP={self.VIP_ISP}, "
                f"REGION={self.REGION}, "
                f"MASTER_ZONE={self.MASTER_ZONE}, "
                f"BACKUP_ZONE={self.BACKUP_ZONE}, "
                f"SNAT={self.SNAT}, "
                f"SECURITY_GROUPS={self.SECURITY_GROUPS}, "
                f"SLA_TYPE={self.SLA_TYPE}, "
                f"INTERNET_MAX_BANDWIDTH_OUT={self.INTERNET_MAX_BANDWIDTH_OUT}, "
                f"NETWORK={self.NETWORK}, "
                f"PASS_TO_TARGET={self.PASS_TO_TARGET}, "
                f"LISTENER_PROTOCOL={self.LISTENER_PROTOCOL}, "
                f"LISTENER={self.LISTENER}, "
                f"HEALTH_CHECK={self.HEALTH_CHECK}, "
                f"CREATION_TIME={self.CREATION_TIME})")

class ProfileManager:
    def __init__(self, cred_file_path):
        self.cred_file_path = cred_file_path

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def convert_time_set(create_time, kst):
    china_tz = pytz.timezone('Asia/Shanghai')
    china_time = china_tz.localize(datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S"))
    kst_time = china_time.astimezone(kst)
    CREATION_TIME = kst_time.strftime("%Y-%m-%d %H:%M:%S")
    return CREATION_TIME

def describe_loadbalancer(cred, REGION):
    httpProfile = HttpProfile()
    httpProfile.endpoint = "clb.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = clb_client.ClbClient(cred, REGION, clientProfile)
    page = 1
    limit = 100
    all_lbs = []
    while True:
        req = models.DescribeLoadBalancersRequest()
        params = {
            "Region": REGION,
            "Limit": limit,
            "Offset": (page - 1) * limit,
        }
        req.from_json_string(json.dumps(params))
        resp = client.DescribeLoadBalancers(req)
        resp_json = json.loads(resp.to_json_string())
        all_lbs.extend(resp_json["LoadBalancerSet"])
        if len(resp_json["LoadBalancerSet"]) < limit:
            break
        page += 1
    return all_lbs

def describe_listener(cred, REGION, load_balancer_id):
    httpProfile = HttpProfile()
    httpProfile.endpoint = "clb.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = clb_client.ClbClient(cred, REGION, clientProfile)
    req = models.DescribeListenersRequest()
    params = {
        "LoadBalancerId": load_balancer_id
    }
    req.from_json_string(json.dumps(params))
    resp = client.DescribeListeners(req)
    response = json.loads(resp.to_json_string())
    return response.get("Listeners", [])

def extract_instance_info(lb, kst):
    load_balancer_id = lb.get("LoadBalancerId", "-")
    load_balancer_name = lb.get("LoadBalancerName", "-")
    load_balancer_type = lb.get("LoadBalancerType", "-")
    load_balancer_vips = "\n".join(lb.get("LoadBalancerVips", ["-"])) or "-"
    load_balancer_domain = lb.get("LoadBalancerDomain", "-") or "-"
    vpc_id = lb.get("VpcId", "-")
    snat = lb.get("Snat", "-")
    subnet_id = lb.get("SubnetId", "-") or "-"
    secure_groups = "\n".join(lb.get("SecureGroups", ["-"]))
    target_region_info = lb.get("TargetRegionInfo", {}).get("Region", "-")
    vip_isp = lb.get("VipIsp", "-") or "-"
    internet_max_bandwidth_out = f"{lb['NetworkAttributes']['InternetMaxBandwidthOut']} Mbps" if load_balancer_type == "OPEN" and "NetworkAttributes" in lb else "-"
    master_zone = lb.get("MasterZone")
    master_zone_value = master_zone.get("Zone", "-") if master_zone else "-"
    backup_zone_set = "\n".join([zone.get("Zone", "-") for zone in (lb.get("BackupZoneSet") or [])]) or "-"
    load_balancer_pass_to_target = lb.get("LoadBalancerPassToTarget", "-")
    snat_ips = "\n".join(lb.get("SnatIps", ["-"])) or "-"
    sla_type = lb.get("SlaType", "-") or "-"
    create_time = lb.get("CreateTime", "-")
    CREATION_TIME = convert_time_set(create_time, kst)
    return load_balancer_id, load_balancer_name, load_balancer_type, load_balancer_vips, load_balancer_domain, vpc_id, snat, subnet_id, secure_groups, target_region_info, vip_isp, internet_max_bandwidth_out, master_zone_value, backup_zone_set, load_balancer_pass_to_target, snat_ips, sla_type, CREATION_TIME

def logic_protocol(listener, kst):
    create_time = listener["CreateTime"]
    LISTENER_CREATION_TIME = convert_time_set(create_time, kst)
    listen = None
    healthcheck = None
    if listener["Protocol"] in ["UDP", "TCP"]:
        listen = (
            f"ListenerName: {listener['ListenerName']}\n"
            f"ListenerId: {listener['ListenerId']}\n"
            f"Port: {listener['Port']}\n"
            f"Certificate: {listener['Certificate']}\n"
            f"Scheduler: {listener['Scheduler']}\n"
            f"SessionExpireTime: {listener['SessionExpireTime']}\n"
            f"Rules: {listener['Rules']}\n"
            f"KeepaliveEnable: {listener['KeepaliveEnable']}\n"
            f"IdleConnectTimeout: {listener['IdleConnectTimeout']}\n"
            f"RescheduleInterval: {listener['RescheduleInterval']}\n"
            f"\nCreateTime: {LISTENER_CREATION_TIME}"
        )
        healthcheck = (
            f"CheckPort: {listener['HealthCheck']['CheckPort']}\n"
            f"CheckType: {listener['HealthCheck']['CheckType']}\n"
            f"TimeOut: {listener['HealthCheck']['TimeOut']}\n"
            f"IntervalTime: {listener['HealthCheck']['IntervalTime']}\n"
            f"HealthNum: {listener['HealthCheck']['HealthNum']}\n"
            f"UnHealthNum: {listener['HealthCheck']['UnHealthNum']}\n"
            f"HttpCode: {listener['HealthCheck']['HttpCode']}\n"
            f"HttpCheckPath: {listener['HealthCheck']['HttpCheckPath']}\n"
            f"HttpCheckDomain: {listener['HealthCheck']['HttpCheckDomain']}\n"
            f"HttpCheckMethod: {listener['HealthCheck']['HttpCheckMethod']}"
        )
    elif listener["Protocol"] in ["HTTP", "HTTPS"]:
        rules = listener["Rules"][0] if listener["Rules"] else {}
        listen = (
            f"ListenerName: {listener['ListenerName']}\n"
            f"ListenerId: {listener['ListenerId']}\n"
            f"Port: {listener['Port']}\n"
            f"Certificate: {listener['Certificate']['CertId'] if listener['Certificate'] else None}\n"
            f"Domain: {rules.get('Domain')}\n"
            f"Url: {rules.get('Url')}\n"
            f"Scheduler: {rules.get('Scheduler')}\n"
            f"ForwardType: {rules.get('ForwardType')}\n"
            f"SessionExpireTime: {rules.get('SessionExpireTime')}\n"
            f"KeepaliveEnable: {listener['KeepaliveEnable']}\n"
            f"IdleConnectTimeout: {listener['IdleConnectTimeout']}\n"
            f"RescheduleInterval: {listener['RescheduleInterval']}\n"
            f"\nCreateTime: {LISTENER_CREATION_TIME}"
        )
        healthcheck = (
            f"CheckPort: {rules.get('HealthCheck', {}).get('CheckPort')}\n"
            f"CheckType: {rules.get('HealthCheck', {}).get('CheckType')}\n"
            f"TimeOut: {rules.get('HealthCheck', {}).get('TimeOut')}\n"
            f"IntervalTime: {rules.get('HealthCheck', {}).get('IntervalTime')}\n"
            f"HealthNum: {rules.get('HealthCheck', {}).get('HealthNum')}\n"
            f"UnHealthNum: {rules.get('HealthCheck', {}).get('UnHealthNum')}\n"
            f"HttpCode: {rules.get('HealthCheck', {}).get('HttpCode')}\n"
            f"HttpCheckPath: {rules.get('HealthCheck', {}).get('HttpCheckPath')}\n"
            f"HttpCheckDomain: {rules.get('HealthCheck', {}).get('HttpCheckDomain')}\n"
            f"HttpCheckMethod: {rules.get('HealthCheck', {}).get('HttpCheckMethod')}"
        )
    return listen, healthcheck

def fetch_loadbalancers(credentials, project_name, AccountId, region_names, loadbalancer_objects, role_arn=None):
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
        lbs = describe_loadbalancer(cred, region)
        for lb in lbs:
            (load_balancer_id, load_balancer_name, load_balancer_type, load_balancer_vips,
             load_balancer_domain, vpc_id, snat, subnet_id, secure_groups, target_region_info,
             vip_isp, internet_max_bandwidth_out, master_zone_value, backup_zone_set,
             load_balancer_pass_to_target, snat_ips, sla_type, CREATION_TIME) = extract_instance_info(lb, kst)
            listeners = describe_listener(cred, region, load_balancer_id)
            for listener in listeners:
                LISTENER_PROTOCOL = listener['Protocol']
                listen, healthcheck = logic_protocol(listener, kst)
                loadbalancer_info = LoadbalancerInfo(
                    CLOUD="TENCENT",
                    PROJECT=project_name,
                    PROJECT_ID=AccountId,
                    LOADBALANCER_NAME=load_balancer_name,
                    LOADBALANCER_ID=load_balancer_id,
                    LOADBALANCER_TYPE=load_balancer_type,
                    LOADBALANCER_DOMAIN=load_balancer_domain,
                    VIPS=load_balancer_vips,
                    VIP_ISP=vip_isp,
                    REGION=target_region_info,
                    MASTER_ZONE=master_zone_value,
                    BACKUP_ZONE=backup_zone_set,
                    SNAT=snat if snat else snat_ips,
                    SECURITY_GROUPS=secure_groups,
                    SLA_TYPE=sla_type,
                    INTERNET_MAX_BANDWIDTH_OUT=internet_max_bandwidth_out,
                    NETWORK=f"{vpc_id} / {subnet_id}",
                    PASS_TO_TARGET=load_balancer_pass_to_target,
                    LISTENER_PROTOCOL=LISTENER_PROTOCOL,
                    LISTENER=listen,
                    HEALTH_CHECK=healthcheck,
                    CREATION_TIME=CREATION_TIME
                )
                loadbalancer_objects.append(loadbalancer_info)


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

    loadbalancer_objects = []

    # main_account
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    fetch_loadbalancers(main_account, main_account['AccountName'], main_account['AccountId'], region_names, loadbalancer_objects)

    # projects
    for project_name, project_info in projects.items():
        print(f"{BLUE}{project_name}{RESET}")
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

        fetch_loadbalancers(credentials_proj, project_name, project_info['AccountId'], region_names, loadbalancer_objects, role_arn=role_arn)

    loadbalancer_objects.sort(key=lambda x: (x.PROJECT, x.REGION, x.LOADBALANCER_TYPE, x.LOADBALANCER_NAME))

    return loadbalancer_objects


if __name__ == "__main__":
    main()
