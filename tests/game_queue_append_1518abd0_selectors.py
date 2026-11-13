from tools.tests import game_queue_append_1518abd0_oracle as o

def run():
 rom=(o.root/'conker/conker.us.bin').read_bytes();retail=o.struct.unpack_from('>82I',rom,0x1b8080);programs=[retail,o.program(o.out/'after.o'),o.program(o.out/'generated.o'),o.program(o.out/'generic.o')];count=0
 for selector in range(256):
  for branch in range(3):
   c=o.Case((selector&1)*8,0 if branch==0 else 1,0 if branch==1 else 1,0xabcd0000|selector,1,0,1,selector)
   expected,calls,result=o.reference(c);want=(o.public(expected,c),calls,result)
   for w in programs:
    m=o.Machine(w,c).run();assert (o.public(m.memory,c),m.calls,m.r[2])==want,(selector,branch)
   count+=1
 print('all 256 selector bytes over',count,'null/allocation/eviction cases; synthetic callback table')
