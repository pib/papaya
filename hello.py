print 'hello'

def hello2():
	print 'hello', 2

def hello():
	print 'hello'
	hello2()
	
hello()