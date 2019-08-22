#2) Write a function that will return True if its string parameter has balanced parentheses, and returns False otherwise

# 10:13 - 10:18

def check_parens(inputstr):
    parens = 0;
    
    for c in inputstr:
        if (c == '('):
            parens += 1;
        elif (c == ')'):
            parens -= 1;
    
    if (parens == 0):
        return True;
    else:
        return False;

if __name__ == '__main__':
    print("input a string to check its parentheses");
    inputstr = input();
    
    print(check_parens(inputstr));