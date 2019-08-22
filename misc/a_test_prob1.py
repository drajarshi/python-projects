# For a warehouse, a set of items need to be assembled together. A list of items is provided, and each member of the list is the size of the item. 
#Another value which is the number of items, is provided. From the given list, only two items can be packed at a time. The sum of the two 
#item sizes, is the size of the new item. It is also the time that it takes to pack the two items together. Find the minimum time that it 
#takes to assemble all the items together.

# approach:
# sort list. pick first 2 elements, replace them with their sum, sort list again, pick first 2 element, replace with sum, sort list again and 
#so on until list is empty.

# fixes over quicksort2.py
# 1. Addressed the case where incoming data for qs() is identical. Return in such a case. (check if count of 1st element is same as length of data)
# 2. Addressed case where left or right element == pivot. So, introduced within while(True): while(data[left] <= data[pivot]) instead of data[left] 
# < data[pivot]. This fix also covers the fix in 1.

import numpy as np
import math

def swap(data, left, right):
    temp = data[left];
    data[left] = data[right];
    data[right] = temp;

# use quicksort to order the list of items
def qs(data):
   
   #print('in qs routine');
   if (len(data)==1):
        return;

   print('started qs with data: ',data); 
   
#   if (data.count(data[0])==len(data)): # all elements are identical. # fix 1. above
#        return;
   
   left = 0;
   right = len(data)-1;
   
   start = left;
   end = right;
   
   if (len(data)%2 == 0):
        pivot = int(len(data)/2) - 1;
   else:
        pivot = int(math.floor(len(data)/2));
   
   swap(data,end,pivot);
   pivot = end;
   
   end = pivot-1;
   right = end;
   
   while(True):
       while((data[left] <= data[pivot]) and (left <= end)):
            #if (left <= end):
                left += 1;
       while((data[right] > data[pivot]) and (right >= start)):
            #if (right >= start):
                right -= 1;
       if (right < left):
            swap(data, left, pivot);
            pivot = left;
            break;
       elif (left < right):
            swap(data, left, right);
            
   print('after first pass: data: ',data);
   if (pivot >= 0):
      if (pivot == 1):
        tempdata = data[0];
        leftdata = [];
        leftdata.append(tempdata);
        qs(leftdata);
      elif (pivot > 1):
        leftdata = data[0:pivot]; # gets data from 0 to pivot-1.
        if (len(leftdata)>0):
            qs(leftdata);
        data[0:pivot] = leftdata;
      print('after leftdata: data: ',data);  
      
      if (pivot+1 == len(data)-1):
            tempdata = data[0];
            rightdata = [];
            rightdata.append(tempdata);
            qs(rightdata);
      else:
        print('pivot+1: ',pivot+1,' len(data): ',len(data));
        rightdata = data[pivot+1:len(data)]; # counts from pivot+1 to len(data)-1
        if (len(rightdata)>0):
            qs(rightdata);
        data[pivot+1:len(data)] = rightdata;
      print('after rightdata: data: ',data);

def parse_input(data, datalist):
   temp = list(map(int, data.split(' ')));
   for i in temp:
        datalist.append(i);

def minTime(numItems, itemList):
   if (numItems <= 0):
        print('incorrect number of items. The count has to be > 0');
        return -1;
   elif (len(itemList) == 0):
        print('item list is empty. Provide a list of items');
        return -1;
   elif (numItems != len(itemList)):
        print('num of items does not match the number of items provided in the list. Provide a matching number of items');
        return -1;
   
   qs(itemList);
   print('after qs. itemList: ',itemList);
   #for i in np.arange(0,len(itemList)):
   temp = 0;
   tempTime = 0;
   
   while (True):
      print('starting with itemList: ',itemList);
      temp = itemList[0] + itemList[1];
      tempTime += temp;
      itemList.remove(itemList[0]);
      itemList.remove(itemList[0]);
      print('itemList after removing 1st 2 elements: ',itemList);
      #qs(itemList);
      itemList.insert(0,temp);
      qs(itemList);
      print('after qs. itemList: ',itemList);
      if (len(itemList)==1):
        break;

   mTime = tempTime;
   return mTime;
   
if __name__ == '__main__':
    print('enter the item sizes to be packaged together');
    input_sizes = input();
    
    print(input_sizes);
    itemList = [];
    
    parse_input(input_sizes, itemList);
    print('after parse_input. numItems: ',len(itemList), ' and list: ',itemList); 
    print('minTime is: ', minTime(len(itemList),itemList));