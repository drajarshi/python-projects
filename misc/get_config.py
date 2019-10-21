# Parse a dictionary style mapping of options from a configuration file into a line. Gateway specific information gets mapped into a dictionary
# The output contains each option and its arguments separated by a space.
import json
import sys
import numpy as np

def get_config(input_file):
    inf = open(input_file,'r');

    data = json.load(inf);

    optionlist = []
    gw_info = {}

    for k in data:
        if 'gateway' in k:
            gw_info[k] = data[k]
            continue;
        
        optionlist.append(k);
        if isinstance(data[k],list): # A list of values is mapped
            for i in np.arange(0,len(data[k])):
                optionlist.append(data[k][i]);
        else:
            optionlist.append(data[k]);

    return [optionlist,gw_info];

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print("Specify a configuration file to parse. run as python get_config.py <config file>");
        exit(-1);
    
    optionlist = [];
    gw_info = {};
    
    [optionlist,gw_info] = get_config(sys.argv[1]);
    print("The passed configuration file contains:");
    print("options:",optionlist);
    print("gateway info:",gw_info);
