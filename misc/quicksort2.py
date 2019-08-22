# quicksort 2. With classes
import numpy as np
import math

class node:
    def __init__(self, data):
        self.value = data;
        self.next = None;
        self.prev = None;
    def __del__(self):
        self.value = None;

def add_nodes(data):
   for i in np.arange(0,len(data)):
        ndata = node(data[i]);
        if (i==0):
            head = ndata;
        else:
            ndata.next = head;
            head.prev = ndata;
            head = ndata;

def swap(data,left,right):
   temp = data[left];
   data[left] = data[right];
   data[right] = temp;

def qs(data):
   if (len(data) == 1): # already sorted
        return;
        
   if (len(data)%2 == 0):
        pivot = int(len(data)/2) - 1;
   else:
        pivot = int(math.floor(len(data)/2));
   
   print('pivot: ',pivot);
   end = len(data)-1;
  
   swap(data,pivot,end);
   pivot = end;
   print('data after swap of pivot and end: ',data);
   
   left = 0;
   right = pivot - 1;
   end = right;
   start = left;

   while(True): # The outer while loop is required since we need to again proceed if we get to the condition left < right.
    while(left <= end):
        if (data[left] < data[pivot]):
            left += 1;
        else:
            break;
    while(right >= start):
        if (data[right] >= data[pivot]):
            right -= 1;
        else:
            break;
            
    if (left < right):
        swap(data,left,right);
        print('data after swap of l and r: ',data);
        continue;
    if (right < left):
        swap(data,left,pivot);
        pivot = left;
        print('data after swap of l and p: ',data);
        break;
   
   #while((left <= end) and (data[left] < data[pivot])): # move until the pivot - 1 position
   #     left += 1;
   #while((data[right] >= data[pivot]) and (right >= left) and (right >= start)):
   #     right -= 1;
   
   #if (left < right):
   #     swap(data,left,right);
   #     print('data after swap of l and r: ',data);
        
   #if (right < left): # all elements to left of left are < pivot, and those to the right of left are > pivot
   #     swap(data,left,pivot);
   #     pivot = left; # pivot at final position
   #     print('data after swap of l and p: ',data);
   
   #if (pivot >= 0):
   if (pivot >= 0): # pivot = 0 does not make sense for left_data
        if (pivot > 0):
            if (pivot == 1):
                temp_data = [];
                temp_data.append(data[0]);
                left_data = temp_data;
                #data[0] = left_data; # No need to set it back since its a single element and already sorted
            elif (pivot > 1):
                left_data = data[0:pivot]; # data actually gets counted from 0 to pivot -1 (including)
                if (len(left_data)>0):
                    qs(left_data);
                    data[0:pivot] = left_data; # set the sorted values back in 'data' variable once qs is done.
            print('left_data length: ',len(left_data));
#                if (len(left_data)>0):
#                   qs(left_data);

        print('next is qs on right_data. len(data): ',len(data), ' and pivot+1: ',pivot+1);
        right_data = data[pivot+1:len(data)]; # data actually gets counted from pivot+1 to len(data)-1 (including)
        print('right_data length: ',len(right_data));
        if (len(right_data)>0):
            qs(right_data);
            data[pivot+1:len(data)] = right_data; # set the sorted values back in 'data' variable once qs is done.
   
def parse_input(data, data_input):
    temp = list(map(int,data_input.split(' ')));
    for i in temp:
        data.append(i);
        
if __name__ == '__main__':
    print('enter a space separated list of numbers to be quick sorted:');
    data_input = input();
    data = [];
    
    head = None;
    parse_input(data, data_input);
    print('data before sort: ',data);
    qs(data);
    print('data after sort: ',data);