import GLM_Tools.parsing_tools as glm_parser
import GLM_Tools.modif_tools as glm_modif_tools
import os

CYME_flag = 1
root_dir = "C:/Users/egseg"
substation_name = "Rochester_1"
subfeeder_name = "N_test"
start_node = "node_2388"
#branches_to_remove = ["overhead_line1835", "overhead_line1668", "overhead_line1024"]
#branches_to_remove = ["overhead_line1668", "overhead_line1024", "overhead_line702", "overhead_line2176"]
branches_to_remove = ["overhead_line2079"]
#branches_to_remove = ["overhead_line 461", "overhead_line1648", "overhead_line216"]
#branches_to_remove = ["overhead_line216", "overhead_line1835", "overhead_line_2_158"] # test
#branches_to_remove = ["overhead_line1648", "overhead_line_2_117"] # test_2

glm_modif_tools.create_subfeeder(root_dir, substation_name, subfeeder_name, CYME_flag, start_node, branches_to_remove)


