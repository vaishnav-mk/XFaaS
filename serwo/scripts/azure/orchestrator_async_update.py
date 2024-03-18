import re
import os

def extract_var(input_str):
    # Define the regular expressions
    variable_regex = r'^\s*([a-zA-Z_]\w*)\s*='
    function_call_regex = r'\bcontext\.call_activity\(\s*"([^"]*)"\s*,\s*([^)]*)\)'

    # Extract the variable name and function call arguments
    variable_match = re.match(variable_regex, input_str)
    variable_name = variable_match.group(1) if variable_match else None

    # Extract function call arguments
    function_call_match = re.search(function_call_regex, input_str)
    if function_call_match:
        first_argument = function_call_match.group(1)
        second_argument = function_call_match.group(2)
    else:
        first_argument = None
        second_argument = None
    first_argument='"'+str(first_argument)+'"'
    # print("Variable Name:", variable_name)
    # print("First Argument:", first_argument)
    # print("Second Argument:", second_argument)
    return str(variable_name), first_argument, str(second_argument)

def find_var(orch_path,var='Async'):
    with open(orch_path, 'r') as file_ptr:
        lines = file_ptr.readlines()
    n = len(lines)
    variable_name_list=[]
    i=0
    while i<n:
        line= lines[i]
        if var in line:
            dl=lines[i+1]
            # print(dl)
            variable_regex = r'^\s*([a-zA-Z_]\w*)\s*='
            variable_match = re.match(variable_regex, dl)
            variable_name = variable_match.group(1) if variable_match else None
            variable_name_list.append(variable_name)
            i += 2
        i +=1
    return variable_name_list


def add_poll(orch_path, async_var_name_list,out_orch_path):
    with open(orch_path, 'r') as file_ptr:
        lines = file_ptr.readlines()

    found_var = False
    x=True
    new_lines = []
    list_ptr = 0
    list_size = len(async_var_name_list)
    total_lines = len(lines)
    i = 0
    while i<total_lines:
        if list_ptr<list_size and async_var_name_list[list_ptr] in lines[i] :
            var1, func1_name, func1_inp = extract_var(lines[i])
            func2_op, func2_name, var1 = extract_var(lines[i+1])
            new_code= '\n\t'+ func2_op +' = '+ func1_inp
            new_code += '\n\twhile True:'
            new_code +='\n\t\t' + var1 + ' = ' + 'yield context.call_activity(' + func1_name + ','+ func2_op +')'
            new_code +='\n\t\t' + func2_op + ' = ' + 'yield context.call_activity(' + func2_name + ','+ var1 +')'
            new_code +='\n\t\t' + 'if checkPoll(' + func2_op + '):'
            new_code +='\n\t\t\tbreak\n\n'
            # print("New code:",new_code) 
            new_lines.append(new_code)
            i+=1
            list_ptr+=1
        else:
            if "def orchestrator_function" in lines[i]:
                new_code ='def checkPoll(obj):\n\tbody=unmarshall(json.loads(obj)).get_body()\n\treturn True if body["Poll"] == "Yes" else False\n'
                new_lines.append(new_code)
            new_lines.append(lines[i])
        i += 1
    # print("New_lines:",new_lines)
    # Write the modified content back to the file
    with open(out_orch_path, 'w') as file_ptr:
        file_ptr.write(''.join(new_lines))
    os.system(f"autopep8 --in-place {out_orch_path}")
class async_update:
    def orchestrator_async_update(in_orchestrator_path,out_orchestrator_path):
        async_var_name_list = find_var(in_orchestrator_path)
        # print("Variable name:", async_var_name_list)
        add_poll(in_orchestrator_path,async_var_name_list,out_orchestrator_path)

# input_path='/home/tarun/Azure/ip_orchestrtor.py'
# output_path='/home/tarun/Azure/out_orch.py'
# orchestrator_update.orchestrator_async_update(input_path,output_path)