# python version < 3.13
# pip3 install google-cloud-container
# The service account requires "Kubernetes Engine Admin" permission.
import json
import os
from google.cloud import container_v1
from google.oauth2 import service_account
from datetime import datetime, timedelta, timezone
from google.api_core.exceptions import PermissionDenied
from google.auth import impersonated_credentials


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class GKEClusterManager:
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = container_v1.ClusterManagerClient(credentials=self.credentials)

    def set_maintenance_policy(self, project_id, location, cluster_name):
        cluster_full_name = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
        current_version = self.client.get_cluster(name=cluster_full_name).maintenance_policy.resource_version

        today = datetime.now(timezone.utc)
        start_time = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = (today + timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

        maintenance_policy = container_v1.MaintenancePolicy(
            window=container_v1.MaintenanceWindow(
                recurring_window=container_v1.RecurringTimeWindow(
                    window=container_v1.TimeWindow(
                        start_time="1970-01-01T18:00:00Z",
                        end_time="1970-01-02T00:00:00Z"
                    ),
                    recurrence="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
                ),
                maintenance_exclusions={
                    "service stabilization": container_v1.TimeWindow(
                        start_time=start_time,
                        end_time=end_time
                    )
                }
            ),
            resource_version=current_version
        )

        response = self.client.set_maintenance_policy(
            request=container_v1.SetMaintenancePolicyRequest(
                name=cluster_full_name,
                maintenance_policy=maintenance_policy
            )
        )

        print(response)

    def list_clusters(self, project_name, region):
        parent = f"projects/{project_name}/locations/{region}"
        try:
            clusters = self.client.list_clusters(parent=parent)
            return clusters.clusters
        except PermissionDenied as e:
            if "IAM_PERMISSION_DENIED" in str(e):
                print("IAM_PERMISSION_DENIED. Continue...")
                return []
            else:
                raise

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


def main():
    target_clusters_list_path = './target_clusters.json'
    gcp_cred_file_path = '../auth/cred_gcp.json'

    profile_manager = ProfileManager(gcp_cred_file_path)

    source_credentials = service_account.Credentials.from_service_account_info(
        profile_manager.service_account_key,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )


    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    with open(target_clusters_list_path, 'r') as target_file:
        target_clusters_data = json.load(target_file)

    for project_name, target_clusters in target_clusters_data.items():
        if project_name == "_comment":
            continue

        if project_name in profile_manager.projects:
            print(f"{UNDERLINE}{project_name}{RESET}")

            if project_name == "project_1":
                credentials = source_credentials
            else:
                target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
                credentials = get_impersonated_credentials(source_credentials, target_sa)

            gke_manager = GKEClusterManager(credentials)

            for region in region_names:
                clusters = gke_manager.list_clusters(project_name, region)
                if not clusters:
                    continue

                for cluster in clusters:
                    cluster_name = cluster.name
                    print(cluster_name)
                    if cluster_name in target_clusters:
                        gke_manager.set_maintenance_policy(project_name, region, cluster_name)
                        print(f"{YELLOW}Update..!{RESET}")
                        print()


if __name__ == "__main__":
    main()



# ----------------------------------------------------------------------------------------------

    # region = "asia-east2"
    # zone = "asia-east2-a"
    # server_config = cluster_client.get_server_config(project_id=project_name, zone=zone)
    # # print(server_config)
    #
    # channels_str = str(server_config.channels)
    #
    # stable_start = channels_str.find("channel: STABLE")
    # if stable_start != -1:
    #     stable_info = channels_str[stable_start:]
    #     stable_end = stable_info.find("channel: ", 1)
    #     if stable_end != -1:
    #         stable_info = stable_info[:stable_end]
    #     print(stable_info)




# 추가할 기능
# 1. 클러스터의 현재 버전을 불러오고, 중간버전이 2이상 차이나면 알람 발생
# End of standard support
# https://cloud.google.com/kubernetes-engine/docs/release-schedule?hl=ko#schedule-for-release-channels
# 보통 릴리즈 되고 1년3개월~1년6개월 지원함.
# gcloud container get-server-config --zone=us-central1-f --format=json | jq '.channels[] | select(.channel == "STABLE")'

# 직접 콘솔에서 눈으로 일정 주기마다 한번더 확인하는 프로세스를 가지고,
# 메인터넌스 자동 연장 후 슬랙 등으로 정상처리에 대한 알림을 보내주는 부분도 추가
