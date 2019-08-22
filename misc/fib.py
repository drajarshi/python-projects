# Generate a fibonacci sequence
import numpy as np

# generate a fibonacci sequence upto the limit value mentioned
def gen_fib(limit):
   count = 0;
   sum = 0;
   series = [];
   
   series.append(0);
   series.append(1);
   
   while (sum < int(limit)+1):
        sum = series[len(series)-1] + series[len(series)-2];
        series.append(sum);
        
   print(series);

if __name__ == "__main__":
    print("input an upper (number) limit to generate the fibonacci sequence.");
    limit = input();
    gen_fib(limit);
    