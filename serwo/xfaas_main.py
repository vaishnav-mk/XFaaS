import xfaas_init as xfaas_init
import xfaas_optimizer as xfaas_optimizer
import xfaas_provenance as xfaas_provenance
import xfaas_resource_generator as xfaas_resource_generator
import xfaas_build as xfaas_build
import xfaas_deploy as xfaas_deploy
from python.src.utils.classes.commons.partition_point import PartitionPoint
from python.src.utils.classes.commons.csp import CSP
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.queue import QueueServiceClient
from azure.storage.blob import BlobServiceClient
import os
import string
import random
import sys
import json
import pathlib
import argparse
import shutil

parser = argparse.ArgumentParser(
    prog="ProgramName",
    description="What the program does",
    epilog="Text at the bottom of help",
)
parser.add_argument("--csp",dest='csp',type=str,help="CSP name")
parser.add_argument("--region",dest='region',type=str,help="Region name")
parser.add_argument("--wf-user-directory",dest='wf_user_directory',type=str,help="Workflow user directory")
parser.add_argument("--dag-benchmark",dest='dag_benchmark',type=str,help="Path DAG Benchmark")
parser.add_argument("--dag-file-name",dest='dag_filename',type=str,help="DAG FILE NAME")
parser.add_argument("--is-async",dest='is_async',type=str,help="Is Async Fn",default=0)
# parser.add_argument("--is-containerbased-aws",dest='is_containerbasedaws',type=str,help="Is Async Fn",default=0)
project_dir = pathlib.Path(__file__).parent.resolve()


args = parser.parse_args()
    
# is_containerbasedaws = bool(int(args.is_containerbasedaws))
USER_DIR = args.wf_user_directory
DAG_DEFINITION_FILE =  args.dag_filename

DAG_DEFINITION_PATH = f"{USER_DIR}/{DAG_DEFINITION_FILE}"
BENCHMARK_FILE =  args.dag_benchmark
benchmark_path = f'{USER_DIR}/{BENCHMARK_FILE}'
csp = args.csp
region = args.region
part_id = "test"
def get_user_pinned_nodes():

    config = json.loads(open(f'{project_dir}/config/xfaas_user_config.json', 'r').read())
    if "user_pinned_nodes" in config:
        return config['user_pinned_nodes']
    else:
        return None

def randomString(stringLength):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def add_collect_logs(dag_definition_path,user_wf_dir, xfaas_user_dag,region):
    if region == 'us-east-1':
        region = 'eastus'
    elif region == 'ap-southeast-1':
        region = 'southeastasia'
    else:
        region = 'centralindia'
    
    # region = 'centralindia'
    
    collect_logs_dir = f'{project_dir}/templates/azure/predefined-functions/CollectLogs'
    new_collect_logs_dir = f'{user_wf_dir}/CollectLogs'
   

    print('creating xfaas logging queue')
    resource_group_name = f"xfaasLog{region}"
    storage_account_name = f"xfaaslog{region}"
   
    queue_name = randomString(5)
    
    credential = DefaultAzureCredential()
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_client = ResourceManagementClient(credential, subscription_id)
    try:
        rg_result = resource_client.resource_groups.create_or_update(
            f"{resource_group_name}", {"location": f"{region}"}
        )
    except Exception as e:
        print(e)
    
    try:
        storage_client = StorageManagementClient(credential, subscription_id)
        poller = storage_client.storage_accounts.begin_create(resource_group_name, storage_account_name,
            {
                "location" : region,
                "kind": "StorageV2",
                "sku": {"name": "Standard_LRS"}
            }
        )
        account_result = poller.result()
        # print(f"Provisioned storage account {account_result.name}")
    except Exception as e:
        print(e)

    try:
        # queue_service_client = QueueServiceClient(account_url=f"https://{storage_account_name}.queue.core.windows.net", credential=credential)
        # queue_service_client.create_queue(queue_name)
        if csp == "azure":
            queue_creation_command = f"az storage queue create -n {queue_name} --account-name {storage_account_name}"
            os.system(queue_creation_command)
        elif csp == "aws":
            queue_creation_command = f"aws sqs create-queue --queue-name {queue_name}"
            stream = os.popen(queue_creation_command)
            output = stream.read()
            stream.close()
            queue_url = json.loads(output)["QueueUrl"]
            print("queue created")
    except Exception as e:
        print(e)

    try:
        #TODO Need a native call to get connection string
        stream = os.popen(f'az storage account show-connection-string --name {storage_account_name} --resource-group {resource_group_name}')
        json_str = stream.read()
        stream.close()
    except Exception as e:
        print(e)

    jsson = json.loads(json_str)
    fin_dict = {'queue_name' : queue_name, 'connection_string' : jsson['connectionString'] , 'storage_account' : storage_account_name, 'group':resource_group_name}
    
    
    ## copy collect_logs_dir to user_wf_dir using shutil copytree

    os.system(f'cp -r {collect_logs_dir} {user_wf_dir}')
    
    connection_string_template = "CONNECTION_STRING"
    queue_name_template = "QUEUE_NAME"
    coll_csp_template = "COLL_CSP"
    
    ##open the file and replace the connection string and queue name
    with open(f'{new_collect_logs_dir}/func.py', 'r') as file :
        filedata = file.read()
    
    if csp == "aws":
        filedata = filedata.replace(
            connection_string_template, queue_url
        )
    elif csp == "azure":
        filedata = filedata.replace(
            connection_string_template, fin_dict["connection_string"]
        )
    filedata = filedata.replace(queue_name_template, fin_dict["queue_name"])
    filedata = filedata.replace(coll_csp_template, csp.lower())

    with open(f'{new_collect_logs_dir}/func.py', 'w') as file:
        file.write(filedata)
    
    node_dict = {
        "NodeId": "253",
        "NodeName": "CollectLogs",
        "Path": new_collect_logs_dir,
        "EntryPoint": "func.py",
        "CSP": "NA",
        "MemoryInMB": 128
    }

    ##open dag definition file and add the node to the dag
    with open(dag_definition_path, 'r') as file :
        filedata = file.read()
    dag = json.loads(filedata)

    dag['Nodes'].append(node_dict)
    
    nx_dag = xfaas_user_dag.get_dag()
    ## find sink node with out degree 0
    sink_node = None
    for node in nx_dag.nodes:
        if nx_dag.out_degree(node) == 0:
            sink_node = node
            break
    
    node_name = node_dict['NodeName']
    sink_node_name = nx_dag.nodes[sink_node]['NodeName']
    dag['Edges'].append({f"{sink_node_name}":[f"{node_name}"]})
    
    
    with open(f'{user_wf_dir}/refactored-dag.json', 'w') as file:
        file.write(json.dumps(dag, indent=4))
    nx_dag.add_node(node_dict['NodeId'], **node_dict)
    nx_dag.add_edge(sink_node,node_dict['NodeId'])

    
    return fin_dict

# This Is going to update refractor-dag.json by adding waiting for x sec mechanism. Now we have shifted to another logic
# def add_async_waitXfn(dag_path,user_wf_dir,dag_refractored_path):

#     data = json.load(open(dag_path))
#     fns_data = data['Nodes']
#     async_fn_name_list=set()
    
#     WaitXSeconds_template_dir= f'{project_dir}/templates/azure/predefined-functions/WaitXSeconds'
#     new_WaitXSeconds_template_dir=f'{user_wf_dir}/WaitXSeconds'
#     for node in fns_data:
#         if "IsAsync" in node and node["IsAsync"]:
#             async_fn_name_list.add(node["NodeName"])
    
#     WaitXSeconds_node_dict = {
#         "NodeId": "252",
#         "NodeName": "WaitXSeconds",
#         "Path": new_WaitXSeconds_template_dir,
#         "EntryPoint": "WaitXSeconds.py",
#         "CSP": "NA",
#         "MemoryInMB": 128
#     }

#     # Here we gonna copy our WaitXSeconds template to our build directory
#     try:
#         # Create the new directory if it does not exist
#         if not os.path.exists(new_WaitXSeconds_template_dir):
#             os.makedirs(new_WaitXSeconds_template_dir)

#         # Copy all files from the current directory to the new directory
#         for filename in os.listdir(WaitXSeconds_template_dir):
#             print("filename to be copied",filename)
#             file_path = os.path.join(WaitXSeconds_template_dir, filename)
#         # Check if it's a file and not a directory
#             if os.path.isfile(file_path):
#                 shutil.copy(file_path, new_WaitXSeconds_template_dir)
#     except Exception as e:
#         print(e)
#         print("Not able to copy WaitXSeconds file to directory")

#     node_id_to_check = "252"
#     node_exists = any(node["NodeId"] == node_id_to_check for node in data['Nodes'])
#     # print("node_exists:",node_exists)
#     if len(async_fn_name_list)>0:
#         if not node_exists:
#             data['Nodes'].append(WaitXSeconds_node_dict)

#     for set_item in async_fn_name_list:
#         # set_item = c_set_item[1:-1]
#         for node in data['Edges']:
#             # print(node,set_item)
#             if set_item in node:
#                 # print("node found")
#                 current_edge_data=node[set_item]
#                 node[set_item]=["WaitXSeconds"]
#                 data['Edges'].append({"WaitXSeconds":current_edge_data})
#         # print(set_item)
#         # print(type(set_item))
            

#     #Writing into dag-refractor.json
#     json_string = json.dumps(data, indent=4)    
#     file_path = dag_refractored_path
#     with open(file_path, "w") as json_file:
#         json_file.write(json_string)

def run(user_wf_dir, dag_definition_file, benchmark_file, csp,region):
    # user_wf_dir += "/workflow-gen"
    dag_definition_path = f"{user_wf_dir}/{dag_definition_file}"
    user_pinned_nodes = get_user_pinned_nodes()
    xfaas_user_dag = xfaas_init.init(dag_definition_path)
    # partition_config = xfaas_optimizer.optimize(xfaas_user_dag,
    #                                             user_pinned_nodes, benchmark_path)

    partition_config = [PartitionPoint("function_name", 2, csp, None, part_id, region)]

    wf_id = xfaas_provenance.push_user_dag(dag_definition_path)
    queue_details = add_collect_logs(dag_definition_path,user_wf_dir,xfaas_user_dag,region)
    dag_definition_path = f'{user_wf_dir}/refactored-{dag_definition_file}'
    # add_async_waitXfn(dag_definition_path,user_wf_dir,dag_definition_path)  # print("Added Async update fn ality to dag.json")
    refactored_wf_id = xfaas_provenance.push_refactored_workflow("refactored-dag.json", user_wf_dir, wf_id,csp)
    wf_deployment_id = xfaas_provenance.push_deployment_logs("refactored-dag.json",user_wf_dir,wf_id,refactored_wf_id,csp)
    xfaas_resource_generator.generate(user_wf_dir, dag_definition_path, partition_config,"refactored-dag.json")
    xfaas_provenance.generate_provenance_artifacts(user_wf_dir,wf_id,refactored_wf_id,wf_deployment_id,csp,region,part_id,queue_details)

    return wf_id, refactored_wf_id, wf_deployment_id
   

if __name__ == '__main__':

    wf_id, refactored_wf_id, wf_deployment_id = run(f'{USER_DIR}', DAG_DEFINITION_FILE, BENCHMARK_FILE, csp,region)
    
