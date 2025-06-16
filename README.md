<h1 class="code-line" data-line-start=0 data-line-end=1 ><a id="Asset_Register_Automation_0"></a>Asset_Register_Automation</h1>
<p class="has-line-data" data-line-start="2" data-line-end="3"><a href="https://travis-ci.org/joemccann/dillinger"><img src="https://travis-ci.org/joemccann/dillinger.svg?branch=master" alt="Build Status"></a></p>
<p class="has-line-data" data-line-start="4" data-line-end="8">This repository contains Python scripts to automate the collection<br>
and processing of key infrastructure resources, permissions, firewall configurations, and monthly security audit logs<br>
across major cloud service providers (AWS, GCP, Tencent Cloud).<br>
(In addition, there are some more fun and creative codes that I have added to this project!!)</p>
<p class="has-line-data" data-line-start="9" data-line-end="65">✨This repository has the following tree structure. ✨<br>
├── auth<br>
│   ├── aws_config.txt<br>
│   ├── aws_credentials.txt<br>
│   ├── cred_aws.json<br>
│   ├── cred_gcp.json<br>
│   ├── cred_tencent.json<br>
│   └── gcp-ie3-grafana-d0e7985d808a.json<br>
├── firewall_control_list<br>
│   ├── aws_firewall_control_list.py<br>
│   ├── gcp_firewall_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_firewall_control_list.py<br>
├── gke_maintenance_autoupdate<br>
│   ├── gke_maintenance_autoupdate.py<br>
│   └── target_clusters.json<br>
├── iam_control_list<br>
│   ├── aws_iam_control_list.py<br>
│   ├── gcp_iam_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_iam_control_list.py<br>
├── instance_control_list<br>
│   ├── aws_instance_control_list.py<br>
│   ├── gcp_instance_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_instance_control_list.py<br>
├── instance_listup_tool<br>
│   ├── aws_instance_listup_tool.py<br>
│   ├── gcp_instance_listup_tool.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_instance_listup_tool.py<br>
├── loadbalancer_control_list<br>
│   ├── aws_loadbalancer_control_list.py<br>
│   ├── gcp_loadbalancer_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_loadbalancer_control_list.py<br>
├── logging_archive<br>
│   └── <a href="http://head.py">head.py</a><br>
├── logging_control_list<br>
│   ├── aws_logging_control_list.py<br>
│   ├── gcp_logging_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_logging_control_list.py<br>
├── snapshot_control<br>
│   ├── gcp_snapshot_control.py<br>
│   └── tencent_snapshot_control.py<br>
├── unused_control_list<br>
│   ├── aws_unused_control_list.py<br>
│   ├── gcp_unused_control_list.py<br>
│   ├── <a href="http://head.py">head.py</a><br>
│   └── tencent_unused_control_list.py<br>
└── vpc_control_list<br>
├── aws_vpc_control_list.py<br>
├── gcp_vpc_control_list.py<br>
├── <a href="http://head.py">head.py</a><br>
└── tencent_vpc_control_list.py</p>
<blockquote>
<p class="has-line-data" data-line-start="66" data-line-end="67">(All collected information is uploaded to Google Spreadsheets.)</p>
</blockquote>
<h2 class="code-line" data-line-start=68 data-line-end=69 ><a id="Directory_and_File_Descriptions_68"></a>Directory and File Descriptions</h2>
<ul>
<li class="has-line-data" data-line-start="70" data-line-end="73">
<p class="has-line-data" data-line-start="70" data-line-end="72">auth<br>
Contains core files for all code. Project information or key details for each CSP (AWS, GCP, TENCENT) are written here to ensure smooth execution of each code.</p>
</li>
<li class="has-line-data" data-line-start="73" data-line-end="76">
<p class="has-line-data" data-line-start="73" data-line-end="75">firewall_control_list<br>
Collects and processes firewall information for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="76" data-line-end="79">
<p class="has-line-data" data-line-start="76" data-line-end="78">iam_control_list<br>
Collects and processes IAM account, permissions, and key information for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="79" data-line-end="82">
<p class="has-line-data" data-line-start="79" data-line-end="81">instance_control_list<br>
Collects and processes instance information for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="82" data-line-end="85">
<p class="has-line-data" data-line-start="82" data-line-end="84">instance_listup_tool<br>
Edits the content of the Google Spreadsheet uploaded by instance_control_list. Designed for updating only the instance information of a specific project.</p>
</li>
<li class="has-line-data" data-line-start="85" data-line-end="88">
<p class="has-line-data" data-line-start="85" data-line-end="87">loadbalancer_control_list<br>
Collects and processes load balancer information for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="88" data-line-end="91">
<p class="has-line-data" data-line-start="88" data-line-end="90">logging_control_list<br>
Collects and processes logs such as firewall, account creation/deletion, permissions, key creation/deletion, and instance edits for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="91" data-line-end="94">
<p class="has-line-data" data-line-start="91" data-line-end="93">logging_archive<br>
Designed to back up each sheet in the Google Spreadsheet collected by logging_control_list. It is suitable to run once a month and automatically creates or finds folders in year-&gt; month order to back up as CSV files.</p>
</li>
<li class="has-line-data" data-line-start="94" data-line-end="97">
<p class="has-line-data" data-line-start="94" data-line-end="96">vpc_control_list<br>
Collects and processes VPC information for each CSP. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets.</p>
</li>
<li class="has-line-data" data-line-start="97" data-line-end="100">
<p class="has-line-data" data-line-start="97" data-line-end="99">unused_control_list<br>
Iterates through each CSP project to collect unused firewall, disk, and IP information. Uses auth information, and the <a href="http://head.py">head.py</a> file sequentially runs and aggregates all other files, then uploads the results to Google Spreadsheets. This code is designed to prevent unnecessary billing.</p>
</li>
<li class="has-line-data" data-line-start="100" data-line-end="103">
<p class="has-line-data" data-line-start="100" data-line-end="102">snapshot_control<br>
Allows you to enter the desired project, region, and instance for each CSP to create an image (AMI) of the instance. Image deletion is also possible, and you can conveniently create images of all or selected disks of an instance.</p>
</li>
<li class="has-line-data" data-line-start="103" data-line-end="105">
<p class="has-line-data" data-line-start="103" data-line-end="105">gke_maintenance_autoupdate<br>
Automatically extends the maintenance period for GCP GKE to prevent maintenance from occurring.</p>
</li>
</ul>
<h2 class="code-line" data-line-start=107 data-line-end=108 ><a id="Plugins_107"></a>Plugins</h2>
<table class="table table-striped table-bordered">
<thead>
<tr>
<th>Plugin</th>
</tr>
</thead>
<tbody>
<tr>
<td>pip3</td>
</tr>
</tbody>
</table>
