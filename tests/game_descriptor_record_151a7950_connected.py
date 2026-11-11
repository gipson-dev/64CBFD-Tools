"""Execute original memcpy and bzero; the outer allocator remains modeled."""
import itertools,json,struct
from tools.experiments import game_descriptor_record_151a7950_match as p
from tools.tests import game_descriptor_record_151a7950_oracle as g

def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 helpers=((g.COPY,0x22ec0,11),(g.ZERO,0x226f0,39))
 code={}
 for addr,off,size in helpers:
     code.update(zip(range(addr,addr+4*size,4),struct.unpack_from('>'+str(size)+'I',rom,off)))
 variants=g.programs();visited=set();cases=0
 for alloc,count,mode,phase in itertools.product((0,1),(-1,0,1,2,3),(0,255),(0,8)):
     c=g.Case(alloc,count,0,mode,phase,cases%3)
     for ws in variants:
         m=g.Oracle(ws,c,connected=code);m.run()
         want,calls,value=g.reference(c,m.initial)
         assert g.public(m.memory)==g.public(want),(c,'memory')
         assert m.calls==calls,(c,m.calls,calls)
         assert m.r[2]==value,(c,m.r[2],value)
         visited.update(m.visits)
     cases+=1
 result=dict(cases=cases,executions=3*cases,original_helpers={hex(addr):sum(addr+4*i in visited for i in range(size)) for addr,off,size in helpers},allocator_modeled=True,helper_mutations_excluded=True,source_installed=False)
 (p.out/'connected.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
