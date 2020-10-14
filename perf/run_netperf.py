__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2020 Rajarshi Das"

import numpy as np
from threading import Thread
from subprocess import call
import time
import json
import fcntl
import struct
import socket
import os
import time
import sys
import errno
import ast
import random

config_kw_option_map = {
"server"    :       "-H",
"duration"  :       "-l",
"pkt_size_tx_rx":   "-r",
"test_type":        "-t",
"num_copies":       "-z",
"inter_run_sleep":  "-y",
"cpu_rate_local":   "-c",
"cpu_rate_remote":  "-C",
"data_path_only":   "-N"
}

supported_output_list = ["mean_latency","transaction_rate","p90_latency"];
supported_output_list_display = "mean_latency/transaction_rate/p90_latency";

class netperf: # one object per server IP address in the config
    def __init__(self,optionlist):
        self.server = None;
        self.type = None;
        self.duration = "10"; # default run duration
        #self.netperf_command = "/usr/bin/netperf"; # 2.6.0
        self.netperf_command = "/usr/local/bin/netperf"; # 2.7.0
        self.Hoption = False;
        self.toption = False;
        self.loption = False;
        self.coption = False;
        self.Coption = False;
        self.Noption = False;
        self.t_roption = False; # t_ is a test option
        self.s_zoption = False; # s_ is a (this) script specific option
        self.source_ip = None;
        self.packet_sizes = "";
        self.commands = [];
        self.command_strings = [];
        self.inter_run_sleep = 2; # default sleep time b/w iterations
        self.num_copies = 1; # default number of copies to run per configuration
        self.cpu_rate_local = 0;
        self.cpu_rate_remote = 0;

    def get_packet_sizes(self,packet_size_array):
        size_string_array = []

        for i in range(len(packet_size_array)):
            print(packet_size_array[i]);
            tmp_size = "";
            tmp_size = str(packet_size_array[i][0]) + "," + \
                    str(packet_size_array[i][1]);
            size_string_array.append(tmp_size);

        return size_string_array;

    def parse_configuration(self,optionlist):
        packet_sizes = []

        for i in range(len(optionlist)):
            if (optionlist[i] == "-H"): # server address
                self.Hoption = True;
                self.server = optionlist[i+1];
            elif (optionlist[i] == "-t"): # test type
                self.toption = True;
                self.type = optionlist[i+1];
            elif (optionlist[i] == "-r"): # packet sizes
                self.t_roption = True;
                if (isinstance(optionlist[i+1],list)):
                    self.packet_sizes = self.get_packet_sizes(optionlist[i+1]);
                elif (isinstance(optionlist[i+1],str)):
                    optionlist[i+1] = ast.literal_eval(optionlist[i+1]);
                    self.packet_sizes = self.get_packet_sizes(optionlist[i+1]);
                else:
                    print("Error: arguments for -r should either be a list or \
                            string. Exiting.");
                    exit(-1);
            elif (optionlist[i] == "-l"): # duration
                self.loption = True;
                self.duration = optionlist[i+1];
            elif (optionlist[i] == "-y"): # sleep time between consecutive runs
                self.inter_run_sleep = int(optionlist[i+1]);
            elif (optionlist[i] == "-z"):
                self.s_zoption = True;
                self.num_copies = int(optionlist[i+1]);
            elif (optionlist[i] == "-c"):
                self.coption = True;
                self.cpu_rate_local = int(optionlist[i+1]);
            elif (optionlist[i] == "-C"):
                self.Coption = True;
                self.cpu_rate_remote = int(optionlist[i+1]);
            elif (optionlist[i] == "-N"):
                self.Noption = True;

    def get_source_ip(self,ifname="ens3"):
        s = socket.socket(family=socket.AF_INET,type=socket.SOCK_DGRAM);

        # use SIOCGIFADDR to fetch the net address.
        # IFNAMSIZ in if.h is 16 chars long
        try:
            netaddr = fcntl.ioctl(s.fileno(),
                        0x8915,
                        struct.pack("256s",\
                        bytearray(ifname[:16],'utf-8')));
        except OSError as e:
            if (e.errno == errno.ENODEV): # device 'ens3' not found. Try 'eth0'
                ifname = 'eth0';
                netaddr = fcntl.ioctl(s.fileno(),
                    0x8915,
                    struct.pack("256s",\
                    bytearray(ifname[:16],'utf-8')));
            else:
                print("Unexpected OS Error. Exiting. ");
                exit(-1);

        self.source_ip = socket.inet_ntoa(netaddr[20:24]);

    def prepare_commands(self,output_fields):
        output_fields_string = "";
        for i in range(len(output_fields)):
            output_fields_string += output_fields[i];
            if i < (len(output_fields)-1):
                    output_fields_string += ",";

        if (len(self.packet_sizes)==0): # no packet size was specified
            size_array = [];
            size_array.append("1,1"); # set the default rx and tx sizes
            self.packet_sizes = size_array;
            self.t_roption = True; # set this to enable cmd creation

        if (self.loption == False): # duration was not specified
            self.loption = True; # use default value

        for i in range(len(self.packet_sizes)):
            cmd = [];
            cmd_string = "";
            cmd = [self.netperf_command];
            #Add global options
            if (self.Hoption == True):
                cmd += ["-H",str(self.server)];
            else: # should never get here
                print("no server address specified. Can not continue.");
                exit(-1);

            if (self.Noption == True): # data path only
                cmd += ["-N"];
                if (cmd_string != ""): # some option's already added
                    cmd_string += "_";
                cmd_string += "N";

            if (self.toption == True):
                cmd += ["-t",str(self.type)];
                if (cmd_string != ""): # some option's already added
                    cmd_string += "_";
                cmd_string += "t" + str(self.type);
            else:
                self.type = "TCP_RR"; # set TCP_RR as default
                cmd += ["-t",str(self.type)];
                if (cmd_string != ""): # some option's already added
                    cmd_string += "_";
                cmd_string += "t" + str(self.type);

            if (self.loption == True):
                cmd += ["-l",str(self.duration)];
                if (cmd_string != ""): # some option's already added
                    cmd_string += "_";
                cmd_string += "l" + str(self.duration);

            if (self.coption == True):
                cmd += ["-c",str(self.cpu_rate_local)];

            if (self.Coption == True):
                cmd += ["-C",str(self.cpu_rate_remote)];

            cmd += ["--"];

            #Add test specific options
            if (self.t_roption == True):
                cmd += ["-r",str(self.packet_sizes[i])];
                if (cmd_string != ""): # some option's already added
                    cmd_string += "_";
                tmp_pkt_size = self.packet_sizes[i].replace(",","_");
                cmd_string += "r" + str(tmp_pkt_size);

            #output_fields are test specific. However, fetching and 
            #adding it as a common set across tests for now.
            cmd += ["-o",output_fields_string];

            cmd_copy = cmd.copy();
            self.commands.append(cmd_copy);
            self.command_strings.append(cmd_string);

    def run_command_core(self,resultf):
        for i in range(len(self.packet_sizes)):
            current_time = time.strftime("%d-%m-%Y_%H-%M-%S");
            start_time = current_time;

            output_filename = "netperf_" + str(random.randint(0,10000)) + "_" \
                + str(self.source_ip) + "_to_" + \
                str(self.server) + "_" + current_time + "_" + \
                str(self.command_strings[i]) + ".csv";

            outf = open(output_filename,"w");

            ret = call(self.commands[i],stdout=outf,stderr=outf);
            end_time = time.strftime("%d-%m-%Y_%H:%M:%S");
            print("netperf call returned ", ret);
            outf.close();

            outf = open(output_filename,"r");

            lines_read = 0;
            #resultf.write("\n");
            result_line = start_time + "," + end_time;
            if (self.toption == True):
                result_line += "," + self.type;
            if (self.t_roption == True):
                result_line += "," + self.packet_sizes[i];
            if (self.loption == True):
                result_line += "," + self.duration;

            for line in outf.readlines():
                lines_read += 1;
                if (lines_read == 3):
                    result_line += "," + line; # third line has data
                    resultf.write(result_line);
                    break;

            outf.close();

            if (i < len(self.packet_sizes)-1): # more packet sizes to run with.
                print("sleeping for ",self.inter_run_sleep," seconds");
                time.sleep(self.inter_run_sleep);

    def run_commands(self,output_fields):
        self.get_source_ip();

        current_time = time.strftime("%d-%m-%Y_%H-%M-%S");

        result_summary_file = "netperf_summary_" + str(random.randint(0,10000))\
                + "_" + str(self.source_ip) + "_to_" + str(self.server) + "_" \
                + current_time + ".csv";

        resultf = open(result_summary_file,"w");
        header = "start_time,end_time";

        if (self.toption == True):
            header += ",test_type";
        if (self.t_roption == True):
            header += ",packet_size_tx(bytes),packet_size_rx(bytes)";
        if (self.loption == True):
            header += ",duration(seconds)";

        for i in range(len(output_fields)):
            header += "," + output_fields[i];
            if "latency" in output_fields[i]:
                header += "(microseconds)";
            elif "transaction_rate" in output_fields[i]:
                header += "(trans/sec)";

        header += "\n";
        resultf.write(header);

        # if we need more than one copy to start simultaneously, spawn threads
        if (self.num_copies > 1):
            th_core = []

            for i in range(self.num_copies):
                th_core.append(Thread(target=self.run_command_core,\
                        args=(resultf,)));
                th_core[i].start();

            for i in range(self.num_copies):
                th_core[i].join();
            
            resultf.close();
        else:
            self.run_command_core(resultf);
            resultf.close();

    def __del(self):
        self.server = None;
        self.packet_sizes = None;
        self.type = None;
        self.duration = None;

def get_config(input_file):
    optionlist = [];
    
    inf = open(input_file,'r');

    full_data = json.load(inf);
    client_server_pairs = [];
    server_address_count = 0;

    data = full_data["test_configuration"];

    for i in np.arange(0,len(data)):
        for k in data[i]:
            if k == "server":
                server_address_count += 1;
                break;
    if (server_address_count < len(data)):
        print("Server address missing for one or more entries \
                in configuration file");
        print("Exiting..");
        exit(-1);

    for i in np.arange(0,len(data)):
        optionlist.clear();
        for key in data[i]:
            if (key in config_kw_option_map):
                optionlist.append(config_kw_option_map[key]);
                #print('key:',key,' data[key]:',data[i][key]); # debug
                optionlist.append(data[i][key]);
            if isinstance(data[i][key],list): # e.g. key == run_configuration
                for j in np.arange(0,len(data[i][key])):
                    data2 = data[i][key][j];
                    for key2 in data2:
                        if (key2 in config_kw_option_map):
                            optionlist.append(config_kw_option_map[key2]);
                            optionlist.append(data2[key2]);
                        if isinstance(data2[key2],list): # e.g. key2 == test_parameters
                            for k in np.arange(0,len(data2[key2])):
                                data3 = data2[key2][k];
                                for key3 in data3:
                                    if (key3 in config_kw_option_map): # e.g. packet_size_tx_rx
                                        optionlist.append(\
                                                config_kw_option_map[key3]);
                                        optionlist.append(data3[key3]);
        options = optionlist.copy();
        client_server_pairs.append(options);

    if "output_fields" not in full_data: #set defaults
        output_fields = supported_output_list;
    else:
        output_fields = full_data["output_fields"];
                            
    return client_server_pairs,output_fields;

def start_netperf(config_data,output_fields):
    np = netperf(config_data);
    np.parse_configuration(config_data);
    np.prepare_commands(output_fields);
    np.run_commands(output_fields);

if __name__ == "__main__":
    client_server_pairs = [];
    output_fields = [];
    output_data = "";
    output_list = [];

    if (len(sys.argv) == 2): # configuration file specified as a parameter
        client_server_pairs,output_fields = get_config(sys.argv[1]);
    elif (len(sys.argv) == 1): # no options or parameter specified
        print("Specify the number of parallel runs of netperf");
        num_combinations = int(input());
        for i in range(num_combinations):
            print("Enter a space separated list of options for the netperf\
                    command");
            print("Ensure that -H <server address> is specified at a minimum.");
            print("Do not specify the test specific output fields (-o) here.");

            option_list = input().split(' ');
            client_server_pairs.append(option_list);

        print("Specify comma-separated fields to print in the run output:");
        print(supported_output_list_display);
        print("Specify None to indicate defaults");
        output_data = input();
        if (output_data == "None"):
            output_fields = supported_output_list;
        else:
            output_list = output_data.split(",");
            if (len(output_list) == 1):
                if (" " in output_list[0]):#space separated list specified 
                    print("A comma separated list of output fields should be\
                        specified. Exiting");
                    exit(-1);
            for i in range(len(output_list)):
                if (output_list[i] not in supported_output_list):
                    print(output_list[i]," not supported. Skipping..");
                    continue;
                output_fields.append(output_list[i]);

            if (len(output_fields)==0):
                print("none of the output fields specified is supported.");
                print("setting defaults..");
                output_fields = supported_output_list;

    else: # full list of options specified directly on command line
        option_list = [];
        output_field = False;

        for i in range(len(sys.argv)):
            if (i==0):
                continue;

            if ((i==len(sys.argv)-1) and (output_field == False)): # -o missing
                output_fields = supported_output_list; # set defaults

            if ("-o" in sys.argv[i]):
                output_field = True;
            else:
                if (output_field == False):
                    option_list.append(sys.argv[i]);
                else:
                    output_list = sys.argv[i].split(",");
                    if (len(output_list) == 1):
                        if (" " in output_list[0]):#space separated list 
                            print("A comma separated list of output fields \
                                    should be specified. Exiting");
                            exit(-1);

                    for i in range(len(output_list)):
                        if (output_list[i] not in supported_output_list):
                            print(output_list[i]," not supported. Skipping..");
                            continue;
                        output_fields.append(output_list[i]);

                    if (len(output_fields)==0):
                        print("none of the output fields specified is \
                                supported.");
                        print("setting defaults..");
                        output_fields = supported_output_list;

        client_server_pairs.append(option_list);

    print('client_server_pairs: ',client_server_pairs); # debug
    print('output_fields: ',output_fields); # debug

    for i in np.arange(0,len(client_server_pairs)):
        run_thread = Thread(target=start_netperf,args=(client_server_pairs[i]\
                ,output_fields,));
        run_thread.start();
