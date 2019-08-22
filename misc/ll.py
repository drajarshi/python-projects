# Create a linked list for a given set of input numbers
import os
import numpy as np

NULL = 0x0;

class node:
    value = "nothing";
    def print_value(self):
        print(self.value);
    next = NULL;

def parse_input(data_list,data):
    temp = list(map(int, data.split(' ')));
    for i in np.arange(0,len(temp)):
        data_list.append(temp[i]);

def add_nodes_addr(node_addrs, data):
   for i in np.arange(0,len(data)):
        node_name = node();
        node_name.value = data[i];
        node_addrs.append(node_name);

def add_node(head,value):
   #node_name = 'node' + str(i);
   node_name = node();
   print('node_name:',node_name);
   node_name.value = value;    
   print('node value:',node_name.value);
   print('node next:',node_name.next);
   
   if (head == NULL):
        head = node_name;
        print('set head for first node.:',head);
   else:
      temp = head;
      node_name.next = temp;
      head = node_name;
      print('set head for additional node with value: ',value);
      
def delete_node_addrs(node_addrs, value):
   print('node_addrs length before deletion: ',len(node_addrs));
   for i in np.arange(0,len(node_addrs)):
        if (node_addrs[i].value == value):
            node_addrs.remove(node_addrs[i]); # remove specific element in list.
            break;

def delete_node(head,value):
   if (head == NULL):
      print('empty linked list...');
      return;
   else:
      temp = head;
      if (temp.value == value):
        print('matching node found');
        if (temp.next == NULL): # only one node
            temp = NULL;
            head = temp;
            return;
        else: # more than one node
            head = temp.next;
            temp = NULL;
            return;
      
      # match at one of the following nodes
      while (temp != NULL):
            prev = temp; # save the current node before going to the next
            temp = temp.next;
      
            if (value == temp.value):
                print('matching node found');
                prev.next = temp.next;
                temp = NULL;

def display_nodes(head):
   temp = head;
   count = 0;
   
   while(temp != NULL):
        count = count + 1;
        print('node at position: ',count,' is: ',temp.value);
        temp = temp.next;

def display_nodes_addr(node_addrs):
    for i in np.arange(0,len(node_addrs)):
        print('value in node ',i,': ',node_addrs[i].value);
        
if __name__ == '__main__':
    print('enter a set of numbers to create a linked list with: ');
    data = input();
    data_list = []
    parse_input(data_list,data);
    
    head = NULL;
    node_addrs = [];
    print('after parse_input. data_list ',data_list);
    #for i in np.arange(0,len(data_list)):
    #     add_node(head, data_list[i]);
    add_nodes_addr(node_addrs,data_list);
    head = node_addrs[0];
    
    #display_nodes(head);
    display_nodes_addr(node_addrs);
    
    print('enter element to delete');
    del_element = input();
    delete_node_addrs(node_addrs,int(del_element));
    
    print('list after deletion');
    display_nodes_addr(node_addrs);
    
    
    
    
            
                       
    