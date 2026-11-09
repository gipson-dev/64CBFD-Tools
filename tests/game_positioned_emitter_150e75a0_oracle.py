"""Initialized descriptor bytes, full call ABI and preserved unwritten storage."""
import json,struct,sys
from pathlib import Path
from dataclasses import dataclass,replace
from tools.experiments.game_positioned_emitter_150e75a0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY=0x150E75A0;SUBMIT=0x1515548C;POSITION=0x50000;PAIR=0x51000
SYMS={'D_80088A64':0x80088A64,'func_1515548C':SUBMIT}
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 value:int=0xABCD8001
 other_size:int=0x76543210
 flag:int=0xAB
 scale:int=0x3F800000
 x:int=0x41480000
 y:int=0xC1C80000
 tag:int=0xA7
 pair:int=PAIR
 mode:int=0x87654321
 slot:int=0xCDEF80A5
 context:int=0xFEDCBA98
 result:int=0x80000000
 phase:int=0
 seed:int=0
 mutate:bool=False
def arguments(c):return(POSITION,c.scale,c.value,c.flag,c.value,c.value,c.value,c.other_size,c.pair,c.mode,c.slot,c.context)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
 for b,n in((POSITION,16),(PAIR,16)):m.update({b+i:(i*29+c.seed*11+0x59)&255 for i in range(n)})
 put(m,POSITION,c.x);put(m,POSITION+4,c.y);m[s['D_80088A64']]=c.tag
 return m
def descriptor(c):
 result={}
 def field(at,v,n=1):
  temp={};put(temp,at,v,n);result.update(temp)
 for at,v in((0,c.x),(4,c.y),(8,c.scale),(12,c.scale)):field(at,v,4)
 field(16,c.tag);field(18,c.value,2);field(20,(c.flag&255)|0x40,2);field(22,c.value,2);field(24,c.other_size,2)
 for at,v in((26,4),(27,255),(28,230),(29,190),(30,c.value),(31,255),(32,255),(33,255),(34,255),(35,c.value),(64,0),(65,10)):field(at,v)
 for at,v in((36,1),(40,0),(44,0),(48,7),(52,60),(56,128),(60,32)):field(at,v,4)
 assert len(result)==65 and set(result)==set(range(66))-{17}
 return result
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS):
  super().__init__(words,memory,c,entry=entry,s=s,arguments=arguments(c));self.before=self.r[:];self.before_f=self.f[:];self.initial=dict(self.memory);self.packet=None;self.unwritten=None
 def record_call(self,t):
  assert t==self.syms['func_1515548C'];a=tuple(map(u32,self.arguments(7)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  p=a[0];self.packet={i:self.memory[p+i]for i in descriptor(self.case)};self.unwritten={i:self.memory[p+i]for i in(17,*range(66,88))}
  assert all(v==self.initial[p+i]for i,v in self.unwritten.items()),'Previously unwritten descriptor bytes changed'
 def hook(self,t):
  c=self.case
  if c.mutate:put(self.memory,POSITION,0xDEADBEEF);put(self.memory,POSITION+4,0x12345678);self.memory[self.syms['D_80088A64']]=0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=u32(c.result);self.hi,self.lo=0xA5000010,0xA5000011
def words(path,s=SYMS):
 raw,fs,rs=parse_object(path);f=fs['func_150E75A0'];return bound_blob(raw[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']},s)
def check(m,c,s=SYMS):
 assert m.packet==descriptor(c),('Descriptor contract',c,m.packet,descriptor(c))
 assert len(m.calls)==1 and m.calls[0][0]==s['func_1515548C']
 a=m.calls[0][1];assert a==(m.before[29]-0x88+0x2C,0,c.pair,u32(c.mode),0,c.slot&255,u32(c.context)),(c,a)
 assert m.r[2]==u32(c.result)and m.r[29]==m.before[29]
 assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
 assert all(m.memory[p]==v for p,v in m.initial.items()if p>=m.before[29]+16 and p<m.before[29]+256),'Caller storage beyond parameter homes changed'
 for i in(0,2,3):assert read(m.memory,m.before[29]+4*i)==u32(arguments(c)[i])
 want=dict(m.initial)
 if c.mutate:put(want,POSITION,0xDEADBEEF);put(want,POSITION+4,0x12345678);want[s['D_80088A64']]=0
 assert {p:v for p,v in m.memory.items()if not STACK-512<=p<STACK+256}=={p:v for p,v in want.items()if not STACK-512<=p<STACK+256}
def cases():
 result=[replace(Case(),flag=i,tag=255-i,slot=0x12340000+i,seed=i%3,mutate=bool(i&1))for i in range(256)]
 edges=(0,1,0x7F,0x80,0xFF,0x100,0x7FFF,0x8000,0xFFFF,0x10000,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
 result.extend(replace(Case(),value=v,result=r,pair=0 if i&1 else PAIR,phase=(i%2)*8,mutate=True)for i,v in enumerate(edges)for r in(0,1,0x80000000,0xFFFFFFFF))
 patterns=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 result.extend(replace(Case(),scale=a,x=b,y=u32(~b),phase=8,seed=2)for a in patterns for b in patterns)
 return result
def main():
 paths={'raw':out/'qualified-owner.o','normalized':out/'qualified-padded.o','retail':out/'retail-reference.o'};counts={};visits={}
 for name,p in paths.items():
  ws=words(p);seen=set()
  for c in cases():
   m=Oracle(ws,fixture(c),c);m.run();check(m,c);seen.update(m.visits)
  counts[name]=len(cases());visits[name]=len([p for p in seen if ENTRY<=p<ENTRY+len(ws)*4]);assert visits[name]==76
 rebase=0
 for k,lo in enumerate((0x0000,0x7FFF,0x8000,0xFFFF)):
  s={'D_80088A64':0x80300000+lo,'func_1515548C':0x15200000+4*k};entry=0x150E75A0+0x4000*k
  for name,p in paths.items():
   for phase in(0,8):
    c=replace(Case(),phase=phase,mutate=True);m=Oracle(words(p,s),fixture(c,s),c,entry=entry,s=s);m.run();check(m,c,s);rebase+=1
 report=dict(cases_per_body=counts,total=sum(counts.values()),visited_words=visits,independent_rebase_cases=rebase,float_word_copy_patterns=12,unknown_bytes_preserved=23,hardware_qualified=False)
 (out/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
