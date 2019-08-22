#1) Consider a human-readable text log file. Each line contains [0 - 1] URL's. 
#For example: 
#1234567 [INFO] Accessed http://random.co.uk/beta.html?b=9 
#1234670 [INFO] Process completed in 4ms. 
#1234678 [Warning] http://random.co.uk unexpected behaviour 
#1234678 [INFO] Accessed http://www.example.com/alpha.html?a=1 ... 
#Write some code that lists all the domains that appear in the log file, and the count of how often each domain appears. 
#Eg, for the above segment the output would be: random.co.uk 2 www.example.com 1
#Follow up: how well does your solution scale for a file with 100 lines, 100,000 lines or 10^9 lines of log entries?
#2) Write a function that will return True if its string parameter has balanced parentheses, and returns False otherwise

# 1) 16:42-16:50 16:51-16:59
import numpy as np
import sys
import re

# parse log file. list all domains and count of how often each appears
def parse(logfile):
    domains = [];
    domaincounts = [];
    
    with open(logfile,'r') as f:
        for line in f:
            if '//' not in line:
                continue;
            #temp = line.split('//')[1];    
            temp = re.split('//',line); # split on //
            print('temp: ',temp);
            elements = re.split(' |/',temp[1]); # split on space or / on the 2nd element returned by previous split.
            #elements = line.split('//')[1].split('/ ',regex=True);
            print('after split: ',elements);
            
            #for i in np.arange(0,len(elements)):
            #    domainfound = False;
            #    if (('http' in elements[i]) or ('https' in elements[i])):
            #        for j in np.arange(0,len(domains)):
            #            if (domains[j] == elements[i+1]):
            #                domaincounts[j] += 1;
            #                domainfound = True;
            #                break;
            #        if (domainfound == False):
            #            domains.append(elements[i+1]);
            #            domaincounts.append(1);
                        
            domainfound = False;
            for j in np.arange(0,len(domains)):
                 if (domains[j] == elements[0]): #elements[0] contains the domain name.
                     domaincounts[j] += 1;
                     domainfound = True;
                     break;
            if (domainfound == False):
              domains.append(elements[0]);
              domaincounts.append(1);                
                


    strfull = '';
    for i in np.arange(0,len(domains)):
        strfull = strfull + str(domains[i]) + " " + str(domaincounts[i]) + " ";
        
    print(strfull); 

if __name__ == '__main__':
    if (len(sys.argv)< 2):
        print('Call program as <program name> <log file>. Exiting.');
        exit(-1);
    
    parse(sys.argv[1]);