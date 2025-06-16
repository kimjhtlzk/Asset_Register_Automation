import json
import io
import pytz
from datetime import timezone, datetime, timedelta
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cam.v20190116 import cam_client, models

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
    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

def log_firewall(event_name, requestParameters, entry, project_name, AccountId, worker, action_time, loggingfirewall_objects):
    if event_name in ["CreateSecurityGroupPolicies", "DeleteSecurityGroupPolicies", "ReplaceSecurityGroupPolicies"]:
        if "SecurityGroupPolicySet" not in requestParameters:
            return
        security_group_policy_set = requestParameters["SecurityGroupPolicySet"]

        for direction in ["Egress", "Ingress"]:
            if direction in security_group_policy_set:
                for rule in security_group_policy_set[direction]:
                    ports = rule["Port"].replace(",", "\n")
                    source = rule["CidrBlock"] if direction == "Ingress" else "-"
                    destination = rule["CidrBlock"] if direction == "Egress" else "-"
                    source = source.replace(",", "\n")
                    destination = destination.replace(",", "\n")

                    loggingfirewall_objects.append(LoggingFirewallInfo(
                        CLOUD="TENCENT",
                        PROJECT=project_name,
                        PROJECT_ID=AccountId,
                        WORKER=worker,
                        ACTION=event_name,
                        SECURITY_GROUP=(entry["resourceName"]).split("/")[1],
                        DIRECTION=direction,
                        RULE_TYPE=rule["Action"],
                        PRIORITY="-",
                        PROTOCOL=rule["Protocol"].upper(),
                        PORTS=ports,
                        SOURCE=source,
                        DESTINATION=destination,
                        ACTION_TIME=action_time
                    ))

def log_account(event_name, requestParameters, responseElements, entry, project_name, AccountId, worker, action_time, loggingaccount_objects):
    if event_name in ["AddUser", "DeleteUser"]:
        uin = entry["resourceName"].split("/")[1] if event_name == "DeleteUser" else responseElements.get('Uin', '')
        name = requestParameters.get("Name") if event_name == "DeleteUser" else responseElements.get('Name', entry["resourceName"].split("/")[-1])
        account = f"{name} ({uin})" if uin else f"{name}"

        loggingaccount_objects.append(LoggingAccountInfo(
            CLOUD="TENCENT",
            PROJECT=project_name,
            PROJECT_ID=AccountId,
            WORKER=worker,
            ACTION=event_name,
            ACCOUNT=account,
            ACTION_TIME=action_time
        ))

def log_iam(client, event_name, entry, project_name, AccountId, worker, action_time, loggingiam_objects):
    if event_name in ["AttachUserPolicies", "DetachUserPolicies", "AttachUserPolicy", "DetachUserPolicy"]:
        request_parameters = json.loads(entry["requestParameters"])
        if "PolicyId" in request_parameters and isinstance(request_parameters["PolicyId"], list) and len(request_parameters["PolicyId"]) > 0:
            permission_id = int(request_parameters["PolicyId"][0])
        elif "PolicyId.0" in request_parameters:
            permission_id = int(request_parameters["PolicyId.0"])
        else:
            permission_id = int(request_parameters["PolicyId"])

        account = None
        if entry["eventName"] == "AttachUserPolicy":
            account = request_parameters.get("AttachUin")
        elif entry["eventName"] == "DetachUserPolicy":
            account = request_parameters.get("DetachUin")
        elif entry["eventName"] in ["AttachUserPolicies", "DetachUserPolicies"]:
            account = request_parameters.get("TargetUin")

        req = models.GetPolicyRequest()
        params = {
            "PolicyId": permission_id
        }
        req.from_json_string(json.dumps(params))
        resp = (client.GetPolicy(req)).to_json_string()
        data = json.loads(resp)
        policy_name = data['PolicyName']

        loggingiam_objects.append(LoggingIamInfo(
            CLOUD="TENCENT",
            PROJECT=project_name,
            PROJECT_ID=AccountId,
            WORKER=worker,
            ACTION=event_name,
            PERMISSION=policy_name,
            ACCOUNT=account,
            ACTION_TIME=action_time
        ))

def log_key(event_name, responseElements, entry, project_name, AccountId, worker, action_time, loggingkey_objects):
    if event_name in ["CreateApiKey", "DeleteApiKey"]:
        account = entry['resourceName'].split("/")[-1]
        secret_id = responseElements.get('IdKeys', [{}])[0].get('SecretId', '-')

        loggingkey_objects.append(LoggingKeyInfo(
            CLOUD="TENCENT",
            PROJECT=project_name,
            PROJECT_ID=AccountId,
            WORKER=worker,
            ACTION=event_name,
            ACCOUNT=account,
            ACCESS_KEY=secret_id,
            ACTION_TIME=action_time
        ))

def log_instance(entry, requestParameters, responseElements, project_name, AccountId, worker, event_name, action_time, logginginstance_objects):
    resource_region = entry["resourceSet"][0]["resourceRegion"] if "resourceSet" in entry else "-"
    REGION = resource_region if resource_region else "-"
    AZ = "-"
    INSTANCE_TYPE = "-"
    INSTANCE = "-"
    NETWORK = "-"

    if event_name in ["RunInstances", "TerminateInstances"]:
        AZ = requestParameters['Placement']['Zone'] if event_name == 'RunInstances' else "-"
        INSTANCE_TYPE = requestParameters['InstanceType'] if event_name == 'RunInstances' else "-"
        INSTANCE = (
            f"{requestParameters.get('InstanceName', '')} ({responseElements['InstanceIdSet'][0]})"
            if event_name == 'RunInstances' and requestParameters.get('InstanceName', '')
            else responseElements['InstanceIdSet'][0] if event_name == 'RunInstances'
            else entry['resourceName'].split("/")[-1]
        )
        NETWORK = f"{requestParameters['VirtualPrivateCloud']['VpcId']} / {requestParameters['VirtualPrivateCloud']['SubnetId']}" if event_name == 'RunInstances' else "-"
    elif event_name == "ResetInstancesType":
        INSTANCE_TYPE = requestParameters['InstanceType']
        INSTANCE = entry['resourceName'].split("/")[-1]
    elif event_name in ["StartInstances", "StopInstances"]:
        INSTANCE = "\n".join([resource['resourceId'] for resource in entry['resourceSet']])
        REGION = "\n".join([resource['resourceRegion'] if resource['resourceRegion'] else "-" for resource in entry['resourceSet']])
    elif event_name in ["ResizeDisk"]:
        disk_size = f"=> {requestParameters['DiskSize']}GB"
        disk_id = requestParameters['DiskId']
        INSTANCE_TYPE = disk_size
        INSTANCE = disk_id
    logginginstance_objects.append(LoggingInstanceInfo(
        CLOUD="TENCENT",
        PROJECT=project_name,
        PROJECT_ID=AccountId,
        WORKER=worker,
        ACTION=event_name,
        REGION=REGION,
        AZ=AZ,
        INSTANCE_TYPE=INSTANCE_TYPE,
        INSTANCE=INSTANCE,
        NETWORK=NETWORK,
        ACTION_TIME=action_time
    ))

def process_cos_data(cos_client, Bucket, prefix):
    all_formatted_json_list = []
    cos_response = cos_client.list_objects(Bucket=Bucket, Prefix=prefix)
    if 'Contents' in cos_response:
        for item in cos_response['Contents']:
            object_response = cos_client.get_object(Bucket=Bucket, Key=item['Key'])
            stream = io.BytesIO(object_response['Body'].read(20000000))
            text = stream.getvalue().decode('utf-8')
            json_lines = text.strip().split('\n')
            all_formatted_json_list.extend([json.dumps(json.loads(line), indent=4, ensure_ascii=False) for line in json_lines])
    return all_formatted_json_list

def fetch_logging_events(credentials, project_name, AccountId, Bucket, region, loggingfirewall_objects, loggingaccount_objects, loggingiam_objects, loggingkey_objects, logginginstance_objects, role_arn=None):
    if role_arn:
        cred = credential.STSAssumeRoleCredential(
            credentials['secret_id'],
            credentials['secret_key'],
            role_arn,
            "sts-session",
            7200
        )
        cos_secret_id = cred.secret_id
        cos_secret_key = cred.secret_key
        cos_token = cred.token
    else:
        cred = credential.Credential(
            credentials['secret_id'],
            credentials['secret_key']
        )
        cos_secret_id = credentials['secret_id']
        cos_secret_key = credentials['secret_key']
        cos_token = None

    httpProfile = HttpProfile()
    httpProfile.endpoint = "cam.intl.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = cam_client.CamClient(cred, "", clientProfile)

    now = datetime.now()
    year, month = now.year, now.month - 1
    if month == 0:
        year -= 1
        month = 12
    prefixes = [
        f"vpc/vpc_trackingset/{year}/{month}",
        f"cam/iam_trackingset/{year}/{month}",
        f"cvm/vm_trackingset/{year}/{month}",
        f"disk/disk_trackingset/{year}/{month}"
    ]

    config = CosConfig(
        Region=region,
        SecretId=cos_secret_id,
        SecretKey=cos_secret_key,
        Token=cos_token,
        Scheme="https"
    )
    cos_client = CosS3Client(config)

    all_formatted_json_list = []
    for prefix in prefixes:
        all_formatted_json_list.extend(process_cos_data(cos_client, Bucket, prefix))

    data = '[\n' + ',\n'.join(all_formatted_json_list) + '\n]'
    data_list = json.loads(data)

    for entry in data_list:
        requestParameters = json.loads(entry["requestParameters"])
        responseElements = json.loads(entry["responseElements"])
        eventType = entry['eventType']
        user_identity = entry['userIdentity']
        event_name = entry['eventName']

        if eventType == 'ConsoleCall':
            extra_info = json.loads(json.loads(user_identity['sessionContext'])['extraInfo'])
            worker = f"{extra_info['roleSessionName']} ({extra_info['roleName']} / {extra_info['assumerOwnerUin']})" if extra_info.get('roleSessionName') else f"{entry['userIdentity']['userName']} ({entry['userIdentity']['principalId']})"
        elif eventType == 'ApiCall':
            worker = f"{entry['userIdentity']['userName']} ({entry['userIdentity']['principalId']})"
        else:
            continue
        if len(entry['apiErrorMessage']) > 0 or (len(requestParameters) == 0 and len(responseElements) == 0):
            continue

        if worker.startswith("eks-") or "AutoScaling" in worker or worker.startswith("databricks"):
            continue

        utc_time = datetime.fromtimestamp(entry["eventTime"], timezone.utc)
        action_time = utc_time.astimezone(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')

        if event_name in ["CreateSecurityGroupPolicies", "DeleteSecurityGroupPolicies", "ReplaceSecurityGroupPolicies", "ModifySecurityGroupPolicies"]:
            log_firewall(event_name, requestParameters, entry, project_name, AccountId, worker, action_time, loggingfirewall_objects)
        elif event_name in ["AddUser", "DeleteUser"]:
            log_account(event_name, requestParameters, responseElements, entry, project_name, AccountId, worker, action_time, loggingaccount_objects)
        elif event_name in ["AttachUserPolicies", "DetachUserPolicies", "AttachUserPolicy", "DetachUserPolicy"]:
            log_iam(client, event_name, entry, project_name, AccountId, worker, action_time, loggingiam_objects)
        elif event_name in ["CreateApiKey", "DeleteApiKey"]:
            log_key(event_name, responseElements, entry, project_name, AccountId, worker, action_time, loggingkey_objects)
        elif event_name in ["RunInstances", "TerminateInstances"]:
            log_instance(entry, requestParameters, responseElements, project_name, AccountId, worker, event_name, action_time, logginginstance_objects)
        elif event_name in ["ResetInstancesType"]:
            log_instance(entry, requestParameters, {}, project_name, AccountId, worker, event_name, action_time, logginginstance_objects)
        elif event_name in ["StartInstances", "StopInstances"]:
            log_instance(entry, {}, {}, project_name, AccountId, worker, event_name, action_time, logginginstance_objects)
        elif event_name in ["ResizeDisk"]:
            log_instance(entry, requestParameters, responseElements, project_name, AccountId, worker, event_name, action_time, logginginstance_objects)

def main():
    print(f"{UNDERLINE}<TENCENT>{RESET}")

    tencent_cred_file_list_path = '../auth/cred_tencent.json'
    profile_manager = ProfileManager(tencent_cred_file_list_path)
    credentials = profile_manager.load_credentials()
    main_account = credentials["main_account"]
    projects = credentials["projects"][0]
    region = 'ap-seoul'

    loggingfirewall_objects = []
    loggingaccount_objects  = []
    loggingiam_objects      = []
    loggingkey_objects      = []
    logginginstance_objects = []

    # main_account
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    fetch_logging_events(
        main_account,
        main_account['AccountName'],
        main_account['AccountId'],
        main_account['Bucket'],
        region,
        loggingfirewall_objects,
        loggingaccount_objects,
        loggingiam_objects,
        loggingkey_objects,
        logginginstance_objects
    )

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

        fetch_logging_events(
            credentials_proj,
            project_name,
            project_info['AccountId'],
            project_info['Bucket'],
            region,
            loggingfirewall_objects,
            loggingaccount_objects,
            loggingiam_objects,
            loggingkey_objects,
            logginginstance_objects,
            role_arn=role_arn
        )

    loggingfirewall_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingaccount_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingiam_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    loggingkey_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))
    logginginstance_objects.sort(key=lambda x: (x.PROJECT, x.ACTION_TIME))

    return loggingfirewall_objects, loggingaccount_objects, loggingiam_objects, loggingkey_objects, logginginstance_objects

if __name__ == "__main__":
    main()
