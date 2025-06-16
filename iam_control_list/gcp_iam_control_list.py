import json
import os
import pytz
import datetime
import re
from google.oauth2 import service_account
from google.cloud import resourcemanager_v3
from google.cloud import iam_admin_v1
from google.cloud.iam_admin_v1 import types
from google.iam.v1 import iam_policy_pb2
from google.api_core.exceptions import NotFound
from google.auth import impersonated_credentials

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class IamInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, USER_NAME, USER_ID, USER_GROUP, PERMISSION, USER_CREATION_TIME, ACCESS_KEY, ACCESS_KEY_CREATION_TIME, LAST_LOGIN, PASSWORD_LAST_CHANGED):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.USER_NAME = USER_NAME
        self.USER_ID = USER_ID
        self.USER_GROUP = USER_GROUP if USER_GROUP else "-"
        self.PERMISSION = PERMISSION if PERMISSION else "-"
        self.USER_CREATION_TIME = USER_CREATION_TIME
        self.ACCESS_KEY = ACCESS_KEY if ACCESS_KEY else "-"
        self.ACCESS_KEY_CREATION_TIME = ACCESS_KEY_CREATION_TIME if ACCESS_KEY_CREATION_TIME else "-"
        self.LAST_LOGIN = LAST_LOGIN if LAST_LOGIN else "-"
        self.PASSWORD_LAST_CHANGED = PASSWORD_LAST_CHANGED if PASSWORD_LAST_CHANGED else "-"

    def __repr__(self):
        return (f"IamInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"USER_NAME={self.USER_NAME}, "
                f"USER_ID={self.USER_ID}, "
                f"USER_GROUP={self.USER_GROUP}, "
                f"PERMISSION={self.PERMISSION}, "        
                f"USER_CREATION_TIME={self.USER_CREATION_TIME}, "
                f"ACCESS_KEY={self.ACCESS_KEY}, "
                f"ACCESS_KEY_CREATION_TIME={self.ACCESS_KEY_CREATION_TIME}, "
                f"LAST_LOGIN={self.LAST_LOGIN}, "
                f"PASSWORD_LAST_CHANGED={self.PASSWORD_LAST_CHANGED})")

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

def get_iam_policy_and_roles(client, project_name):
    request = iam_policy_pb2.GetIamPolicyRequest()
    request.resource = f"projects/{project_name}"
    policy = client.get_iam_policy(request)

    unique_members = set()
    role_mapping = {}

    for binding in policy.bindings:
        for member in binding.members:
            unique_members.add(member)

            if member not in role_mapping:
                role_mapping[member] = []
            role_mapping[member].append(binding.role)
    return role_mapping

def get_service_accounts(project_name, credentials):
    iam_admin_client = iam_admin_v1.IAMClient(credentials=credentials)
    request = iam_admin_v1.ListServiceAccountsRequest(
        name=f"projects/{project_name}",
    )
    response = iam_admin_client.list_service_accounts(request=request)
    return [sa.email for sa in response.accounts]

def serviceaccount_key_info(project_name, user_name, kst, credentials):
    keys = []
    keys_createtime = []

    iam_admin_client = iam_admin_v1.IAMClient(credentials=credentials)

    sa_key_request = types.ListServiceAccountKeysRequest()
    sa_key_request.name = f"projects/{project_name}/serviceAccounts/{user_name}"

    try:
        sa_key_response = iam_admin_client.list_service_account_keys(request=sa_key_request)
        for sa_keys in sa_key_response.keys:
            if sa_keys.key_type == 1:  # 1 = "USER_MANAGED", 2 = SYSTEM_MANAGED
                keys.append((sa_keys.name).split("/")[-1])

                dt_utc = datetime.datetime.fromtimestamp(sa_keys.valid_after_time.timestamp(), tz=datetime.timezone.utc)
                dt_korea = dt_utc.replace(tzinfo=pytz.utc).astimezone(kst)
                formatted_time = dt_korea.strftime('%Y-%m-%d %H:%M:%S')
                keys_createtime.append(formatted_time)
            else:
                pass
    except NotFound:
        pass

    return keys, keys_createtime


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

    iam_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        client = resourcemanager_v3.ProjectsClient(credentials=credentials)
        role_mapping = get_iam_policy_and_roles(client, project_name)

        role_mapping_dict = {
            "712": "role_monitor",
            "763": "role_terraform",
            "549": "role_Billing_Viewer",
            "386": "serviceusage",
            "821": "role_cloud_bucket"
        }

        service_accounts = get_service_accounts(project_name, credentials)

        for member in role_mapping.keys():
            user_name = member.split(":")[-1]
            if (
                    not re.match(r'^\d', user_name)
                    and not user_name.startswith('service-')
                    and 'appspot.gserviceaccount.com' not in user_name
            ):
                user_type = member.split(":")[0]
                permissions = [role_mapping_dict.get(role.split("/")[-1], role.split("/")[-1]) for role in role_mapping[member]]
                permissions = '\n'.join(permissions)

                keys = None
                keys_createtime = None

                if user_type == "serviceAccount":
                    keys, keys_createtime = serviceaccount_key_info(project_name, user_name, kst, credentials)

                access_keys = '\n'.join(keys) if keys else "-"
                access_keys_creation = '\n'.join(keys_createtime) if keys_createtime else "-"

                iam_info = IamInfo(
                    CLOUD="GCP",
                    PROJECT=project_display_name,
                    PROJECT_ID=project_name,
                    USER_NAME=user_name,
                    USER_ID="-",
                    USER_GROUP="",
                    PERMISSION=permissions,
                    USER_CREATION_TIME="-",
                    ACCESS_KEY=access_keys,
                    ACCESS_KEY_CREATION_TIME=access_keys_creation,
                    LAST_LOGIN="-",
                    PASSWORD_LAST_CHANGED="-"
                )
                iam_objects.append(iam_info)

        for sa_email in service_accounts:
            if sa_email not in [member.split(":")[-1] for member in role_mapping.keys()]:
                if (
                        not re.match(r'^\d', sa_email)
                        and not sa_email.startswith('service-')
                        and 'appspot.gserviceaccount.com' not in sa_email
                ):

                    user_name = sa_email
                    permissions = "-"
                    keys, keys_createtime = serviceaccount_key_info(project_name, user_name, kst, credentials)
                    access_keys = '\n'.join(keys) if keys else "-"
                    access_keys_creation = '\n'.join(keys_createtime) if keys_createtime else "-"

                    iam_info = IamInfo(
                        CLOUD="GCP",
                        PROJECT=project_display_name,
                        PROJECT_ID=project_name,
                        USER_NAME=user_name,
                        USER_ID="-",
                        USER_GROUP="",
                        PERMISSION=permissions,
                        USER_CREATION_TIME="-",
                        ACCESS_KEY=access_keys,
                        ACCESS_KEY_CREATION_TIME=access_keys_creation,
                        LAST_LOGIN="-",
                        PASSWORD_LAST_CHANGED="-"
                    )
                    iam_objects.append(iam_info)

    iam_objects.sort(key=lambda x: (x.PROJECT, x.USER_NAME))
    return iam_objects


if __name__ == "__main__":
    main()
