# Parse output of iperf2, specifically the last
# line which is a summary of the form:
# [SUM]  0.0-10.1 sec  1.34 GBytes  1.15 Gbits/sec

import os
import sys

def get_bw(outfile,finaltime):
	total_duration = "0.0-" + str(finaltime);
	for line in outfile.readlines():
		#print(line);
		if '[SUM]' in line:
			if total_duration in line: # final SUM
				columns = line.split('  '); # split columns
				print(columns);
				bw_string = columns[3].split(' '); # bw data in last column
				print(bw_string);
				notation = bw_string[2].split('bits/sec');# get format
				print(notation);
				if (notation[0] == 'K'):
					factor = 1024.0;
				elif (notation[0] == 'M'):
					factor = 1024.0*1024.0;
				elif (notation[0] == 'G'):
					factor = 1024.0*1024.0*1024.0;

				print(factor*float(bw_string[1]));

if __name__ == "__main__":
	outfile = sys.argv[1];
	outf = open(outfile,'r');
	get_bw(outf,60); # try sample final time as 10
