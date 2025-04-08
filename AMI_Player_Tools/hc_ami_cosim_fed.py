import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import helics as h
import logging
import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE" # Note that this is a bad fix. Should create a seperate python environment
import argparse

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)



def destroy_federate(fed):
    grantedtime = h.helicsFederateRequestTime(fed, h.HELICS_TIME_MAXTIME)
    status = h.helicsFederateDisconnect(fed)
    h.helicsFederateDestroy(fed)
    logger.info("Federate finalized")


if __name__ == "__main__":

    ################################# Parse Command Line Arguments ############################################
    parser = argparse.ArgumentParser()
    parser.add_argument('substation_name', type=str, help='Substation_Name')
    parser.add_argument('start_time', type=str, help='Start time in YYYY-MM-DD hh:mm:ss format')
    parser.add_argument('end_time', type=str, help='End time in YYYY-MM-DD hh:mm:ss format')
    parser.add_argument('load_fixed_pf', type=float, help='Fixed power factor for AMI loads')
    args = parser.parse_args()

    substation_name = args.substation_name

    #################################  Registering  federate from json  ########################################
    fed = h.helicsCreateValueFederateFromConfig(f"Feeder_Data/{substation_name}/Config_Files/{substation_name}_ami_player_config.json")
    federate_name = h.helicsFederateGetName(fed)
    logger.info("HELICS Version: {}".format(h.helicsGetVersion()))
    logger.info("{}: Federate {} has been registered".format(federate_name, federate_name))
    pubkeys_count = h.helicsFederateGetPublicationCount(fed)
    subkeys_count = h.helicsFederateGetInputCount(fed)

    ######################   Reference to Publications and Subscription from index  #############################
    pubid = {}
    subid = {}
    for i in range(0, pubkeys_count):
        pubid["m{}".format(i)] = h.helicsFederateGetPublicationByIndex(fed, i)
        pubtype = h.helicsPublicationGetType(pubid["m{}".format(i)])
        pubname = h.helicsPublicationGetName(pubid["m{}".format(i)])
        logger.info("{}: Registered Publication ---> {}".format(federate_name, pubname))
    for i in range(0, subkeys_count):
        subid["m{}".format(i)] = h.helicsFederateGetInputByIndex(fed, i)
        h.helicsInputSetDefaultComplex(subid["m{}".format(i)], 0, 0)
        sub_key = h.helicsSubscriptionGetTarget(subid["m{}".format(i)])
        logger.info("{}: Registered Subscription ---> {}".format(federate_name, sub_key))

    ######################   Entering Execution Mode  ##########################################################
    h.helicsFederateEnterInitializingMode(fed)
    status = h.helicsFederateEnterExecutingMode(fed)


    ######################   Co-Simulation Timing Setup  ######################################

    # Define the start and end dates as strings
    start_date = args.start_time
    end_date = args.end_time

    # Generate the list of hourly datetimes
    datetimes_list = pd.date_range(start=start_date, end=end_date, freq='h', tz='US/Eastern')

    tsim_hr = len(datetimes_list) # in hours
    tstep_hr = 1 # in hours
    tsim = 60*60*tsim_hr # in seconds
    tstep = 60*60*tstep_hr # in seconds

    ######################   AMI Reading Setup  ######################################

    # Load meter databases
    load_dict_file = f"Feeder_Data/{substation_name}/meter_number_data.csv"
    gen_dict_file = f"Feeder_Data/{substation_name}/gen_meter_number_data.csv"

    load_dict = pd.read_csv(load_dict_file)
    gen_dict = pd.read_csv(gen_dict_file)

    # Load the AMI data
    load_ami_data_file = f"Feeder_Data/{substation_name}/AMI_Data/{substation_name}_True_Load_AMI_Data.csv"
    gen_ami_data_file = f"Feeder_Data/{substation_name}/AMI_Data/{substation_name}_True_Gen_AMI_Data.csv"

    load_ami_data = pd.read_csv(load_ami_data_file)
    gen_ami_data = pd.read_csv(gen_ami_data_file)

    # Convert times to datetime
    load_ami_data['start_date_time'] = pd.to_datetime(load_ami_data['start_date_time'], utc=True)
    gen_ami_data['start_date_time'] = pd.to_datetime(gen_ami_data['start_date_time'], utc=True)

    # Loads to skip: these loads are in GIS but not in WindMil/GLD, need to investigate further...    
    loads_to_skip_file = f"Feeder_Data/{substation_name}/loads_in_gis_but_not_glm.csv"
    gens_to_skip_file = f"Feeder_Data/{substation_name}/gens_in_gis_but_not_glm.csv"

    loads_to_skip_data = pd.read_csv(loads_to_skip_file)
    gens_to_skip_data = pd.read_csv(gens_to_skip_file)

    loads_to_skip = [str(load) for load in loads_to_skip_data['Service Number'].tolist()]
    gens_to_skip = [str(gen) for gen in gens_to_skip_data['Object ID'].tolist()]

    ######################   Heating and Cooling Simulation Setup  ######################################

    # Define constants
    Tstep = tstep # in seconds
    T_On_H = 18 + 273.15
    T_Off_H = 24 + 273.15
    T_On_C = 30 + 273.15
    T_Off_C = 24 + 273.15
    # n = int(8760 * 3600 / Tstep)
    n = tsim_hr+1
    COP_HP_H = 4
    COP_HP_C = 4
    eta_else_H = 0.95
    eta_else_C = 0.95
    Percent_renewable_share_Elec = 90
    kg_CO2_per_m3_NG = 2.2
    kg_CO2_per_kwh_Elec = 0.39
    Percent_HP_H = 50
    Percent_HP_C = 100
    NG_HV = 12.5  # KWh/m3

    # Load the weather data
    weather_data_path = f"Feeder_Data/{substation_name}/Input_Data/Weather.csv"

    weather_data = pd.read_csv(weather_data_path)
    Tamb_column = pd.to_numeric(weather_data.iloc[:, 9], errors='coerce').fillna(0)
    Tamb = Tamb_column.to_numpy() + 273.15

    # Load housing data from Excel
    input_data_path = f"Feeder_Data/{substation_name}/Input_Data/HC_Input_Data.xlsx"
    housing_data = pd.read_excel(input_data_path)

    # Clean housing data
    AA = housing_data.iloc[:, 8].replace({0: 0, 1: 25, 2: 75, 3: 125, 4: 175, 5: 225}).values
    S = housing_data.iloc[:, 10].astype(float).values
    ARR = housing_data.iloc[:, 11].replace({0: 0, 1: 1, 2: 1.5, 3: 2, 4: 3}).values
    gs_meter_number = housing_data.iloc[:, 12]
    gs_service_number = housing_data.iloc[:, 13]
    gs_phase = housing_data.iloc[:, 14]
    ID=housing_data.iloc[:,0]

    # Initialize variables
    GWA = 2 * S * 2.8 * (np.sqrt(ARR * AA) + np.sqrt(AA / ARR))
    Ca = 3 * 0.2402 * 0.0735 * 9.19 * AA * 10.76 * 0.000527527926 * S * 3600 * 1000
    Um = 1.46 * 5.68 * (2.5 * GWA + S * AA) / 10
    Cm = (2 * AA * S * 10.76 - 2 * 0.2402 * 0.075 * 9.19 * 10.76 * S * AA) * 0.000527527926 * 3600 * 1000
    R = [30, 11, 11, 1/0.6, 3]  # Using normal Rs values
    Ua = ((AA * 10.76 / R[0] + AA * 10.76 / R[1] + GWA * 10.76 / R[2] + GWA * 0.15 * 10.76 / R[3] +
           2 * 10.76 / R[4]) + (0.5 * 9.19 * 10.764 * 0.0735 * 0.2402 * AA)) * S * 5.68 / 10.764 / 10

    a1 = Ua / Ca
    a2 = Um / Ca
    a3 = 1 / Ca
    a4 = Um / Cm
    a5 = 3 * S * AA / Cm
    QQ_H = 35 * AA
    QQ_C = 35 * AA

    # Time and interpolation setup
    # t = np.arange(0, 8760)
    # T_amb_interpolated = np.interp(t, np.arange(len(Tamb)), Tamb)
    T_amb_interpolated = np.interp(np.arange(0,tsim_hr+1,tstep_hr), np.arange(len(Tamb)), Tamb)

    # Initializing dynamic variables
    NB = len(AA)
    T_a = np.zeros((NB, n))
    # T_a[:, 0:2] = 24 + 273.15
    T_a[:, 0] = 24 + 273.15
    QH = np.zeros((NB, n))
    QC = np.zeros((NB, n))
    PS_out = np.zeros((NB, 4))
    PS_out[:, 0] = ID
    PS_out[:, 1] = gs_meter_number
    PS_out[:, 2] = gs_service_number

    # Initializing output variables
    Elec_consumption_H = np.zeros((NB, n))
    Elec_consumption_C = np.zeros((NB, n))
    NG_consumption_H = np.zeros((NB, n))
    Total_Elec_consumption = np.zeros((NB, n))

    #########################################   Starting Co-simulation  ####################################################

    grantedtime = -1

    for t in range(0, tsim_hr, tstep_hr):

        t_sec = 60*60*t
        curr_time = datetimes_list[t]
        logger.info(f"Processing {curr_time}...")

        ############################   Heating and Cooling Simulation #######################################################

        for b in range(NB):
            T_air = T_a[b, :]
            Q_H = QH[b, :]
            Q_C = QC[b, :]

            # Heating and cooling control logic
            if T_air[t] < T_On_H:
                Q_H[t+1] = QQ_H[b]
            elif T_air[t] > T_Off_H:
                Q_H[t+1] = 0
            else:
                Q_H[t+1] = Q_H[t]

            if T_air[t] > T_On_C:
                Q_C[t+1] = -QQ_C[b]
            elif T_air[t] < T_Off_C:
                Q_C[t+1] = 0
            else:
                Q_C[t+1] = Q_C[t]

            Q_dot_H = (Q_H[t+1] - Q_H[t]) / Tstep
            Q_dot_C = (Q_C[t+1] - Q_C[t]) / Tstep
            T_amb_dot = (T_amb_interpolated[t+1] - T_amb_interpolated[t]) / Tstep
            DENOM = 1 / (Tstep**2) + (a1[b] + a2[b] + a4[b]) / Tstep + a1[b] * a4[b]
            AAA = (a3[b] * (Q_dot_H + Q_dot_C) + a3[b] * a4[b] * (Q_H[t+1] + Q_C[t+1]) +
                   a1[b] * T_amb_dot + a1[b] * a4[b] * T_amb_interpolated[t+1] + a2[b] * a5[b])
            
            # check special case for first time step
            if t == 0:
                # assume T_air[t-1] = T_air[0]
                T_air[t+1] = (AAA + T_air[t] * ((a1[b] + a2[b] + a4[b]) / Tstep + 2 / (Tstep**2)) -
                              T_air[0] / (Tstep**2)) / DENOM
            else:
               T_air[t+1] = (AAA + T_air[t] * ((a1[b] + a2[b] + a4[b]) / Tstep + 2 / (Tstep**2)) -
                             T_air[t-1] / (Tstep**2)) / DENOM

            T_a[b, t+1] = T_air[t+1]
            QH[b, t+1] = Q_H[t+1]
            QC[b, t+1] = Q_C[t+1]

        # Energy consumption calculations
        Elec_consumption_H[:, t+1] = QH[:, t+1] * Percent_HP_H / (100000 * COP_HP_H)
        Elec_consumption_C[:, t+1] = -QC[:, t+1] * Percent_HP_C / (100000 * COP_HP_C)
        NG_consumption_H[:, t+1] = QH[:, t+1] * (100 - Percent_HP_H) / (NG_HV * eta_else_H * 100)
        Total_Elec_consumption[:, t+1] = Elec_consumption_C[:, t+1] + Elec_consumption_H[:, t+1] # in kW
        PS_out[:, 3] = 1000*Total_Elec_consumption[:, t+1] # in W
        
        ############################   Publishing Load and Gen to GridLAB-D #######################################################
        
        load_ami_snap = load_ami_data[load_ami_data['start_date_time']==curr_time]
        gen_ami_snap = gen_ami_data[gen_ami_data['start_date_time']==curr_time]

        pub_json = "{\n"

        # Loop through AMI loads
        for index, row in load_dict.iterrows():
            service_num = row['Service Number']
            meter_num = row['Meter Number']
            if service_num not in loads_to_skip:
                load_name = f"_{service_num}_cons"
                pub_json += "\t\"{name}\": {{\n".format(name=load_name)
                load_phase = row['Phase']
                num_phases = len(load_phase)
                for ph_ind in range(num_phases):
                    ph = load_phase[ph_ind]
                    if str(meter_num) not in load_ami_snap.columns[1:]:
                        load_value_P = 0.0
                    else:
                        load_value_P = 1000*(load_ami_snap[str(meter_num)].values[0])
                    if int(service_num) in gs_service_number.tolist():
                        building_index = gs_service_number[gs_service_number==int(service_num)].index[0]
                        load_value_P += PS_out[building_index,3]
                        logger.info(f"Increased load at {service_num} by {PS_out[building_index,3]}.")
                    fixed_pf = args.load_fixed_pf
                    load_value_Q = load_value_P*np.sign(fixed_pf)*np.sqrt(1/(fixed_pf**2)-1)
                    load_value_str = f"{load_value_P/num_phases}+{load_value_Q/num_phases}j" # For multi-phase loads this divides load evenly across all phases.
                    load_string = "\t\t\"constant_power_{phase}\": \"{value}\"".format(phase=ph,value=load_value_str)
                    pub_json += load_string
                    if ph_ind < num_phases-1:
                        pub_json += ",\n"
                pub_json += "\n\t}"
                # if index < len(load_dict)-1:
                #     pub_json += ",\n"
                pub_json += ",\n"

        # Loop through AMI Generation
        for index, row in gen_dict.iterrows():
            object_id = row['Object ID']
            meter_num = row['Meter Number']
            if str(object_id) not in gens_to_skip:
                gen_name = f"gene_{object_id}_negLdGen"
                pub_json += "\t\"{name}\": {{\n".format(name=gen_name)
                gen_phase = row['Phase']
                num_phases = len(gen_phase)
                for ph_ind in range(num_phases):
                    ph = gen_phase[ph_ind]
                    if str(meter_num) not in gen_ami_snap.columns[1:]:
                        gen_value_P = 0.0
                    else:
                        gen_value_P = -1000*(gen_ami_snap[str(meter_num)].values[0])
                    fixed_pf = 1.00
                    gen_value_Q = gen_value_P*np.sign(fixed_pf)*np.sqrt(1/(fixed_pf**2)-1)
                    gen_value_str = f"{gen_value_P/num_phases}+{gen_value_Q/num_phases}j" # For multi-phase gens this divides gen evenly across all phases.
                    gen_string = "\t\t\"constant_power_{phase}\": \"{value}\"".format(phase=ph,value=gen_value_str)
                    pub_json += gen_string
                    if ph_ind < num_phases-1:
                        pub_json += ",\n"
                pub_json += "\n\t}"
                if index < len(gen_dict)-1:
                    pub_json += ",\n"
        
        pub_json += "\n}"

        # Uncomment this line to print json to log
        logger.info(pub_json)

        logger.info(f"Net load [kW]: {load_ami_snap.iloc[:,2:].sum(axis=1)-gen_ami_snap.iloc[:,2:].sum(axis=1)}")

        for i in range(0, pubkeys_count):
            pub = pubid["m{}".format(i)]
            status = h.helicsPublicationPublishString(pub, pub_json)

        # logger.info("{} - {}".format(grantedtime, t_sec))
        while grantedtime < t_sec:
            grantedtime = h.helicsFederateRequestTime(fed, t_sec)
            logger.info("{} - {}".format(grantedtime, t_sec))

    ##############################   Terminating Federate   ########################################################

    while grantedtime < tsim:
        grantedtime = h.helicsFederateRequestTime(fed, tsim)
    logger.info("{}: Destroying federate".format(federate_name))
    destroy_federate(fed)
    logger.info("{}: Done!".format(federate_name))

