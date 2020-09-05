__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2020 Rajarshi Das"

import numpy as np
from subprocess import call
import time
import json
import fcntl
import struct
import socket
import os
import shutil
import time
import sys
import errno
import ast

# bx is login should be functional.
class vpn_connection:
	def __init__(self,data):
		self.local_cidrs = None;
		self.remote_cidrs = None;
		self.ike_policy_id = None;
		self.ipsec_policy_id = None;
		self.id = data['gateway_connection_id'];
		self.gateway_id = data['gateway_id'];
		self.peer_id = data['peer_gateway_connection_id'];
		self.peer_gateway_id = data['peer_gateway_id'];
		self.ike_policies = []; # all policies are for the VPC not the connection.
		self.ipsec_policies = []; 
		#self.lock = Lock();

	def get_policy_info(self,what,policy_list):
		ike = 0;
		ipsec = 1;

		if (what == ipsec):
			f = open('ipsecs.json','r');
		else: #ike
			f = open('ikes.json','r');

		arr = json.load(f);

		for i in np.arange(0,len(arr)):
			policy_map = {'id':arr[i]['id'],
			'auth_algo':arr[i]['authentication_algorithm'],
			'encrypt_algo':arr[i]['encryption_algorithm']
			};

			policy_list.append(policy_map);
	
	def get_ike_policies(self):
		ike = 0;
		ikes_outf = open('ikes.json','w');
		ikes_errf = open('ikes_err.json','w');
		ret = call(['bx','is','ike-policies','--json'],stdout=ikes_outf,stderr=ikes_errf);
		if (ret != 0):
			print("could not get ike policies. Exiting.");
			exit(-1);
	
		ikes_errf.close();
		ikes_outf.close();
		self.get_policy_info(ike,self.ike_policies);

	def get_ipsec_policies(self):
		ipsec = 1;
		ipsec_policies = [];

		ipsecs_outf = open('ipsecs.json','w');
		ipsecs_errf = open('ipsecs_err.json','w');
		ret = call(['bx','is','ipsec-policies','--json'],stdout=ipsecs_outf,stderr=ipsecs_errf);
		if (ret != 0):
			print("could not get ipsec policies. Exiting");
			exit(-1);
		
		ipsecs_errf.close();
		ipsecs_outf.close();
		self.get_policy_info(ipsec,self.ipsec_policies);

	def disable_check_version(self):
		ret = call(['bx','config','--check-version=false']);

	def get_current_policy(self):
                if  not os.path.exists('current_policy.json'):
                    outf = open('current_policy.json','w');
                    ret = call(['bx','is','vpn-cn',self.gateway_id,self.id,'--json'],stdout=outf,stderr=outf);
                    if (ret != 0):
                        print("Failed to get current policy. Exiting");
                        exit(-1);

                    outf.close();

                inf = open('current_policy.json','r');
                arr = json.load(inf);

                # If current policies are set to Auto(IKEv2)/ Auto
                # the ike_policy and ipsec_policy nodes are not seen,
                # return None so that we continue to set a new policy.

                if "ike_policy" in arr:
                    current_ike_policy = arr["ike_policy"]["id"];
                else:
                    current_ike_policy = None;
                if "ipsec_policy" in arr:
                    current_ipsec_policy = arr["ipsec_policy"]["id"];
                else:
                    current_ipsec_policy = None;

                inf.close();

                if (os.path.exists('current_policy.json')):
                    os.remove('current_policy.json');

                return current_ike_policy,current_ipsec_policy;
        
	def set_ike_policy(self,ike_policy):
		curr_ike_policy_id,curr_ipsec_policy_id = self.get_current_policy();
		print('current policy: IKE: ', curr_ike_policy_id);

		if (curr_ike_policy_id == ike_policy["id"]):
			print("Policy with ike ", ike_policy, " already set. ");
			return;
			
		ret = call(['bx','is','vpn-cnu',self.gateway_id,self.id,'--ike-policy',ike_policy['id']]);
		if (ret != 0):
			print("failed to set ike policy. Exiting\n");
			exit(-1);

		ret = call(['bx','is','vpn-cnu',self.peer_gateway_id,self.peer_id,'--ike-policy',ike_policy['id']]);
		if (ret != 0):
			print("failed to set ike policy on peer gw. Exiting\n");
			exit(-1);

		self.ike_policy_id = ike_policy['id'];

		print('set ike policy to auth:',ike_policy['auth_algo'], ' and encrypt:', ike_policy['encrypt_algo']);
                
	def set_ipsec_policy(self,ipsec_policy):
		curr_ike_policy_id,curr_ipsec_policy_id = self.get_current_policy();
		print('current policy: IPSec: ', curr_ipsec_policy_id);

		if (curr_ipsec_policy_id == ipsec_policy["id"]):
			print("Policy with ipsec ", ipsec_policy, " already set. ");
			return;
		
		ret = call(['bx','is','vpn-cnu',self.gateway_id,self.id,'--ipsec-policy',ipsec_policy['id']]);
		if (ret != 0):
			print("failed to set ipsec policy. Exiting\n");
			exit(-1);

		ret = call(['bx','is','vpn-cnu',self.peer_gateway_id,self.peer_id,'--ipsec-policy',ipsec_policy['id']]);
		if (ret != 0):
			print("failed to set ipsec policy on peer gw. Exiting\n");
			exit(-1);

		self.ipsec_policy_id = ipsec_policy['id'];

		print('set ipsec policy to auth:',ipsec_policy['auth_algo'], ' and encrypt:', ipsec_policy['encrypt_algo']);

	def set_policy(self,ike_policy,ipsec_policy):
		# First check the currently set ike_policy and ipsec_policy.
		# If they match what we are trying to set, return.
		curr_ike_policy_id,curr_ipsec_policy_id = self.get_current_policy();
		print('current policy: IKE: ', curr_ike_policy_id, ' IPSec: ', curr_ipsec_policy_id);

		if ((curr_ike_policy_id == ike_policy["id"]) and (curr_ipsec_policy_id == ipsec_policy["id"])):
			print("Policy with ike ", ike_policy, " and ipsec ", ipsec_policy, " already set. ");
			return;
		
		ret = call(['bx','is','vpn-cnu',self.gateway_id,self.id,'--ike-policy',ike_policy['id'],'--ipsec-policy',ipsec_policy['id']]);
		if (ret != 0):
			print("failed to set ike and ipsec policies. Exiting\n");
			exit(-1);

		ret = call(['bx','is','vpn-cnu',self.peer_gateway_id,self.peer_id,'--ike-policy',ike_policy['id'],'--ipsec-policy',ipsec_policy['id']]);
		if (ret != 0):
			print("failed to set ike and ipsec policies on peer gw. Exiting\n");
			exit(-1);

		self.ike_policy_id = ike_policy['id'];
		self.ipsec_policy_id = ipsec_policy['id'];

		print('set ike policy to auth:',ike_policy['auth_algo'], ' and encrypt:', ike_policy['encrypt_algo']);
		print('set ipsec policy to auth:',ipsec_policy['auth_algo'], ' and encrypt:', ipsec_policy['encrypt_algo']);

class netperf:
	def __init__(self,optionlist):
		self.netperf_command = "/usr/bin/netperf";
		self.ifconfig_command = "/sbin/ifconfig";
		self.allowed_options = ["-H","-r","-l","-z"];
		self.coption = None;
		self.ioption = None;
		self.Poption = None;
		self.list_c = [];
		self.list_P = [];
		self.list_i = [];
		self.list_t = [];
		self.step = 5; # default step to be used with lower and upper bounds 
				# if none explicitly specified (-e)
		self.option_map = {
		#	"-c": None,
		#	"-t":[60],
		#	"-i":[5,10],
		#	"-P":[5,50]
		};
		self.source_ip = None;
		self.run_path = None; # Folder to run within
		self.cwd = None; # to remember where to get back
		self.ike_ipsec_option = "Current"; # Run current IKE and IPSec combination only
		self.sleep_time = 10; # default sleep time between consecutive test runs
		print("set default sleep time between consecutive runs to: ",self.sleep_time," seconds.");
		self.run_mode = "vpn"; # run for vpn connections by default
		self.bw_limit = "None"; # No bandwidth limit value (-b) by default

      # prepare option map
		for i in np.arange(0,len(optionlist)):
			if optionlist[i] == "-e":
				self.option_map[optionlist[i]] = str(optionlist[i+1]);
				self.step = int(optionlist[i+1]);
			elif optionlist[i] == "-c":
				print("setting step to: ",self.step);
				self.coption = True;
				self.option_map[optionlist[i]] = str(optionlist[i+1]);
				#print(self.option_map);
				continue;
			elif optionlist[i] == "-s": # sleep time between runs
				if (self.is_integer(optionlist[i+1])):
				    print("setting sleep time to ",optionlist[i+1]);
				    self.sleep_time = int(optionlist[i+1]);
				else:
				    print("a integer value needs to be specified with -s. Retry as -s <sleeptime>");
				    exit(-1);
				continue;
			elif optionlist[i] == "-p": # Run for all IKE/IPSec policy combinations or
					# run in pairs e.g. the combination of the 1st IKE and 
                                        # IPSec policies, then the 2nd of each and so on.
                                        # or run for the currently set IKE/IPSec policy only
				if ((optionlist[i+1] == "All") or\
					(optionlist[i+1] == "Pair") or\
					(optionlist[i+1] == "Current_IKE") or\
					(optionlist[i+1] == "Current")): # just run with the currently set IKE/IPSec policies
						self.ike_ipsec_option = optionlist[i+1];
						print("set policy option to: ",optionlist[i+1]);
				else:
					print("Invalid parameter specified for -p or parameter missing.\n");
					print("Ignoring -p option. Will run with currently set policies only.\n");
					continue;
			elif optionlist[i] == "-b":
				self.bw_limit = optionlist[i+1];
				continue;
			elif ((optionlist[i] == "-t") or (optionlist[i] == "-i") or (optionlist[i] == "-P")): 
				self.option_map[optionlist[i]] = [];
				if (optionlist[i] == "-t"):
					self.toption = True;
				elif (optionlist[i] == "-i"):
					self.ioption = True;
				else:
					self.Poption = True;

				option = optionlist[i];
				if (isinstance(optionlist[i+1],str)):
					optionlist[i+1] = ast.literal_eval(optionlist[i+1]);
				if (isinstance(optionlist[i+1],list)): # one list found. 
					self.set_options("type_list",option,optionlist[i+1]);
					j = i+2;
					# A '-' indicates the next option
					while(j<len(optionlist) and\
					("-" not in optionlist[j])): 
						if (isinstance(optionlist[j],str)):
							optionlist[j] = ast.literal_eval(optionlist[j]);
						if (isinstance(optionlist[j],list)):#more lists?
							self.set_options("type_list",option,optionlist[j]);
						j += 1;
					if ((j<len(optionlist)) and ("-" in optionlist[j])):
						i = i+2; # set 'i' so as to start at the next option
				elif (isinstance(optionlist[i+1],int)): # single range
					self.set_options("type_int",option,optionlist[i+1]);
					j = i+2;
					if (j<len(optionlist) and isinstance(optionlist[j],int)): # If the upper limit exists, add it
						self.set_options("type_int",option,optionlist[j]);

        # common routine to set options esp. for -P
	def set_options(self,optiontype,option,optionlist):
		temp = [];

		if (optiontype=="type_list"): # only -P
			if ((len(optionlist)==2) and (self.is_integer(optionlist[1]))): # check if we have the upper limit
				j = int(optionlist[0]);
				while(j <= int(optionlist[1])):
					temp.append(j);
					j += self.step;
				for j in temp:
					if (option == "-P"):			
						self.list_P.append(j);
					else:
						self.option_map[option].append(j);
			else:	# only one limit specified?
				if ((len(optionlist)==1) and (self.is_integer(optionlist[0]))):
					temp.append(optionlist[0]);
					for j in temp:
						self.list_P.append(j);
				else: # no limits specified for the option
					print("No limits specified for option ",option);
					exit(-1);
		else: # type_int
			if (option == "-P"):
				temp.append(optionlist);
				self.list_P.append(temp);
			else: # '-t' or '-i'
				temp.append(optionlist);
				self.option_map[option] = temp;

	# change directory to the folder specified
	def change_dir_in(self):
		if (os.path.exists(self.run_path)):
			shutil.rmtree(self.run_path);
			os.makedirs(self.run_path);
		else:
			os.makedirs(self.run_path);

		print('self.path: ',self.run_path);

		try:
			self.cwd = os.getcwd();
		except OSError:
			print('Could not get current working directory. error: ',OSError.args);
			exit(-1);

		try:
			os.chdir(self.run_path);
		except (OSError,FileNotFoundError,PermissionError,NotADirectoryError) as e:
			print('could not change directory to ',self.run_path);
			print('Error: ',e.args);
			exit(-1);

	# Change back to parent dir, tar up the folder and print tarball file name
	def change_dir_out(self):
		try:
			os.chdir(self.cwd);
		except (OSError,FileNotFoundError,PermissionError,NotADirectoryError) as e:
			print('could not change directory to ',self.cwd);
			print('Error: ',e.args);
			exit(-1);

		tarfile = self.run_path + ".tar";
		ret = call(['tar','-cvf',tarfile,self.run_path]);
		if (ret != 0):
			print('failed to tar the results.');
			exit(-1);
		ret = call(['gzip',tarfile]);
		if (ret != 0):
			print('failed to zip the tarfile.');
			exit(-1);

		shutil.rmtree(self.run_path);

		print('results in :',tarfile,'.gz');

	# set source IP address using the if specified.
	#def set_source_ip(self,ifname='eth0'):
	def set_source_ip(self,ifname='ens3'):
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

	# to check if the input is an integer
	def is_integer(self,string):
		try:
			value = int(string);
			return True;
		except ValueError:
			return False;	

	def print_option_map(self):
		#print(self.option_map);
		for k,v in self.option_map.items():
			print(k,":",v);
            
	def __del(self):
		self.coption = None;
		self.ioption = None;
		self.Poption = None;
						
# Given a lower and upper bound, find all the values between the two.                        
	def get_options(list_min_max,step=1):
		temp = [];

		if (len(list_min_max) == 1):
			temp.append(list_min_max);
		
		else: # both min and max specified
			i = list_min_max[0];
			while (i < list_min_max[1]):
				temp.append(i);
				i += step;
		return temp;
        
   
	def switch_option(self,option):
		self.switch_opt= {
			"-P":self.list_P,
			"-c":self.list_c,
			"-i":self.list_i,
			"-t":self.list_t
		}		
		list_None = [];
      
		return (self.switch_opt.get(option,list_None));

	def get_avg_bw(self,jsonfile):
		f = open(jsonfile, 'r');
		data_arr = json.load(f);

		sent_rate = float(data_arr['end']['sum_sent']['bits_per_second']);
		rcv_rate  = float(data_arr['end']['sum_received']['bits_per_second']);

		return sent_rate,rcv_rate;

	def run_core_loops(self,summ_f,i,j):
        # following loop runs once per policy set above
		self.set_source_ip();

		for ii in np.arange(0,len(self.list_i)):
			for ic in np.arange(0,len(self.list_c)):
				for iP in np.arange(0,len(self.list_P)):
					for it in np.arange(0,len(self.list_t)):
						current_time = time.strftime("%d-%m-%Y_%H:%M:%S");
						if (self.run_mode == "vpn"): # set policy info in file name if in vpn mode
						    current_policy = "ike_" + i['auth_algo'] + "-" + i['encrypt_algo'] +\
										"_ipsec_" + j['auth_algo'] + "-" + j['encrypt_algo'];
						outfile_opt = "i" + str(self.list_i[ii]) + "_" + str(self.source_ip) + \
									"_to_" + str(self.list_c[ic]) + \
									"_" + "P" + str(self.list_P[iP]) + "_" + "t" + \
									str(self.list_t[it]);
						if (self.bw_limit != "None"):
							outfile_opt += "_" + "b" + str(self.bw_limit);

						outfile = outfile_opt + ".json";
						outfile = current_time + "_" + outfile;

						if (self.run_mode == "vpn"):
						    outfile = current_policy + "_" + outfile;

						outf = open(outfile,"w");
						print('outfile: ',outfile);
						command_array = [self.iperf_command,"-c",str(self.list_c[ic]),"-i",\
										str(self.list_i[ii]),"-P",str(self.list_P[iP]),"-t",\
										str(self.list_t[it])];

						# Add '-b' flag if specified
						if (self.bw_limit != "None"):
							command_array += ["-b",str(self.bw_limit)];

						command_array += ["--json"];

						print('command_array: ',command_array);

						ret = call(command_array,stdout=outf,stderr=outf);
						print("iperf call returned ",ret);

						send_rate,rcv_rate = self.get_avg_bw(outfile);
						summary_line = current_time + "," + outfile_opt + "," + \
								str(send_rate/pow(10,6)) + "," + str(rcv_rate/pow(10,6)) \
										+ "," + outfile + "\n";
						if (self.run_mode == "vpn"):
						    summary_line = i['auth_algo'] + "," + i['encrypt_algo'] +\
										"," + j['auth_algo'] + "," + j['encrypt_algo'] +\
										"," + summary_line;

						summ_f.write(summary_line);

						print('avg send rate: ',send_rate,',avg receive rate: ',rcv_rate);
						print('sleeping for ',self.sleep_time,' seconds.');
						time.sleep(self.sleep_time);

        
	def run_current_only(self,summ_f,vpn_c):
		current_ike_id,current_ipsec_id = vpn_c.get_current_policy();
		print('current ike: ',current_ike_id,' current_ipsec: ',current_ipsec_id);

		if (current_ike_id == None):
		    current_ike_policy = {'id':'No_id',
		    'auth_algo':'Auto_auth_IKE',
		    'encrypt_algo':'Auto_encrypt_IKE'};
		else:
		    for i in vpn_c.ike_policies:
                        if (i['id'] == current_ike_id):
                            current_ike_policy = i;
                            break;

		if (current_ipsec_id == None):
		    current_ipsec_policy = {'id':'No_id',
		    'auth_algo':'Auto_auth_IPSec',
		    'encrypt_algo':'Auto_encrypt_IPSec'};
		else:
		    for i in vpn_c.ipsec_policies:
                        if (i['id'] == current_ipsec_id):
                            current_ipsec_policy = i;
                            break;

		self.run_core_loops(summ_f,current_ike_policy,current_ipsec_policy);

    # Run all other ipsec policies against IKE-Auto: currently this does not include IPSec-Auto
	def run_ike_auto(self,summ_f,vpn_c):        
	    ike_auto_policy = {'id':'No_id',
	    'auth_algo':'Auto_auth_IKE',
	    'encrypt_algo':'Auto_encrypt_IKE'};

	    for j in vpn_c.ipsec_policies:
                vpn_c.set_ipsec_policy(j);
                self.run_core_loops(summ_f,ike_auto_policy,j);

    # Workaround routine. Run this after setting IKE/IPSec to Auto in console
    # Helps cover IKE/IPSec : Auto/Auto as well as IKE/IPSec: Auto/<configured policies>
    # This is because IKE/IPSec: Auto/Auto can not be set using CLI for now (no associated id)
	def run_auto_workaround(self,summ_f,vpn_c):
            self.run_current_only(summ_f,vpn_c);
            self.run_ike_auto(summ_f,vpn_c);

	def run_all(self,summ_f,vpn_c):
	# Comment the workaround below once IKE/IPSec:Auto/Auto can be set using the CLI
            self.run_auto_workaround(summ_f,vpn_c);

            for i in vpn_c.ike_policies:
                vpn_c.set_ike_policy(i);
                for j in vpn_c.ipsec_policies:
                    vpn_c.set_ipsec_policy(j);
                    self.run_core_loops(summ_f,i,j);

	# Run all ipsec policies (excludes Auto as it doesn't have a id) against the current ike policy
	def run_all_ipsec(self,summ_f,vpn_c):
	    current_ike_id,current_ipsec_id = vpn_c.get_current_policy();
	    for i in vpn_c.ike_policies:
                if i['id'] == current_ike_id:
                    for j in vpn_c.ipsec_policies:
                        vpn_c.set_ipsec_policy(j);
                        self.run_core_loops(summ_f,i,j);
                else:
                    continue;

	def run_pairs(self,summ_f,vpn_c):
		for (i,j) in zip(vpn_c.ike_policies,vpn_c.ipsec_policies):
			vpn_c.set_policy(i,j);
			self.run_core_loops(summ_f,i,j);

	# Run for non-vpn scenarios
	def run_others(self,summ_f):
	    dummy_ike_policy = {'id':'None',
	    'auth_algo':'None',
	    'encrypt_algo':'None'};
	    dummy_ipsec_policy = {'id':'None',
	    'auth_algo':'None',
	    'encrypt_algo':'None'};

	    self.run_core_loops(summ_f,dummy_ike_policy,dummy_ipsec_policy);

      
	#def execute_test(self,gw_info):
	def execute_test(self,gw_info,optionlist):
		for k,v in self.option_map.items():
			temp = self.switch_option(k);
			if (k != "-c"): # for '-c' set the IP address directly.
				for i in v:
					temp.append(i);
			else:
				temp.append(v);
			#temp = v;
        
		#print('self lists:');
		print('i:',self.list_i);
		print('t:',self.list_t);
		print('P:',self.list_P);
		print('c:',self.list_c);

		# set up the vpn_connection object here.
		if (gw_info):
		    vpn_c = vpn_connection(gw_info);
		    vpn_c.disable_check_version(); # Avoid upgrade messages in policy json output
		    vpn_c.get_ike_policies();
		    vpn_c.get_ipsec_policies();
		else:
		    self.run_mode = "other"; # normal run. vpn connections not required

		current_time = time.strftime("%d-%m-%Y_%H-%M-%S");
		self.run_path = "server_" + self.option_map["-c"] + "_run_" + current_time;
		
		# get inside the run folder
		self.change_dir_in();

		# create summary file inside the run folder
		summary_filename = "summary" + "_" + current_time + ".csv";
		summ_f = open(summary_filename,'w');

		if (gw_info):
		    header = "IKE_auth_policy,IKE_encrypt_policy,IPSec_auth_policy,IPSec_encrypt_policy,Start_time_of_run,Options_used,Average_send_BW (Mbits/s),Average_receive_BW (Mbits/s),Detailed_output_filename\n";
		else:
		    header = "Start_time_of_run,Options_used,Average_send_BW (Mbits/s),Average_receive_BW (Mbits/s),Detailed_output_filename\n";

		summary_line = "";

		summ_f.write(header);
		if (gw_info):
		    if (self.ike_ipsec_option == "Current"):
			    self.run_current_only(summ_f,vpn_c);
		    elif (self.ike_ipsec_option == "Current_IKE"): # Iterate current IKE against all IPSec
			    self.run_all_ipsec(summ_f,vpn_c);
		    elif (self.ike_ipsec_option == "All"):
			    self.run_all(summ_f,vpn_c);
		    else: # Pair
			    self.run_pairs(summ_f,vpn_c);
		else:
		    self.run_others(summ_f);

		summ_f.close();
		self.change_dir_out();

def test_iperf3(option):
	call(["/usr/bin/iperf3",option]);	
	return;

def run_test(options):
	return;

def get_config(input_file):
        inf = open(input_file,'r');

        data = json.load(inf);
        client_server_pairs = [];
        for i in np.arange(0,len(data)):
            if 'server' not in data[i]:
                print("Server address missing in configuration file");
                print("Exiting..");
                exit(-1);
            if 'run_configuration' not in data[i]:
                print("run_configuration missing in configuration file");
                print("setting defaults");

            server = data[i]["ser

            data[i]["server"]

        for k in data:
            if 'gateway' in k:
                gw_info[k] = data[k];
                continue;

            optionlist.append(k);
            if isinstance(data[k],list): # A list of values is mapped
                for i in np.arange(0,len(data[k])):
                    optionlist.append(data[k][i]);
            else:
                optionlist.append(data[k]);

        return [optionlist,gw_info];

if __name__ == "__main__":
#	test_iperf3("-h");
	optionlist = []
	gw_info = {}
        client_server_pairs = [];

	if (len(sys.argv) == 2):
	   client_server_pairs = get_config(sys.argv[1]);
	else:
            print("Specify the number of parallel runs of netperf");
            num_combinations = input();
            for(i=0;i<num_combinations;i++) {
	        print("Enter a space separated list of options for the netperf command\n");
                print("Ensure that -H <server address> is specified at a minimum.\n");
	        optionlist = input().split(' ');

                client_server_pairs.append(optionlist);
            }

