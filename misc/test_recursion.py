# test recursion

def compare(i,max):
   print('i:',i,'max:',max);
   if ((i > 0) and (i < max)):
        print(i,' is less than ',max);
        compare(i-1,max);
      
		

if __name__ == '__main__':
	print('enter a number');
	i = input();
	print('enter the max to compare against');
	max = input();
	compare(int(i),int(max));