import opcode
import new

class Label(str):
	def __repr__(self):
		return self+':'
class Opcode:
	def __init__(self, code, param=0):
		self.code = opcode.opmap[code]
		if self.code in opcode.hasconst
		self.param = param
	def __repr__(self):
		return "%s(%d) %d" % (opcode.opname[self.code], self.code, self.param)

def parse(filename):
	f = file(filename)
	for line in f:
		line = line.rstrip()
		if line.endswith(':'):
			yield Label(line[:-1])
		else:
			line = line.strip()
			if ' ' in line:
				code, param = line.split(' ', 1)
			else:
				code = line
				param = None
			yield Opcode(code, int(param))
				

class Assembler:
	def assemble(self, input):
		for line in input:
			print line
			
if __name__ == '__main__':
	parser = parse('test.pya')
	asm = Assembler()
	code = asm.assemble(parser)