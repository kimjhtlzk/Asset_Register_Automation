# ~/.bashrc
# alias tcsnap='/game/terraform.git/com2us/0.powershell/python/.venv/bin/python3 /game/terraform.git/com2us/0.powershell/python/snapshot_control/tencent_snapshot_control.py'
# source ~/.bashrc
# tcsnap project_1-live ap-singapore disk-ccgxrgkq disk-c91qgucu disk-8mae0zws
# tcsnap project_1-live ap-singapore snap-nqzlhi6v snap-8fqmsmy9 snap-obskh2xf
import json
import sys
import concurrent.futures
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.cvm.v20170312 import cvm_client
from tencentcloud.cbs.v20170312 import cbs_client, models as cbs_models

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"

project_name = sys.argv[1]
region = sys.argv[2]
source = sys.argv[3:]

print()
print(f"{YELLOW}Project Name : {BLUE}{project_name}{RESET}")
print(f"{YELLOW}Region : {BLUE}{region}{RESET}")
print(f"{YELLOW}Source : {BLUE}{', '.join(source)}{RESET}")

def authenticate(project_name, region, credentials, main_account):
    projects_dict = credentials["projects"][0]

    if project_name == "Chinaproject_1":
        secret_id = projects_dict[project_name]['secret_id']
        secret_key = projects_dict[project_name]['secret_key']
        cred = credential.Credential(secret_id, secret_key)
        role_arn = None
    elif project_name == main_account['AccountName']:
        secret_id = main_account['secret_id']
        secret_key = main_account['secret_key']
        cred = credential.Credential(secret_id, secret_key)
        role_arn = None
    else:
        secret_id = main_account['secret_id']
        secret_key = main_account['secret_key']
        role_arn = f"qcs::cam::uin/{projects_dict[project_name]['AccountId']}:roleName/@owner"
        cred = credential.STSAssumeRoleCredential(
            secret_id, secret_key, role_arn, "sts-session", 7200
        )
    httpProfile = HttpProfile()
    httpProfile.endpoint = f"cvm.{region}.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    return cred, cvm_client.CvmClient(cred, region, clientProfile), role_arn

def create_snapshot(client, source_disk, snapshot_name):
    try:
        httpProfile = HttpProfile()
        httpProfile.endpoint = "cbs.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        cbs_client_instance = cbs_client.CbsClient(client.credential, client.region, clientProfile)

        req = cbs_models.CreateSnapshotRequest()
        params = {
            "SnapshotName": snapshot_name,
            "DiskId": source_disk
        }
        req.from_json_string(json.dumps(params))
        resp = cbs_client_instance.CreateSnapshot(req)
        response_json = json.loads(resp.to_json_string())

        snapshot_id = response_json["SnapshotId"]
        print(f'\n{GREEN}...succeed work!{RESET}')
        print(req)
        print(f'Snapshot ID: {BLUE}{snapshot_id}{RESET}')

    except Exception as e5:
        print(f'{RED}Error creating snapshot for volume {source_disk}: {e5}{RESET}')

def delete_snapshot(client, source_snap):
    try:
        httpProfile = HttpProfile()
        httpProfile.endpoint = "cbs.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        cbs_client_instance = cbs_client.CbsClient(client.credential, client.region, clientProfile)

        req = cbs_models.DeleteSnapshotsRequest()
        params = {
            "SnapshotIds": [source_snap]
        }
        req.from_json_string(json.dumps(params))
        resp = cbs_client_instance.DeleteSnapshots(req)
        print(f'\n{GREEN}Snapshot {source_snap} deleted successfully!{RESET}')

    except Exception as e5:
        print(f'{RED}Error deleting snapshot {source_snap}: {e5}{RESET}')

def main():
    tencent_cred_file_list_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_tencent.json'
    with open(tencent_cred_file_list_path, 'r') as file:
        credentials = json.load(file)
    main_account = credentials["main_account"]

    cred, client, role_arn = authenticate(project_name, region, credentials, main_account)

    action = input(f"{ORANGE}Do you want to create or delete snapshots? ({GREEN}c{ORANGE} for create, {RED}dd{ORANGE} for delete): {RESET}").strip().lower()

    if action in ['c', 'create']:
        while True:
            print()
            confirmation = input(
                f"{GREEN}Are you sure about {BLUE}{', '.join(source)}{GREEN} volumes? {RESET}({YELLOW}yes{RESET}/{RED}no{RESET}): ").strip().lower()

            if confirmation == 'yes':
                default_snapshot_name = [f'snap-{disk}' for disk in source]
                print(f"{GREEN}Default snapshot names: \n{BLUE}" + '\n'.join(default_snapshot_name) + f"{RESET}")

                print()
                use_default = input(
                    f"{GREEN}Do you want to use this name? ({YELLOW}yes{RESET}/{RED}no{GREEN}): {RESET}").strip().lower()

                if use_default == 'yes':
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {executor.submit(create_snapshot, client, source_disk, f'snap-{source_disk}'): source_disk for source_disk in source}
                        for future in concurrent.futures.as_completed(futures):
                            future.result()
                    break

                elif use_default == 'no':
                    custom_snapshot_names = input(
                        f"{GREEN}Enter snapshot names for disks {BLUE}{', '.join(source)}{GREEN} (comma-separated): {RESET}").strip()

                    custom_snapshot_names_list = [name.strip() for name in custom_snapshot_names.split(',')]

                    if len(custom_snapshot_names_list) != len(source):
                        print(f"{RED}Error: You must provide exactly {len(source)} names.{RESET}")
                    else:
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            futures = {executor.submit(create_snapshot, client, source_disk, custom_snapshot_name): source_disk for source_disk, custom_snapshot_name in zip(source, custom_snapshot_names_list)}
                            for future in concurrent.futures.as_completed(futures):
                                future.result()  # 결과를 기다림
                        break

                else:
                    print(f"{ORANGE}Invalid input. Please enter '{YELLOW}yes{ORANGE}' or '{RED}no{ORANGE}'.{RESET}")

            elif confirmation == 'no':
                break

            else:
                print(f"{ORANGE}Invalid input. Please enter 'yes', 'no'.{RESET}")

    elif action in ['dd', 'delete']:
        while True:
            print()
            confirmation = input(
                f"{GREEN}Are you sure you want to delete the following snapshots: {BLUE}{', '.join(source)}{GREEN}? {RESET}({YELLOW}yes{RESET}/{RED}no{GREEN}): ").strip().lower()

            if confirmation == 'yes':
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(delete_snapshot, client, source_snap): source_snap for source_snap in source}
                    for future in concurrent.futures.as_completed(futures):
                        future.result()
                break

            elif confirmation == 'no':
                break

            else:
                print(f"{ORANGE}Invalid input. Please enter 'yes', 'no'.{RESET}")

    else:
        print(f"{RED}Invalid action. Please enter 'c' for create or 'dd' for delete.{RESET}")

if __name__ == "__main__":
    main()
