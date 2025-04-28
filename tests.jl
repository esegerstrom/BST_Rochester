using PyCall
using SparseArrays
using Plots
gr()
using ColorTypes
using Colors
using JuMP
using Ipopt
# import HSL_jll
using LinearAlgebra
using CSV
using DataFrames
include("Opt_Tools/modif_tools.jl")

# Import Python modules
pickle = pyimport("pickle")
pushfirst!(pyimport("sys")."path", "")
pyimport("GLM_Tools")

# Load the .pkl file 
CYME_flag = 1
root_directory = "C:/Users/egseg/"
substation_name = "Rochester_1_05"
fname = root_directory * "Feeder_Data/$(substation_name)/Python_Model/$(substation_name)_Model.pkl"
pkl_file_05 = open(fname, "r")
psm = pickle.load(pkl_file_05)
close(pkl_file_05)

gld_node_mags_A_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_A")
gld_node_mags_B_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_B")
gld_node_mags_C_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_C")

gld_node_angs_A_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_A")
gld_node_angs_B_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_B")
gld_node_angs_C_df_05 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_C")

Vph_gld_05 = zeros(ComplexF64, 3, n_nodes)
for (nd_ind, Node) in enumerate(psm.Nodes)
    Vmag_a = gld_node_mags_A_df_05[t_ind,Node.name]
    Vang_a = gld_node_angs_A_df_05[t_ind,Node.name]
    Vmag_b = gld_node_mags_B_df_05[t_ind,Node.name]
    Vang_b = gld_node_angs_B_df_05[t_ind,Node.name]
    Vmag_c = gld_node_mags_C_df_05[t_ind,Node.name]
    Vang_c = gld_node_angs_C_df_05[t_ind,Node.name]
    Vph_gld_05[1,nd_ind] = Vmag_a*exp(1im*Vang_a)/Node.Vbase
    Vph_gld_05[2,nd_ind] = Vmag_b*exp(1im*Vang_b)/Node.Vbase
    Vph_gld_05[3,nd_ind] = Vmag_c*exp(1im*Vang_c)/Node.Vbase
end

# Load the other .pkl file 
substation_name = "Rochester_1_5"
fname = root_directory * "Feeder_Data/$(substation_name)/Python_Model/$(substation_name)_Model.pkl"
pkl_file_5 = open(fname, "r")
psm = pickle.load(pkl_file_5)
close(pkl_file_5)

gld_node_mags_A_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_A")
gld_node_mags_B_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_B")
gld_node_mags_C_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_C")

gld_node_angs_A_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_A")
gld_node_angs_B_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_B")
gld_node_angs_C_df_5 = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_C")

Vph_gld_5 = zeros(ComplexF64, 3, n_nodes)
for (nd_ind, Node) in enumerate(psm.Nodes)
    Vmag_a = gld_node_mags_A_df_5[t_ind,Node.name]
    Vang_a = gld_node_angs_A_df_5[t_ind,Node.name]
    Vmag_b = gld_node_mags_B_df_5[t_ind,Node.name]
    Vang_b = gld_node_angs_B_df_5[t_ind,Node.name]
    Vmag_c = gld_node_mags_C_df_5[t_ind,Node.name]
    Vang_c = gld_node_angs_C_df_5[t_ind,Node.name]
    Vph_gld_5[1,nd_ind] = Vmag_a*exp(1im*Vang_a)/Node.Vbase
    Vph_gld_5[2,nd_ind] = Vmag_b*exp(1im*Vang_b)/Node.Vbase
    Vph_gld_5[3,nd_ind] = Vmag_c*exp(1im*Vang_c)/Node.Vbase
end

abs.(Vph_gld_05)
abs.(Vph_gld_5)

abs.(Vph_gld_05)==abs.(Vph_gld_5)

gld_node_mags_A_df_5 == gld_node_mags_A_df_05