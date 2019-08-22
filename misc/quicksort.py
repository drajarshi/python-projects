# implement quicksort on a input array
import sys
import numpy as np
import math as math

def swap(data, left, right):
    temp = data[left];
    data[left] = data[right];
    data[right] = temp;
    
def swappos(left, right):
    temp = left;
    left = right;
    right = temp;

def qs(data,l,p,r): # l : left position, p: pivot position, r: right position
    print("inside the qs routine");
    
    # Move the pivot to the end
    end_p = r; # Save the current end position as it will be required while invoking the subarrays
    
    print('debug:, p: ', p, ' data[p]: ', data[p], 'end_p: ', end_p, 'data[end_p]: ', data[end_p]);
    swap(data, p, end_p);
    print('move p to end. swap p,end : data: ',data);
    p = end_p;
    
    print('after initial move of p to end: p: ', p, ' data[p]: ', data[p]);
    # partition the array
    r = p - 1;
    start = l;
    end = r;
    
    # Check if we have only one element
    #if (l == r): # only one element, hence sorted.
    #    return;
    
    # Fix the position of the pivot
    firstpass = False;
    
    while (firstpass == False):
        while ((l < end) and (data[l] < data[p])):
            l = l + 1;
        while ((r > start) and (r >= l) and (data[r] >= data[p])): # at each step check if r crosses l.
            r = r - 1;
        if (l < r):
            swap(data, l, r);
            print('l < r swap l,r data: ',data);
        if (r < l): # right has crossed the left
            swap(data, p, l);
            print('r < l swap p,l data: ',data);
            #swappos(p,l);
            p = l; # Do not swap since l needs to be used further.
            firstpass = True;
            if (firstpass == True):
                fp_pivot = p; # Save the pivot from first pass
            print('r < l firstpass set to True. data: ', data);
            
        elif ((l == end) or (r == start)):
            firstpass = True;
            print('firstpass set to True.');
    # run qs on left half
    #if (firstpass == True):
    #    p = fp_pivot;
    #    firstpass = False;

    print('Before calling subarrays, and completing firstpass, p,start,end:',p,start,end); 
    r = p - 1;
    l = start;  

    if (l < r and l >= start): # If l == r, the single element is already sorted. if r < l, we have already swapped as in the if case above.
        p = int(math.floor((r-l)/2));
        print('calling left subarr qs with l,r,start,end: ',l,p,r);
        qs(data, l, p, r);
    else:
        print('can not call left subarray with l,p,r:',l,p,r);
    # run qs on right half # The pivot to be used below is the position obtained when 1st pass was completed, and not the pivot used in completing
    # left half.
    l = p + 1;
    r = end_p;
    
    if (l < r and r <= end): # If l == r, its already sorted. 
        p = l + int(math.floor((r-l)/2));
        print('calling right subarr qs with l,r,start,end: ',l,p,r);
        qs(data, l, p, r);
    else:
        print('can not call right subarray with l,p,r:',l,p,r);
        
def parse_input(text,data):

#data = list(text);

    null = '';
    templist = [];
    temp = '';

# Convert the input into a list
    for i in np.arange(0,len(text)):
        if (text[i] != ' '):
            templist.append(text[i]);
            #print('templist: ',templist);
        else:
            temp = null.join(templist);
            templist[:] = [];
            #print('temp: ',temp);
            data.append(int(temp));

    temp = null.join(templist);
    data.append(int(temp));
   
    print(data);

def parse_input2(text, data2):
    l_data = list(map(int,text.split(' ')));
    for i in l_data:
        data2.append(i);
    print('in parse_input2:',data2);
    
    #data2 = list(map(int, text.split(' '))); # This REPLACES data2 and therefore, the value is  not retained once we return from 
                                    # parse_input2. Instead the previous method of appending MODIFIES data2 and it is 
                                    # treated as pass by reference. Once we return, we have the value retained. Further
                                    # list is mutable, a string is not.
    
if __name__ == "__main__":

    print("enter the numbers which need to be sorted:");
    text = input();

    print('Initial array: ',text);

    data = [];

    #print('before parse_input. data: ',data);
    parse_input(text, data);

    #print('completed parse_input. data: ',data);
    
    data[:] = [];
    #data.clear();
    
    parse_input2(text, data);
    #print('completed parse_input2. data: ',data);
    
    if (len(data)%2 == 0): # even number of elements
        pivot = int(len(data)/2 - 1);
    else:
        pivot = int(math.floor(len(data)/2));
        
    left = 0;
    right = len(data)-1;
    
    print('debug: input to qs: ', 'data:',data,'left: ',left, 'pivot: ',pivot, 'right: ', right);
    qs(data, left, pivot, right);
    print('sorted array: ', data);