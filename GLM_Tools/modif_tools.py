import os
import re
import pickle
import numpy as np
import shutil
import GLM_Tools.PowerSystemModel as psm
import GLM_Tools.parsing_tools as glm_parser

def modify_glm_clock(substation_name,start_time,end_time):

    glm_file_dir = f"Feeder_Data/{substation_name}/Input_Data/"
    glm_file_name = f"{substation_name}_Helics.glm"
    glm_file = os.path.join(glm_file_dir,glm_file_name)

    new_glm_file_name = f"{substation_name}_Helics_Mod.glm"
    new_glm_file = os.path.join(glm_file_dir,new_glm_file_name)

    with open(glm_file, 'r') as file:
        glm_data = file.read()

    clock_match = re.search(r"clock \{[^{}]*\}", glm_data, re.S)
    clock_obj = clock_match.group(0)

    old_time_match = re.search(r"starttime ([^;]*); stoptime ([^;]*);", clock_obj, re.S)

    new_time = f"starttime \"{start_time} UTC\"; stoptime \"{end_time} UTC\";" # Note: Times not actually in UTC

    new_clock_obj = clock_obj[:old_time_match.start()] + new_time + clock_obj[old_time_match.end():]

    new_glm_data = glm_data[:clock_match.start()] + new_clock_obj + glm_data[clock_match.end():]

    with open(new_glm_file, 'w') as file:
        file.write(new_glm_data)

def modify_reg_controls(substation_name,regulator_control):

    glm_file_dir = f"Feeder_Data/{substation_name}/Input_Data/"
    glm_file_name = f"{substation_name}_Helics_Mod.glm"
    glm_file = os.path.join(glm_file_dir,glm_file_name)

    with open(glm_file, 'r') as file:
        glm_data = file.read()

    new_glm_data = glm_data
    for reg_config_obj in re.finditer(r"object regulator_configuration \{[^{}]*\}", new_glm_data, re.S):
        reg_config = reg_config_obj.group(0)
        control_match = re.search(r"Control\s+([^\s][^;]*);", reg_config, re.S)
        old_control = control_match.group(1)
        new_config = re.sub(old_control,regulator_control,reg_config)
        new_glm_data = new_glm_data.replace(reg_config,new_config)
        
    with open(glm_file, 'w') as file:
        file.write(new_glm_data)


def create_subfeeder(substation_name, subfeeder_name, start_node_name, branches_to_remove):

    new_substation_name = f"{substation_name}_{subfeeder_name}"

    pkl_file_dir = f"Feeder_Data/{substation_name}/Python_Model/"
    pkl_file_name = f"{substation_name}_Model.pkl"
    pkl_file = os.path.join(pkl_file_dir,pkl_file_name)

    with open(pkl_file, 'rb') as file:
        pkl_model = pickle.load(file)

    start_node = pkl_model.Node_Dict[start_node_name]

    # depth first search
    New_Nodes = []
    New_Branches = []
    has_swing = False
    visited_nodes = set()
    visited_branches = set()
    nodes_to_visit = [start_node.index]
    while nodes_to_visit:
        node_ind = nodes_to_visit.pop()
        if node_ind not in visited_nodes:
            visited_nodes.add(node_ind)
            node = pkl_model.Nodes[node_ind]
            New_Nodes.append(node)
            if node.node_type == "SWING":
                has_swing = True
            for branch_ind in node.outgoing_branches:
                branch = pkl_model.Branches[branch_ind]
                if branch.name not in branches_to_remove:
                    if branch.from_node_ind != node_ind:
                        ValueError(f"Outgoing branch ({branch_ind}) from_node_ind ({branch.from_node_ind}) doesn't match node_ind {node_ind}")
                    if branch.to_node_ind not in visited_nodes:
                        nodes_to_visit.append(branch.to_node_ind)
                    if branch.index not in visited_branches:
                        New_Branches.append(branch)
                        visited_branches.add(branch.index)

            for branch_ind in node.incoming_branches:
                branch = pkl_model.Branches[branch_ind]
                if branch.name not in branches_to_remove:
                    if branch.to_node_ind != node_ind:
                        ValueError(f"Incoming branch ({branch_ind}) to_node_ind ({branch.to_node_ind}) doesn't match node_ind {node_ind}")
                    if branch.from_node_ind not in visited_nodes:
                        nodes_to_visit.append(branch.from_node_ind)
                    if branch.index not in visited_branches:
                        New_Branches.append(branch)
                        visited_branches.add(branch.index)
            
            for child_ind in node.child_nodes:
                nodes_to_visit.append(child_ind)

    # add relevant loads to the new model
    New_Loads = []
    for Load in pkl_model.Loads:
        if Load.parent_node_ind in visited_nodes:
            New_Loads.append(Load)

    # add relevant loads to the new model
    New_Generators = []
    for Generator in pkl_model.Generators:
        if Generator.parent_node_ind in visited_nodes:
            New_Generators.append(Generator)

    # add relevant shunts to the new model
    New_Shunts = []
    for Shunt in pkl_model.Shunts:
        if Shunt.parent_node_ind in visited_nodes:
            New_Shunts.append(Shunt)

    # add relevant configs to the new model
    New_Configs = []
    configs_visited = set()
    for Branch in New_Branches:
        if hasattr(Branch, 'config'):
            config_name = Branch.config
            if config_name not in pkl_model.Config_Dict:
                raise ValueError(f"Could not find line config object: {config_name}")
            branch_config = pkl_model.Config_Dict[config_name] 
            if branch_config.index not in configs_visited:
                New_Configs.append(branch_config)
                configs_visited.add(branch_config.index)

    # make sure there is a swing node in the model
    if not has_swing:
        # change first node (start_node) to swing node
        New_Nodes[0].node_type = "SWING"
        Vbase = New_Nodes[0].Vbase
        voltage_A = Vbase
        voltage_B = Vbase*np.exp(1j*(-2*np.pi/3))
        voltage_C = Vbase*np.exp(1j*(2*np.pi/3))
        voltage_A_str = "{:+}{:+}j".format(voltage_A.real, voltage_A.imag)
        voltage_B_str = "{:+}{:+}j".format(voltage_B.real, voltage_B.imag)
        voltage_C_str = "{:+}{:+}j".format(voltage_C.real, voltage_C.imag)
        old_glm_string = New_Nodes[0].glm_string 
        add_swing_string = f"bustype SWING; voltage_A {voltage_A_str}; voltage_B {voltage_B_str}; voltage_C {voltage_C_str}; "
        new_glm_string = old_glm_string[:-1] + add_swing_string + old_glm_string[-1]
        New_Nodes[0].glm_string = new_glm_string
    
    # Create a new model
    New_Model = psm.PowerSystemModel(New_Nodes,New_Branches,New_Loads,New_Generators,New_Shunts,New_Configs)

    New_Model.compute_impedances()

    # update header, helics object, and recorder objects
    New_Model.glm_header = pkl_model.glm_header
    New_Model.glm_helics_obj = pkl_model.glm_helics_obj.replace(substation_name,new_substation_name)
    new_glm_misc_objs = []
    for misc_obj in pkl_model.glm_misc_objs:
        new_misc_obj = misc_obj.replace(substation_name,new_substation_name)
        # update substation recorder parent
        if "substation_power.csv" in new_misc_obj:
            parent_match = re.search(r"parent\s+([^\s][^;]*);", new_misc_obj, re.S)
            if parent_match:
                parent = parent_match.group(1)
            else:
                raise ValueError(f"Could not find parent of substation recorder object: {new_misc_obj}")
            new_parent = New_Branches[0].name
            new_misc_obj = new_misc_obj.replace(parent,new_parent)
        new_glm_misc_objs.append(new_misc_obj)
    New_Model.glm_misc_objs = new_glm_misc_objs
    

    # Save the new power system model to a .pkl
    new_pkl_file_dir = f"Feeder_Data/{new_substation_name}/Python_Model/"
    new_pkl_file_name = f"{new_substation_name}_Model.pkl"
    new_pkl_file = os.path.join(new_pkl_file_dir,new_pkl_file_name)
    if not os.path.exists(new_pkl_file_dir):
        os.makedirs(new_pkl_file_dir)
    with open(new_pkl_file, 'wb') as file:
        pickle.dump(New_Model, file)

    # write a glm file for the new model
    new_glm_file_dir = f"Feeder_Data/{new_substation_name}/Input_Data/"
    new_glm_file_name = f"{new_substation_name}_Helics.glm"
    new_glm_file = os.path.join(new_glm_file_dir,new_glm_file_name)

    if not os.path.exists(new_glm_file_dir):
        os.makedirs(new_glm_file_dir)
    glm_parser.create_glm_from_pkl(new_pkl_file,new_glm_file)

    print(f"Created a new subfeeder ({subfeeder_name}) for {substation_name}. Python model saved to {new_pkl_file}. GridLAB-D model saved to {new_glm_file}")

    # copy over the files we need to run the simulation
    shutil.copy(f"Feeder_Data/{substation_name}/meter_number_data.csv",f"Feeder_Data/{new_substation_name}/")
    shutil.copy(f"Feeder_Data/{substation_name}/gen_meter_number_data.csv",f"Feeder_Data/{new_substation_name}/")
    if not os.path.exists(f"Feeder_Data/{new_substation_name}/AMI_Data/"):
        os.makedirs(f"Feeder_Data/{new_substation_name}/AMI_Data/")
    shutil.copy(f"Feeder_Data/{substation_name}/AMI_Data/{substation_name}_True_Load_AMI_Data.csv",f"Feeder_Data/{new_substation_name}/AMI_Data/{new_substation_name}_True_Load_AMI_Data.csv")
    shutil.copy(f"Feeder_Data/{substation_name}/AMI_Data/{substation_name}_True_Gen_AMI_Data.csv",f"Feeder_Data/{new_substation_name}/AMI_Data/{new_substation_name}_True_Gen_AMI_Data.csv")
    if not os.path.exists(f"Feeder_Data/{new_substation_name}/Coordinate_Data/"):
        os.makedirs(f"Feeder_Data/{new_substation_name}/Coordinate_Data/")
    shutil.copy(f"Feeder_Data/{substation_name}/Coordinate_Data/{substation_name}_Branch_Coords.xls",f"Feeder_Data/{new_substation_name}/Coordinate_Data/{new_substation_name}_Branch_Coords.xls")