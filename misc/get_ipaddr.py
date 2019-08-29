# Acknowledgements: https://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-from-nic-in-python
# Get the ip address of the host
import socket
import fcntl
import struct

class current_host:
	def __init__(self):
		self.ip_addr = None;	
		self.ghbn_ex = (None,None,None);
		self.addrinfo = [];
		self.ifnamesize = 16; # IFNAMSIZ in if.h has a max value of 16
	def get_ipaddr(self):
		name = socket.gethostname();
		#self.ip_addr = socket.gethostbyname(name);
		#self.ghbn_ex = socket.gethostbyname_ex(name);
		#self.addrinfo = socket.getaddrinfo(name,80,0,0,0);	
		self.addrinfo = socket.if_nameindex();

	def get_ipaddr2(self,ifname):
		s = socket.socket(family=socket.AF_INET,type=socket.SOCK_DGRAM);
		# SIOCGIFADDR = 0x8915
		netaddr = fcntl.ioctl(s.fileno(),0x8915 \
				,struct.pack('256s',\
				bytearray(ifname[:self.ifnamesize],'utf-8')));
		return socket.inet_ntoa(netaddr[20:24]);

	def print_ipaddr(self):
		#print('The current host has ip address: ',self.ip_addr);
		#print('triple returned: ',self.ghbn_ex); # shows ip addr 127.0.1.1
		print('addrinfo returned by if_nameindex(): ',self.addrinfo);

if __name__ == "__main__":
	print("getting current host ip address.");
	print("Specify the interface to fetch the address for (e.g. eth0):");
	iface = input();
	ch = current_host();
	ch.get_ipaddr();
	#print('ipaddr for eth0: ',ch.get_ipaddr2('eth0'));
	print('ipaddr for ',str(iface),": ",ch.get_ipaddr2(str(iface)));
