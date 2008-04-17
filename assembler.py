"""
Python Assembler/Disassembler Copyright 2008 Paul Bonser <paul@paulbonser.com>

Pass a .pya or .pyc filename in as a parameter. If you pass a .pya file, it will be assembled 
into the matching .pyc file. If you pass in a .pyc file, it will be disassembled into a .pyd 
file (to avoid overwriting an already existing .pya).

Support for jumping to labels and variable argument lists is not yet in place, but it will be 
soon. You could also use this code as the backend for a compiler, but it's not really very well 
suited for that yet, and quite messy since this was a quick prototype. I plan on cleaning it up,
and/or rewriting it, really! Right now, it's about impossible to do anything useful with loops
or jumps so you probably shouldn't try, unless you are insane.

The syntax consists of a Python opcode name (LOAD_CONST, CALL_FUNCTION, etc) optionally followed
by a parameter (if that opcode takes a parameter). In cases where the opcode takes an index to
a value in one of the code object's tuples (co_consts, co_varnames, etc.), give the literal 
value or name and the assembler will automatically build the corresponding tuples for you.

To load a function with a LOAD_CONST opcode, put "function", followed by a comma-separated list
of parameter names (so they can be added to the co_varnames tuple), and on the following lines
put the content of the function as with the other lines (probably indented for easier reading).
After the final line of the function put the word 'end' on a single line by itself.


    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import opcode
import new
from types import CodeType
from py_compile import MAGIC
import time
import struct
import marshal

cmp_map = dict(zip(opcode.cmp_op, range(len(opcode.cmp_op))))

class BlankLine: 
	def __init__(self, line):
		self.linenumber = line
class Label:
	def __init__(self, label, line):
		self.label = label
		self.linenumber = line
	def __str__(self):
		return self.label
class End:
	def __init__(self, line):
		self.linenumber = line
	def __repr__(self):
		return 'end'
class RawStr(str):
	def __repr__(self):
		return self
		
class Opcode:
	def __init__(self, op, param=None, label='', indent=''):
		self.indent = indent
		self.label = label
		if isinstance(op, str):
			self.opname = op
			if op == 'stack':
				self.opcode = -1
			else:
				self.opcode = opcode.opmap[op]
		else:
			self.opcode = op
			self.opname = opcode.opname[op]
		self.param = param
		self.linenumber = None
	def __repr__(self):
		rep = ''
		if self.label:
			rep = "%s:\n" % self.label
		if self.opcode >= opcode.HAVE_ARGUMENT:
			rep += "%s%s %s" % (self.indent, self.opname, self.param)
		else:
			rep += "%s%s" % (self.indent, self.opname)
		return rep
	
def parse(filename):
	f = file(filename)
	linenumber = 0
	for line in f:
		linenumber += 1
		line = line.strip()
		
		if line == '' or line.startswith('#'):
			yield BlankLine(linenumber)
			continue
		elif line == 'end':
			yield End(linenumber)
			continue
		elif line.endswith(':'):
			yield Label(line[:-1], linenumber)
			continue
		elif ' ' in line:
			code, param = line.split(' ', 1)
		else:
			code = line
			param = None
		op = Opcode(code, param)
		op.linenumber = linenumber
		yield op

class AsmCollection(dict):
	def __init__(self):
		dict.__init__(self)
		self.items = []
	def __missing__(self, item):
		arg = self[item] = len(self.items)
		self.items.append(item)
		return arg
	def add(self, list):
		for val in list:
			self[val]

class Pya:
	def __init__(self, filename='<none>'):
		self.const = AsmCollection()
		self.free = AsmCollection()
		self.name = AsmCollection()
		self.varname = AsmCollection()
		self.filename = filename
		self.linenumber = 1
	def printcode(self, code):
		for c in code:
			print "0x%02x" % ord(c),
			print
		
	def asm(self, input, args=None):
		self.input = input # store in case we need to use this internally

		firstline = 0
		
		if args:
			self.varname.add(args)
			func = True
		else:
			args = []
			func = False
		
		labelmap = {}
		jrelmap = {}
		jabsmap = {}
		#import pdb
		#pdb.set_trace()
		stacksize = 0
		codestring = []
		lnotab = ''
		lastline = 0
		lastbyte = 0
		while True:
			try:
				op = input.next()
			except StopIteration:
				break
			if isinstance(op, End):
				break
		
			if isinstance(op, BlankLine):
				continue
		
			if isinstance(op, Label):
				op_str = str(op)
				labelmap[op_str] = label = len(codestring)
				if op_str in jabsmap:
					for jump in jabsmap[op_str]:
						extarg, arg = self.encode_param(label)
						codestring[jump+1:jump+3] = arg
				if op_str in jrelmap:
					for jump in jrelmap[op_str]:
						rel = label - (jump+3)
						extarg, arg = self.encode_param(rel)
						codestring[jump+1:jump+3] = arg
				continue
			
			# not a real opcode, just used to set the max stack size
			if op.opname == 'stack':
				stacksize = int(op.param)
				continue
			
			if op.opcode in opcode.hasjabs:
				if op.param in labelmap:
					op.param = labelmap[op.param]
				else:
					jumps = jabsmap.setdefault(op.param, list())
					jumps.append(len(codestring))
			elif op.opcode in opcode.hasjrel:
				jumps = jrelmap.setdefault(op.param, list())
				jumps.append(len(codestring))
			
			code = self.encode_op(op)
			codestring += code
			
			if not firstline:
				firstline = op.linenumber
				lastline = firstline
				lastbyte = len(code)
			else:
				lnotab += chr(lastbyte) + chr(op.linenumber-lastline)
				lastbyte = len(code)
				lastline = op.linenumber
		codestring = ''.join(codestring)
		if func:
			name = '<func>'
		else:
			name = '<module>'
		co = new.code(
			len(args), # argcount
			len(self.varname.items), # nlocals
			stacksize, # stacksize
			0, # flags
			codestring, # codestring
			tuple(self.const.items), #constants
			tuple(self.name.items), # names
			tuple(self.varname.items), #varnames
			self.filename, #filename
			name, # name
			firstline, # first line number
			lnotab, # lnotab
			)
		return co

	def dis(self, co, func=False, indent='    '):
		out = []
		if func:
			out = [RawStr("function %s\n" % ', '.join(co.co_varnames[:co.co_argcount]))]
		
		out.append(RawStr("%sstack %d" % (indent, co.co_stacksize)))
		
		i = 0
		code = co.co_code
		length = len(code)
		bytemap = {}
		jumpmap = {}
		labels = 0
		while i < length:
			op = ord(code[i])
			if op >= opcode.HAVE_ARGUMENT:
				arg = ord(code[i+1]) + (ord(code[i+2]) << 8)
			else:
				arg = None
			opc = self.decode_op(co, op, arg, indent)
			
			if opc.opcode in opcode.hasjabs:
				jumpmap[arg] = opc
			elif opc.opcode in opcode.hasjrel:
				jumpmap[i+3+arg] = opc
			
			bytemap[i] = opc
			out.append(opc)
			if op >= opcode.HAVE_ARGUMENT:
				i += 3
			else:
				i += 1
		if func:
			out.append(End())
		
		jumps = jumpmap.items()
		jumps.sort()
		for jump, opc in jumps:
			labelname = "label%d" % labels
			opc.param = labelname
			bytemap[jump].label = labelname
			labels += 1
		return "\n".join([repr(i) for i in out])

						
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
				if argument.startswith('function'):
					if ' ' in argument:
						_, params = argument.split(' ', 1)
						params = [param.strip() for param in params.split(',')]
					else:
						params = []
					# recursively build a new code object to go into the consts
					asm = Pya(self.filename)
					fn = asm.asm(self.input, params, self.linenumber+1)
					self.linenumber += asm.linenumber - self.linenumber
					arg = self.const[fn]
				else:
					arg = self.const[eval(argument)]
			elif op in opcode.hasfree:
				arg = self.free[argument]
			elif op in opcode.hasjabs:
				if isinstance(argument, str):
					argument = 0
				arg = int(argument)
			elif op in opcode.hasjrel:
				if isinstance(argument, str):
					argument = 0
				arg = int(argument)
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
		
	def decode_op(self, co, op, argument, indent):
		if op >= opcode.HAVE_ARGUMENT:
			if op in opcode.hascompare:
				arg = cmp_op[argument]
			elif op in opcode.hasconst:
				arg = co.co_consts[argument]
				if arg.__class__ == CodeType:
					arg = self.dis(arg, True, indent + '    ')
				else:
					arg = repr(arg)
			elif op in opcode.hasfree:
				arg = co.co_freevars[argument]
			elif op in opcode.hasjabs:
				arg = argument
			elif op in opcode.hasjrel:
				arg = argument
			elif op in opcode.haslocal:
				arg = co.co_varnames[argument]
			elif op in opcode.hasname:
				arg = co.co_names[argument]
			else:
				arg = argument
		else:
			arg = argument
		return Opcode(op, arg, '', indent)

def read_pyc(fname):
	f = open(fname, "rb")
	magic = f.read(4)
	if magic != MAGIC:
		raise Exception('Magic number mismatch. This .pyc is from a different version of Python')
	moddate = f.read(4)
	modtime = time.asctime(time.localtime(struct.unpack('L', moddate)[0]))
	code = marshal.load(f)
	f.close()
	return magic, moddate, modtime, code

def write_pyc(fname, code):
	f = open(fname, 'wb')
	f.write(MAGIC)
	f.write(struct.pack('L', int(time.time())))
	marshal.dump(code, f)
	f.close()

if __name__ == '__main__':
	import sys

	if len(sys.argv) < 2:
		print "Usage %s file.[pya|pyc]\n" % sys.argv[0]
		exit(1)
	asm = Pya(sys.argv[1])
	base, ext = sys.argv[1].split('.')
	if ext == 'pya':
		parser = parse(sys.argv[1])
		code = asm.asm(parser)
		write_pyc(base+'.pyc', code)
	elif ext == 'pyc':
		magic, moddate, modtime, code = read_pyc(sys.argv[1])
		out = asm.dis(code)
		f = open(base+'.pyd', 'w')
		f.write(out)
		f.close()
	else:
		print ".pya or .pyc files only, please!"
		