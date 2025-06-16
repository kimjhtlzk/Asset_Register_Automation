import json
import os
import pytz
from datetime import datetime
from google.oauth2 import service_account
from google.cloud import resourcemanager_v3
from googleapiclient.discovery import build
from google.auth import impersonated_credentials


RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;214m"
UNDERLINE = "\033[4m"


class LoadbalancerInfo:
    def __init__(self, CLOUD, PROJECT, PROJECT_ID, LOADBALANCER_NAME, LOADBALANCER_ID, LOADBALANCER_TYPE,
                 LOADBALANCER_DOMAIN, VIPS, VIP_ISP, REGION, MASTER_ZONE, BACKUP_ZONE, SNAT, SECURITY_GROUPS, SLA_TYPE,
                 INTERNET_MAX_BANDWIDTH_OUT, NETWORK, PASS_TO_TARGET, LISTENER_PROTOCOL, LISTENER, HEALTH_CHECK,
                 CREATION_TIME):
        self.CLOUD = CLOUD
        self.PROJECT = PROJECT
        self.PROJECT_ID = PROJECT_ID
        self.LOADBALANCER_NAME = LOADBALANCER_NAME
        self.LOADBALANCER_ID = LOADBALANCER_ID
        self.LOADBALANCER_TYPE = LOADBALANCER_TYPE
        self.LOADBALANCER_DOMAIN = LOADBALANCER_DOMAIN
        self.VIPS = VIPS
        self.VIP_ISP = VIP_ISP
        self.REGION = REGION
        self.MASTER_ZONE = MASTER_ZONE
        self.BACKUP_ZONE = BACKUP_ZONE
        self.SNAT = SNAT
        self.SECURITY_GROUPS = SECURITY_GROUPS
        self.SLA_TYPE = SLA_TYPE
        self.INTERNET_MAX_BANDWIDTH_OUT = INTERNET_MAX_BANDWIDTH_OUT
        self.NETWORK = NETWORK
        self.PASS_TO_TARGET = PASS_TO_TARGET
        self.LISTENER_PROTOCOL = LISTENER_PROTOCOL
        self.LISTENER = LISTENER
        self.HEALTH_CHECK = HEALTH_CHECK
        self.CREATION_TIME = CREATION_TIME

    def __repr__(self):
        return (f"LoadbalancerInfo(CLOUD={self.CLOUD}, "
                f"PROJECT={self.PROJECT}, "
                f"PROJECT_ID={self.PROJECT_ID}, "
                f"LOADBALANCER_NAME={self.LOADBALANCER_NAME}, "
                f"LOADBALANCER_ID={self.LOADBALANCER_ID}, "
                f"LOADBALANCER_TYPE={self.LOADBALANCER_TYPE}, "
                f"LOADBALANCER_DOMAIN={self.LOADBALANCER_DOMAIN}, "
                f"VIPS={self.VIPS}, "
                f"VIP_ISP={self.VIP_ISP}, "
                f"REGION={self.REGION}, "
                f"MASTER_ZONE={self.MASTER_ZONE}, "
                f"BACKUP_ZONE={self.BACKUP_ZONE}, "
                f"SNAT={self.SNAT}, "
                f"SECURITY_GROUPS={self.SECURITY_GROUPS}, "
                f"SLA_TYPE={self.SLA_TYPE}, "
                f"INTERNET_MAX_BANDWIDTH_OUT={self.INTERNET_MAX_BANDWIDTH_OUT}, "
                f"NETWORK={self.NETWORK}, "
                f"PASS_TO_TARGET={self.PASS_TO_TARGET}, "
                f"LISTENER_PROTOCOL={self.LISTENER_PROTOCOL}, "
                f"LISTENER={self.LISTENER}, "
                f"HEALTH_CHECK={self.HEALTH_CHECK}, "
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

def get_backend_services(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    backend_services = []

    # Global Backend Services
    request = compute_service.backendServices().list(project=project_name)
    response = request.execute()
    for backend_service in response.get('items', []):
        filtered_service = {k: v for k, v in backend_service.items() if k not in exclude_attributes}
        backend_services.append(filtered_service)

    # Regional Backend Services
    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    for region in region_names:
        region_backend_services_request = compute_service.regionBackendServices().list(project=project_name,
                                                                                       region=region)
        region_backend_services_response = region_backend_services_request.execute()
        for region_backend_service in region_backend_services_response.get('items', []):
            filtered_service = {k: v for k, v in region_backend_service.items() if k not in exclude_attributes}
            backend_services.append(filtered_service)

    return backend_services

def get_url_maps(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    url_maps = []

    # Global urlMaps
    request1 = compute_service.urlMaps().list(project=project_name)
    response1 = request1.execute()
    for url_map in response1.get('items', []):
        filtered_map = {k: v for k, v in url_map.items() if k not in exclude_attributes}
        url_maps.append(filtered_map)

    # Regional urlMaps
    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    for region in region_names:
        request2 = compute_service.regionUrlMaps().list(project=project_name, region=region)
        response2 = request2.execute()
        for url_map in response2.get('items', []):
            filtered_map = {k: v for k, v in url_map.items() if k not in exclude_attributes}
            url_maps.append(filtered_map)

    return url_maps

def get_forwarding_rules(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    forwarding_rules = []

    # Global Forwarding Rules
    global_forwarding_rules_request = compute_service.globalForwardingRules().list(project=project_name)
    global_forwarding_rules_response = global_forwarding_rules_request.execute()
    for global_forwarding_rule in global_forwarding_rules_response.get('items', []):
        filtered_rule = {k: v for k, v in global_forwarding_rule.items() if k not in exclude_attributes}
        forwarding_rules.append(filtered_rule)

    # Regional Forwarding Rules
    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    for region in region_names:
        forwarding_rules_request = compute_service.forwardingRules().list(project=project_name, region=region)
        forwarding_rules_response = forwarding_rules_request.execute()
        for forwarding_rule in forwarding_rules_response.get('items', []):
            filtered_rule = {k: v for k, v in forwarding_rule.items() if k not in exclude_attributes}
            forwarding_rules.append(filtered_rule)

    return forwarding_rules

def get_health_checks(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    health_checks = []

    health_checks_request = compute_service.healthChecks().list(project=project_name)
    health_checks_response = health_checks_request.execute()
    for health_check in health_checks_response.get('items', []):
        filtered_check = {k: v for k, v in health_check.items() if k not in exclude_attributes}
        health_checks.append(filtered_check)

    return health_checks

def get_target_http_proxies(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    target_http_proxies = []

    # Global Target HTTP Proxies
    request = compute_service.targetHttpProxies().list(project=project_name)
    response = request.execute()
    for target_http_proxy in response.get('items', []):
        filtered_proxy = {k: v for k, v in target_http_proxy.items() if k not in exclude_attributes}
        target_http_proxies.append(filtered_proxy)

    # Regional Target HTTP Proxies
    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    for region in region_names:
        region_target_http_proxies_request = compute_service.regionTargetHttpProxies().list(project=project_name, region=region)
        region_target_http_proxies_response = region_target_http_proxies_request.execute()
        for region_target_http_proxy in region_target_http_proxies_response.get('items', []):
            filtered_proxy = {k: v for k, v in region_target_http_proxy.items() if k not in exclude_attributes}
            target_http_proxies.append(filtered_proxy)

    return target_http_proxies

def get_target_https_proxies(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    target_https_proxies = []

    # Global Target HTTPS Proxies
    request = compute_service.targetHttpsProxies().list(project=project_name)
    response = request.execute()
    for target_https_proxy in response.get('items', []):
        filtered_proxy = {k: v for k, v in target_https_proxy.items() if k not in exclude_attributes}
        target_https_proxies.append(filtered_proxy)

    # Regional Target HTTPS Proxies
    region_names = [
        "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2",
        "asia-northeast3", "asia-south1", "asia-south2", "asia-southeast1",
        "asia-southeast2", "australia-southeast1", "australia-southeast2",
        "europe-central2", "europe-west1", "europe-west2", "europe-west3",
        "europe-west4",
        "us-east1", "us-east4", "us-east5", "us-south1",
        "us-west1", "us-west2", "us-west3", "us-west4"
    ]

    for region in region_names:
        region_target_https_proxies_request = compute_service.regionTargetHttpsProxies().list(project=project_name, region=region)
        region_target_https_proxies_response = region_target_https_proxies_request.execute()
        for region_target_https_proxy in region_target_https_proxies_response.get('items', []):
            filtered_proxy = {k: v for k, v in region_target_https_proxy.items() if k not in exclude_attributes}
            target_https_proxies.append(filtered_proxy)

    return target_https_proxies

def get_ssl_certificates(project_name, exclude_attributes=None, credentials=None):
    compute_service = build('compute', 'v1', credentials=credentials)

    ssl_certificates = []

    # SSL Certificates
    ssl_certificates_request = compute_service.sslCertificates().list(project=project_name)
    ssl_certificates_response = ssl_certificates_request.execute()
    for ssl_certificate in ssl_certificates_response.get('items', []):
        filtered_certificate = {k: v for k, v in ssl_certificate.items() if k not in exclude_attributes}
        ssl_certificates.append(filtered_certificate)

    return ssl_certificates

def get_loadbalancer_info(project_name, project_display_name, forwarding_rules, backend_services, url_maps, target_http_proxies, target_https_proxies, health_checks, ssl_certificates):
    loadbalancer_objects = []

    for forwarding_rule in forwarding_rules:
        if 'target' in forwarding_rule:
            target = forwarding_rule['target']
            if 'targetHttpsProxies' in target:
                # Target HTTPS Proxies
                target_https_proxy_name = target.split('/')[-1]
                target_https_proxy = next(
                    (proxy for proxy in target_https_proxies if proxy['name'] == target_https_proxy_name), None)
                if target_https_proxy:
                    url_map_name = target_https_proxy['urlMap'].split('/')[-1]
                    url_map = next((url_map for url_map in url_maps if url_map['name'] == url_map_name), None)
                    ssl_certificate_ids = [cert.split('/')[-1] for cert in
                                           target_https_proxy.get('sslCertificates', [])]
                    ssl_certificates_info = [cert for cert in ssl_certificates if cert['name'] in ssl_certificate_ids]

                    backend_service_name = url_map['defaultService'].split('/')[-1]
                    backend_service = next(
                        (service for service in backend_services if service['name'] == backend_service_name), None)
                    if backend_service:
                        health_check_ids = [check.split('/')[-1] for check in backend_service.get('healthChecks', [])]
                        health_checks_info = [check for check in health_checks if check['name'] in health_check_ids]

                        health_check_dict = {}
                        for health_check in health_checks_info:
                            health_check_dict['checkIntervalSec'] = health_check.get('checkIntervalSec', '')
                            health_check_dict['timeoutSec'] = health_check.get('timeoutSec', '')
                            health_check_dict['unhealthyThreshold'] = health_check.get('unhealthyThreshold', '')
                            health_check_dict['healthyThreshold'] = health_check.get('healthyThreshold', '')
                            health_check_dict['type'] = health_check.get('type', '')
                            if health_check_dict['type'] == 'TCP':
                                health_check_dict['port'] = health_check.get('tcpHealthCheck', {}).get('port', '')
                            elif health_check_dict['type'] == 'HTTP':
                                health_check_dict['portSpecification'] = health_check.get('httpHealthCheck', {}).get(
                                    'portSpecification', '')
                                health_check_dict['port'] = health_check.get('httpHealthCheck', {}).get('port', '')
                                health_check_dict['requestPath'] = health_check.get('httpHealthCheck', {}).get(
                                    'requestPath', '')
                            elif health_check_dict['type'] == 'HTTPS':
                                health_check_dict['port'] = health_check.get('httpsHealthCheck', {}).get('port', '')
                                health_check_dict['requestPath'] = health_check.get('httpsHealthCheck', {}).get(
                                    'requestPath', '')
                            health_check_dict['healthCheck'] = health_check.get('name', '')
                            break

                        creation_time_utc = datetime.strptime(forwarding_rule['creationTimestamp'],
                                                              '%Y-%m-%dT%H:%M:%S.%f%z')
                        creation_time_kst = creation_time_utc.astimezone(pytz.timezone('Asia/Seoul')).strftime(
                            '%Y-%m-%d %H:%M:%S')

                        network_info = forwarding_rule.get('network', '')
                        subnetwork_info = forwarding_rule.get('subnetwork', '')
                        network_value = network_info.split('/')[-1] if network_info else '-'
                        subnetwork_value = subnetwork_info.split('/')[-1] if subnetwork_info else '-'
                        network = f"{network_value} / {subnetwork_value}" if network_value != '-' or subnetwork_value != '-' else '-'
                        region = forwarding_rule.get('region', 'global')
                        if isinstance(region, str) and '/' in region:
                            region = region.split('/')[-1]

                        listener_protocol = backend_service.get('protocol', '')

                        listener = forwarding_rule.get('portRange', forwarding_rule.get('ports', ''))
                        if ssl_certificates_info:
                            ssl_cert_info_str = '\n'.join(
                                [f"Name: {cert['name']}, SANs: {', '.join(cert.get('subjectAlternativeNames', []))}" for
                                 cert in ssl_certificates_info])
                            listener += f"\nSSL Certificates:\n{ssl_cert_info_str}"

                        loadbalancer_info = LoadbalancerInfo(
                            CLOUD="GCP",
                            PROJECT=project_display_name,
                            PROJECT_ID=project_name,
                            LOADBALANCER_NAME=forwarding_rule['name'],
                            LOADBALANCER_ID=forwarding_rule['id'],
                            LOADBALANCER_TYPE=forwarding_rule['loadBalancingScheme'],
                            LOADBALANCER_DOMAIN="-",
                            VIPS=[forwarding_rule['IPAddress']],
                            VIP_ISP="-",
                            REGION=region,
                            MASTER_ZONE="-",
                            BACKUP_ZONE="-",
                            SNAT="-",
                            SECURITY_GROUPS="-",
                            SLA_TYPE="-",
                            INTERNET_MAX_BANDWIDTH_OUT="-",
                            NETWORK=network,
                            PASS_TO_TARGET="-",
                            LISTENER_PROTOCOL=listener_protocol,
                            LISTENER=listener,
                            HEALTH_CHECK=health_check_dict,
                            CREATION_TIME=creation_time_kst
                        )
                        loadbalancer_objects.append(loadbalancer_info)

            elif 'targetHttpProxies' in target:
                # Target HTTP Proxies
                target_http_proxy_name = target.split('/')[-1]
                target_http_proxy = next(
                    (proxy for proxy in target_http_proxies if proxy['name'] == target_http_proxy_name), None)
                if target_http_proxy:
                    url_map_name = target_http_proxy['urlMap'].split('/')[-1]
                    url_map = next((url_map for url_map in url_maps if url_map['name'] == url_map_name), None)
                    ssl_certificates_info = []
                    backend_service_name = url_map['defaultService'].split('/')[-1]
                    backend_service = next(
                        (service for service in backend_services if service['name'] == backend_service_name), None)
                    if backend_service:
                        health_check_ids = [check.split('/')[-1] for check in backend_service.get('healthChecks', [])]
                        health_checks_info = [check for check in health_checks if check['name'] in health_check_ids]

                        health_check_dict = {}
                        for health_check in health_checks_info:
                            health_check_dict['checkIntervalSec'] = health_check.get('checkIntervalSec', '')
                            health_check_dict['timeoutSec'] = health_check.get('timeoutSec', '')
                            health_check_dict['unhealthyThreshold'] = health_check.get('unhealthyThreshold', '')
                            health_check_dict['healthyThreshold'] = health_check.get('healthyThreshold', '')
                            health_check_dict['type'] = health_check.get('type', '')
                            if health_check_dict['type'] == 'TCP':
                                health_check_dict['port'] = health_check.get('tcpHealthCheck', {}).get('port', '')
                            elif health_check_dict['type'] == 'HTTP':
                                health_check_dict['portSpecification'] = health_check.get('httpHealthCheck', {}).get(
                                    'portSpecification', '')
                                health_check_dict['port'] = health_check.get('httpHealthCheck', {}).get('port', '')
                                health_check_dict['requestPath'] = health_check.get('httpHealthCheck', {}).get(
                                    'requestPath', '')
                            elif health_check_dict['type'] == 'HTTPS':
                                health_check_dict['port'] = health_check.get('httpsHealthCheck', {}).get('port', '')
                                health_check_dict['requestPath'] = health_check.get('httpsHealthCheck', {}).get(
                                    'requestPath', '')
                            health_check_dict['healthCheck'] = health_check.get('name', '')
                            break

                        creation_time_utc = datetime.strptime(forwarding_rule['creationTimestamp'],
                                                              '%Y-%m-%dT%H:%M:%S.%f%z')
                        creation_time_kst = creation_time_utc.astimezone(pytz.timezone('Asia/Seoul')).strftime(
                            '%Y-%m-%d %H:%M:%S')

                        network_info = forwarding_rule.get('network', '')
                        subnetwork_info = forwarding_rule.get('subnetwork', '')
                        network_value = network_info.split('/')[-1] if network_info else '-'
                        subnetwork_value = subnetwork_info.split('/')[-1] if subnetwork_info else '-'
                        network = f"{network_value} / {subnetwork_value}" if network_value != '-' or subnetwork_value != '-' else '-'
                        region = forwarding_rule.get('region', 'global')
                        if isinstance(region, str) and '/' in region:
                            region = region.split('/')[-1]

                        listener_protocol = backend_service.get('protocol', '')

                        listener = forwarding_rule.get('portRange', forwarding_rule.get('ports', ''))

                        loadbalancer_info = LoadbalancerInfo(
                            CLOUD="GCP",
                            PROJECT=project_display_name,
                            PROJECT_ID=project_name,
                            LOADBALANCER_NAME=forwarding_rule['name'],
                            LOADBALANCER_ID=forwarding_rule['id'],
                            LOADBALANCER_TYPE=forwarding_rule['loadBalancingScheme'],
                            LOADBALANCER_DOMAIN="-",
                            VIPS=[forwarding_rule['IPAddress']],
                            VIP_ISP="-",
                            REGION=region,
                            MASTER_ZONE="-",
                            BACKUP_ZONE="-",
                            SNAT="-",
                            SECURITY_GROUPS="-",
                            SLA_TYPE="-",
                            INTERNET_MAX_BANDWIDTH_OUT="-",
                            NETWORK=network,
                            PASS_TO_TARGET="-",
                            LISTENER_PROTOCOL=listener_protocol,
                            LISTENER=listener,
                            HEALTH_CHECK=health_check_dict,
                            CREATION_TIME=creation_time_kst
                        )
                        loadbalancer_objects.append(loadbalancer_info)

        elif 'backendService' in forwarding_rule:
            backend_service_name = forwarding_rule['backendService'].split('/')[-1]
            backend_service = next((service for service in backend_services if service['name'] == backend_service_name),
                                   None)
            if backend_service:
                health_check_ids = [check.split('/')[-1] for check in backend_service.get('healthChecks', [])]
                health_checks_info = [check for check in health_checks if check['name'] in health_check_ids]

                health_check_dict = {}
                for health_check in health_checks_info:
                    health_check_dict['checkIntervalSec'] = health_check.get('checkIntervalSec', '')
                    health_check_dict['timeoutSec'] = health_check.get('timeoutSec', '')
                    health_check_dict['unhealthyThreshold'] = health_check.get('unhealthyThreshold', '')
                    health_check_dict['healthyThreshold'] = health_check.get('healthyThreshold', '')
                    health_check_dict['type'] = health_check.get('type', '')
                    if health_check_dict['type'] == 'TCP':
                        health_check_dict['port'] = health_check.get('tcpHealthCheck', {}).get('port', '')
                    elif health_check_dict['type'] == 'HTTP':
                        health_check_dict['portSpecification'] = health_check.get('httpHealthCheck', {}).get(
                            'portSpecification', '')
                        health_check_dict['port'] = health_check.get('httpHealthCheck', {}).get('port', '')
                        health_check_dict['requestPath'] = health_check.get('httpHealthCheck', {}).get('requestPath',
                                                                                                       '')
                    elif health_check_dict['type'] == 'HTTPS':
                        health_check_dict['port'] = health_check.get('httpsHealthCheck', {}).get('port', '')
                        health_check_dict['requestPath'] = health_check.get('httpsHealthCheck', {}).get('requestPath',
                                                                                                        '')
                    health_check_dict['healthCheck'] = health_check.get('name', '')
                    break  # 첫 번째 health check 정보만 저장

                creation_time_utc = datetime.strptime(forwarding_rule['creationTimestamp'], '%Y-%m-%dT%H:%M:%S.%f%z')
                creation_time_kst = creation_time_utc.astimezone(pytz.timezone('Asia/Seoul')).strftime(
                    '%Y-%m-%d %H:%M:%S')
                network_info = forwarding_rule.get('network', '')
                subnetwork_info = forwarding_rule.get('subnetwork', '')
                network_value = network_info.split('/')[-1] if network_info else '-'
                subnetwork_value = subnetwork_info.split('/')[-1] if subnetwork_info else '-'
                network = f"{network_value} / {subnetwork_value}" if network_value != '-' or subnetwork_value != '-' else '-'

                region = forwarding_rule.get('region', 'global')
                if isinstance(region, str) and '/' in region:
                    region = region.split('/')[-1]

                listener_protocol = backend_service.get('protocol', '')

                listener = forwarding_rule.get('portRange', forwarding_rule.get('ports', ''))

                loadbalancer_info = LoadbalancerInfo(
                    CLOUD="GCP",
                    PROJECT=project_display_name,
                    PROJECT_ID=project_name,
                    LOADBALANCER_NAME=forwarding_rule['name'],
                    LOADBALANCER_ID=forwarding_rule['id'],
                    LOADBALANCER_TYPE=forwarding_rule['loadBalancingScheme'],
                    LOADBALANCER_DOMAIN="-",
                    VIPS=[forwarding_rule['IPAddress']],
                    VIP_ISP="-",
                    REGION=region,
                    MASTER_ZONE="-",
                    BACKUP_ZONE="-",
                    SNAT="-",
                    SECURITY_GROUPS="-",
                    SLA_TYPE="-",
                    INTERNET_MAX_BANDWIDTH_OUT="-",
                    NETWORK=network,
                    PASS_TO_TARGET="-",
                    LISTENER_PROTOCOL=listener_protocol,
                    LISTENER=listener,
                    HEALTH_CHECK=health_check_dict,
                    CREATION_TIME=creation_time_kst
                )
                loadbalancer_objects.append(loadbalancer_info)

    return loadbalancer_objects

def modify_vips_and_health_check_to_string(loadbalancer_objects):
    for lb in loadbalancer_objects:
        if isinstance(lb.VIPS, list):
            lb.VIPS = ', '.join(lb.VIPS)  # Convert list to comma-separated string

        if isinstance(lb.HEALTH_CHECK, dict):
            health_check_str = '\n'.join([f"{key}: {value}" for key, value in lb.HEALTH_CHECK.items()])
            lb.HEALTH_CHECK = health_check_str  # Convert dict to newline-separated string

        if isinstance(lb.LISTENER, list):
            lb.LISTENER = '\n'.join(lb.LISTENER)  # Convert list of ports to newline-separated string

    return loadbalancer_objects


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

    loadbalancer_objects = []

    for project_name in project_names:
        print(f"{YELLOW}{project_name}{RESET}")

        if project_name == "project_1":
            credentials = source_credentials
        else:
            target_sa = f"terraform@{project_name}.iam.gserviceaccount.com"
            credentials = get_impersonated_credentials(source_credentials, target_sa)

        project_display_name = get_project_info(project_name, credentials).display_name

        # Backend Services
        backend_services_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                               'logConfig', 'iap', 'labelFingerprint']
        backend_services = get_backend_services(project_name, backend_services_exclude_attributes, credentials)

        # urlMaps
        url_maps_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                       'logConfig', 'iap', 'labelFingerprint']
        url_maps = get_url_maps(project_name, url_maps_exclude_attributes, credentials)

        # Forwarding Rules
        forwarding_rules_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                               'logConfig', 'iap', 'labelFingerprint', 'networkTier']
        forwarding_rules = get_forwarding_rules(project_name, forwarding_rules_exclude_attributes, credentials)

        # Health Checks
        health_checks_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                            'logConfig', 'iap', 'labelFingerprint']
        health_checks = get_health_checks(project_name, health_checks_exclude_attributes, credentials)

        # Target HTTP Proxies
        target_http_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                         'logConfig', 'iap', 'labelFingerprint', 'quicOverride', 'quicOverride']
        target_http_proxies = get_target_http_proxies(project_name, target_http_exclude_attributes, credentials)

        # Target HTTPS Proxies
        target_https_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                           'logConfig', 'iap', 'labelFingerprint', 'quicOverride', 'quicOverride']
        target_https_proxies = get_target_https_proxies(project_name, target_https_exclude_attributes, credentials)

        # SSL Certificates
        ssl_exclude_attributes = ['kind', 'selfLink', 'fingerprint', 'description', 'maxUtilization', 'capacityScaler',
                                  'logConfig', 'iap', 'labelFingerprint', 'certificate', 'selfManaged']
        ssl_certificates = get_ssl_certificates(project_name, ssl_exclude_attributes, credentials)

        # Loadbalancer Info
        find_loadbalancer_objects = get_loadbalancer_info(project_name, project_display_name, forwarding_rules, backend_services, url_maps,
                                                     target_http_proxies, target_https_proxies, health_checks,
                                                     ssl_certificates)
        # Modify VIPS and HEALTH_CHECK
        modified_loadbalancer_objects = modify_vips_and_health_check_to_string(find_loadbalancer_objects)

        loadbalancer_objects.extend(modified_loadbalancer_objects)

    loadbalancer_objects.sort(key=lambda x: (x.PROJECT, x.REGION, x.LOADBALANCER_TYPE, x.LOADBALANCER_NAME))

    return loadbalancer_objects


if __name__ == "__main__":
    main()
