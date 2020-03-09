__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2020 Rajarshi Das"

import json
import sys

# Specify a json file as argument. This json is generated
# from running iperf3_test.py. A space separated list of
# all throughput and corresponding retransmits is printed.

fp = open(sys.argv[1],'r');
f = json.load(fp);


ints = f['intervals'];

for j in ints:
	print(j['sum']['bits_per_second'],j['sum']['retransmits']);
