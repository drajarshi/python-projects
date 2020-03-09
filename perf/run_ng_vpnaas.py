__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2020 Rajarshi Das"

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
	def __init__(self,ip,key_filename,user=None,jumpbox_user=None,\
				jumpbox_key_filename=None,jumpbox_ip=None,vpn_port=None,\
				args=["-P ALL 2 > ", " 2>&1 &"]):
		self.command = "/usr/bin/mpstat";
		self.args = args;
		self.ip = ip;
		self.key_filename = key_filename;
		self.user = user;
		self.jumpbox_user = jumpbox_user;
		self.jumpbox_key_filename = jumpbox_key_filename;
		self.jumpbox_ip = jumpbox_ip;
		self.vpn_port = vpn_port;

	def exec_mpstat(self):
		try:
			if (self.jumpbox_ip != None): # with a jumpbox_ip, targeting a vpn gateway
				proxyCommand = "ssh -i " + self.jumpbox_key_filename + " -v -W " + \
								self.ip + ":" + str(self.vpn_port) + " " + \
								self.jumpbox_user + "@" + self.jumpbox_ip;

				conn = Connection(self.ip,user=self.user,
					port=self.vpn_port,
					gateway=proxyCommand,
					connect_kwargs={
						"key_filename":self.key_filename,
					},
				)
			else:
				conn = Connection(self.ip,user=self.user,
					connect_kwargs={
						"key_filename":self.key_filename,
					},
				)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
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
	def __init__(self,ip,key_filename,user=None,jumpbox_user=None,\
				jumpbox_key_filename=None,jumpbox_ip=None,vpn_port=None,\
				args=[" -t 2 > "," 2>&1 &"]):
		self.command = "/usr/bin/vmstat";
		self.args = args;
		self.ip = ip;
		self.key_filename = key_filename;
		self.user = user;
		self.jumpbox_user = jumpbox_user;
		self.jumpbox_key_filename = jumpbox_key_filename;
		self.jumpbox_ip = jumpbox_ip;
		self.vpn_port = vpn_port;

	def exec_vmstat(self):
		try:
			if (self.jumpbox_ip != None): # with a jumpbox_ip, targeting a vpn gateway
				proxyCommand = "ssh -i " + self.jumpbox_key_filename + " -v -W " + \
								self.ip + ":" + str(self.vpn_port) + " " + \
								self.jumpbox_user + "@" + self.jumpbox_ip;

				conn = Connection(self.ip,user=self.user,
					port=self.vpn_port,
					gateway=proxyCommand,
					connect_kwargs={
						"key_filename":self.key_filename,
					},
				)
			else:
				conn = Connection(self.ip,user=self.user,
					connect_kwargs={
						"key_filename":self.key_filename,
					},
				)
		except ValueError as e:
			print("Value error while connecting to ",self.ip);
			exit(-1);
			
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
	def __init__(self,ip,mpstat_args,vmstat_args,key_filename,\
				user=None,jumpbox_user=None,jumpbox_key_filename=None,\
				jumpbox_ip=None,vpn_port=None):
		print('in monitors init. ip: ',ip);
		print('in monitors init. vpn_port: ',vpn_port);
		if (jumpbox_ip != None):# VPN gateway
			self.mpstat = mpstat(ip,key_filename,user,jumpbox_user,\
							jumpbox_key_filename,jumpbox_ip,vpn_port);
			self.vmstat = vmstat(ip,key_filename,user,jumpbox_user,\
							jumpbox_key_filename,jumpbox_ip,vpn_port);
		else:
			print('monitors: client or server');
			self.mpstat = mpstat(ip,key_filename,user);
			self.vmstat = vmstat(ip,key_filename,user);
		self.listdir = list_dir(ip,key_filename);

	def start(self):
		print('in monitors start.');
		self.mpstat.start();
		self.vmstat.start();
		#self.listdir.start();

class iperf3_server:
	def __init__(self,ip,key_filename,server_user,args=[" -s > "," 2>&1 &"]):
		self.command = "/usr/bin/iperf3";
		self.ip = ip;
		self.args = args;
		self.key_filename = key_filename;
		self.user = server_user;

	def start(self):
		try:
			conn = Connection(self.ip,user=self.user,
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
	def __init__(self,client_ip,server_ip,key_filename,client_user,\
				config="input.config",args=[" > "," 2>&1 &"]):
		self.command = "/root/iperf3_test.py";
		self.config_file = "/root/" + config;
		self.args = args;
		self.ip = client_ip;
		self.server_ip = server_ip;
		self.key_filename = key_filename;
		self.user = client_user;

	def start(self):
		try:
			conn = Connection(self.ip,user=self.user,
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
		
class peer_vpn_gateway():
	def __init__(self,peer_vpn_ip,vpn_key_filename,user,jumpbox_user,\
				jumpbox_key_filename,jumpbox_ip,vpn_port,\
				mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(peer_vpn_ip,mpstat_args,vmstat_args,\
						vpn_key_filename,user,jumpbox_user,jumpbox_key_filename,\
						jumpbox_ip,vpn_port);

	def start_run(self):
		self.monitors.start();

class primary_vpn_gateway():
	def __init__(self,primary_vpn_ip,vpn_key_filename,user,jumpbox_user,\
				jumpbox_key_filename,jumpbox_ip,vpn_port,\
				mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(primary_vpn_ip,mpstat_args,vmstat_args,\
						vpn_key_filename,user,jumpbox_user,jumpbox_key_filename,\
						jumpbox_ip,vpn_port);

	def start_run(self):
		print("primary_vpn: in start_run");
		self.monitors.start();

class server():
	def __init__(self,server_ip,key_filename,server_user,mpstat_args=None,\
				vmstat_args=None):
		self.monitors = monitors(server_ip,mpstat_args,vmstat_args,key_filename,\
								server_user);
		self.iperf3_server = iperf3_server(server_ip,key_filename,server_user);

	def start_run(self):
		self.monitors.start();
		self.iperf3_server.start();
		
class client:
	def __init__(self,client_ip,server_ip,client_config,key_filename,\
				client_user,mpstat_args=None,vmstat_args=None):
		self.monitors = monitors(client_ip,mpstat_args,vmstat_args,key_filename,client_user);
		self.iperf3_client = iperf3_client(client_ip,server_ip,key_filename,client_user,\
										client_config);

	def start_run(self):
		print("client: in start_run");
		self.monitors.start();
		self.iperf3_client.start();

class run_combination():
	def __init__(self,client_ip,server_ip,client_config,key_filename,primary_vpn_ip,\
				peer_vpn_ip,jumpbox_ip,jumpbox_key_filename,vpn_key_filename,\
				vpn_port,client_user,server_user,vpn_user,jumpbox_user):
		self.server = server(server_ip,key_filename,server_user);
		self.client = client(client_ip,server_ip,client_config,key_filename,client_user);
		self.primary_vpn = primary_vpn_gateway(primary_vpn_ip,vpn_key_filename,vpn_user,\
							jumpbox_user,jumpbox_key_filename,jumpbox_ip,vpn_port);
		self.peer_vpn = peer_vpn_gateway(peer_vpn_ip,vpn_key_filename,vpn_user,\
							jumpbox_user,jumpbox_key_filename,jumpbox_ip,vpn_port);

	def start_server(self):
		self.server.start_run();

	def start_client(self):
		self.client.start_run();

	def start_primary_vpn(self):
		self.primary_vpn.start_run();

	def start_peer_vpn(self):
		self.peer_vpn.start_run();
# Start iperf3 server

# All routines to be started within a thread context
#def start_client_server_pair(client_server_addresses):
def start_client_server_pair(client_server_data):
	client_ip,server_ip,client_config,key_filename,primary_vpn_ip,\
	peer_vpn_ip,jumpbox_ip,jumpbox_key_filename,vpn_key_filename,\
	vpn_port,client_user,server_user,vpn_user,\
	jumpbox_user = client_server_data;

	rc = run_combination(client_ip,server_ip,client_config,key_filename,\
						primary_vpn_ip,peer_vpn_ip,jumpbox_ip,\
						jumpbox_key_filename,vpn_key_filename,vpn_port,\
						client_user,server_user,vpn_user,jumpbox_user);
	rc.start_primary_vpn();
	rc.start_peer_vpn();
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
				data[i]["key_filename"],data[i]["primary_vpn"],data[i]["peer_vpn"],\
				data[i]["jumpbox"],data[i]["jumpbox_key_filename"],data[i]["vpn_key_filename"],\
				data[i]["vpn_port"],data[i]["client_user"],data[i]["server_user"],\
				data[i]["vpn_user"],data[i]["jumpbox_user"]));

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
			print("Enter the Public IP addresses of the primary and peer VPN gateways\
					separated by a space");
			primary_vpn_ip,peer_vpn_ip = input().split(' ');
			print("Enter the public IP address of the jumpbox for reaching the VPN gateways:");
			jumpbox_ip = input();
			print("Enter the name of the file (including path) locally present, that contains \
				 the ssh key to connect to the VPN jumpbox");
			jumpbox_key_filename = input();
			if (len(jumpbox_key_filename)==0):
				print("ssh key filename must be specified to proceed further. Exiting.");
				exit(-1);
			print("Enter the name of the file (including path) locally present, that contains \
				 the ssh key to connect from the VPN jumpbox to the VPN gateway");
			vpn_key_filename = input();
			if (len(vpn_key_filename)==0):
				print("ssh key filename must be specified to proceed further. Exiting.");
				exit(-1);
			print("Enter the port number used to ssh to the VPN gateway from the jumpbox");
			print("Specify 22 if no special port is assigned");
			vpn_port = input();
			print("Enter the client username, server username, vpn username, and jumpbox\
					username, separated by commas");
			client_user,server_user,vpn_user,jumpbox_user = input().split();
			cli_serv_pairs.append((client_ip,server_ip,client_config,key_filename,\
								primary_vpn_ip,peer_vpn_ip,jumpbox_ip,\
								jumpbox_key_filename,vpn_key_filename,vpn_port,\
								client_user,server_user,vpn_user,jumpbox_user));

	for i in np.arange(0,len(cli_serv_pairs)):
		run_thread = Thread(target=start_client_server_pair,args=(cli_serv_pairs[i],));
		run_thread.start();
