# Given a square grid, find the minimum number of steps required for a robot to reach the obstacle inside the grid. Each flat section which can be 
# traversed, is marked with a '0', and each trench which can not be traversed, is marked with a '1'. The obstacle is marked with a '9'. If the robot
# encounters a trench, it has to look for a different direction which has a flat section. 
# The robot can move a step either left, right, up or down.
# It has to start navigating from the top-left corner (0,0), and has to reach the obstacle once it gets inside the grid, and can not get out of the grid.
# Given a grid, find the minimum number of steps required to reach the obstacle.

# A square grid may be further tilted by 45 deg clockwise, so that the starting position is at the he and the rest of the nodes resemble a tree
# like a bird's nest, slowly widening, being widest at the diagonal, and then narrowing down slowly, till it reaches the diagonally opposite node 
# of the starting node.


import numpy as np

class node:
    def __init__(self,data):
        self.value = data;
        self.left = None;
        self.right = None;
        self.leftp = None; # left parent
        self.rightp = None; # right parent
        # self.sibling = None; # for BFS
    def __del__(self):
        self.value = None;
        self.leftp = None;
        self.rightp = None;
        self.left = None;
        self.right = None;
        
class obstacle_node:
    def __init__(self,data):
        self.value = data;
        self.left = None;
        self.right = None;
        self.leftp = None; # left parent
        self.rightp = None; # right parent
        self.min_steps = 99999999; # minimum steps required to reach this node
        # self.sibling = None; # for BFS
    def __del__(self):
        self.value = None;
        self.leftp = None;
        self.rightp = None;
        self.left = None;
        self.right = None;
        print('min_steps: ',self.min_steps);
        self.min_steps = 99999999;

# Save the grid as a tree for traversal
def convert_grid_to_tree(grid,numRows,numCols):
   obstacle = 9;
   
   for i in np.arange(0,numRows):
        for j in np.arange(0,numCols):
            if (grid[i][j] == obstacle):
                g_node = obstacle_node(grid[i][j]);
            else:
                g_node = node(grid[i][j]);
            if ((i == 0) and (j == 0)):
                head = g_node;
                prev = g_node;
                first_node_prev = g_node;
            elif (j == 0): # first node in each (i > 0) level. Save first_node_prev as its required for 
                         # adding first node at each level.
                first_node_prev.left = g_node;
                g_node.rightp = first_node_prev;
                first_node_prev = g_node;
                prev = g_node;
            else: # j > 0
                prev.right = g_node;
                g_node.leftp = prev;
                prev = g_node;

   
   # Now interconnect the missing links, not covered above
   temp = head; 
   # For each row, iterate through all the columns and connect
   while (temp.left != None):
        row = temp.left;
        col = temp.right;
        local_row = row;
        local_col = col;
        while (local_col != None): # The lower tip / last node
            new_node = local_row.right;
            local_col.left = new_node;
            new_node.rightp = local_col;
            local_col = local_col.right;
            local_row = local_row.right;
        temp = temp.left;
   
   return head;     
   
# print the values in the grid by links   
def print_grid_by_links(head, grid):
   temp = head;
   row = temp;
   col = temp;

   while(row != None):
        print('node value: ',row.value);
        local_col = row.right;
        while (local_col != None):
            print('node value: ',local_col.value);
            local_col = local_col.right;
        row = row.left;

# i and j are the current x and y coordinates
def getsteps(grid, numRows, numCols):
    # mark starting position
    i = 0; 
    j = 0;
    steps = 0;
    while(True):
        if ((i+1 < numRows) and (grid[i+1][j] != 1)):
            i=i+1;
            steps += 1;
        elif ((i-1 > 0) and (grid[i-1][j] != 1)):
            i = i-1;
            steps += 1;
        elif ((j+1 < numCols) and (grid[i][j+1] != 1)):
            j = j+1;
            steps += 1;
        elif ((j-1 > 0) and (grid[i][j-1] != 1)):
            j = j-1;
            steps += 1;
        
        if (grid[i][j] == 9):
            break;
        
    return steps;
    
def print_grid(grid,coords):
   #shape = np.shape(grid);
   
   #shape = list(map(int,shape));
   #print(shape[0],shape[1]);
   #print('grid: ');
   print('print_grid: coords: ',coords[0],coords[1]);
   print('grid: ',grid);
   for i in np.arange(0,coords[0]):
        row = [];
        rowstr = '';
        for j in np.arange(0,coords[1]):
            #row.append(' ');
            row.append(grid[i][j]);
            #print(' ',grid[i][j]);            
        rowstr = (' ').join(str(row).split(','));
        print(rowstr);
        #print(str(row));

# Count the number of steps needed to reach the obstacle, traversing through the tree
def traverse_grid(head):
    temp = head;
    obstacle = 9;
    trench = 1;
    flat = 0;
    
    while (temp.value != obstacle):
        #prev = temp;
        if ((temp.right != None) and (temp.right.value != trench)):
            temp = temp.right;
            steps += 1;
            continue;
        elif ((temp.left != None) and (temp.left.value != trench)):
            temp = temp.left;
            steps += 1;
            continue;
        elif ((temp.leftp != None) and (temp.leftp.value != trench)):
            temp = temp.leftp;
            steps += 1;
            continue;
        elif ((temp.rightp != None) and (temp.rightp.value != trench)):
            temp = temp.rightp;
            steps += 1;
            continue;
        else:
            print('deadlock. Unable to move');
            return -1;

    return steps;

# which directions can the robot go next from current node?
def find_dir(temp,prev,path):
    right = False;
    left = False;
    leftp = False;
    rightp = False;
    
    trench = 1;
    flat = 0;
    obstacle = 9;
    
    print('temp: ',temp);
    if ((temp.right != None) and (temp.right.value != trench)):
            print('prev: ',prev);
            print('temp.right: ',temp.right);
            if (temp.right != prev): # The node where we want to go, isn't the one we came from.
                right = True;
                
                for i in np.arange(0,len(path)): # in the currently traversed path
                    if (temp.right == path[i]):      # if any of the nodes matches temp.right, 
                        right = False;
                        break;             # do not allow the right direction to be followed.
                    
    if ((temp.left != None) and (temp.left.value != trench)):
            print('temp.left: ',temp.left);
            if (temp.left != prev):
                left = True;
                for i in np.arange(0,len(path)): # in the currently traversed path
                    if (temp.left == path[i]):      # if any of the nodes matches temp.left, 
                        left = False;
                        break;             # do not allow the right direction to be followed.

    if ((temp.leftp != None) and (temp.leftp.value != trench)):
            print('temp.leftp: ',temp.leftp);
            if (temp.leftp != prev):
                leftp = True;
                for i in np.arange(0,len(path)): # in the currently traversed path
                    if (temp.leftp == path[i]):      # if any of the nodes matches temp.leftp, 
                        leftp = False;
                        break;             # do not allow the right direction to be followed.

    if ((temp.rightp != None) and (temp.rightp.value != trench)):
            print('temp.rightp: ',temp.rightp);
            if (temp.rightp != prev):
                rightp = True;    
                for i in np.arange(0,len(path)): # in the currently traversed path
                    if (temp.rightp == path[i]):      # if any of the nodes matches temp.rightp, 
                        rightp = False;
                        break;             # do not allow the right direction to be followed.
    
    return [right,left,rightp,leftp];
    
def traverse_grid2(temp,head,prev,steps,path):
    #temp = head;
    obstacle = 9;
    
    print('temp.value: ',temp.value);
    if (temp.value == obstacle):
        print('took ', steps, ' to reach the obstacle.');
        if (steps < temp.min_steps): # Reset the min_steps and save it in the obstacle_node.min_steps
            temp.min_steps = steps;
        return;
    # intuition: At each point, find how many paths are available (minus the path from the previous point). If there is more than one path,
    # create as many branches as there are paths and keep doing so, iteratively till obstacle is reached. Complete reaching the obstacle for 
    # all the divergent paths (inclusive). Then get the shortest path.
    
    # Save the minimum steps value as a member of the 'special' obstacle node.
    
    if (temp == head):
        [right,left,rightp,leftp] = find_dir(temp,None,path); # no prev node for head
        print('at head. directions: right: ',right,' left: ',left, 'rightp: ',rightp, 'leftp: ',leftp);
        prev = temp;
        #return;
    else:
        [right,left,rightp,leftp] = find_dir(temp,prev,path);
        print('directions: right: ',right,' left: ',left, 'rightp: ',rightp, 'leftp: ',leftp);
        prev = temp;
        #return;
        
    stepadded = False; # add the step count only once at each level`
    if (right == True):
        steps += 1;
        stepadded = True;
        path.append(temp);
        print('stepped right. steps: ',steps);
        #temp = temp.right; # Do not change temp since the node will be required when we check the other cases.
        traverse_grid2(temp.right,head,prev,steps,path);
    if (left == True): # if we already added a step as part of the 'right' path, then, retain that step
                   # for the 'left' path as well.
        if (stepadded == False):
            steps += 1;
            stepadded = True;
            path.append(temp);
        print('stepped left. steps: ',steps);
        #temp = temp.left;
        traverse_grid2(temp.left,head,prev,steps,path);
    if (rightp == True):
        if (stepadded == False):
           steps += 1;
           stepadded = True;
           path.append(temp);
        print('stepped rightp. steps: ',steps);
        #temp = temp.rightp;
        traverse_grid2(temp.rightp,head,prev,steps,path);
    if (leftp == True):
        if (stepadded == False):
            steps += 1;
            stepadded = True;
            path.append(temp);
        print('stepped leftp. steps: ',steps);
        #temp = temp.leftp;
        traverse_grid2(temp.leftp,head,prev,steps,path);
        
def traverse_grid_bfs(head):    
   return None;

def get_grid_input(grid,coords):
    for i in np.arange(0,int(coords[0])):
        temprow = [];
        for j in np.arange(0,int(coords[1])):
            print('enter either 0 or 1 or 9 for position: (',i,j,'): ');
            #temprow.append((list(map(int,input())))[0])
            value = input();
            #lval = list(map(int,value)); # useful only if there are multiple values entered at one go.
            lval = int(value);
            temprow.append(lval);
            print('temprow: ',temprow);
        grid.append(temprow);
        
if __name__ == '__main__':
    #grid = [[]];
    grid = [];
    print('enter the number of rows and columns of the grid (space separated), e.g. 2 3');
    coords = list(map(int,input().split(' ')));
    print('coords: ',coords);
    
    get_grid_input(grid,coords);
    
    #grid = [[0,1,1],[0,0,1],[1,9,0]];     # test
    #grid = [[0,0,0],[0,1,0],[0,9,0]];     # test
    #grid = [[0,0],[1,9]]; # test
    #grid = [[0,0,0],[0,0,1],[9,0,1]]; # test for looping paths.
    
    print_grid(grid,coords);
    #print('calling getsteps');
    #print('Robot took ',getsteps(grid,coords[0],coords[1]), ' steps to reach obstacle.');
    
    head = convert_grid_to_tree(grid,coords[0],coords[1]);
    print_grid_by_links(head,grid);
    
    print('obstacle node from head: ', head.right.right.left.left.leftp.value);
    print('obstacle node path 2 from head: ', head.left.left.right.value);
    #exit(-1);
    
    temp = head;
    path = [];
    traverse_grid2(temp,head,None,0,path);
    