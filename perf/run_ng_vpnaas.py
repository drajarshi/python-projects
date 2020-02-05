__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2019 Rajarshi Das"

from threading import Thread
import numpy as np
import os
import sys
import time
import datetime
import iperf3_test
from fabric import Connection
import json

# ls -l for test purposes.
class list_dir:
	def __init__(self,ip,key_filename,args=[" -l > "," 2>&1 &"]):
		print("list_dir: __init__");
		self.command = "/bin/ls";
		self.ip = ip;
		self.args = args;
		self.key_filename = key_filename;
	
	def exec_listdir(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":self.key_filename,
				},
			)
			print("exec_listdir: conn: ",conn);
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
		current_time = datetime.datetime.utcnow().strftime("%d-%m-%Y_%H-%M-%S");
		output_file = self.ip + "_listdir_" + current_time + ".out";
		self.command = "nohup " + self.command + "  " + self.args[0] + output_file + self.args[1];

		result = conn.run(self.command,hide=True);
		print(self.command,' returned ',result.exited);
		conn.close();
		if (result.exited != 0):
			print('Failed to run command: ',self.command, ' Exiting..');
			exit(-1);

	def start(self):
		print("list_dir: start");
		t_listdir = Thread(target=self.exec_listdir);
		t_listdir.start();
		

class mpstat:
	def __init__(self,ip,key_filename,args=["-P ALL 2 > ", " 2>&1 &"]):
		self.command = "/usr/bin/mpstat";
		self.args = args;
		self.ip = ip;
		self.key_filename = key_filename;

	def exec_mpstat(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":self.key_filename,
				},
			)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
		print('in exec_mpstat: self.ip: ',self.ip,' self.args: ',self.args);
		current_time = datetime.datetime.utcnow().strftime("%d-%m-%Y_%H-%M-%S");
		output_file = self.ip + "_mpstat_" + current_time + ".out";
		self.command = "nohup " + self.command + "  " + self.args[0] + output_file + self.args[1];

		result = conn.run(self.command,hide=True);
		print(self.command,' returned ',result.exited);
		conn.close();
		if (result.exited != 0):
			print('Failed to run command: ',self.command, ' Exiting..');
			exit(-1);

	def start(self):
		t_mpstat = Thread(target=self.exec_mpstat);
		t_mpstat.start();

		
class vmstat:
	def __init__(self,ip,key_filename,args=[" -t 2 > "," 2>&1 &"]):
		self.command = "/usr/bin/vmstat";
		self.args = args;
		self.ip = ip;
		self.key_filename = key_filename;

	def exec_vmstat(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":self.key_filename,
				},
			)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
		print('in exec_vmstat: self.ip: ', self.ip, ' self.args: ',self.args);
		current_time = datetime.datetime.utcnow().strftime("%d-%m-%Y_%H-%M-%S");
		output_file = self.ip + "_vmstat_" + current_time + ".out";
		self.command = "nohup " + self.command + "  " + self.args[0] + output_file + self.args[1];

		result = conn.run(self.command,hide=True);
		print(self.command,' returned ',result.exited);
		conn.close();
		if (result.exited != 0):
			print('Failed to run command: ',self.command, ' Exiting..');
			exit(-1);

	def start(self):
		t_vmstat = Thread(target=self.exec_vmstat);
		t_vmstat.start();

class monitors():
	def __init__(self,ip,mpstat_args,vmstat_args,key_filename):
		print('in monitors init. ip: ',ip);
		self.mpstat = mpstat(ip,key_filename);
		self.vmstat = vmstat(ip,key_filename);
		self.listdir = list_dir(ip,key_filename);

	def start(self):
		print('in monitors start.');
		self.mpstat.start();
		self.vmstat.start();
		#self.listdir.start();

class iperf3_server:
	def __init__(self,ip,key_filename,args=[" -s > "," 2>&1 &"]):
		self.command = "/usr/bin/iperf3";
		self.ip = ip;
		self.args = args;
		self.key_filename = key_filename;

	def start(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":self.key_filename,
				},
			)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
		current_time = datetime.datetime.utcnow().strftime("%d-%m-%Y_%H-%M-%S");
		output_file = self.ip + "_iperf3_server_" + current_time + ".out";
		self.command = "nohup " + self.command + "  " + self.args[0] + output_file + self.args[1];

		result = conn.run(self.command,hide=True);
		print(self.command,' returned ',result.exited);
		conn.close();
		if (result.exited != 0):
			print('Failed to run command: ',self.command, ' Exiting..');
			exit(-1);
	
class iperf3_client:
	def __init__(self,client_ip,server_ip,key_filename,config="input.config",args=[" > "," 2>&1 &"]):
		self.command = "/root/iperf3_test.py";
		self.config_file = "/root/" + config;
		self.args = args;
		self.ip = client_ip;
		self.server_ip = server_ip;
		self.key_filename = key_filename;

	def start(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":self.key_filename,
				},
			)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
		current_time = datetime.datetime.utcnow().strftime("%d-%m-%Y_%H-%M-%S");
		output_file = self.ip + "_" + self.server_ip + "_iperf3_test_client_" + current_time + ".out";
		self.command = "nohup /usr/bin/python3 " + self.command + "  " + self.config_file + self.args[0] + output_file\
				+ self.args[1];

		result = conn.run(self.command,hide=True);
		print(self.command,' returned ',result.exited);
		conn.close();
		if (result.exited != 0):
			print('Failed to run command: ',self.command, ' Exiting..');
			exit(-1);
		
	
class server():
	def __init__(self,server_ip,key_filename,mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(server_ip,mpstat_args,vmstat_args,key_filename);
		self.iperf3_server = iperf3_server(server_ip,key_filename);

	def start_run(self):
		print("server: in start_run");
		self.monitors.start();
		self.iperf3_server.start();
		
class client:
	def __init__(self,client_ip,server_ip,client_config,key_filename,mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(client_ip,mpstat_args,vmstat_args,key_filename);
		self.iperf3_client = iperf3_client(client_ip,server_ip,key_filename,client_config);

	def start_run(self):
		print("client: in start_run");
		self.monitors.start();
		self.iperf3_client.start();

class run_combination():
	def __init__(self,client_ip,server_ip,client_config,key_filename):
		self.server = server(server_ip,key_filename);
		self.client = client(client_ip,server_ip,client_config,key_filename);

	def start_server(self):
		self.server.start_run();

	def start_client(self):
		self.client.start_run();

# Start iperf3 server

# All routines to be started within a thread context
#def start_client_server_pair(client_server_addresses):
def start_client_server_pair(client_server_data):
	client_ip,server_ip,client_config,key_filename = client_server_data;
	rc = run_combination(client_ip,server_ip,client_config,key_filename);
	rc.start_server();
	rc.start_client();

def get_config(configfile="cli_serv.config"):
	cli_serv_pairs = [];

	print('config file passed: ',configfile);
	inf = open(configfile,"r");

	data = json.load(inf);
	print('data after json load: ',data);
	
	for i in np.arange(0,len(data)):
		cli_serv_pairs.append((data[i]["client"],data[i]["server"],data[i]["client_config"],\
				data[i]["key_filename"]));

	return cli_serv_pairs;

if __name__ == "__main__":
	cli_serv_pairs = [];

	if (len(sys.argv) == 2):
		cli_serv_pairs = get_config(sys.argv[1]);
	else:
		print("Enter the number of client server combinations to start:");
		num_combinations = input();
		for i in np.arange(0,int(num_combinations)):
			print("Enter client IP and server IP separated by a space, one pair of ips per line");
			client_ip,server_ip = input().split(' ');
			print("Enter the name of the configuration file in the root folder of the client");
			client_config = input();
			print("Enter the name of the file (including path) locally present, that contains \
				 the ssh key to connect to the clients and servers");
			key_filename = input();
			if (len(key_filename)==0):
				print("ssh key filename must be specified to proceed further. Exiting.");
				exit(-1);
			cli_serv_pairs.append((client_ip,server_ip,client_config,key_filename));

	for i in np.arange(0,len(cli_serv_pairs)):
		run_thread = Thread(target=start_client_server_pair,args=(cli_serv_pairs[i],));
		run_thread.start();
