# Implement a switch
# Ensure that once the dictionary's get method returns the function address, that function is explicitly called.
# Also, the function names mapped in the dict should be without the parentheses.

def option_one():
    print("in option one");
 
def option_two():
    print("in option two");
    
def option_def():
    print("in option def");

def option_to_fn(option):
    switch_option = {
    1: option_one,
    2: option_two
    };
    
    function = switch_option.get(int(option), option_def);
    function();
    
if __name__ == "__main__":
        print("provide an input integer value");
        option = input();
        
        option_to_fn(option);
        