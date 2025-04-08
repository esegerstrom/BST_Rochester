To run the 3ph power flow solver in Julia:
    1. Clone this repo into local directory
    2. Follow the instructions in the Word doc (attached to email from Dakota) 
       to copy the input data from folder /netfiles/nest-vt-fs1/data_for_MAPLE_BST_Demo/Feeder_Data (on server)
       into your local copy of this repo
    3. Setup Julia packages
        a. Open Julia REPL
        b. Press "]" to enter package manager
        c. Run "activate ." to activate environment
        d. Run "instantiate" to add required Julia packages
    4. Run Opt_Tools/solve_3ph_pf.jl to solve the 3-phase power flow using JuMP

(Not required for demo) To set up a HELICS co-simulation (GridLAB-D+AMI Data) or change AMI input data (dates or load power factor):
    1. Create a Python virtual environment in this folder and activate it (Optional, but highly recommended) 
        a. In VS Code: >Python: Select Interpreter, then +Create Virtual Environment
        b. In command line: "python -m venv venv", then
            1. On Windows: "venv\Scripts\activate"
            2. On Linux/macOS: "source venv/bin/activate"
    3. Install required Python packages
        a. pip install -r py_reqs.txt
    4. Run setup_cosim.py script in Python with desired settings
