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
	def __init__(self,ip,args=[" -l > "," 2>&1 &"]):
		print("list_dir: __init__");
		self.command = "/bin/ls";
		self.ip = ip;
		self.args = args;
	
	def exec_listdir(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":"/home/rajarshi/.ssh/id_rsa_vpnaas_ng_prod",
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
	def __init__(self,ip,args=["-P ALL 2 > ", " 2>&1 &"]):
		self.command = "/usr/bin/mpstat";
		self.args = args;
		self.ip = ip;

	def exec_mpstat(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":"/home/rajarshi/.ssh/id_rsa_vpnaas_ng_prod",
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
	def __init__(self,ip,args=[" -t 2 > "," 2>&1 &"]):
		self.command = "/usr/bin/vmstat";
		self.args = args;
		self.ip = ip;

	def exec_vmstat(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":"/home/rajarshi/.ssh/id_rsa_vpnaas_ng_prod",
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
	def __init__(self,ip,mpstat_args,vmstat_args):
		print('in monitors init. ip: ',ip);
		self.mpstat = mpstat(ip);
		self.vmstat = vmstat(ip);
		self.listdir = list_dir(ip);

	def start(self):
		print('in monitors start.');
		self.mpstat.start();
		self.vmstat.start();
		#self.listdir.start();

class iperf3_server:
	def __init__(self,ip,args=[" -s > "," 2>&1 &"]):
		self.command = "/usr/bin/iperf3";
		self.ip = ip;
		self.args = args;

	def start(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":"/home/rajarshi/.ssh/id_rsa_vpnaas_ng_prod",
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
	def __init__(self,client_ip,server_ip,config="input.config",args=[" > "," 2>&1 &"]):
		self.command = "/root/iperf3_test.py";
		self.config_file = "/root/" + config;
		self.args = args;
		self.ip = client_ip;
		self.server_ip = server_ip;

	def start(self):
		try:
			conn = Connection(self.ip,user="root",
				connect_kwargs={
					"key_filename":"/home/rajarshi/.ssh/id_rsa_vpnaas_ng_prod",
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
	def __init__(self,server_ip,mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(server_ip,mpstat_args,vmstat_args);
		self.iperf3_server = iperf3_server(server_ip);

	def start_run(self):
		print("server: in start_run");
		self.monitors.start();
		self.iperf3_server.start();
		
class client:
	def __init__(self,client_ip,server_ip,client_config,mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(client_ip,mpstat_args,vmstat_args);
		self.iperf3_client = iperf3_client(client_ip,server_ip,client_config);

	def start_run(self):
		print("client: in start_run");
		self.monitors.start();
		self.iperf3_client.start();

class run_combination():
	def __init__(self,client_ip,server_ip,client_config):
		self.server = server(server_ip);
		self.client = client(client_ip,server_ip,client_config);

	def start_server(self):
		self.server.start_run();

	def start_client(self):
		self.client.start_run();

# Start iperf3 server

# All routines to be started within a thread context
#def start_client_server_pair(client_server_addresses):
def start_client_server_pair(client_server_data):
	client_ip,server_ip,client_config = client_server_data;
	rc = run_combination(client_ip,server_ip,client_config);
	rc.start_server();
	rc.start_client();

def get_config(configfile="cli_serv.config"):
	cli_serv_pairs = [];

	print('config file passed: ',configfile);
	inf = open(configfile,"r");

	data = json.load(inf);
	print('data after json load: ',data);
	
	for i in np.arange(0,len(data)):
		cli_serv_pairs.append((data[i]["client"],data[i]["server"],data[i]["client_config"]));

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
			cli_serv_pairs.append((client_ip,server_ip));

	for i in np.arange(0,len(cli_serv_pairs)):
		run_thread = Thread(target=start_client_server_pair,args=(cli_serv_pairs[i],));
		run_thread.start();
