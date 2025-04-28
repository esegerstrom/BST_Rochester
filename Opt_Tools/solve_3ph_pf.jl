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
include("modif_tools.jl")

# Import Python modules
pickle = pyimport("pickle")
pushfirst!(pyimport("sys")."path", "")
pyimport("GLM_Tools")

# Load the .pkl file 
CYME_flag = 1
root_directory = "C:/Users/egseg/"
substation_name = "Rochester_1_5"
fname = root_directory * "Feeder_Data/$(substation_name)/Python_Model/$(substation_name)_Model.pkl"
pkl_file = open(fname, "r")
psm = pickle.load(pkl_file)
close(pkl_file)

# get network info
n_nodes = length(psm.Nodes)
n_branches = length(psm.Branches)

# Substation Voltage
V0_mag = 1
V0_ref = V0_mag*[1,exp(-im*2*pi/3),exp(im*2*pi/3)]

# Model Setup
model = Model(Ipopt.Optimizer)
linear_solver = "mumps"
if linear_solver in ["ma27","ma57","ma77","ma86","ma97"]
    set_attribute(model, "hsllib", HSL_jll.libhsl_path)
    set_attribute(model, "linear_solver", linear_solver)
elseif linear_solver == "mumps"
    set_attribute(model, "linear_solver", linear_solver)
else
    throw(ArgumentError("linear_solver $linear_solver not supported."))
end

# Variable Definitions
@variable(model, Vph_real[ph=1:3,1:n_nodes], start=real(V0_ref[ph]*exp(-im*pi/6)))
@variable(model, Vph_imag[ph=1:3,1:n_nodes], start=imag(V0_ref[ph]*exp(-im*pi/6)))
@variable(model, Iph_real[1:3,1:n_branches], start=0)
@variable(model, Iph_imag[1:3,1:n_branches], start=0)

set_start_value.(Vph_real[:,1], real(V0_ref))
set_start_value.(Vph_imag[:,1], imag(V0_ref))

# Complex Variable Expressions
@expression(model, Vph, Vph_real.+im*Vph_imag)
@expression(model, Iph, Iph_real.+im*Iph_imag)

# Substation Voltage Constraint
@constraint(model, Vph[:,1] .== V0_ref)

# Power Flow Constraints
pb_lhs = zeros(GenericQuadExpr{ComplexF64, VariableRef}, 3, n_nodes)
pb_rhs = zeros(GenericQuadExpr{ComplexF64, VariableRef}, 3, n_nodes)
for (br_ind,Branch) in enumerate(psm.Branches)
    # skip open branches
    if Branch.type == "switch" 
        if Branch.status == "OPEN"
            Iph[:,br_ind] .== 0.0
            continue
        end
    end
    from_node_ind = Branch.from_node_ind+1
    to_node_ind = Branch.to_node_ind+1
    # "Ohm's law"
    @constraint(model, Vph[:,from_node_ind] .== Branch.A_br*Vph[:,to_node_ind] + Branch.B_br*Iph[:,br_ind])
    # Add branch flows to power balance expressions
    pb_lhs[:,to_node_ind] += diag(Vph[:,to_node_ind]*Iph[:,br_ind]')
    pb_rhs[:,from_node_ind] += diag(Branch.A_br*Vph[:,to_node_ind]*Iph[:,br_ind]'*(Branch.D_br')+Branch.B_br*Iph[:,br_ind]*Iph[:,br_ind]'*(Branch.D_br'))
end


# Power Injection Constraints
t_ind = 1
s_load = zeros(GenericQuadExpr{ComplexF64, VariableRef}, 3, n_nodes)
for (ld_ind, Load) in enumerate(psm.Loads)
    if haskey(Load,"Sload")
        #s_load[:,Load.parent_node_ind+1] += Load.Sload[t_ind,:]
        s_load[:,Load.parent_node_ind+1] += Load.Sload
    end
end
s_gen = zeros(GenericQuadExpr{ComplexF64, VariableRef}, 3, n_nodes)
for (gen_ind, Gen) in enumerate(psm.Generators)
    if haskey(Gen,"Sgen")
        s_gen[:,Gen.parent_node_ind+1] += Gen.Sgen[t_ind,:]
    end
end
for (sht_ind, Shunt) in enumerate(psm.Shunts)
    if Shunt.type == "capacitor"
        status = zeros(Int, 3, 1)
        if Shunt.switchA == "CLOSED"
            status[1] = 1
        end
        if Shunt.switchB == "CLOSED"
            status[2] = 1
        end
        if Shunt.switchC == "CLOSED"
            status[3] = 1
        end
        parent_node_ind = Shunt.parent_node_ind+1
        s_load[:,parent_node_ind] += status.*diag(Vph[:,parent_node_ind]*Vph[:,parent_node_ind]'*conj(Shunt.Ycap))
    end
end
@constraint(model, pb_rhs[:,2:end] - pb_lhs[:,2:end] .== s_gen[:,2:end]-s_load[:,2:end])

# Objective
# @objective(model, Min, sum(real(s_inj[:,1])))

# print(model)
optimize!(model)

## Compare results to GLD
output_file_path = "$(root_directory)/Feeder_Data/$(substation_name)/Output_Data/"
meter_test = "$(output_file_path)meter_voltage_mags_A.csv"
if isfile(meter_test)
    gld_node_mags_A_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_A")
    gld_node_mags_B_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_B")
    gld_node_mags_C_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_mags_C")

    gld_node_angs_A_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_A")
    gld_node_angs_B_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_B")
    gld_node_angs_C_df = combine_node_and_meter_dumps(root_directory, substation_name, "voltage_angs_C")
else
    gld_node_mags_A_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_mags_A.csv",skipto=10,header=9) |> DataFrame
    gld_node_mags_B_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_mags_B.csv",skipto=10,header=9) |> DataFrame
    gld_node_mags_C_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_mags_C.csv",skipto=10,header=9) |> DataFrame

    gld_node_angs_A_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_angs_A.csv",skipto=10,header=9) |> DataFrame
    gld_node_angs_B_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_angs_B.csv",skipto=10,header=9) |> DataFrame
    gld_node_angs_C_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_voltage_angs_C.csv",skipto=10,header=9) |> DataFrame
end

Vph_gld = zeros(ComplexF64, 3, n_nodes)
for (nd_ind, Node) in enumerate(psm.Nodes)
    Vmag_a = gld_node_mags_A_df[t_ind,Node.name]
    Vang_a = gld_node_angs_A_df[t_ind,Node.name]
    Vmag_b = gld_node_mags_B_df[t_ind,Node.name]
    Vang_b = gld_node_angs_B_df[t_ind,Node.name]
    Vmag_c = gld_node_mags_C_df[t_ind,Node.name]
    Vang_c = gld_node_angs_C_df[t_ind,Node.name]
    Vph_gld[1,nd_ind] = Vmag_a*exp(1im*Vang_a)/Node.Vbase
    Vph_gld[2,nd_ind] = Vmag_b*exp(1im*Vang_b)/Node.Vbase
    Vph_gld[3,nd_ind] = Vmag_c*exp(1im*Vang_c)/Node.Vbase
end

# correct for missing phases
Vph_opt = value.(Vph)
for (nd_ind,Node) in enumerate(psm.Nodes)
    if ~occursin("A",Node.phases)
        Vph_opt[1,nd_ind] = 0.0
    end
    if ~occursin("B",Node.phases)
        Vph_opt[2,nd_ind] = 0.0
    end
    if ~occursin("C",Node.phases)
        Vph_opt[3,nd_ind] = 0.0
    end
end

mag_err = abs.(Vph_opt)-abs.(Vph_gld)
p2 = plot(1:n_nodes,transpose(mag_err),label=["Phase A" "Phase B" "Phase C"])
xlabel!("Node Index")
ylabel!("Absolute Voltage Magnitude Error (pu)")
display(p2)

ang_err = angle.(Vph_opt)-angle.(Vph_gld)
p3 = plot(1:n_nodes,transpose(ang_err),label=["Phase A" "Phase B" "Phase C"])
xlabel!("Node Index")
ylabel!("Absolute Voltage Angle Error (rad)")
display(p3)

# visualize feeder
node_Xcoords = [Node.X_coord for Node in psm.Nodes]
node_Ycoords = [Node.Y_coord for Node in psm.Nodes]
node_colormap = cgrad(:turbo)
colorbar_title = "Voltage (p.u.)"
#colorbar_ticks = 0.9:0.05:1.1
Vph_mag = abs.(value.(Vph))
Vmin = minimum([filter(!iszero, c) for c in eachcol(Vph_mag)])[1]
Vmax = maximum(Vph_mag)[1]
colorbar_ticks = Vmin:0.05:Vmax
# Vmin = 0.95
# Vmax = 1.05
Vmag_out_a = Vph_mag[1,:]
Vmag_out_b = Vph_mag[2,:]
Vmag_out_c = Vph_mag[3,:]
norm_Vmag_out_a = (Vmag_out_a .- Vmin) ./ (Vmax-Vmin)
norm_Vmag_out_b = (Vmag_out_b .- Vmin) ./ (Vmax-Vmin)
norm_Vmag_out_c = (Vmag_out_c .- Vmin) ./ (Vmax-Vmin)
node_colors_a = [get(node_colormap,val) for val in norm_Vmag_out_a]
node_colors_b = [get(node_colormap,val) for val in norm_Vmag_out_b]
node_colors_c = [get(node_colormap,val) for val in norm_Vmag_out_c]

vis_plt = plot(layout=grid(1,3, widths=(1/3,1/3,1/3)), size=(1200,300))
if CYME_flag != 1
    for (br_ind,Branch) in enumerate(psm.Branches)
        plot!([Branch.X_coord,Branch.X2_coord],[Branch.Y_coord,Branch.Y2_coord],color=:black,subplot=1)
        plot!([Branch.X_coord,Branch.X2_coord],[Branch.Y_coord,Branch.Y2_coord],color=:black,subplot=2)
        plot!([Branch.X_coord,Branch.X2_coord],[Branch.Y_coord,Branch.Y2_coord],color=:black,subplot=3)
    end
    for (nd_ind,Node) in enumerate(psm.Nodes)
        if occursin("A",Node.phases)
            plot!([Node.X_coord],[Node.Y_coord],seriestype=:scatter,color=node_colors_a[nd_ind],markersize=3,subplot=1)
        end
        if occursin("B",Node.phases)
            plot!([Node.X_coord],[Node.Y_coord],seriestype=:scatter,color=node_colors_b[nd_ind],markersize=3,subplot=2)
        end
        if occursin("C",Node.phases)
            plot!([Node.X_coord],[Node.Y_coord],seriestype=:scatter,color=node_colors_c[nd_ind],markersize=3,subplot=3)
        end
    end
else
    # Get indices of substation nodes 
    node_file = joinpath(root_directory, "Feeder_Data", substation_name, "Coordinate_Data", "Nodes.csv")
    nodes = CSV.read(node_file, DataFrame)
    node_keys = names(nodes)
    node_xs  = nodes[:, node_keys[5]]
    substation_inds = findall(x -> x == minimum(node_xs), node_xs)

    for (br_ind,Branch) in enumerate(psm.Branches)
        branch_from_ind = split(Branch.from_node, "_")
        branch_to_ind = split(Branch.to_node, "_")

        for ii in 1:length(branch_from_ind)
            if all(isdigit,branch_from_ind[ii])
                branch_from_ind = branch_from_ind[ii:end]
                break
            end
        end
        for ii in 1:length(branch_to_ind)
            if all(isdigit,branch_to_ind[ii])
                branch_to_ind = branch_to_ind[ii:end]
                break
            end
        end
        # Only include nodes in plot if they are not substation nodes
        include_branch = true
        for x in branch_from_ind
            if parse(Int, x)+1 in substation_inds
                println("Excluded from_node index: ", x)
                include_branch = false
                break
            end
        end
        for x in branch_to_ind
            if parse(Int, x)+1 in substation_inds
                println("Excluded to_node index: ", x)
                include_branch = false
                break
            end
        end
        if include_branch
            plot!(vis_plt[1], [Branch.X_coord[],Branch.X2_coord[]],[Branch.Y_coord[],Branch.Y2_coord[]],color=:black)
            plot!(vis_plt[2], [Branch.X_coord[],Branch.X2_coord[]],[Branch.Y_coord[],Branch.Y2_coord[]],color=:black)
            plot!(vis_plt[3], [Branch.X_coord[],Branch.X2_coord[]],[Branch.Y_coord[],Branch.Y2_coord[]],color=:black)
        end
    end

    for (nd_ind,Node) in enumerate(psm.Nodes)
        node_ind = split(Node.name, "_")
        for ii in 1:length(node_ind)
            if all(isdigit,node_ind[ii])
                node_ind = node_ind[ii:end]
                break
            end
        end
        include_node = true
        for x in node_ind
            if parse(Int, x)+1 in substation_inds
                println("Excluded node index: ", x)
                include_node = false
                break
            end
        end

        if include_node
            if occursin("A",Node.phases)
                plot!(vis_plt[1], [Node.X_coord[]],[Node.Y_coord[]],
                        seriestype=:scatter,
                        marker_z=Vmag_out_a[nd_ind],  # Use unnormalized voltage magnitude
                        color=node_colormap,
                        clims=(Vmin, Vmax),
                        colorbar=false,
                        colorbar_title = colorbar_title,
                        colorbar_ticks = colorbar_ticks,
                        markersize=3)
            end
            if occursin("B",Node.phases)
                plot!(vis_plt[2], [Node.X_coord[]],[Node.Y_coord[]],
                        seriestype=:scatter,
                        marker_z=Vmag_out_b[nd_ind],  # Use unnormalized voltage magnitude
                        color=node_colormap,
                        clims=(Vmin, Vmax),
                        colorbar=false,
                        colorbar_title = colorbar_title,
                        colorbar_ticks = colorbar_ticks,
                        markersize=3)
            end
            if occursin("C",Node.phases)
                plot!(vis_plt[3], [Node.X_coord[]],[Node.Y_coord[]],
                        seriestype=:scatter,
                        marker_z=Vmag_out_c[nd_ind],  # Use unnormalized voltage magnitude
                        color=node_colormap,
                        clims=(Vmin, Vmax),
                        colorbar=true,
                        colorbar_title = colorbar_title,
                        colorbar_ticks = colorbar_ticks,
                        markersize=3)
            end
        end
    end
end

plot!(title="Phase A",xformatter=:none,yformatter=:none,legend=:false,subplot=1)
plot!(title="Phase B",xformatter=:none,yformatter=:none,legend=:false,subplot=2)
plot!(title="Phase C",xformatter=:none,yformatter=:none,legend=:false,subplot=3)
display(vis_plt)


# # cb_plt = heatmap(rand(2,2), clims=(Vmin,Vmax),  right_margin = 10Plots.mm, framestyle=:none, c=node_colormap, cbar=true, lims=(-1,0),colorbar_title = " \nVoltage Magnitude (pu)")
# # display(cb_plt)
