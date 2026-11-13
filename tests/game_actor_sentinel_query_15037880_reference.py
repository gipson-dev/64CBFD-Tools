from tools.tests.game_actor_sentinel_query_15037880_oracle import *

def run():
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>87I',rom,0x64d30);programs=[retail,program(out/'after.o'),program(out/'generated.o'),program(out/'generic.o')];count=0
 for phase,index,mode,kind,ref,threshold,alias in itertools.product((0,8),(-1,0,1),range(8),(0,4,255),range(4),range(5),range(6)):
  c=Case(phase,index,mode,kind,ref,threshold,alias);want,result=reference(c)
  for w in programs:
   m=Machine(w,c).run();assert (m.memory,m.r[2])==(want,result),(c,m.r[2],result)
  count+=1
 print('independent query model',count,'cases across four streams including output aliases and quiet NaN threshold')
