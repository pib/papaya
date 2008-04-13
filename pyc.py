#based on the code in the blog post here: http://nedbatchelder.com/blog/200804/the_structure_of_pyc_files.html

import dis, marshal, struct, sys, time, types

def read_file(fname):
    f = open(fname, "rb")
    magic = f.read(4)
    moddate = f.read(4)
    modtime = time.asctime(time.localtime(struct.unpack('L', moddate)[0]))
    code = marshal.load(f)
    f.close()
    return magic, moddate, modtime, code
    
def show_file(fname):
    magic, moddate, modtime, code = read_file(fname)
    print "magic %s" % (magic.encode('hex'))
    print "moddate %s (%s)" % (moddate.encode('hex'), modtime)
    show_code(code)
    
def show_code(code, indent='', i=None):
    if i: i = "%d: " % i
    else: i = ''
    print "%s%scode" % (indent, i)
    indent += '   '
    print "%sargcount %d" % (indent, code.co_argcount)
    print "%snlocals %d" % (indent, code.co_nlocals)
    print "%sstacksize %d" % (indent, code.co_stacksize)
    print "%sflags %04x" % (indent, code.co_flags)
    show_hex("code", code.co_code, indent=indent)
    dis.disassemble(code)
    print "%sconsts" % indent
    for i, const in zip(range(len(code.co_consts)),code.co_consts):
        if type(const) == types.CodeType:
            show_code(const, indent+'   ', i)
        else:
            print "   %s%d: %r" % (indent, i, const)
    print "%snames" % indent
    for i, name in zip(range(len(code.co_names)), code.co_names):
	    print "   %s%d: %r" % (indent, i, name)
    print "%svarnames %r" % (indent, code.co_varnames)
    print "%sfreevars %r" % (indent, code.co_freevars)
    print "%scellvars %r" % (indent, code.co_cellvars)
    print "%sfilename %r" % (indent, code.co_filename)
    print "%sname %r" % (indent, code.co_name)
    print "%sfirstlineno %d" % (indent, code.co_firstlineno)
    show_hex("lnotab", code.co_lnotab, indent=indent)
    
def show_hex(label, h, indent):
    h = h.encode('hex')
    if len(h) < 60:
        print "%s%s %s" % (indent, label, h)
    else:
        print "%s%s" % (indent, label)
        for i in range(0, len(h), 60):
            print "%s   %s" % (indent, h[i:i+60])

show_file(sys.argv[1])