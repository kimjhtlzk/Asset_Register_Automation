import pytz
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cam.v20190116 import cam_client, models
from datetime import datetime

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

    def load_credentials(self):
        with open(self.cred_file_path, 'r') as file:
            return json.load(file)

class UserManager:
    def __init__(self, client):
        self.client = client

    def list_users(self):
        user_list_req = models.ListUsersRequest()
        params = {}
        user_list_req.from_json_string(json.dumps(params))
        user_list_resp = json.loads((self.client.ListUsers(user_list_req)).to_json_string())
        return user_list_resp['Data']

    def get_user_access_keys(self, user_id, kst):
        access_key_ids = []
        accesskey_create_times = []
        accesskey_req = models.ListAccessKeysRequest()
        params = {
            "TargetUin": user_id
        }
        accesskey_req.from_json_string(json.dumps(params))
        accesskey_resp = json.loads((self.client.ListAccessKeys(accesskey_req)).to_json_string())
        for access_key in accesskey_resp['AccessKeys']:
            access_key_ids.append(access_key['AccessKeyId'])
            created_time_utc = datetime.strptime(access_key['CreateTime'], '%Y-%m-%d %H:%M:%S')
            created_time_kst = (created_time_utc.astimezone(kst)).strftime('%Y-%m-%d %H:%M:%S')
            accesskey_create_times.append(created_time_kst)
        return access_key_ids, accesskey_create_times

    def get_user_groups(self, user_id):
        group_names = []
        user_group_req = models.ListGroupsForUserRequest()
        params = {
            "SubUin": user_id
        }
        user_group_req.from_json_string(json.dumps(params))
        user_group_resp = json.loads((self.client.ListGroupsForUser(user_group_req)).to_json_string())
        for group_info in user_group_resp['GroupInfo']:
            group_names.append(group_info['GroupName'])
        return group_names

    def get_user_permissions(self, user_id):
        permission_req = models.ListAttachedUserAllPoliciesRequest()
        params = {
            "TargetUin": int(user_id),
            "Page": 1,
            "Rp": 20,
            "AttachType": 0
        }
        permission_req.from_json_string(json.dumps(params))
        permission_resp = json.loads((self.client.ListAttachedUserAllPolicies(permission_req)).to_json_string())
        policy_names = [policy['PolicyName'] for policy in permission_resp['PolicyList']]
        return policy_names

    def get_user_recently_login_time(self, user_name, kst):
        get_user_req = models.GetUserRequest()
        params = {
            "Name": user_name
        }
        get_user_req.from_json_string(json.dumps(params))
        get_user_resp = json.loads((self.client.GetUser(get_user_req)).to_json_string())
        recently_login_time = get_user_resp.get('RecentlyLoginTime')
        if recently_login_time:
            try:
                recently_login_utc = datetime.strptime(recently_login_time, '%Y-%m-%d %H:%M:%S')
                recently_login_kst = recently_login_utc.astimezone(kst).strftime('%Y-%m-%d %H:%M:%S')
                return recently_login_kst
            except Exception:
                return recently_login_time
        else:
            return "-"

    def get_user_password_last_changed(self, user_id, kst):
        # 텐센트 클라우드는 패스워드 변경 시점을 API로 제공하지 않음 (공식 문서 기준)
        # 따라서 항상 "-" 반환
        return "-"

def fetch_iam_info(credentials, project_name, AccountId, firewalls_objects, role_arn=None):
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
    httpProfile.endpoint = "cam.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = cam_client.CamClient(cred, "", clientProfile)

    user_manager = UserManager(client)
    users = user_manager.list_users()

    kst = pytz.timezone('Asia/Seoul')

    for user in users:
        USER_NAME = user['Name']
        USER_ID = user['Uin']

        user_created_time_utc = datetime.strptime(user['CreateTime'], '%Y-%m-%d %H:%M:%S')
        USER_CREATION_TIME = (user_created_time_utc.astimezone(kst)).strftime('%Y-%m-%d %H:%M:%S')

        access_key_ids, accesskey_create_times = user_manager.get_user_access_keys(USER_ID, kst)
        group_names = user_manager.get_user_groups(USER_ID)
        policy_names = user_manager.get_user_permissions(USER_ID)

        # 최근 로그인 시각 (GetUser API의 RecentlyLoginTime 사용)
        LAST_LOGIN = user_manager.get_user_recently_login_time(USER_NAME, kst)

        # 패스워드 변경 시각 (API 미제공, 항상 "-")
        PASSWORD_LAST_CHANGED = user_manager.get_user_password_last_changed(USER_ID, kst)

        iam_info = IamInfo(
            CLOUD="TENCENT",
            PROJECT=project_name,
            PROJECT_ID=AccountId,
            USER_NAME=USER_NAME,
            USER_ID=USER_ID,
            USER_GROUP="\n".join(group_names),
            PERMISSION="\n".join(policy_names),
            USER_CREATION_TIME=USER_CREATION_TIME,
            ACCESS_KEY="\n".join(access_key_ids),
            ACCESS_KEY_CREATION_TIME="\n".join(accesskey_create_times),
            LAST_LOGIN=LAST_LOGIN,
            PASSWORD_LAST_CHANGED=PASSWORD_LAST_CHANGED
        )
        firewalls_objects.append(iam_info)


def main():
    print(f"{UNDERLINE}<TENCENT>{RESET}")

    tencent_cred_file_list_path = '../auth/cred_tencent.json'

    profile_manager = ProfileManager(tencent_cred_file_list_path)
    credentials = profile_manager.load_credentials()
    main_account = credentials["main_account"]
    projects = credentials["projects"][0]

    iam_objects = []

    # main_account
    print(f"{BLUE}{main_account['AccountName']}{RESET}")
    fetch_iam_info(main_account, main_account['AccountName'], main_account['AccountId'], iam_objects)

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

        fetch_iam_info(credentials, project_name, project_info['AccountId'], iam_objects, role_arn=role_arn)

    iam_objects.sort(key=lambda x: (x.PROJECT, x.USER_NAME))

    return iam_objects


if __name__ == "__main__":
    main()
