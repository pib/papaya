import opcode
import new

cmp_map = dict(zip(opcode.cmp_op, range(len(opcode.cmp_op))))

class Label(str):
	def __repr__(self):
		return self+':'
class Arg:
	def __init__(self, name):
		if '=' in val:
			name, self.def_val = name.split('=')
			name = name.strip()
			self.def_val = self.def_val.strip()
		else:
			self.def_val = None
		self.name = name
		
class Opcode:
	def __init__(self, opname, param=None):
		self.opname = opname
		self.opcode = opcode.opmap[opname]
		self.param = param
	def __repr__(self):
		return "%s(%d) %s" % (self.opname, self.opcode, self.param)
	

def parse(filename):
	f = file(filename)
	for line in f:
		line = line.strip()
		
		if line.endswith(':'):
			yield Label(line[:-1])
			
		if ' ' in line:
			code, param = line.split(' ', 1)
		else:
			code = line
			param = None
		if code == 'arg':
			yield Arg(param)
		yield Opcode(code, param)

class AsmCollection(dict):
	def __init__(self):
		dict.__init__(self)
		self.items = []
	def __missing__(self, item):
		arg = self[item] = len(self.items)
		self.items.append(item)
		return arg

class Assembler:
	def __init__(self, filename='<none>'):
		self.const = AsmCollection()
		self.free = AsmCollection()
		self.name = AsmCollection()
		self.varname = AsmCollection()
		self.filename = filename
	def printcode(self, code):
		for c in code:
			print "0x%02x" % ord(c),
			print
	def asm(self, input):
		codestring = ''
		lnotab = ''
		for op in input:
			line_inc = 1
			code = self.encode_op(op)
			codestring += code
			lnotab += chr(len(code)) + chr(1)
		co = new.code(
			0, # argcount
			len(self.varname.items), # nlocals
			0, # stacksize
			0, # flags
			codestring, # codestring
			tuple(self.const.items), #constants
			tuple(self.name.items), # names
			tuple(self.varname.items), #varnames
			self.filename, #filename
			'test', # name
			1, # first line number
			lnotab, # lnotab
			)
		return co
			
						
	def encode_param(self, param):
		if param > 65535:
			ext_arg = self.encode_param(param >> 16)
			param = param & 65535
		else: 
			ext_arg = 0
		arg = chr(param & 255) + chr(param >> 8)
		return (ext_arg, arg)
		
	def encode_op(self, op_obj):
		argument = op_obj.param
		op = op_obj.opcode
		out = chr(op)
		if op >= opcode.HAVE_ARGUMENT:
			if op in opcode.hascompare:
				arg = cmp_map[argument]
			elif op in opcode.hasconst:
				arg = self.const[eval(argument)]
			elif op in opcode.hasfree:
				arg = self.free[argument]
			elif op in opcode.hasjabs:
				pass
			elif op in opcode.hasjrel:
				pass
			elif op in opcode.haslocal:
				arg = self.varname[argument]
			elif op in opcode.hasname:
				arg = self.name[argument]
			else:
				arg = int(argument)
				
			ext_arg, arg = self.encode_param(arg)
			if ext_arg:
				out = chr(opcode.EXTENDED_ARG) + ext_arg + out
			out += arg
		return out
			
#if __name__ == '__main__':
parser = parse('test.pya')
asm = Assembler()
code = asm.asm(parser)