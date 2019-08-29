# create given folder name, cd to it, and run command inside it.
from subprocess import call
import os
import shutil

class run_command:
	def __init__(self,path,command,outputfile):
		self.path = path;
		self.command = command;
		self.outputfile = outputfile;
		self.cwd = None;

	def exec_cmd(self):
		outf = open(self.outputfile,'w');
		ret = call([self.command],stdout=outf,stderr=outf);
		if (ret != 0):
			print('failed to call ',str(self.command));
			exit(-1);
		outf.close();	

	def change_dir_in(self):
		if (os.path.exists(self.path)):
			shutil.rmtree(self.path);
			os.makedirs(self.path);
		else:
			os.makedirs(self.path);

		print('self.path: ',self.path);

		try:
			self.cwd = os.getcwd();
		except OSError:
			print('Could not get current working directory. error: ',OSError.args);
			exit(-1);

		try:
			os.chdir(self.path);
		except (OSError,FileNotFoundError,PermissionError,NotADirectoryError) as e:
			print('could not change directory to ',self.path);
			print('Error: ',e.args);
			exit(-1);

	def change_dir_out(self):
		try:
			os.chdir(self.cwd);
		except (OSError,FileNotFoundError,PermissionError,NotADirectoryError) as e:
			print('could not change directory to ',self.cwd);
			print('Error: ',e.args);
			exit(-1);

		tarfile = self.path + ".tar";
		ret = call(['tar','-cvf',tarfile,self.path]);
		if (ret != 0):
			print('failed to tar the results.');
			exit(-1);
		ret = call(['gzip',tarfile]);
		if (ret != 0):
			print('failed to zip the tarfile.');
			exit(-1);
		print('results in :',tarfile,'.gz');

if __name__ == "__main__":
	print("enter name of folder to create.");
	path = input();
	
	print("enter command to run");
	command,outputfile = map(str,input().split(' '));

	rc = run_command(path,command,outputfile);
	rc.change_dir_in();
	rc.exec_cmd();
	rc.change_dir_out();
