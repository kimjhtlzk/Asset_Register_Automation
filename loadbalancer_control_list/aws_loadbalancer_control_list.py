import boto3
import os
import pytz
import re
import json

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class LoadbalancerInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, LOADBALANCER_NAME, LOADBALANCER_ID, LOADBALANCER_TYPE,
                 LOADBALANCER_DOMAIN, VIPS, VIP_ISP, REGION, MASTER_ZONE, BACKUP_ZONE, SNAT, SECURITY_GROUPS, SLA_TYPE,
                 INTERNET_MAX_BANDWIDTH_OUT, NETWORK, PASS_TO_TARGET, LISTENER_PROTOCOL, LISTENER, HEALTH_CHECK,
                 CREATION_TIME):
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

def convert_utc_to_kst(utc_time):
    kst = pytz.timezone('Asia/Seoul')
    kst_time = utc_time.astimezone(kst).strftime("%Y-%m-%d %H:%M:%S")

    return kst_time

def get_loadbalancer_basic_info(loadbalancer):

    basic_info = {
        "name": loadbalancer['LoadBalancerName'],
        "id": loadbalancer['LoadBalancerArn'],
        "domain": loadbalancer['DNSName'],
        "vips": "-",
        "vip_isp": "-",
        "master_zone": "-",
        "backup_zone": "\n".join([zone['ZoneName'] for zone in loadbalancer['AvailabilityZones']]),
        "snat": "-",
        "security_groups": "\n".join(loadbalancer['SecurityGroups']),
        "sla_type": loadbalancer['Type'],
        "internet_max_bandwidth_out": "-",
        "network": loadbalancer['VpcId'],
        "pass_to_target": "-",
        "loadbalancer_type": loadbalancer['Scheme'],
    }
    return basic_info

def get_listener_info(listener, elb_client):
    listener_protocol = listener['Protocol']
    listener_arn = listener['ListenerArn']
    listener_name = listener_arn.split("/")[-1]
    listener_id = listener_arn
    port = listener['Port']
    certificates = listener.get('Certificates', [])
    certificate_arn = certificates[0]['CertificateArn'] if certificates else "-"
    default_actions = listener['DefaultActions']
    scheduler = default_actions[0]['Type']

    target_group_arns = []
    if 'ForwardConfig' in default_actions[0]:
        if 'TargetGroups' in default_actions[0]['ForwardConfig']:
            target_group_arns = [tg['TargetGroupArn'] for tg in default_actions[0]['ForwardConfig']['TargetGroups']]
    elif 'TargetGroupArn' in default_actions[0]:
        target_group_arns = [default_actions[0]['TargetGroupArn']]

    if not target_group_arns:
        health_check_info = "-"
        target_group_names = "-"
    else:
        target_group_names = []
        health_check_info = []
        for target_group_arn in target_group_arns:
            target_group_name = target_group_arn.split("/")[-1]
            target_group_names.append(target_group_name)

            health_check = elb_client.describe_target_groups(TargetGroupArns=[target_group_arn])
            health_check_str = (
                f"TargetGroupName: {target_group_name}\n"
                f"HealthCheckProtocol: {health_check['TargetGroups'][0].get('HealthCheckProtocol', '-')}\n"
                f"HealthCheckPort: {health_check['TargetGroups'][0].get('HealthCheckPort', '-')}\n"
                f"HealthCheckPath: {health_check['TargetGroups'][0].get('HealthCheckPath', '-')}\n"
                f"HealthCheckIntervalSeconds: {health_check['TargetGroups'][0].get('HealthCheckIntervalSeconds', '-')}\n"
                f"HealthCheckTimeoutSeconds: {health_check['TargetGroups'][0].get('HealthCheckTimeoutSeconds', '-')}\n"
                f"HealthyThresholdCount: {health_check['TargetGroups'][0].get('HealthyThresholdCount', '-')}\n"
                f"UnhealthyThresholdCount: {health_check['TargetGroups'][0].get('UnhealthyThresholdCount', '-')}"
            )
            health_check_info.append(health_check_str)

    listener_str = (
        f"Listener Name: {listener_name}\n"
        f"Listener ID: {listener_id}\n"
        f"Port: {port}\n"
        f"Certificate: {certificate_arn}\n"
        f"Scheduler: {scheduler}\n"
        f"Target Group Names: {', '.join(target_group_names) if target_group_names else '-'}"
    )

    return listener_protocol, listener_str, "\n".join(health_check_info) if health_check_info else "-"

def get_loadbalancer_info(project_name, session, REGION):
    try:
        elb_client = session.client('elbv2',)

        load_balancers = elb_client.describe_load_balancers()

        loadbalancer_infos = []

        for lb in load_balancers['LoadBalancers']:
            basic_info = get_loadbalancer_basic_info(lb)
            creation_time_utc = lb['CreatedTime']
            creation_time_kst = convert_utc_to_kst(creation_time_utc)

            listeners = elb_client.describe_listeners(LoadBalancerArn=lb['LoadBalancerArn'])

            if listeners['Listeners']:
                for listener in listeners['Listeners']:
                    listener_protocol, listener_str, health_check_info = get_listener_info(listener, elb_client)

                    loadbalancer_info = LoadbalancerInfo(
                        CLOUD="AWS",
                        PROJECT=project_name,
                        PROJECT_ID="-",
                        LOADBALANCER_NAME=basic_info['name'],
                        LOADBALANCER_ID=basic_info['id'],
                        LOADBALANCER_TYPE=basic_info['loadbalancer_type'],
                        LOADBALANCER_DOMAIN=basic_info['domain'],
                        VIPS=basic_info['vips'],
                        VIP_ISP=basic_info['vip_isp'],
                        REGION=REGION,
                        MASTER_ZONE=basic_info['master_zone'],
                        BACKUP_ZONE=basic_info['backup_zone'],
                        SNAT=basic_info['snat'],
                        SECURITY_GROUPS=basic_info['security_groups'],
                        SLA_TYPE=basic_info['sla_type'],
                        INTERNET_MAX_BANDWIDTH_OUT=basic_info['internet_max_bandwidth_out'],
                        NETWORK=basic_info['network'],
                        PASS_TO_TARGET=basic_info['pass_to_target'],
                        LISTENER_PROTOCOL=listener_protocol,
                        LISTENER=listener_str,
                        HEALTH_CHECK=health_check_info,
                        CREATION_TIME=creation_time_kst
                    )
                    loadbalancer_infos.append(loadbalancer_info)

        return loadbalancer_infos

    except Exception as e:
        print(f"Error occurred: {e}")
        return []


def main():
    print(f"{UNDERLINE}<AWS>{RESET}")

    cred_json_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_aws.json'
    cred_manager = CredentialManager(cred_json_path)
    project_names = cred_manager.get_projects()

    region_names = [
        "us-east-1", "us-east-2",
        "us-west-1", "us-west-2",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ap-southeast-1", "ap-southeast-2",
        "eu-central-1",
        "eu-west-1", "eu-west-2", "eu-west-3",
    ]

    loadbalancer_objects = []

    for project_name in project_names:
        print(f"{ORANGE}{project_name}{RESET}")
        account_id = cred_manager.get_account_id(project_name)
        role_arn = cred_manager.get_role_arn(account_id)

        try:
            credentials = assume_role(role_arn, session_name=project_name)
        except Exception as e:
            print(f"{RED}AssumeRole failed for {project_name}: {e}{RESET}")
            continue

        for REGION in region_names:
            session = boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=REGION
            )

            loadbalancer_infos = get_loadbalancer_info(project_name, session, REGION)
            loadbalancer_objects.extend(loadbalancer_infos)

        loadbalancer_objects.sort(key=lambda x: (x.PROJECT, x.REGION, x.LOADBALANCER_TYPE, x.LOADBALANCER_NAME))

    return loadbalancer_objects


if __name__ == "__main__":
    main()
