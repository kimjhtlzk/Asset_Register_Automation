import json
import os
import pytz
import datetime
from google.oauth2 import service_account
from google.cloud import resourcemanager_v3
from google.cloud import compute_v1
from google.auth import impersonated_credentials


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class FirewallInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, SECURITY_GROUP, SECURITY_GROUP_ID, DIRECTION, ACTION, SOURCE, DESTINATION, PROTOCOL, PORTS, PRIORITY, TAGS, VPC, CREATION_TIME ):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.SECURITY_GROUP = SECURITY_GROUP
        self.SECURITY_GROUP_ID = SECURITY_GROUP_ID
        self.DIRECTION = DIRECTION
        self.ACTION = ACTION
        self.SOURCE = SOURCE
        self.DESTINATION = DESTINATION
        self.PROTOCOL = PROTOCOL
        self.PORTS = PORTS
        self.PRIORITY = PRIORITY
        self.TAGS = TAGS
        self.VPC = VPC
        # self.TARGET = TARGET
        self.CREATION_TIME = CREATION_TIME


    def __repr__(self):
        return (f"FirewallInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"SECURITY_GROUP={self.SECURITY_GROUP}, "
                f"SECURITY_GROUP_ID={self.SECURITY_GROUP_ID}, "
                f"DIRECTION={self.DIRECTION}, "
                f"ACTION={self.ACTION}, "
                f"SOURCE={self.SOURCE}, "        
                f"DESTINATION={self.DESTINATION}, "
                f"PROTOCOL={self.PROTOCOL}, "
                f"PORTS={self.PORTS}, "
                f"PRIORITY={self.PRIORITY}, "
                f"TAGS={self.TAGS}, "        
                f"VPC={self.VPC}, "
                # f"TARGET={self.TARGET}, "
                f"CREATION_TIME={self.CREATION_TIME})")

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

class FirewallHandler:
    def __init__(self, project_display_name, project_name, kst):
        self.project_display_name = project_display_name
        self.project_name = project_name
        self.kst = kst
        self.firewall_objects = []

    def create_firewall_info(self, firewall, action, source_ranges, destination_ranges, protocol, ports, creation_time):
        security_group = firewall.name
        security_group_id = str(firewall.id)
        tags = "\n".join(firewall.target_tags) if firewall.target_tags else "-"

        if not (security_group.startswith("default-") or security_group.startswith("blacklist-")):
            return FirewallInfo(
                CLOUD="GCP",
                PROJECT=self.project_display_name,
                PROJECT_ID=self.project_name,
                SECURITY_GROUP=security_group,
                SECURITY_GROUP_ID=security_group_id,
                DIRECTION=firewall.direction,
                ACTION=action,
                SOURCE=source_ranges,
                DESTINATION=destination_ranges,
                PROTOCOL=protocol,
                PORTS=ports,
                PRIORITY=firewall.priority,
                TAGS=tags,
                VPC=firewall.network.split("/")[-1],
                # TARGET="-",
                CREATION_TIME=creation_time
            )
        return None

    def handle_firewall_rules(self, firewall):
        source_ranges = "\n".join(firewall.source_ranges) if firewall.source_ranges else "-"
        destination_ranges = "\n".join(firewall.destination_ranges) if firewall.destination_ranges else "-"

        if firewall.allowed:
            for allowed in firewall.allowed:
                allow_protocol = allowed.I_p_protocol
                allow_ports = "\n".join(allowed.ports) if allowed.ports else "-"
                creation_time = self.get_creation_time(firewall)
                firewall_info = self.create_firewall_info(firewall, "allow", source_ranges, destination_ranges, allow_protocol, allow_ports, creation_time)
                if firewall_info:
                    self.firewall_objects.append(firewall_info)

        if firewall.denied:
            for denied in firewall.denied:
                deny_protocol = denied.I_p_protocol
                deny_ports = "\n".join(denied.ports) if denied.ports else "-"
                creation_time = self.get_creation_time(firewall)
                firewall_info = self.create_firewall_info(firewall, "deny", source_ranges, destination_ranges, deny_protocol, deny_ports, creation_time)
                if firewall_info:
                    self.firewall_objects.append(firewall_info)

    def get_creation_time(self, firewall):
        if isinstance(firewall.creation_timestamp, str):
            creation_timestamp = datetime.datetime.fromisoformat(firewall.creation_timestamp.replace("Z", "+00:00"))
        else:
            creation_timestamp = firewall.creation_timestamp

        dt_utc = creation_timestamp.replace(tzinfo=datetime.timezone.utc)
        dt_korea = dt_utc.astimezone(self.kst)
        return dt_korea.strftime('%Y-%m-%d %H:%M:%S')


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

    firewalls_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        firewall_client = compute_v1.FirewallsClient(credentials=credentials)
        firewall_request = compute_v1.ListFirewallsRequest(
            project=project_name,
        )
        firewalls = firewall_client.list(request=firewall_request)

        firewall_handler = FirewallHandler(project_display_name, project_name, kst)

        for firewall in firewalls:
            firewall_handler.handle_firewall_rules(firewall)

        if firewall_handler.firewall_objects:
            firewall_handler.firewall_objects.sort(
                key=lambda x: (x.PROJECT, x.VPC, x.SECURITY_GROUP, x.DIRECTION, x.ACTION)
            )
            firewalls_objects.extend(firewall_handler.firewall_objects)

    return firewalls_objects


if __name__ == "__main__":
    main()
