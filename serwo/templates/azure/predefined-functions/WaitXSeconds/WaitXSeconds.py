from python.src.utils.classes.commons.serwo_objects import SerWOObject, SerWOObjectsList
import logging
import time
# import sys
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
def merge_serwo_objects(list_xfaas_obj):
    merged_dict = {}
    xfaas_obj_list=list_xfaas_obj.get_objects()
    # print(type(xfaas_obj_list))
    # returnbody = {}
    # returnbody["RESULT"] = {}
    for i,body in enumerate(xfaas_obj_list):
        # print(type(xfaas_obj))
        # print(aggregate(body, returnbody))
        # print(body)
        # print(type(d))
        # print(d)
        d = body.get_body()
        for key, value in d.items():
            if key in merged_dict:
                # If the key already exists and the value is not the same, append to list
                if isinstance(merged_dict[key], list):
                    if value not in merged_dict[key]:
                        merged_dict[key].append(value)
                else:
                    # If the value is different, create a list with both values
                    if merged_dict[key] != value:
                        merged_dict[key] = [merged_dict[key], value]
            else:
                # If the key does not exist, add it to the merged dictionary
                merged_dict[key] = value
    return merged_dict

def user_function(xfaas_object) -> SerWOObject:
  try:
    logging.info("We are in the sleep fn")
    wait_time=0
    body=xfaas_object.get_body()
    if isinstance(xfaas_object,SerWOObjectsList):
        newbody=merge_serwo_objects(xfaas_object)
        wait_time = newbody["time"]
        new_xfaas_object = SerWOObject(body=newbody)
    else:
      wait_time = body["time"]
      new_xfaas_object=xfaas_object
    time.sleep(wait_time)
    return new_xfaas_object
  except Exception as e:
    logging.info(e)
    logging.info(e)
    logging.info("Error in Sleep function")
    raise Exception("[SerWOLite-Error]::Error at user function",e)

# x={'job_id': 'cnldvmttjerd52himaog'}
# z=user_function(SerWOObject(body=x))
# print("Z's value:",z.get_body())