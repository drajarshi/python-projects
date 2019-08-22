# return multiple values from a python routine

import numpy as np

def test_mult_return(a,b):
    return a+b,a-b;
    
def parse_input(numbers,num_list):
    temp = list(map(int,numbers.split(' ')));
    for i in np.arange(0,len(temp)):
        num_list.append(temp[i]);
        
if __name__ == '__main__':
    print('enter two numbers:');
    numbers = input();
    
    num_list = [];
    parse_input(numbers, num_list);
    print(num_list);
    sum,diff = test_mult_return(num_list[0],num_list[1]);
    print(sum,diff);