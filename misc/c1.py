# zhiwehu: python challenge problem 1 from https://github.com/zhiwehu/Python-programming-exercises
# Write a program which will find all such numbers which are divisible by 7 but are not a multiple of 5,
# between 2000 and 3200 (both included).
# The numbers obtained should be printed in a comma-separated sequence on a single line.
import numpy as np

def find_nums(start=0, end=0):
    series = [];

    # getting the below statements within the find_nums routine in order to implement a switch case.
    print("enter the start and end values of the test range: ");
    range = list(map(int,input().split(' ')));
    
    start = range[0];
    end = range[1];
    
    for i in np.arange(start, end+1):
        if ((i%7 == 0) and (i%5 != 0)):
            series.append(i);
    print(series);
    return;
    
# Generate factorial for a given number    
def gen_factorial(num=0):
    print("enter the value for which the factorial value has to be generated:");
    num = int(input());

    fact = 1;
    print('value entered: ',num);
    ip_value = num;
    while (num >= 1):
        fact = fact * num;
        print('fact: ',fact);
        num -= 1;

    #return fact;
    print("the factorial of ",ip_value," is ",fact);
    return;

#With a given integral number n, write a program to generate a dictionary that contains (i, i*i) such that is an integral number between 1 and n 
#(both included). and then the program should print the dictionary.
def gen_square_dict(num=0):
    print("Enter the upper limit to generate the square value upto: ");
    limit = input();
    
    sq_dict = {}
    
    for i in np.arange(1,int(limit)+1):
        sq_dict[i] = i*i;
    
    print(sq_dict);
    
def no_option_call():
    print("no option was specified. Exiting");
    return;
    
# test options using dictionary's get method    
def map_option_to_test(option):
    option_test = {
    1:"one",
    2:"two"
    };
    
    print(option_test.get(int(option),"none"));
    
def map_option_to_call(option):
   option_call = {
    1:find_nums,
    2:gen_factorial,
    3:gen_square_dict
   };
   
   fn_to_call = option_call.get(int(option),no_option_call);
   fn_to_call();

def print_options():
    print("options available:. choose one of the numbers specified in ()");
    print("get values which are in a specified range, divisible by 7 but not a multiple of 5: (1)");
    print("Return the factorial value for a given value: (2)");
    print("Given a number, generate a dictionary mapping i:i^2 from 1 to the number: (3)");
    
if __name__ == "__main__":
    print_options();

    options = [1,2,3];
    
    option = input();
    while(int(option) not in options):
        print_options();
        option = input();
    
    # all options are being called! fix this.
    map_option_to_call(option);
    
    #map_option_to_test(option);
