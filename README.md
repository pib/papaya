# Papaya: a Python Assember/Disassembler

To use, do the usual "python setup.py install", and then, once
installed, you should be able to run pyasm and pydis to assemble and
disassemble, respectively.

See the top of ppya.py for some information on how to write code in
Papaya assembly. See fib.pya and test.pya for simple examples.

For a bit more information on Python bytecodes, see the documentation
for the [python dis module][dis], and my [first blog post about
Papaya][papaya].

[dis]: http://docs.python.org/library/dis.html
[papaya]: http://probablyprogramming.com/2008/04/18/ppya-python-assembler

## Note:

This code has been basically untouched for 4 years, aside from a
little fix a year ago to make it work with new bytecodes in Python
2.7. It would likely need some TLC to be brought to a state usable for
anything serious.