# ~/.bashrc
# alias gcpimg='/game/terraform.git/com2us/0.powershell/python/.venv/bin/python3 /game/terraform.git/com2us/0.powershell/python/imgshot_control/gcp_imgshot_control.py'
# source ~/.bashrc
from __future__ import annotations
import json
import os
import sys
import concurrent.futures
from google.oauth2 import service_account
from google.cloud import compute_v1
from google.auth import impersonated_credentials

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


# /game/terraform.git/com2us/0.powershell/python/.venv/bin/python3 /game/terraform.git/com2us/0.powershell/python/imgshot_control/gcp_imgshot_control.py project_1 europe-west1-b techgcp-live-belgium-01 techgcp-live-belgium-01-data-8
# gcpsnap project_1 europe-west1-b techgcp-live-belgium-01 techgcp-live-belgium-01-data-8
# gcpsnap project_1 europe-west1-b img-techgcp-live-belgium-01 img-techgcp-live-belgium-01-data-8

project_name = sys.argv[1]
zone = sys.argv[2]
source = sys.argv[3:]

print()
print(f"{YELLOW}Project Name : {BLUE}{project_name}{RESET}")
print(f"{YELLOW}Region : {BLUE}{zone}{RESET}")
print(f"{YELLOW}Source : {BLUE}{', '.join(source)}{RESET}")


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

def create_image(credentials, zone, source_disk, image_name):
    try:
        disk_client = compute_v1.DisksClient(credentials=credentials)
        image_client = compute_v1.ImagesClient(credentials=credentials)

        disk = disk_client.get(project=GCP_PROFILE, zone=zone, disk=source_disk)

        image = compute_v1.Image()
        image.name = image_name
        image.source_disk = disk.self_link

        operation = image_client.insert(
            compute_v1.InsertImageRequest(
                project=GCP_PROFILE,
                image_resource=image,
                force_create=True
            )
        )

        operation.result()
        print(f'{GREEN}...succeed work!{RESET}')
        print(f'Image ID: {BLUE}{image_name}{RESET}')

    except Exception as e:
        print(f'{RED}Error creating image for volume {source_disk}: {e}{RESET}')

def delete_image(credentials, image_name):
    try:
        image_client = compute_v1.ImagesClient(credentials=credentials)
        operation = image_client.delete(project=GCP_PROFILE, image=image_name)
        operation.result()  # Wait for the operation to complete
        print(f'{GREEN}Successfully deleted image: {BLUE}{image_name}{RESET}')
    except Exception as e:
        print(f'{RED}Error deleting image {image_name}: {e}{RESET}')


gcp_cred_file_path = '/Users/ihanni/Desktop/my_empty/my_drive/pycharm/python_project/auth/cred_gcp.json'

profile_manager = ProfileManager(gcp_cred_file_path)

source_credentials = service_account.Credentials.from_service_account_info(
    profile_manager.service_account_key,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
project_names = profile_manager.projects

if project_name not in project_names:
    print(
        f"{RED}Error: Project name '{project_name}' is not valid. Available projects: {', '.join(project_names)}{RESET}")
    sys.exit(1)


GCP_PROFILE = project_name

if project_name == "project_1":
    credentials = source_credentials
else:
    target_sa = f"terraform@{GCP_PROFILE}.iam.gserviceaccount.com"
    credentials = get_impersonated_credentials(source_credentials, target_sa)

action = input(f"{ORANGE}Do you want to create or delete images? ({GREEN}c{ORANGE} for create, {RED}dd{ORANGE} for delete): {RESET}").strip().lower()

if action in ['c', 'create']:
    confirmation = input(
        f"{GREEN}Are you sure about {BLUE}{', '.join(source)}{GREEN} volumes? {RESET}({YELLOW}yes{RESET}/{RED}no{RESET}): ").strip().lower()

    if confirmation == 'yes':
        default_image_name = [f'img-{disk}' for disk in source]
        print(f"{GREEN}Default image names: \n{BLUE}{', '.join(default_image_name)}{RESET}")

        use_default = input(f"{GREEN}Do you want to use this name? ({YELLOW}yes{RESET}/{RED}no{GREEN}): {RESET}").strip().lower()

        if use_default == 'yes':
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(create_image, credentials, zone, source_disk, f'img-{source_disk}'): source_disk for source_disk in source}
                for future in concurrent.futures.as_completed(futures):
                    future.result()

        elif use_default == 'no':
            custom_image_names = input(f"{GREEN}Enter image names for disks {BLUE}{', '.join(source)}{GREEN} (comma-separated): {RESET}").strip()
            custom_image_names_list = [name.strip() for name in custom_image_names.split(',')]
            if len(custom_image_names_list) != len(source):
                print(f"{RED}Error: You must provide exactly {len(source)} names.{RESET}")

            else:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {
                        executor.submit(create_image, credentials, zone, source_disk, custom_image_name): source_disk
                        for source_disk, custom_image_name in zip(source, custom_image_names_list)}
                    for future in concurrent.futures.as_completed(futures):
                        future.result()

    elif confirmation == 'no':
        print(f"{ORANGE}Operation cancelled.{RESET}")

    else:
        print(f"{ORANGE}Invalid input. Please enter 'yes' or 'no'.{RESET}")

elif action in ['dd', 'delete']:
    confirmation = input(
        f"{GREEN}Are you sure you want to delete the following images: {BLUE}{', '.join(source)}{GREEN}? {RESET}({YELLOW}yes{RESET}/{RED}no{GREEN}): ").strip().lower()

    if confirmation == 'yes':
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(delete_image, credentials, image_name): image_name for image_name in source}
            for future in concurrent.futures.as_completed(futures):
                future.result()

    elif confirmation == 'no':
        print(f"{ORANGE}Operation cancelled.{RESET}")

    else:
        print(f"{ORANGE}Invalid input. Please enter 'yes' or 'no'.{RESET}")

else:
    print(f"{RED}Invalid action. Please enter 'c' for create or 'dd' for delete.{RESET}")
