import boto3
import os
import pytz
import re
import json
import csv
import io
import time
from datetime import datetime
from dateutil import parser

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

def get_group_info(client):
    group_info_list = []
    group_list = client.list_groups()

    for group in group_list['Groups']:
        user_group = client.get_group(GroupName=group['GroupName'])
        group_permission = client.list_attached_group_policies(GroupName=group['GroupName'])

        group_info = {
            'GroupName': group['GroupName'],
            'Users': [],
            'Permissions': []
        }

        for user in user_group['Users']:
            user_info = {
                'UserName': user['UserName'],
                'UserId': user['UserId']
            }
            group_info['Users'].append(user_info)

        for policy in group_permission['AttachedPolicies']:
            policy_info = policy['PolicyName']
            group_info['Permissions'].append(policy_info)

        group_info_list.append(group_info)

    return group_info_list

def get_user_group_mapping(client, group_info_list):
    user_group_mapping = {}
    users = client.list_users()

    for user in users['Users']:
        user_group_mapping[user['UserId']] = []

        for group_info in group_info_list:
            for user_info in group_info['Users']:
                if user_info['UserId'] == user['UserId']:
                    user_group_mapping[user['UserId']].append(group_info['GroupName'])

    return user_group_mapping

def get_user_permissions(client, user, group_info_list):
    user_permissions = {}

    managed_permission = client.list_user_policies(UserName=user['UserName'])
    inline_permission = client.list_attached_user_policies(UserName=user['UserName'])['AttachedPolicies']

    managed_policy_names = "\n".join([policy['PolicyName'] for policy in managed_permission.get('Policies', [])]) if managed_permission else ""
    inline_policy_names = "\n".join([policy['PolicyName'] for policy in inline_permission]) if inline_permission else ""

    group_permissions = []
    for group_info in group_info_list:
        if user['UserId'] in [user_info['UserId'] for user_info in group_info['Users']]:
            group_permissions.extend(group_info['Permissions'])

    all_permissions = managed_policy_names + "\n" + inline_policy_names + "\n" + "\n".join(group_permissions)
    all_permissions = all_permissions.strip()

    user_permissions[user['UserName']] = all_permissions if all_permissions else "-"
    return user_permissions

def get_access_keys(client, user, kst):
    access_key_ids = []
    key_creation_times = []
    access_keys = client.list_access_keys(UserName=user['UserName'])

    if access_keys['AccessKeyMetadata']:
        for access_key in access_keys['AccessKeyMetadata']:
            access_key_ids.append(access_key['AccessKeyId'])
            key_created_time_kst = access_key['CreateDate'].replace(tzinfo=pytz.UTC).astimezone(kst)
            key_creation_times.append(key_created_time_kst.strftime('%Y-%m-%d %H:%M:%S'))
    else:
        access_key_ids.append("-")
        key_creation_times.append("-")

    return "\n".join(access_key_ids), "\n".join(key_creation_times)

def get_credential_report_dict(client, max_wait_sec=30):
    # 자격 증명 보고서 생성 요청 및 폴링
    client.generate_credential_report()
    waited = 0
    while True:
        try:
            report = client.get_credential_report()
            break
        except client.exceptions.CredentialReportNotReadyException:
            time.sleep(2)
            waited += 2
            if waited > max_wait_sec:
                raise Exception("Credential report generation timed out")
    report_csv = report['Content'].decode('utf-8')
    reader = csv.DictReader(io.StringIO(report_csv))
    report_dict = {}
    for row in reader:
        report_dict[row['user']] = row
    return report_dict

def get_last_login_and_password_changed(user, kst, credential_report_dict):
    last_login = "-"
    if 'PasswordLastUsed' in user and user['PasswordLastUsed']:
        last_login_kst = user['PasswordLastUsed'].replace(tzinfo=pytz.UTC).astimezone(kst)
        last_login = last_login_kst.strftime('%Y-%m-%d %H:%M:%S')

    password_last_changed = "-"
    row = credential_report_dict.get(user['UserName'])
    if row:
        pwd_changed = row.get('password_last_changed')
        if pwd_changed and pwd_changed != 'N/A':
            dt = parser.isoparse(pwd_changed)
            password_last_changed = dt.astimezone(kst).strftime('%Y-%m-%d %H:%M:%S')
    return last_login, password_last_changed


def main():
    print(f"{UNDERLINE}<AWS>{RESET}")

    kst = pytz.timezone('Asia/Seoul')

    cred_json_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_aws.json'
    cred_manager = CredentialManager(cred_json_path)
    project_names = cred_manager.get_projects()

    iam_objects = []

    for project_name in project_names:
        print(f"{ORANGE}{project_name}{RESET}")

        account_id = cred_manager.get_account_id(project_name)
        role_arn = cred_manager.get_role_arn(account_id)

        try:
            credentials = assume_role(role_arn, session_name=project_name)
        except Exception as e:
            print(f"{RED}AssumeRole failed for {project_name}: {e}{RESET}")
            continue

        session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
        client = session.client("iam")

        group_info_list = get_group_info(client)
        user_group_mapping = get_user_group_mapping(client, group_info_list)
        credential_report_dict = get_credential_report_dict(client)

        users = client.list_users()
        for user in users['Users']:
            user_created_time_utc = user['CreateDate']
            user_created_time_kst = user_created_time_utc.replace(tzinfo=pytz.UTC).astimezone(kst)
            USER_CREATION_TIME = user_created_time_kst.strftime('%Y-%m-%d %H:%M:%S')

            user_in_groups = "\n".join(user_group_mapping.get(user['UserId'], ["-"]))
            user_permissions = get_user_permissions(client, user, group_info_list)
            access_key_ids_str, key_creation_times_str = get_access_keys(client, user, kst)

            last_login, password_last_changed = get_last_login_and_password_changed(user, kst, credential_report_dict)

            iam_info = IamInfo(
                CLOUD="AWS",
                PROJECT=project_name,
                PROJECT_ID=user['Arn'].split(":")[-2],
                USER_NAME=user['UserName'],
                USER_ID=user['UserId'],
                USER_GROUP=user_in_groups,
                PERMISSION=list(set(user_permissions.values())),
                USER_CREATION_TIME=USER_CREATION_TIME,
                ACCESS_KEY=access_key_ids_str,
                ACCESS_KEY_CREATION_TIME=key_creation_times_str,
                LAST_LOGIN=last_login,
                PASSWORD_LAST_CHANGED=password_last_changed
            )
            iam_objects.append(iam_info)

        iam_objects.sort(key=lambda x: (x.PROJECT, x.USER_NAME))

    return iam_objects


if __name__ == "__main__":
    main()
