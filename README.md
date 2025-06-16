# Asset_Register_Automation

[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://travis-ci.org/joemccann/dillinger)

This repository contains Python scripts to automate the collection 
and processing of key infrastructure resources, permissions, firewall configurations, and monthly security audit logs 
across major cloud service providers (AWS, GCP, Tencent Cloud).
(In addition, there are some more fun and creative codes that I have added to this project!!)

✨This repository has the following tree structure. ✨
├── auth
│   ├── aws_config.txt
│   ├── aws_credentials.txt
│   ├── cred_aws.json
│   ├── cred_gcp.json
│   ├── cred_tencent.json
│   └── gcp-ie3-grafana-d0e7985d808a.json
├── firewall_control_list
│   ├── aws_firewall_control_list.py
│   ├── gcp_firewall_control_list.py
│   ├── head.py
│   └── tencent_firewall_control_list.py
├── gke_maintenance_autoupdate
│   ├── gke_maintenance_autoupdate.py
│   └── target_clusters.json
├── iam_control_list
│   ├── aws_iam_control_list.py
│   ├── gcp_iam_control_list.py
│   ├── head.py
│   └── tencent_iam_control_list.py
├── instance_control_list
│   ├── aws_instance_control_list.py
│   ├── gcp_instance_control_list.py
│   ├── head.py
│   └── tencent_instance_control_list.py
├── instance_listup_tool
│   ├── aws_instance_listup_tool.py
│   ├── gcp_instance_listup_tool.py
│   ├── head.py
│   └── tencent_instance_listup_tool.py
├── loadbalancer_control_list
│   ├── aws_loadbalancer_control_list.py
│   ├── gcp_loadbalancer_control_list.py
│   ├── head.py
│   └── tencent_loadbalancer_control_list.py
├── logging_archive
│   └── head.py
├── logging_control_list
│   ├── aws_logging_control_list.py
│   ├── gcp_logging_control_list.py
│   ├── head.py
│   └── tencent_logging_control_list.py
├── snapshot_control
│   ├── gcp_snapshot_control.py
│   └── tencent_snapshot_control.py
├── unused_control_list
│   ├── aws_unused_control_list.py
│   ├── gcp_unused_control_list.py
│   ├── head.py
│   └── tencent_unused_control_list.py
└── vpc_control_list
    ├── aws_vpc_control_list.py
    ├── gcp_vpc_control_list.py
    ├── head.py
    └── tencent_vpc_control_list.py

> (All collected information is uploaded to Google Spreadsheets.)

## Directory and File Descriptions

- auth
Contains core files for all code. Project information or key details for each CSP (AWS, GCP, TENCENT) are written here to ensure smooth execution of each code.

- firewall_control_list
Collects and processes firewall information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- iam_control_list
Collects and processes IAM account, permissions, and key information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- instance_control_list
Collects and processes instance information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- instance_listup_tool
Edits the content of the Google Spreadsheet uploaded by instance_control_list. Designed for updating only the instance information of a specific project.

- loadbalancer_control_list
Collects and processes load balancer information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- logging_control_list
Collects and processes logs such as firewall, account creation/deletion, permissions, key creation/deletion, and instance edits for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- logging_archive
Designed to back up each sheet in the Google Spreadsheet collected by logging_control_list. It is suitable to run once a month and automatically creates or finds folders in year-> month order to back up as CSV files.

- vpc_control_list
Collects and processes VPC information for each CSP. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.

- unused_control_list
Iterates through each CSP project to collect unused firewall, disk, and IP information. Uses auth information, and the head.py file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets. This code is designed to prevent unnecessary billing.

- snapshot_control
Allows you to enter the desired project, region, and instance for each CSP to create an image (AMI) of the instance. Image deletion is also possible, and you can conveniently create images of all or selected disks of an instance.

- gke_maintenance_autoupdate
Automatically extends the maintenance period for GCP GKE to prevent maintenance from occurring.


## Plugins


| Plugin |
| ------ | 
| pip3 |


