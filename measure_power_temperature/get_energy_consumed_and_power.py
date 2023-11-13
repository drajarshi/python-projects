__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2023 Rajarshi Das"

# Get the total energy consumed and total elapsed time, given a power reading file
# and the start and end time stamps
# e.g. $ python3 get_energy_consumed.py ./sample_power.out 13-18-56.270417 13-18-59.839517
# v1: Gives the total energy consumed, average sampling time and total application runtime
# v2 (current): Additionally generates a file delta_energy.out which captures the energy 
# consumed at each sample.
# New option: to get average power at 100% GPU Utilization, and desired core and memory
# frequencies. e.g. python3 get_energy_consumed_and_power.py <power readings file> 100
# two forms supported:
# 1. python <.py> 1 <power readings file> <gpu util threshold> <desired core freq> 
#			<desired memory freq>
# 2. python <.py> 2 <power readings file> <start timestamp> <end timestamp>
#	<MICROSECS/TIMESTAMP>
# Use the option 2 as above by specifying start and end times in microsecs format such
# as xxxxxxxx.zabcde if the intent is to gather the average power and the total energy
# consumed. MICROSECS is the default option. The TIMESTAMP option should be 
# specified only if the start and end times are provided as timestamp.
# 13-jun: Add new use case for option 2: The start time may be specified between 2 sample
# times in the csv. This can happen with a accelwattch ubench run. _v3() routine is invoked
# in such a case.
# 3. python <.py 3 <power readings file> <last #readings>
# Option 3 returns the average power of the last # iterations specified as a parameter. Useful
# for computing the average power at steady state temperature. The last parameter defaults to
# 300 if not specified.

import sys
from datetime import datetime

MICROSECS=1
TIMESTAMP=2

# ref: https://www.educative.io/edpresso/how-to-extract-the-fractional-part-of-a-float-number-in-python
def convert_usecs_to_timestamp(useconds):
	usecs = float(useconds);

	usecs = usecs%86400;
	hr = round(usecs//3600);
	min = round((usecs-(hr*3600))//60);
	rem_secs = usecs - (hr*3600) - (min*60);
	secs = round(rem_secs//1);
	msecs = round((rem_secs%1)*1e6);

	timestring = str(hr)+"-"+str(min)+"-"+str(secs)+"."+str(msecs);
	return timestring;

def get_timestamp_msecs(timestamp):
	dt_obj = datetime.strptime(timestamp,"%H-%M-%S.%f");
	dt_obj_msecs = dt_obj.timestamp()*1e6;

	return dt_obj_msecs;

# fetch the start timestamp based on number of last readings to be considered
def get_start_and_end_timestamps_by_offset(power_reading_file, num_last_readings):
	lines = 0;
	offset = 0;
	current_line = 0;

	power_file = open(power_reading_file,'r');
	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;
		lines += 1;

	power_file.seek(0,0);
	lastLine = power_file.readlines()[-1];
	if (len(lastLine.split(","))< 5):
		lines -= 1;

	offset = lines - num_last_readings + 1;

	power_file.seek(0,0);
	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;
		current_line += 1;
		if (current_line == offset):
			start_timestamp = line.split(",")[0];
		elif (current_line == lines):
			end_timestamp = line.split(",")[0];
			break;

	#print("start:",start_timestamp,"end:",end_timestamp);

	return start_timestamp,end_timestamp;
	

# credit: https://www.delftstack.com/howto/python/python-read-last-line-of-file/
def	get_start_and_end_timestamps(power_reading_file,gpu_util_threshold,\
								desired_core_freq,desired_memory_freq=5005):
	prev_sample_time = 0.0;
	firstLine_parsed = 0;
	start_timestamp = 0.0;

	#print("desired core freq:{0},desired mem freq:{1}".format(desired_core_freq,\
	#desired_memory_freq));

	power_file = open(power_reading_file,'r');
	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;

		vals = line.split(",");
		if (firstLine_parsed == 0):
			firstLine = vals;
			firstLine_parsed = 1;

		#print("vals[3-5]: ",vals[3],vals[4],vals[5]);

		if ((int(vals[4]) == desired_core_freq) and \
				(int(vals[5]) == desired_memory_freq)):
				if (int(vals[2]) < gpu_util_threshold):
					prev_sample_time = float(vals[0]);
				else:
					start_timestamp = prev_sample_time;
					break;
		else:
			continue;

	if (start_timestamp == 0.0): # the file starts at the specified util
		start_timestamp = float(firstLine[0]);

	power_file.seek(0,0);
	lastLine = power_file.readlines()[-1];
	if (len(lastLine.split(","))< 5):
		#print("incomplete last line. get previous\n");
		power_file.seek(0,0);
		lastLine = power_file.readlines()[-2];

	end_timestamp = float(lastLine.split(",")[0]);
	
	#print("start:{0}, end:{1}".format(start_timestamp,end_timestamp));

	return start_timestamp,end_timestamp

def get_max_power(power_reading_file):
	max_power = 0.0;

	power_file = open(power_reading_file,'r');
	power_file.seek(0,0);

	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;

		vals = line.split(",");
		if (float(vals[1]) > max_power):
			max_power = float(vals[1]);

	return max_power;

def get_energy_consumed_v2(power_reading_file,sample_start_time_msecs,sample_end_time_msecs):
	start_sample_found = 0;
	end_sample_found = 0;
	prev_sample_time = 0.0;
	energy_total = 0.0;
	time_total = 0.0;

	power_file = open(power_reading_file,'r');
	power_file.seek(0,0);
	#print("debug: start: ",sample_start_time_msecs," end: ",sample_end_time_msecs);

	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;

		#print("debug: line in power data file: ",line);
		vals = line.split(",");

		if (float(vals[0]) == sample_start_time_msecs):
			start_sample_found = 1;
			prev_sample_time = float(vals[0]);
		elif (float(vals[0]) == sample_end_time_msecs):
			end_sample_found = 1;
			time_delta = float(vals[0]) - prev_sample_time;
			energy_delta = time_delta*float(vals[1]);
			energy_total += energy_delta;
			time_total += time_delta;
			#print("debug: time_delta: ",time_delta," power: ",float(vals[1]),\
			#" energy_delta: ",energy_delta," energy_total: ",energy_total);
			break;
		elif (start_sample_found == 1):
			time_delta = float(vals[0]) - prev_sample_time;
			energy_delta = time_delta*float(vals[1]);
			energy_total += energy_delta;
			time_total += time_delta;
			prev_sample_time = float(vals[0]);
			#print("debug: time_delta: ",time_delta," power: ",float(vals[1]),\
			#" energy_delta: ",energy_delta," energy_total: ",energy_total);

	if ((start_sample_found == 0) or (end_sample_found == 0)): # exact matching start or
															   # end sample not found
		#print("debug: switching to routine v3");
		energy_total,time_total=get_energy_consumed_v3(power_file,\
			sample_start_time_msecs,sample_end_time_msecs);

	return energy_total,time_total;

# Is the start time between 2 samples?
def get_energy_consumed_v3(power_file,start_time_msecs,end_time_msecs):
	time_total = 0.0;
	energy_total = 0.0;
	time_delta = 0.0;
	start_sample_found = 0;
	prev_sample = 0.0;

	power_file.seek(0,0);

	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;

		vals = line.split(",");

		#print("debug v3: line: ",line);

		if ((start_sample_found == 0) and \
				(float(vals[0]) > start_time_msecs)):
			start_sample_found = 1;
			start_sample = float(vals[0]);
			#print("debug: v3: start sample: ",start_sample);
			# If the current sample covers both start and end time, we are done
			if (float(vals[0]) > end_time_msecs):
				time_delta = end_time_msecs - start_time_msecs;
				energy_total = time_delta * float(vals[1]);
				return energy_total,time_delta;
			else:# the end_time is after the current sample
				time_delta = float(vals[0]) - start_time_msecs;
				energy_total += time_delta * float(vals[1]);
				time_total += time_delta;
				prev_sample = float(vals[0]);

			#print("debug v3: time_delta: ",time_delta," power: ",float(vals[1]),\
			#" energy_total: ",energy_total);

		elif (start_sample_found == 1):
			if (float(vals[0]) > end_time_msecs):# end time in this sample
				time_delta = end_time_msecs - prev_sample;
				energy_total += time_delta * float(vals[1]);
				time_total += time_delta;
				return energy_total,time_total;

			else: # end time not in this sample. accumulate
				time_delta = float(vals[0]) - prev_sample;
				energy_total += time_delta * float(vals[1]);
				time_total += time_delta;
				prev_sample = float(vals[0]);

			#print("debug v3: time_delta: ",time_delta," power: ",float(vals[1]),\
			#" energy_total: ",energy_total);

	if (start_sample_found == 0):
		print("specified start time outside available range. Retry.\n");
		exit(-1);
	return energy_total,time_total;

def get_energy_consumed(power_reading_file,run_start_time_msecs,run_end_time_msecs):
	delta_energy_file = open("delta_energy.out",'w');
	power_file = open(power_reading_file,'r');

	start_time_partial_update = 0; # 2: complete 
	end_time_partial_update = 0; # 2: complete

	dt_obj_msecs_prev = 0;
	intermediate_elapsed_time = 0;

	total_energy_consumed = 0;
	start_energy_partial = end_energy_partial = start_time_partial =\
	end_time_partial = 0;

	sample_count = 0;
	total_sample_time = 0;
	total_intermediate_energy = 0;

	# https://www.codegrepper.com/code-examples/python/python+timestamp+in+microseconds
	for line in power_file.readlines():
		if 'argument' in line or 'Clock' in line: # first 2 lines
			continue;

		vals = line.split(",");
		dt_obj_msecs = get_timestamp_msecs(vals[0]);

		if ((start_time_partial_update == 0) and \
				(dt_obj_msecs_prev != 0) and \
				(dt_obj_msecs_prev <= run_start_time_msecs) and \
				(dt_obj_msecs > run_start_time_msecs)):
			start_time_partial = dt_obj_msecs - run_start_time_msecs;
				# elapsed time reading based on current line
			start_time_partial_update = 1;

			start_power_factor_partial = vals[1]; # power reading in current line
			start_energy_partial = float(start_time_partial) * \
				float(start_power_factor_partial);
			#print("debug: starting elapsed time: ",start_time_partial);
			#print("debug: starting energy partial: ",start_energy_partial);

			total_sample_time += dt_obj_msecs - dt_obj_msecs_prev;
			sample_count += 1;
			delta_energy_file.write(str(start_energy_partial));
			delta_energy_file.write("\n");

		elif ((end_time_partial_update == 0) and \
			(dt_obj_msecs_prev <= run_end_time_msecs) and \
			(dt_obj_msecs > run_end_time_msecs)):
				# elapsed time reading based on previous line
			end_time_partial = run_end_time_msecs - dt_obj_msecs_prev;
			end_time_partial_update = 1;

			end_power_factor_partial = vals[1]; # power reading in current line
			end_energy_partial = float(end_time_partial) * \
				float(end_power_factor_partial);
			#print("debug: ending elapsed time: ",end_time_partial);

			total_sample_time += dt_obj_msecs - dt_obj_msecs_prev;
			sample_count += 1;
			delta_energy_file.write(str(end_energy_partial));
			delta_energy_file.write("\n");
			break;

		elif (start_time_partial_update > 0): # first update is done
			intermediate_elapsed_time += dt_obj_msecs - dt_obj_msecs_prev;
			sample_count += 1;

			delta_energy = float(vals[1]) * float(dt_obj_msecs - dt_obj_msecs_prev);
			delta_energy_file.write(str(delta_energy));
			delta_energy_file.write("\n");

			total_intermediate_energy += delta_energy;
		
		dt_obj_msecs_prev = dt_obj_msecs;

	#print("debug: Total intermediate elapsed time: ",intermediate_elapsed_time,"\n");
	total_sample_time = total_sample_time + intermediate_elapsed_time; # Add the elapsed for
								# intermediate samples

	total_energy_consumed += total_intermediate_energy + start_energy_partial +\
				end_energy_partial;

	#print("Total number of samples: ",sample_count,"\n");
	average_sample_time = float(total_sample_time)/sample_count;

	average_int_sample_time = float(intermediate_elapsed_time)/(sample_count-2);

	return total_energy_consumed,total_sample_time,average_sample_time\
		,average_int_sample_time;

def compute_average_power(total_energy,total_sample_time):
	return float(total_energy/total_sample_time);

if __name__ == "__main__":
	# two forms supported:
	# 1. python <.py> 1 <power readings file> <gpu util threshold> <desired core freq> 
	#			<desired memory freq>
	# 2. python <.py> 2 <power readings file> <start timestamp> <end timestamp>
	#	<MICROSECS/TIMESTAMP>
	# 3. python <.py> 4 <power readings file> # print max power
	if (len(sys.argv) < 3):
		print("Insufficient args. Please specify the power readings file\n");
		exit(-2);

	command_type = 1; # default
	command_type = int(sys.argv[1]);

	if ((command_type != 1) and (command_type != 2) and (command_type != 3)\
			and (command_type != 4)):
		print("unsupported command type. Please specify 1,2,3 or 4 in the 1st parameter.\n");
		exit(-1);

	if (command_type == 1):
		if (len(sys.argv) < 5):
			print("Please specify 1 <power reading file> <gpu util> <desired core freq>..\n");
			print("space separated. Optionally you may also add <desired memory freq> at the end\n");
			exit(-2);

		#print("arg 0",sys.argv[0]);
		#print("arg 1",sys.argv[1]);
		#print("arg 2",sys.argv[2]);

		min_threshold_util = int(sys.argv[3]);
		if (min_threshold_util < 0) or (min_threshold_util > 100):
			print("Please specify second param as the min GPU utilization threshold..\n")
			print("between 0 and 100.. \n");
			exit(-1);

		start_timestamp,end_timestamp = get_start_and_end_timestamps(sys.argv[2]\
										,min_threshold_util,int(sys.argv[4]));

	elif (command_type == 2): # command type 2
		if (len(sys.argv) < 5):
			print("Please specify 2 <power readings file> <start timestamp> <end timestamp>\n");
			print("timestamps in the form (hh-mm-ss.ssssss) space");
			print(" separated.\n");
			exit(-3);
	elif (command_type == 3): # command type 3
		num_last_readings = 300; # default
		if (len(sys.argv) < 3):
			print("Please specify 3 <power readings file> <# last number of readings: default 300>\n");
			exit(-4);
		elif (len(sys.argv) == 4):
			num_last_readings = sys.argv[3];
	else: # command type 4: get max values
		if (len(sys.argv) < 3):
			print("Please specify 4 <power readings file> \n");
			exit(-5);

	power_reading_file = sys.argv[2];

	if (command_type == 2):
		start_timestamp = sys.argv[3];
		end_timestamp = sys.argv[4];

	if (command_type == 3):
		start_timestamp,end_timestamp = get_start_and_end_timestamps_by_offset(power_reading_file,\
												num_last_readings);
	
	time_format = MICROSECS; # default

	if ((command_type == 2) and (len(sys.argv) == 6)):
		time_format = sys.argv[5];

	#print("start timestamp: {0}, end_timestamp: {1}".format(start_timestamp,\
	#		end_timestamp));

	if (command_type == 4): # get max value
		max_power = get_max_power(sys.argv[2]);
		print("max power: ",max_power);
		exit(0);

	if (time_format == MICROSECS):
		start_time_msecs = float(start_timestamp);
		end_time_msecs = float(end_timestamp);
		total_energy_consumed,total_elapsed_time =\
			get_energy_consumed_v2(sys.argv[2],\
			start_time_msecs,end_time_msecs);
	else:
		start_time_msecs = float(get_timestamp_msecs(start_timestamp));
		end_time_msecs = float(get_timestamp_msecs(end_timestamp));
		total_energy_consumed,total_elapsed_time,average_sample_time,\
		average_int_sample_time = get_energy_consumed(sys.argv[2],\
					start_time_msecs,end_time_msecs);

	average_power = compute_average_power(total_energy_consumed,\
				total_elapsed_time);

	#print("total energy consumed: ",total_energy_consumed/1e6,\
	#		"J, total elapsed time: ",total_elapsed_time/1e6," seconds\n");

	if (time_format == TIMESTAMP):
		print("average sample time: ",average_sample_time," microseconds\n");
		print("average intermediate sample time: ",average_int_sample_time,\
				" microseconds\n");

	#print("average power: ",average_power,"W");
	if (command_type == 1):
		print(average_power,);
	else: # command type 2
		print("average power: ",average_power,"W");
		print("total energy consumed: ",total_energy_consumed/1e6,"J");
