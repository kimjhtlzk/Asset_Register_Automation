📁 이 레포지터리는 아래의 <span style="color:#4F8EF7; font-weight:bold;">Tree 구조</span>를 가집니다.
<div style="background:#f8f8f8; border:1px solid #ccc; border-radius:6px; padding:16px; font-family:monospace; font-size:15px; line-height:1.5;"> <b>text</b> ├── <b>auth</b> │ ├── aws_config.txt │ ├── aws_credentials.txt │ ├── cred_aws.json │ ├── cred_gcp.json │ ├── cred_tencent.json │ └── gcp-ie3-grafana-d0e7985d808a.json ├── <b>firewall_control_list</b> │ ├── aws_firewall_control_list.py │ ├── gcp_firewall_control_list.py │ ├── head.py │ └── tencent_firewall_control_list.py ├── <b>gke_maintenance_autoupdate</b> │ ├── gke_maintenance_autoupdate.py │ └── target_clusters.json ├── <b>iam_control_list</b> │ ├── aws_iam_control_list.py │ ├── gcp_iam_control_list.py │ ├── head.py │ └── tencent_iam_control_list.py ├── <b>instance_control_list</b> │ ├── aws_instance_control_list.py │ ├── gcp_instance_control_list.py │ ├── head.py │ └── tencent_instance_control_list.py ├── <b>instance_listup_tool</b> │ ├── aws_instance_listup_tool.py │ ├── gcp_instance_listup_tool.py │ ├── head.py │ └── tencent_instance_listup_tool.py ├── <b>loadbalancer_control_list</b> │ ├── aws_loadbalancer_control_list.py │ ├── gcp_loadbalancer_control_list.py │ ├── head.py │ └── tencent_loadbalancer_control_list.py ├── <b>logging_archive</b> │ └── head.py ├── <b>logging_control_list</b> │ ├── aws_logging_control_list.py │ ├── gcp_logging_control_list.py │ ├── head.py │ └── tencent_logging_control_list.py ├── <b>snapshot_control</b> │ ├── gcp_snapshot_control.py │ └── tencent_snapshot_control.py ├── <b>unused_control_list</b> │ ├── aws_unused_control_list.py │ ├── gcp_unused_control_list.py │ ├── head.py │ └── tencent_unused_control_list.py └── <b>vpc_control_list</b> ├── aws_vpc_control_list.py ├── gcp_vpc_control_list.py ├── head.py └── tencent_vpc_control_list.py </div>
<span style="color:#4F8EF7"><b>수집된 모든 정보는 구글 스프레드 시트에 업로드됩니다.</b></span>

📂 <span style="color:#4F8EF7;">디렉터리 및 파일 설명</span>
<b style="color:#6A1B9A;">auth</b>
모든 코드의 중심이 되는 파일들로 이루어져 있으며, 각 CSP(AWS, GCP, TENCENT) 코드가 원활히 실행될 수 있도록 프로젝트 정보 또는 해당 프로젝트의 키 정보가 작성됩니다.

<b style="color:#6A1B9A;">firewall_control_list</b>
각 CSP의 방화벽 내용이 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">iam_control_list</b>
각 CSP의 IAM 계정 및 권한, 키 정보 등이 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">instance_control_list</b>
각 CSP의 인스턴스의 정보가 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">instance_listup_tool</b>
instance_control_list로 인해 업로드된 구글 스프레드 시트의 내용을 편집합니다. 특정 프로젝트의 인스턴스 정보만 갱신하고 싶을 경우 사용하도록 만들어졌습니다.

<b style="color:#6A1B9A;">loadbalancer_control_list</b>
각 CSP의 로드밸런서의 정보가 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">logging_control_list</b>
각 CSP의 방화벽, 계정 생성/삭제, 권한, 키 생성/삭제, 인스턴스 편집 등의 로그가 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">logging_archive</b>
logging_control_list로 수집된 구글 스프레드 시트의 각 시트를 백업하기 위한 용도로 만들어졌습니다. 매월 1회 실행하는 것이 적합하며, 스스로 연->월 순의 폴더를 생성하거나 찾아서 csv 파일로 백업합니다.

<b style="color:#6A1B9A;">vpc_control_list</b>
각 CSP의 VPC의 정보가 수집, 가공됩니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다.

<b style="color:#6A1B9A;">unused_control_list</b>
각 CSP의 프로젝트를 순회하며 미사용 중인 방화벽, 디스크, IP 정보 등을 수집합니다. auth 정보를 사용하며, head.py 파일이 나머지 모든 파일을 순차 실행, 취합 후 구글 스프레드 시트에 업로드합니다. 이 코드는 불필요한 비용 청구를 막기 위해 만들어졌습니다.

<b style="color:#6A1B9A;">snapshot_control</b>
각 CSP에서 원하는 프로젝트와 리전, 인스턴스를 입력하여 해당 인스턴스의 이미지(AMI)를 생성하기 위한 코드입니다. 이미지 삭제도 가능하며, 인스턴스의 모든 디스크 또는 선택적으로 고른 디스크의 이미지를 편리하게 생성합니다.

<b style="color:#6A1B9A;">gke_maintenance_autoupdate</b>
이 코드는 GCP의 GKE의 메인터넌스가 일어나지 않도록 기간을 자동으로 연장해주는 코드입니다.


📁 This repository has the following <span style="color:#4F8EF7; font-weight:bold;">tree structure</span>.
<div style="background:#f8f8f8; border:1px solid #ccc; border-radius:6px; padding:16px; font-family:monospace; font-size:15px; line-height:1.5;"> <b>text</b> ├── <b>auth</b> │ ├── aws_config.txt │ ├── aws_credentials.txt │ ├── cred_aws.json │ ├── cred_gcp.json │ ├── cred_tencent.json │ └── gcp-ie3-grafana-d0e7985d808a.json ├── <b>firewall_control_list</b> │ ├── aws_firewall_control_list.py │ ├── gcp_firewall_control_list.py │ ├── head.py │ └── tencent_firewall_control_list.py ├── <b>gke_maintenance_autoupdate</b> │ ├── gke_maintenance_autoupdate.py │ └── target_clusters.json ├── <b>iam_control_list</b> │ ├── aws_iam_control_list.py │ ├── gcp_iam_control_list.py │ ├── head.py │ └── tencent_iam_control_list.py ├── <b>instance_control_list</b> │ ├── aws_instance_control_list.py │ ├── gcp_instance_control_list.py │ ├── head.py │ └── tencent_instance_control_list.py ├── <b>instance_listup_tool</b> │ ├── aws_instance_listup_tool.py │ ├── gcp_instance_listup_tool.py │ ├── head.py │ └── tencent_instance_listup_tool.py ├── <b>loadbalancer_control_list</b> │ ├── aws_loadbalancer_control_list.py │ ├── gcp_loadbalancer_control_list.py │ ├── head.py │ └── tencent_loadbalancer_control_list.py ├── <b>logging_archive</b> │ └── head.py ├── <b>logging_control_list</b> │ ├── aws_logging_control_list.py │ ├── gcp_logging_control_list.py │ ├── head.py │ └── tencent_logging_control_list.py ├── <b>snapshot_control</b> │ ├── gcp_snapshot_control.py │ └── tencent_snapshot_control.py ├── <b>unused_control_list</b> │ ├── aws_unused_control_list.py │ ├── gcp_unused_control_list.py │ ├── head.py │ └── tencent_unused_control_list.py └── <b>vpc_control_list</b> ├── aws_vpc_control_list.py ├── gcp_vpc_control_list.py ├── head.py └── tencent_vpc_control_list.py </div>
<span style="color:#4F8EF7"><b>All collected information is uploaded to Google Spreadsheets.</b></span>

📂 <span style="color:#4F8EF7;">Directory and File Descriptions</span>
<b style="color:#6A1B9A;">auth</b>
Contains core files for all code. Project information or key details for each CSP (AWS, GCP, TENCENT) are written here to ensure smooth execution of each code.

<b style="color:#6A1B9A;">firewall_control_list</b>
Collects and processes firewall information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">iam_control_list</b>
Collects and processes IAM account, permissions, and key information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">instance_control_list</b>
Collects and processes instance information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">instance_listup_tool</b>
Edits the content of the Google Spreadsheet uploaded by instance_control_list. Designed for updating only the instance information of a specific project.

<b style="color:#6A1B9A;">loadbalancer_control_list</b>
Collects and processes load balancer information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">logging_control_list</b>
Collects and processes logs such as firewall, account creation/deletion, permissions, key creation/deletion, and instance edits for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">logging_archive</b>
Designed to back up each sheet in the Google Spreadsheet collected by logging_control_list. It is suitable to run once a month and automatically creates or finds folders in year->month order to back up as CSV files.

<b style="color:#6A1B9A;">vpc_control_list</b>
Collects and processes VPC information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

<b style="color:#6A1B9A;">unused_control_list</b>
Iterates through each CSP project to collect unused firewall, disk, and IP information. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets. This code is designed to prevent unnecessary billing.

<b style="color:#6A1B9A;">snapshot_control</b>
Allows you to enter the desired project, region, and instance for each CSP to create an image (AMI) of the instance. Image deletion is also possible, and you can conveniently create images of all or selected disks of an instance.

<b style="color:#6A1B9A;">gke_maintenance_autoupdate</b>
Automatically extends the maintenance period for GCP GKE to prevent maintenance from occurring.