"""
Paul's Python Assembler/Disassembler Copyright 2008 Paul Bonser <paul@paulbonser.com>

Pass a .pya or .pyc filename in as a parameter. If you pass a .pya file, it will be assembled  into
the matching .pyc file. If you pass in a .pyc file, it will be disassembled into a .pyd  file (to
avoid overwriting an already existing .pya).

For a good example of how to write a .pya file from scratch, write some code in a .py file, compile
it, and then decompile it to see what code is generated.

The syntax consists of a Python opcode name (LOAD_CONST, CALL_FUNCTION, etc) optionally followed by
a parameter (if that opcode takes a parameter). In cases where the opcode takes an index to a value
in one of the code object's tuples (co_consts, co_varnames, etc.), give the literal  value or name
and the assembler will automatically build the corresponding tuples for you.

When using a JUMP_* instruction, use a label, and then at the location where you want to jump
(immediately before the instruction to jump to, on its own line), put the label, followed by a colon.

To load a function with a LOAD_CONST opcode, put "def funcname(...)", following the function
definition for Python, minus the ending colon, and on the following lines put the content of the
function as with the other lines (probably indented for easier reading). After the final line of the
function put the word 'end' on a single line by itself.

"""

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
import new
from types import CodeType
from py_compile import MAGIC
import time
import struct
import marshal
import peak.util.assembler as asm

hasint = (asm.UNPACK_SEQUENCE, asm.DUP_TOPX, asm.BUILD_TUPLE, asm.BUILD_LIST, asm.RAISE_VARARGS, 
          asm.MAKE_FUNCTION, asm.BUILD_SLICE)

class Label:
    def __init__(self, label, line=0):
        self.label = label
        self.linenumber = line
    def __str__(self):
        return self.label

class End:
    def __init__(self, line=0, indent=0):
        self.linenumber = line
        self.indent = indent
    def __repr__(self):
        return '%send' % ('    ' * (self.indent-1))
        
class Opcode:
    def __init__(self, op, arg='', label='', indent=0):
        self.indent = indent
        self.label = label
        if isinstance(op, str):
            self.name = op
            self.opcode = asm.opmap[op]
        else:
            self.opcode = op
            self.name = asm.opname[op]
        self.arg = arg
        self.linenumber = None
    def __repr__(self):
        rep = ''
        if self.label:
            rep = "%s%s:\n" % (('    '*self.indent)[:-2], self.label)
        rep += "%s%s %s" % ('    '*self.indent, self.name, self.arg)
        return rep
    
def parse(filename):
    f = file(filename)
    linenumber = 0
    for line in f:
        linenumber += 1
        line = line.strip()
        
        if line == '' or line.startswith('#'):
            continue
        elif line == 'end':
            yield End(linenumber)
            continue
        elif line.endswith(':'):
            yield Label(line[:-1], linenumber)
            continue
        elif ' ' in line:
            code, arg = line.split(' ', 1)
        else:
            code = line
            arg = None
        try:
            op = Opcode(code, arg)
        except KeyError:
            print "ERROR: Undefined opcode '%s' at line %d\n" % (code, linenumber)
            raise
        op.linenumber = linenumber
        yield op

class PPya:
    def __init__(self, filename='<none>'):
        self.filename = filename
        
    def assemble(self, input, fn_def=None):
        if fn_def:
            code = asm.Code.from_function(fn_def)
        else:
            code = asm.Code()
            code.co_name = '<module>'
            code.co_flags &= ~asm.CO_NEWLOCALS # this seems to break modules
        code.co_filename = self.filename
        
        labelmap = {}
        jumpmap = {}
        last_closure_count = 0
        
        for op in input:
            if isinstance(op, End): break
        
            # fillin any forward references to this label, save this label's location
            if isinstance(op, Label):
                op_str = str(op)
                labelmap[op_str] = label = code.here()
                if op_str in jumpmap:
                    for jump in jumpmap[op_str]:
                        jump()
                continue
            
            code.set_lineno(op.linenumber)
            op_fn = getattr(code, op.name)
            arg = op.arg
            
            # handle jumping to labels or forward references
            if op.opcode in asm.hasjabs or op.opcode in asm.hasjrel:
                if op.name.startswith('SETUP'):
                    op_fn() # BytecodeAssembler takes care of these
                    continue
                elif arg in labelmap:
                    arg = labelmap[arg]
                else:
                    jumps = jumpmap.setdefault(arg, list())
                    jump = op_fn()
                    jumps.append(jump)
                    continue
            elif op.opcode in asm.hasconst:
                if arg.startswith('def'):
                    # create an empty function object with the signature
                    l = {}
                    try:
                        exec ('%s: pass' % arg) in {}, l
                    except SyntaxError:
                        print "Invalid function definition at line %d\n" % op.linenumber
                        raise
                    func_def = l.values()[0]
                    
                    # recursively build a new code object to go into the consts
                    pya = PPya(self.filename)
                    fn = pya.assemble(input, func_def)
                    arg = fn
                    last_closure_count = len(fn.co_freevars)
                else:
                    try:
                        arg = eval(arg)
                    except SyntaxError:
                        print "Syntax error trying to parse literal: '%s' at line %d\n" % (arg, op.linenumber)
                        raise
            elif op.name.startswith('CALL_FUNCTION'):
                if ',' in arg:
                    pos, kw = [int(s) for s in arg.split(',')]
                else:
                    pos = int(arg)
                    kw = 0
                op_fn(pos, kw)
                continue
            elif op.opcode == asm.MAKE_CLOSURE:
                arg = int(arg)
                op_fn(arg, last_closure_count)
            elif op.opcode in hasint:
                arg = int(arg)

            if op.opcode >= asm.HAVE_ARGUMENT:
                op_fn(arg)
            else:
                op_fn()
        
        return code.code()

    def disassemble(self, co, func=False, indent=1):
        out = []
        if func:
            argcount = co.co_argcount
            fndef = "def %s(%s" % (co.co_name, (', '.join(co.co_varnames[:argcount])))
            varargs = co.co_flags & asm.CO_VARARGS
            kwargs = co.co_flags & asm.CO_VARKEYWORDS
            if varargs:
                fndef += ', *%s' % co.co_varnames[argcount:argcount+1]
                argcount += 1
            if kwargs:
                fndef += ', **%s' % co.co_varnames[argcount:argcount+1]
            fndef += ')'
            out.append(fndef)
        
        i = 0
        code = co.co_code
        length = len(code)
        bytemap = {}
        jumpmap = {}
        labels = 0
        while i < length:
            op = ord(code[i])
            if op >= asm.HAVE_ARGUMENT:
                arg = ord(code[i+1]) + (ord(code[i+2]) << 8)
            else:
                arg = None
            opc = self.decode_op(co, op, arg, indent)
            
            if opc.opcode in asm.hasjabs and not opc.name.startswith('SETUP'):
                jumpmap[arg] = opc
            elif opc.opcode in asm.hasjrel and not opc.name.startswith('SETUP'):
                jumpmap[i+3+arg] = opc
            
            bytemap[i] = opc
            out.append(opc)
            if op >= asm.HAVE_ARGUMENT:
                i += 3
            else:
                i += 1
        if func:
            out.append(End(0,indent))
        
        jumps = jumpmap.items()
        jumps.sort()
        for jump, opc in jumps:
            labelname = "label%d" % labels
            opc.arg = labelname
            bytemap[jump].label = labelname
            labels += 1
        return "\n".join([str(i) for i in out])

    def decode_op(self, co, op, argument, indent):
        if op >= asm.HAVE_ARGUMENT:
            if op in asm.hascompare:
                arg = asm.cmp_op[argument]
            elif op in asm.hasconst:
                arg = co.co_consts[argument]
                if arg.__class__ == CodeType:
                    arg = self.disassemble(arg, True, indent + 1)
                else:
                    arg = repr(arg)
            elif op in asm.hasfree:
                arg = co.co_freevars[argument]
            elif op in asm.hasjabs:
                arg = argument
            elif op in asm.hasjrel:
                arg = argument
            elif op in asm.haslocal:
                arg = co.co_varnames[argument]
            elif op in asm.hasname:
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
    pya = PPya(sys.argv[1])
    base, ext = sys.argv[1].split('.')
    if ext == 'pya':
        parser = parse(sys.argv[1])
        code = pya.assemble(parser)
        write_pyc(base+'.pyc', code)
    elif ext == 'pyc':
        magic, moddate, modtime, code = read_pyc(sys.argv[1])
        out = pya.disassemble(code)
        f = open(base+'.pyd', 'w')
        f.write(out)
        f.close()
    else:
        print ".pya or .pyc files only, please!"
        