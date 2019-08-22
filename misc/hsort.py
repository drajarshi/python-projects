# h sort
import os
import numpy as np

class node:
    def __init__(self,data=-1):
        self.left = None;
        self.right = None;
        self.parent = None;
        self.value = data;
        self.sibling = None; # to track nodes at the same level

    def print_value():
        print(self.value);
    
    def __del__(self):
        self.left = None;
        self.right = None;
        self.parent = None;
        self.value = -1;
        self.sibling = None;

#def add_nodes(node_arr, data_arr):
#    for i in np.arange(0,len(data_arr)):
#        node_new = node();
#        node_new.value = int(data_arr[i]);
        
#        node_arr.append(node_new);

def add_nodes(data_arr,level_store): # Add in BFS fashion so that each level fills up first before going to the next.
    for i in np.arange(0,len(data_arr)):
        current = node(data_arr[i]);
        if (i == 0):
            head = current;
            prev = head; # save for the next iteration
            level_store.append(current.value);
        elif prev.left == None:
                prev.left = current;
                current.parent = prev;
                level_store.append(current.value);
                #level.append(current); # keep track of all nodes at the same level.
        elif prev.right == None:
            prev.right = current;
            current.parent = prev;
            current.sibling = current.parent.left;
            current.parent.left.sibling = current;
            level_store.append(current.value);
            #right = prev.right;
            #level.append(current);
            #prev.full = True;
            if ((prev.sibling != None) and (prev.sibling.left == None)):# right sibling has both left and right children empty
                                                            # prev.sibling is None for the head node
                prev = prev.sibling;
            else: # This assumes that both left and right children are filled
                 # since the next iteration will fill both left and right children in sequence
                if (prev.sibling != None):
                    prev = prev.sibling.left; # both left and right siblings have both children filled.
                                        # start adding to the left child of the left sibling
                                        # does not apply for head node (prev.sibling is None)
                else:
                    prev = prev.left; # for head node
                                     
    print('level_store: ',level_store);
    return head;

# After the swap of two elements, the previous elements may be out of order. So, all elements prior need to be placed 
# in order (root > left and root > right) until the head node is reached.
def swap(datastore,left, right):
    left_idx = -1;
    right_idx = -1;
    
    print('calling swap with left : ',left,' right: ',right);
    for i in np.arange(0,len(datastore)):
        if (datastore[i] == left):
            left_idx = i;
        elif (datastore[i] == right):
            right_idx = i;
        if ((left_idx != -1) and (right_idx != -1)):
            break;
    print('setting left idx to: ',left_idx,' and right_idx to: ',right_idx);
    print('before swap. at left idx: ',datastore[left_idx],' and at right idx: ', datastore[right_idx]);
    temp = datastore[left_idx];
    datastore[left_idx] = datastore[right_idx];
    datastore[right_idx] = temp;
    print('after swap. at left idx: ',datastore[left_idx],' and at right idx: ', datastore[right_idx]);
    
    return datastore[left_idx],datastore[right_idx];
    
def check_values(temp, level_store):
        
        if (temp == None):
            return;
        #print('temp,temp.left,temp.right:',temp,temp.left,temp.right);
        #print('temp.value,temp.left.value,temp.right.value:',temp.value,temp.left.value,temp.right.value);
        if ((temp.left != None) and (temp.left.value > temp.value)):
            #print('1swap: temp.value:',temp.value,' with temp.left.value:',temp.left.value);
            temp.value,temp.left.value = swap(level_store, temp.value, temp.left.value);
            #print('1level_store after swap: ',level_store);
            #if (temp.parent != None):
                #print('after swap. temp.value: ',temp.value,' temp.parent: ',temp.parent,' temp.parent.value: ',temp.parent.value);
            #else:
                #print('after swap. temp.value: ',temp.value,' temp.parent: ',temp.parent);
            temp2 = temp;
            while (temp2.parent != None):
                temp2 = temp2.parent;
                if (temp2.left.value > temp2.value):
                    #print('2swap:',temp2.value,' with ',temp2.left.value);
                    temp2.value,temp2.left.value = swap(level_store, temp2.value, temp2.left.value);
                    #print('2level_store after swap: ',level_store);
                if (temp2.right.value > temp2.value):
                    #print('3swap:',temp2.value,' with ',temp2.left.value);
                    temp2.value,temp2.right.value = swap(level_store, temp2.value, temp2.right.value);    
                    #print('3level_store after swap: ',level_store);
        if ((temp.right != None) and (temp.right.value > temp.value)):
            #print('4swap:',temp.value,' with ',temp.left.value);
            temp.value,temp.right.value = swap(level_store, temp.value, temp.right.value);
            #print('4level_store after swap: ',level_store);
            temp2 = temp;
            while (temp2.parent != None):
                temp2 = temp2.parent;
                if (temp2.left.value > temp2.value):
                    #print('5swap:',temp2.value,' with ',temp2.left.value);
                    temp2.value,temp2.left.value = swap(level_store, temp2.value, temp2.left.value); 
                    #print('5level_store after swap: ',level_store);
                if (temp2.right.value > temp2.value):
                    #print('6swap:',temp2.value,' with ',temp2.left.value);
                    temp2.value,temp2.right.value = swap(level_store, temp2.value, temp2.right.value);       
                    #print('6level_store after swap: ',level_store);
        
        check_values(temp.left, level_store);
        check_values(temp.right, level_store);
        
def max_heap(head,level_store):
    # data laid out as BFS
    temp = head;
    
    check_values(temp,level_store);
    
# swap both in the tree as well as level_store (array)    
def swap_root_last_return_max(head,temp,level_store):
    if (temp == None):
        return None;
    
    print('in swap_root routine. temp.value: ',temp.value,' last_value: ',level_store[len(level_store)-1]);
    if (temp.value == level_store[len(level_store)-1]): # found the last element in the tree
        head.value,temp.value = swap(level_store, head.value, temp.value);
        
        if (temp.parent.left == temp):
            temp.parent.left = None;
        elif (temp.parent.right == temp):
            temp.parent.right = None;
        #temp.left = None;
        #temp.right = None;
        #temp.sibling = None;
        
        last_element_value = temp.value;
        del(temp);
        
        return last_element_value;

    last_element_value = swap_root_last_return_max(head,temp.left,level_store);
    print(' last_element_value left: ',last_element_value);
    if (last_element_value != None): # last element found
        return last_element_value;
   
    last_element_value = swap_root_last_return_max(head,temp.right,level_store);
    print(' last_element_value right: ',last_element_value);
    if (last_element_value != None):
        return last_element_value;
   
def hs(data,level_store):
    # final sorted array
    sorted_store = [];
    
    # arrange in a array form
    # data is already an array
    #data_arr = np.array(data);
    head = add_nodes(data,level_store);
    print('before creating max heap');
    print_tree(level_store);
    #print_tree_addresses(head);
    
    # create a max heap
    
    while(len(level_store) > 1):
        max_heap(head, level_store);
        print('after creating max heap');
        print_tree(level_store);
   
        # swap the root with the last element
        # do this both in the tree as well as in level_store
        temp = head;
        last_value = swap_root_last_return_max(head,temp,level_store);
   
        #level_store[0],level_store[len(level_store)-1] = swap(level_store,level_store[0],level_store[len(level_store)-1]);
        # tree after swapping root with the last element
        #print('replaced the root with the last element. Modified tree:');
        #print_tree(level_store);
    
        # store the last element in the sorted list and remove it from the end of the list
        sorted_store.insert(0,last_value);
        level_store.remove(level_store[len(level_store)-1]); 
        print('level_store: ',level_store, ' sorted_store: ',sorted_store);
    
    sorted_store.insert(0,level_store[0]);
    print('level_store: ',level_store, ' sorted_store: ',sorted_store);
    
def print_tree(level_store):
    print('values:');
    for i in np.arange(0,len(level_store)):
        print(level_store[i]);

def print_tree_addresses(temp):
    #print('addresses:');
    
    if (temp!=None):
        print('root:',temp);
        print('left:',temp.left);
        print('right:',temp.right);
    else:
        return;
    print_tree_addresses(temp.left);
    print_tree_addresses(temp.right);
        
def parse_input(data, data_input):
    temp = list(map(int,data_input.split(' ')));
    for i in temp:
        data.append(i);

if __name__ == '__main__':
    print('enter the numbers to be sorted: ');
    data = [];
    level_store = []; # values stored by level (BFS)
    inputstr = input();
    parse_input(data,inputstr);
    print('after parse_input. data: ',data);
    hs(data,level_store);