from tools.tests.game_queue_append_1518abd0_oracle import *

def run():
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>82I',rom,0x1b8080);raw=program(out/'after.o');padded=[program(out/'generated.o'),program(out/'generic.o')];count=0
 for phase,present,allocation,selector,num,limit,nonempty in itertools.product((0,8),(0,1),(0,1),(0,1,2,255,0x100,0x12345678),(0,1,0x7fffffff,0xffffffff),(-1,0,1,0x7fffffff),(0,1)):
  c=Case(phase,present,allocation,selector,num,limit,nonempty,1);expected,calls,result=reference(c);a=Machine(retail,c).run();b=Machine(raw,c).run();want=(public(expected,c),calls,result)
  assert (public(a.memory,c),a.calls,a.r[2])==want,(c,'retail',a.calls,calls,a.r[2],result)
  assert (public(b.memory,c),b.calls,b.r[2])==want,(c,'candidate',b.calls,calls,b.r[2],result)
  for ws in padded:
   v=Machine(ws,c).run();assert (public(v.memory,c),v.calls,v.r[2])==want,(c,'padded')
  count+=1
 print('independent queue model',count,'cases retail and candidate pass')
