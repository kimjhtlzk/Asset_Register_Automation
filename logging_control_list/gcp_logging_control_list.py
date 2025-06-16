# pip3 install google-api-python-client
# pip3 install google-auth
# pip3 install google-cloud-logging google-cloud-iam
import json
import os
import time
import google
from google.oauth2 import service_account
from google.cloud import resourcemanager_v3, logging
from datetime import datetime, timedelta
from google.api_core import exceptions
from google.auth import impersonated_credentials


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class LoggingFirewallInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, SECURITY_GROUP, DIRECTION, RULE_TYPE, PRIORITY, PROTOCOL, PORTS, SOURCE, DESTINATION, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.SECURITY_GROUP = SECURITY_GROUP
        self.DIRECTION = DIRECTION
        self.RULE_TYPE = RULE_TYPE
        self.PRIORITY = PRIORITY
        self.PROTOCOL = PROTOCOL
        self.PORTS = PORTS
        self.SOURCE = SOURCE
        self.DESTINATION = DESTINATION
        self.ACTION_TIME = ACTION_TIME

class LoggingAccountInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, ACCOUNT, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.ACCOUNT = ACCOUNT
        self.ACTION_TIME = ACTION_TIME

class LoggingIamInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, PERMISSION, ACCOUNT, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.PERMISSION = PERMISSION
        self.ACCOUNT = ACCOUNT
        self.ACTION_TIME = ACTION_TIME

class LoggingKeyInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, ACCOUNT, ACCESS_KEY, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.ACCOUNT = ACCOUNT
        self.ACCESS_KEY = ACCESS_KEY
        self.ACTION_TIME = ACTION_TIME

class LoggingInstanceInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, WORKER, ACTION, REGION, AZ, INSTANCE_TYPE, INSTANCE, NETWORK, ACTION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.WORKER = WORKER
        self.ACTION = ACTION
        self.REGION = REGION
        self.AZ = AZ
        self.INSTANCE_TYPE = INSTANCE_TYPE
        self.INSTANCE = INSTANCE
        self.NETWORK = NETWORK
        self.ACTION_TIME = ACTION_TIME

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

def calculate_previous_month_dates():
    current_date = datetime.now()
    first_day_previous_month = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_previous_month = current_date.replace(day=1) - timedelta(days=1)
    return first_day_previous_month.strftime('%Y-%m-%dT00:00:00Z'), last_day_previous_month.strftime(
        '%Y-%m-%dT23:59:59Z')

def get_log_entries(client, filter_):
    log_entries = []
    for entry in client.list_entries(filter_=filter_):
        if entry.severity != 'ERROR':
            log_entries.append(entry)

    return log_entries

def get_iam_common_logs(start_time, end_time, credentials, project_name):
    client = logging.Client(
        project=project_name,
        credentials=credentials
    )
    filter_ = f'''
        timestamp >= "{start_time}" AND timestamp <= "{end_time}" 
        AND protoPayload.methodName = "SetIamPolicy"
        AND NOT (
          protoPayload.authenticationInfo.principalEmail =~ "^service-"
          OR protoPayload.authenticationInfo.principalEmail =~ "system.gserviceaccount.com"
          OR protoPayload.authenticationInfo.principalEmail =~ "container-engine-robot"
          OR protoPayload.authenticationInfo.principalEmail =~ "^[0-9]"
        )
    '''
    return get_log_entries(client, filter_)

def iam_logs(project_display_name, project_name, loggingiam_objects, log_entries):
    role_mapping_dict = {
        "712": "role_monitor",
        "763": "role_terraform",
        "549": "role_Billing_Viewer",
        "386": "serviceusage",
        "821": "role_cloud_bucket"
    }
    for entry in log_entries:
        action_time = entry.timestamp.astimezone(tz=None).strftime('%Y-%m-%d %H:%M:%S')
        worker = entry.payload.get('authenticationInfo', {}).get('principalEmail', '')
        binding_deltas = entry.payload.get('serviceData', {}).get('policyDelta', {}).get('bindingDeltas', [])

        if not binding_deltas:
            continue

        actions = [delta.get('action', '') for delta in binding_deltas]
        permissions = [
            role_mapping_dict.get(
                delta.get('role', '').split('/')[-1],
                delta.get('role', '').split('/')[-1]
            )
            for delta in binding_deltas
        ]
        accounts = [delta.get('member', '').split(':')[-1] for delta in binding_deltas]

        loggingiam_objects.append(LoggingIamInfo(
            CLOUD="GCP",
            PROJECT=project_display_name,
            PROJECT_ID=project_name,
            WORKER=worker,
            ACTION='\n'.join(actions),
            PERMISSION='\n'.join(permissions),
            ACCOUNT='\n'.join(accounts),
            ACTION_TIME=action_time
        ))

def account_logs(project_display_name, project_name, loggingaccount_objects, log_entries):
    processed_accounts = set()

    for entry in log_entries:
        action_time = entry.timestamp.astimezone(tz=None).strftime('%Y-%m-%d %H:%M:%S')
        worker = entry.payload.get('authenticationInfo', {}).get('principalEmail', '')
        binding_deltas = entry.payload.get('serviceData', {}).get('policyDelta', {}).get('bindingDeltas', [])

        all_members = {member for binding in entry.payload.get('request', {}).get('policy', {}).get('bindings', [])
                       for member in binding.get('members', [])}

        entry_processed_accounts = set()

        for delta in binding_deltas:
            action = delta.get('action')
            member = delta.get('member', '')
            account = member.split(':')[-1]
            account_key = f"{account}_{action_time}_{'DELETE' if action == 'REMOVE' else 'CREATE'}"

            if account_key in processed_accounts or account_key in entry_processed_accounts:
                continue

            if (action == 'REMOVE' and member not in all_members) or (action == 'ADD' and not any(
                    binding.get('role') != delta.get('role') and member in binding.get('members', [])
                    for binding in entry.payload.get('request', {}).get('policy', {}).get('bindings', []))):
                loggingaccount_objects.append(LoggingAccountInfo(
                    CLOUD="GCP",
                    PROJECT=project_display_name,
                    PROJECT_ID=project_name,
                    WORKER=worker,
                    ACTION="DELETE" if action == 'REMOVE' else "CREATE",
                    ACCOUNT=account,
                    ACTION_TIME=action_time
                ))
                entry_processed_accounts.add(account_key)
                processed_accounts.add(account_key)

def key_logs(project_display_name, project_name, start_time, end_time, loggingkey_objects, credentials):
    client = logging.Client(project=project_name, credentials=credentials)
    filter_ = f'''
    timestamp >= "{start_time}" AND timestamp <= "{end_time}" 
    AND (protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"
         OR protoPayload.methodName = "google.iam.admin.v1.DeleteServiceAccountKey")
    '''

    for entry in get_log_entries(client, filter_):
        worker = entry.payload['authenticationInfo']['principalEmail']
        action = entry.payload['request']['@type'].split('.')[-1].replace('Request', '')
        account = entry.resource.labels['email_id']
        access_key = entry.payload['request' if action == "DeleteServiceAccountKey" else 'response']['name'].split('/')[
            -1]
        action_time = (entry.timestamp + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')

        loggingkey_objects.append(LoggingKeyInfo(
            CLOUD="GCP",
            PROJECT=project_display_name,
            PROJECT_ID=project_name,
            WORKER=worker,
            ACTION=action,
            ACCOUNT=account,
            ACCESS_KEY=access_key,
            ACTION_TIME=action_time
        ))

def firewall_logs(project_display_name, project_name, start_time, end_time, loggingfirewall_objects, credentials):
    client = logging.Client(project=project_name, credentials=credentials)
    filter_ = f'''
    timestamp >= "{start_time}" AND timestamp <= "{end_time}" 
    AND (
        protoPayload.methodName="v1.compute.firewalls.patch" 
        OR protoPayload.methodName="v1.compute.firewalls.delete"
    )
    AND NOT (
      protoPayload.authenticationInfo.principalEmail =~ "^service-"
      OR protoPayload.authenticationInfo.principalEmail =~ "system.gserviceaccount.com"
      OR protoPayload.authenticationInfo.principalEmail =~ "container-engine-robot"
      OR protoPayload.authenticationInfo.principalEmail =~ "^[0-9]"
    )
    '''

    for entry in get_log_entries(client, filter_):
        if 'last' in str(entry):
            continue

        worker = entry.payload['authenticationInfo']['principalEmail']
        action = entry.payload.get('methodName', '').split('.')[-1].lower()
        action = {'patch': 'update', 'delete': 'delete'}.get(action, action)

        security_group = entry.payload.get('resourceName', '').split('/')[-1]
        if security_group.lower().startswith('blacklist'):
            continue

        request = entry.payload.get('request', {})
        resource_original_state = entry.payload.get('resourceOriginalState', {})

        if action == 'delete':
            direction = rule_type = protocol = ports = source = destination = priority = "-"
        else:
            def check_change(old, new):
                if old != new:
                    return f"{old} -> {new}"
                return "-"

            # DIRECTION 변경
            old_direction = resource_original_state.get('direction', '').upper()
            new_direction = request.get('direction', old_direction).upper()
            direction = check_change(old_direction, new_direction)

            # RULE_TYPE 변경
            old_rule_type = 'ALLOWED' if 'alloweds' in resource_original_state else 'DENIED' if 'denieds' in resource_original_state else ''
            new_rule_type = 'ALLOWED' if 'alloweds' in request else 'DENIED' if 'denieds' in request else old_rule_type
            rule_type = check_change(old_rule_type, new_rule_type)

            # PRIORITY 변경
            old_priority = resource_original_state.get('priority', '')
            new_priority = request.get('priority', old_priority)
            priority = check_change(old_priority, new_priority)

            # PROTOCOL 변경
            old_protocol_rules = resource_original_state.get('alloweds', []) or resource_original_state.get('denieds',
                                                                                                            [])
            new_protocol_rules = request.get('alloweds', []) or request.get('denieds', [])
            old_protocol = old_protocol_rules[0].get('IPProtocol', '').upper() if old_protocol_rules else ''
            new_protocol = new_protocol_rules[0].get('IPProtocol', old_protocol).upper() if new_protocol_rules else old_protocol
            protocol = check_change(old_protocol, new_protocol)

            # PORTS 변경
            old_ports_list = old_protocol_rules[0].get('ports', []) if old_protocol_rules and 'ports' in old_protocol_rules[0] else ['all']
            new_ports_list = new_protocol_rules[0].get('ports', []) if new_protocol_rules and 'ports' in new_protocol_rules[0] else ['all']

            # 숫자 순서로 정렬 (문자열 'all'은 별도 처리)
            def sort_ports(ports_list):
                if ports_list == ['all']:
                    return ports_list
                try:
                    return sorted([int(p) for p in ports_list])
                except:
                    return sorted(ports_list)

            old_ports_list = sort_ports(old_ports_list)
            new_ports_list = sort_ports(new_ports_list)

            old_ports = ", ".join(map(str, old_ports_list))
            new_ports = ", ".join(map(str, new_ports_list))

            # 변경 사항 표시
            if old_ports != new_ports:
                ports = f"{old_ports} -> {new_ports}"
            else:
                ports = "-"

            # SOURCE 변경
            old_source = set(resource_original_state.get('sourceRanges', []))
            new_source = set(request.get('sourceRanges', []))
            added_source = new_source - old_source
            removed_source = old_source - new_source
            source = '\n'.join([f"(+) {ip}" for ip in added_source] + [f"(-) {ip}" for ip in removed_source]) or "-"

            # DESTINATION 변경
            old_destination = set(resource_original_state.get('destinationRanges', []))
            new_destination = set(request.get('destinationRanges', []))
            added_destination = new_destination - old_destination
            removed_destination = old_destination - new_destination
            destination = '\n'.join([f"(+) {ip}" for ip in added_destination] + [f"(-) {ip}" for ip in removed_destination]) or "-"

        action_time = (entry.timestamp + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')

        loggingfirewall_objects.append(LoggingFirewallInfo(
            CLOUD="GCP",
            PROJECT=project_display_name,
            PROJECT_ID=project_name,
            WORKER=worker,
            ACTION=action,
            SECURITY_GROUP=security_group,
            DIRECTION=direction,
            RULE_TYPE=rule_type,
            PRIORITY=priority,
            PROTOCOL=protocol,
            PORTS=ports,
            SOURCE=source,
            DESTINATION=destination,
            ACTION_TIME=action_time
        ))

def instance_logs(project_display_name, project_name, start_time, end_time, logginginstance_objects, credentials):
    client = logging.Client(project=project_name, credentials=credentials)

    def process_log_entry(entry):
        if 'last' in str(entry):
            return

        worker = entry.payload['authenticationInfo']['principalEmail']
        if worker.startswith("eks-") or "AutoScaling" in worker or worker.startswith("databricks"):
            return
        action = entry.payload['methodName'].split('.')[-1]
        az = entry.resource.labels.get('zone', '')
        region = '-'.join(az.split('-')[:-1]) if az else ''
        instance_type = instance = network = "-"

        if action == "delete":
            instance = entry.payload.get('resourceName', '').split('/')[-1]
        elif action == "insert":
            request = entry.payload.get('request', {})
            instance_type = request.get('machineType', '').split('/')[-1]
            instance = request.get('name') or entry.payload.get('resourceName', '').split('/')[-1]
            network_interfaces = request.get('networkInterfaces', [{}])[0]
            network_name = network_interfaces.get('network', '').split('/')[-1]
            subnetwork_name = network_interfaces.get('subnetwork', '').split('/')[-1]
            network = f"{network_name} / {subnetwork_name}" if network_name and subnetwork_name else network_name or subnetwork_name or "-"
        elif action == "setMachineType":
            instance_type = entry.payload.get('request', {}).get('machineType', '').split('/')[-1]
            instance = entry.payload.get('resourceName', '').split('/')[-1]
        elif action == "resize":
            action = "disk_resize"
            instance_type = f"=> {entry.payload.get('request', {}).get('sizeGb', '')}GB"
            instance = entry.payload.get('resourceName', '').split('/')[-1]
        elif action in ["attachDisk", "detachDisk"]:
            disk_key = 'newlyAttachedDisks' if action == "attachDisk" else 'newlyDetachedDisks'
            disks = entry.payload.get('metadata', {}).get(disk_key, [])
            instance_type = "=> " + "\n=> ".join([disk.split('/')[-1] for disk in disks]) if disks else "-"
            instance = entry.payload.get('resourceName', '').split('/')[-1]
        elif action in ["start", "stop"]:
            instance = entry.payload.get('resourceName', '').split('/')[-1]

        action_time = (entry.timestamp + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')

        logginginstance_objects.append(LoggingInstanceInfo(
            CLOUD="GCP",
            PROJECT=project_display_name,
            PROJECT_ID=project_name,
            WORKER=worker,
            ACTION=action,
            REGION=region,
            AZ=az,
            INSTANCE_TYPE=instance_type,
            INSTANCE=instance,
            NETWORK=network,
            ACTION_TIME=action_time
        ))

    # 로그 필터 템플릿
    filter_template = '''
        timestamp >= "{start}" AND timestamp <= "{end}" 
        AND (protoPayload.methodName="v1.compute.instances.insert"
             OR protoPayload.methodName="v1.compute.instances.delete"
             OR protoPayload.methodName="v1.compute.instances.setMachineType"
             OR protoPayload.methodName="v1.compute.disks.resize"
             OR protoPayload.methodName="v1.compute.instances.attachDisk"
             OR protoPayload.methodName="v1.compute.instances.detachDisk"
             OR protoPayload.methodName="v1.compute.instances.start"
             OR protoPayload.methodName="v1.compute.instances.stop")
        AND NOT (
          protoPayload.authenticationInfo.principalEmail =~ "^service-"
          OR protoPayload.authenticationInfo.principalEmail =~ "system.gserviceaccount.com"
          OR protoPayload.authenticationInfo.principalEmail =~ "container-engine-robot"
          OR protoPayload.authenticationInfo.principalEmail =~ "^[0-9]"
        )
    '''

    try:
        # 전체 기간에 대해 시도
        # print(f"전체 기간({GREEN}{start_time} ~ {end_time}{RESET})에 대해 로그 조회 시도...")
        filter_ = filter_template.format(start=start_time, end=end_time)
        entries = get_log_entries(client, filter_)

        # 로그 처리
        for entry in entries:
            process_log_entry(entry)

        # print(f"전체 기간({GREEN}{start_time} ~ {end_time}{RESET})에 대해 로그 조회 및 처리 성공...")
    except google.api_core.exceptions.ResourceExhausted as e:
        # 할당량 초과 오류 발생 시 시간 범위를 나누어 처리
        # print(f"{ORANGE}limit exceeded 'Read requests per minute' 오류 발생. 60초 대기 후 시간 범위를 1달 -> 7일로 나누어 처리합니다{RESET}")
        time.sleep(60)

        # 시간 범위 분할 처리
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

        # 초기 청크 크기 설정
        chunk_size = timedelta(days=7)
        current_start = start_dt

        # 최소 청크 크기 설정 (더 이상 줄이지 않을 크기)
        min_chunk_days = 1

        while current_start < end_dt:
            try:
                # 겹치지 않도록 끝 시간 설정 (마지막 청크는 예외)
                current_end = min(current_start + chunk_size, end_dt)

                # 마지막 청크가 아닌 경우 1초 빼서 겹치지 않게 함
                if current_end < end_dt:
                    current_end_str = (current_end - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    # 마지막 청크는 원래대로 설정
                    current_end_str = current_end.strftime('%Y-%m-%dT%H:%M:%SZ')

                current_start_str = current_start.strftime('%Y-%m-%dT%H:%M:%SZ')

                # print(f"시간 범위 처리 중: {GREEN}{current_start_str} ~ {current_end_str}{RESET}")

                filter_ = filter_template.format(start=current_start_str, end=current_end_str)

                chunk_entries = get_log_entries(client, filter_)
                # 로그 처리
                for entry in chunk_entries:
                    process_log_entry(entry)

                # 다음 청크로 이동
                current_start = current_end

                # 청크 사이에 추가 대기 시간 추가
                # print(f"시간 범위 {GREEN}{current_start_str} ~ {current_end_str}{RESET} 처리 완료, 다음 시간 범위 처리 전 대기 중...")
                time.sleep(60)

            except google.api_core.exceptions.ResourceExhausted as e:
                # 청크 처리 중에도 할당량 초과 발생 시 청크 크기 조정 및 재시도
                days = chunk_size.days
                if days > min_chunk_days:
                    # 청크 크기를 줄임 (7일 -> 5일 -> 4일 -> 3일 -> 2일 -> 1일)
                    days -= 1 if days <= 5 else 2  # 7일에서는 5일로, 그 이하는 1일씩 감소
                    chunk_size = timedelta(days=days)
                    # print(f"{ORANGE}시간 범위 처리 중 할당량 초과 오류 발생. 시간 범위를 {days}일로 조정하고 60초 대기 후 재시도{RESET}")
                    time.sleep(61)
                    # 실패한 청크를 다시 시도 (현재 청크 반복)
                    continue
                else:
                    # 최소 크기에 도달했는데도 오류가 발생하면 더 긴 대기 시간 적용
                    # print(f"{ORANGE}최소 시간 범위 크기({min_chunk_days}일)에서도 할당량 초과 오류 발생. 120초 대기 후 재시도{RESET}")
                    time.sleep(120)
                    continue

        # print(f"모든 범위 기간에 대해 로그 조회 및 처리 성공...")


def main():
    print(f"{UNDERLINE}<GCP>{RESET}")

    gcp_cred_file_path = '../auth/cred_gcp.json'

    profile_manager = ProfileManager(gcp_cred_file_path)

    source_credentials = service_account.Credentials.from_service_account_info(
        profile_manager.service_account_key,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    project_names = profile_manager.projects

    loggingfirewall_objects = []
    loggingaccount_objects  = []
    loggingiam_objects      = []
    loggingkey_objects      = []
    logginginstance_objects = []


    start_time, end_time = calculate_previous_month_dates()
    # start_time = "2025-02-01T00:00:00Z" #################################################################################
    # end_time   = "2025-02-28T23:59:59Z" #################################################################################

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        log_entries = get_iam_common_logs(start_time, end_time, credentials, project_name)
        iam_logs(project_display_name, project_name, loggingiam_objects, log_entries)
        account_logs(project_display_name, project_name, loggingaccount_objects, log_entries)
        key_logs(project_display_name, project_name, start_time, end_time, loggingkey_objects, credentials)
        firewall_logs(project_display_name, project_name, start_time, end_time, loggingfirewall_objects, credentials)
        instance_logs(project_display_name, project_name, start_time, end_time, logginginstance_objects, credentials)

    loggingfirewall_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingaccount_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingiam_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingkey_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    logginginstance_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))

    return loggingfirewall_objects, loggingaccount_objects, loggingiam_objects, loggingkey_objects, logginginstance_objects


if __name__ == "__main__":
    main()
