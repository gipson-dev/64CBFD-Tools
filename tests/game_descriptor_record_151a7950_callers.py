"""Bounded original call-site windows, including delay slots and result branch."""
import itertools,json,struct
from tools.experiments import game_descriptor_record_151a7950_match as p
from tools.tests import game_descriptor_record_151a7950_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes()
 variants=g.programs()
 class Caller(g.Oracle):
     def record_call(self,t):
         if t==p.ENTRY: self.target_arguments=tuple(self.arguments(4))
         else: super().record_call(t)

 counts=[0,0]
 for kind,alloc,mode,mutation in itertools.product((0,1),(0,1),(0,255),(0,1,2)):
     # The second caller's original preparation writes the element count 9.
     c=g.Case(alloc,2 if kind==0 else 9,mutation,mode,0,counts[kind]%3,
              bytes=0x10 if kind==0 else 0x68, data=g.STACK+(0x7c if kind==0 else 0x4c))
     start=0x150ef260 if kind==0 else 0x151a87bc
     ends=(0x150ef274,) if kind==0 else (0x151a87cc,0x151a87e4)
     size=5 if kind==0 else 4
     window=struct.unpack_from('>'+str(size)+'I',rom,start-0x15000000+0x2d4b0)
     machines=[]
     for ws in variants:
         m=Caller(window,c)
         m.code=dict(zip(range(start,start+4*size,4),window))
         m.code.update(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws))
         for end in ends: m.code[end]=0
         m.code=WindowCode(m.code,m); m.code.ends=ends; m.entry=start
         if kind==0:
             m.r[17]=c.data; m.r[19]=mode; m.r[20]=c.parameter
         else:
             m.r[4:8]=[c.data,c.bytes-0x28,mode,c.parameter]
         m.initial=dict(m.memory)
         try: m.run()
         except WindowBoundary: pass
         else: raise AssertionError('caller did not reach a bounded window exit')
         want,calls,value=g.reference(c,m.initial)
         assert g.public(m.memory)==g.public(want),(kind,c,'memory')
         assert m.calls==calls,(kind,c,m.calls,calls)
         assert m.target_arguments==(c.data,c.bytes,mode,c.parameter),(kind,c,m.target_arguments)
         if kind==0: assert m.r[2]==value and ends[0] in m.visits
         else: assert m.r[3]==value and (ends[0] in m.visits,ends[1] in m.visits)==(bool(value),not value)
         machines.append(m)
     a,b,d=machines
     assert (a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(kind,c,'normalized state')
     counts[kind]+=1
 result=dict(first_call_cases=counts[0],second_call_cases=counts[1],executions=3*sum(counts),original_call_sites=['0x150EF26C','0x151A87BC'],delay_slots_and_result_branch=True,full_parent_functions_not_qualified=True,helpers_modeled=True,source_installed=False)
 (p.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
