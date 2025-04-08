import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Function to read CSV and plot data for multiple asset IDs within a specified date range
def plot_asset_data_by_index(file_path, asset_indices, start_date, end_date):
    # Read the CSV file
    data = pd.read_csv(file_path, parse_dates=['start_date_time'])

    # Get the list of asset IDs (column names), excluding the 'start_date_time' column
    asset_ids = data.columns[1:]  # Assuming the first column is 'start_date_time'

    # Validate the asset indices
    invalid_indices = [idx for idx in asset_indices if idx < 0 or idx >= len(asset_ids)]
    if invalid_indices:
        print(f"Invalid asset indices: {invalid_indices}. Available indices: 0 to {len(asset_ids) - 1}.")
        return

    # Filter data for the specified date range
    mask = (data['start_date_time'] >= start_date) & (data['start_date_time'] <= end_date)
    filtered_data = data.loc[mask]

    # Check if there's data to plot
    if filtered_data.empty:
        print("No data available for the specified date range.")
        return

    # Plotting
    plt.figure(figsize=(10, 6))

    for asset_index in asset_indices:
        # Get the selected asset ID based on the index
        asset_id = asset_ids[asset_index]
        
        # Plot the asset data
        plt.step(filtered_data['start_date_time'], filtered_data[asset_id], where='pre', label=f'Asset {asset_id}')
    
    plt.axhline(0, color='red', linestyle='--', linewidth=1)
    plt.title(f'Energy Consumption for Meters from {start_date} to {end_date}')
    plt.xlabel('Date')
    plt.ylabel('Energy (kWh)')
    plt.xticks(rotation=45)
    plt.legend(title="Asset IDs")
    plt.grid()
    plt.tight_layout()

# Function to read CSV and plot data for a specific asset ID and date range
def plot_asset_data_by_ids(file_path, asset_ids, start_date, end_date):
    # Read the CSV file
    data = pd.read_csv(file_path, parse_dates=['start_date_time'])

    # Validate the asset ids
    invalid_ids = [id for id in asset_ids if id not in data.columns[1:]]
    if invalid_ids:
        print(f"Invalid asset ids: {invalid_ids}.")
        print(len(invalid_ids))

    # Filter data for the specified date range
    mask = (data['start_date_time'] >= start_date) & (data['start_date_time'] <= end_date)
    filtered_data = data.loc[mask]

    # Check if there's data to plot
    if filtered_data.empty:
        print("No data available for the specified date range.")
        return

    # Plotting
    plt.figure(figsize=(10, 6))

    for asset_id in asset_ids:
        if asset_id not in invalid_ids:
            # Plot the asset data
            plt.step(filtered_data['start_date_time'], filtered_data[asset_id], where='pre', label=f'Asset {asset_id}')
    
    plt.axhline(0, color='red', linestyle='--', linewidth=1)
    plt.title(f'Energy Consumption for Meters from {start_date} to {end_date}')
    plt.xlabel('Date')
    plt.ylabel('Energy (kWh)')
    # plt.ylim([-50,50])
    plt.xticks(rotation=45)
    plt.legend(title="Asset IDs")
    plt.grid()
    plt.tight_layout()

# Function to read CSV and plot data for a specific asset ID and date range
def plot_comp_asset_data_by_ids(file_path1, file_path2, asset_ids1, asset_ids2, start_date, end_date):
    # Read the CSV file
    data1 = pd.read_csv(file_path1, parse_dates=['start_date_time'])
    data2 = pd.read_csv(file_path2, parse_dates=['start_date_time'])

    # Validate the asset ids
    invalid_ids1 = [id for id in asset_ids1 if id not in data1.columns[1:]]
    if invalid_ids1:
        print(f"Invalid asset ids: {invalid_ids1}.")
        print(len(invalid_ids1))

    # Filter data for the specified date range
    mask = (data1['start_date_time'] >= start_date) & (data1['start_date_time'] <= end_date)
    filtered_data1 = data1.loc[mask]

    invalid_ids2 = [id for id in asset_ids2 if id not in data2.columns[1:]]
    if invalid_ids2:
        print(f"Invalid asset ids: {invalid_ids2}.")
        print(len(invalid_ids2))

    # Filter data for the specified date range
    mask = (data1['start_date_time'] >= start_date) & (data1['start_date_time'] <= end_date)
    filtered_data1 = data1.loc[mask]

    mask = (data2['start_date_time'] >= start_date) & (data2['start_date_time'] <= end_date)
    filtered_data2 = data2.loc[mask]

    # Check if there's data to plot
    if filtered_data1.empty:
        print("No data available for the specified date range.")
        return
    
    if filtered_data2.empty:
        print("No data available for the specified date range.")
        return

    # Plotting
    plt.figure(figsize=(10, 6))

    for asset_id in asset_ids1:
        if asset_id not in invalid_ids1:
            # Plot the asset data
            plt.step(filtered_data1['start_date_time'], filtered_data1[asset_id], where='pre', label=f'Asset {asset_id}')

    for asset_id in asset_ids2:
        if asset_id not in invalid_ids2:
            # Plot the asset data
            plt.step(filtered_data2['start_date_time'], filtered_data2[asset_id], where='pre', label=f'Asset {asset_id}', color='orange')
    
    plt.axhline(0, color='red', linestyle='--', linewidth=1)
    plt.title(f'Energy Consumption for Meters from {start_date} to {end_date}')
    plt.xlabel('Date')
    plt.ylabel('Energy (kWh)')
    # plt.ylim([-50,50])
    plt.xticks(rotation=45)
    plt.legend(title="Asset IDs")
    plt.grid()
    plt.tight_layout()

