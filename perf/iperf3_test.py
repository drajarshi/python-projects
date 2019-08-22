__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2019 Rajarshi Das"

import numpy as np
from subprocess import call
import time

class iperf3:
	def __init__(self,optionlist):
		self.iperf_command = "/usr/bin/iperf3";
		self.ifconfig_command = "/sbin/ifconfig";
		self.allowed_options = ["-c","-i","-P","-t"];
		self.coption = None;
		self.ioption = None;
		self.Poption = None;
		self.list_c = [];
		self.list_P = [];
		self.list_i = [];
		self.list_t = [];
		self.step = 5; # default step to be used with lower and upper bounds if none explicitly specified.
		self.option_map = {
		#	"-c": None,
		#	"-t":[60],
		#	"-i":[5,10],
		#	"-P":[5,50]
		};

      # prepare option map
		for i in np.arange(0,len(optionlist)):
			if optionlist[i] == "-c":
				self.coption = True;
				self.option_map[optionlist[i]] = str(optionlist[i+1]);
				print(self.option_map);
				continue;
			elif ((optionlist[i] == "-t") or (optionlist[i] == "-i") or (optionlist[i] == "-P")): 
				if (optionlist[i] == "-t"):
					self.toption = True;
				elif (optionlist[i] == "-i"):
					self.ioption = True;
				else:
					self.Poption = True;
				temp = [];
				#temp.append(optionlist[i+1]);
				#if ((i+2 < len(optionlist)) and (isinstance(optionlist[i+2],int))): # check if we have the upper limit
				if ((i+2 < len(optionlist)) and (self.is_integer(optionlist[i+2]))): # check if we have the upper limit
					j = int(optionlist[i+1]);
					while(j <= int(optionlist[i+2])):
					#for j in np.arange(int(optionlist[i+1]),int(optionlist[i+2])+1):
						temp.append(j);
						j += self.step;
					self.option_map[optionlist[i]] = temp;
				else:	# only one limit specified?
					#if ((i+1 < len(optionlist)) and (isinstance(optionlist[i+1],int))):
					if ((i+1 < len(optionlist)) and (self.is_integer(optionlist[i+1]))):
						temp.append(optionlist[i+1]);
						self.option_map[optionlist[i]] = temp;
					else: # no limits specified for the option
						print("No limits specified for option ",optionlist[i]);
						exit(-1);

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
      
	def execute_test(self):
		for k,v in self.option_map.items():
			temp = self.switch_option(k);
			if (k != "-c"): # for '-c' set the IP address directly.
				for i in v:
					temp.append(i);
			else:
				temp.append(v);
			#temp = v;
        
		print('self lists:');
		print(self.list_i);
		print(self.list_t);
		print(self.list_P);
		print(self.list_c);

		for ii in np.arange(0,len(self.list_i)):
			for ic in np.arange(0,len(self.list_c)):
				for iP in np.arange(0,len(self.list_P)):
					for it in np.arange(0,len(self.list_t)):
						current_time = time.strftime("%d-%m-%Y_%H:%M:%S_");
						outfile = "i" + str(self.list_i[ii]) + "_to_" + str(self.list_c[ic]) + \
							"_" + "P" + str(self.list_P[iP]) + "_" + "t" + str(self.list_t[it]) + ".out";
						outfile = current_time + outfile;
						outf = open(outfile,"w");
						print('outfile: ',outfile);
						print('i value type: ',type(self.list_P[iP]));
						print('i value : ',self.list_P[iP]);
						ret = call([self.iperf_command,"-c",str(self.list_c[ic]),"-i",str(self.list_i[ii]),\
								"-P",str(self.list_P[iP]),"-t",str(self.list_t[it])],stdout=outf,stderr=outf);
						print("iperf call returned ",ret);
						#exit(-1);

def test_iperf3(option):
	call(["/usr/bin/iperf3",option]);	
	return;

def run_test(options):
	return;

if __name__ == "__main__":
#	test_iperf3("-h");
	print("Enter a comma separated list of options for the iperf3 command\n");
	optionlist = []
	#optionlist = list(input().split(' '));
	optionlist = input().split(' ');

	print(optionlist);		
	ipf3 = iperf3(optionlist);
	ipf3.print_option_map();

	ipf3.execute_test();
