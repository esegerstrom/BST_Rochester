function combine_node_and_meter_dumps(root_dir, substation_name, csv_suffix)
    file_path = "$(root_dir)/Feeder_Data/$(substation_name)/Output_Data/"
    meter_test = "$(file_path)meter_$(csv_suffix).csv"
    if isfile(meter_test)
        node_file_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/node_$(csv_suffix).csv",skipto=10,header=9) |> DataFrame
        meter_file_df = CSV.File(root_directory * "Feeder_Data/$(substation_name)/Output_Data/meter_$(csv_suffix).csv",skipto=10,header=9) |> DataFrame
        cols_to_append = names(meter_file_df)[2:end]
        combined_df = hcat(node_file_df, meter_file_df[!, cols_to_append])
    end
    return combined_df
end

