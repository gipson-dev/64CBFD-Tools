"""Connect the complete original 484-word actor effect parent to its real helper."""
from dataclasses import dataclass
import hashlib,itertools,json,math,struct,subprocess
from tools.tests import game_scaled_radial_150b85c0_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
PARENT,CONTINUE,ACTOR,MODEL=0x150B7B40,0x150B7D9C,0x60000,0x68000
elf=(g.f/'conker/build/conker.us.elf').read_bytes();rom=(g.f/'conker/conker.us.bin').read_bytes();original=rom[0xE4FF0:0xE5780]
assert len(original)==1936
installed_parent=elf[elf_slot_offset(elf,PARENT,len(original)):][:len(original)]
assert installed_parent!=original and (g.f/'conker/src/game/generated_E4070.c').read_text().count('s32 func_150B7B40() {\n    return 0;\n}')==1
rows=symbol_rows(elf);assert next(v[2][2]for v in rows if v[1]=='func_150B7B40')==12
asm=(g.f/'conker/asm/E4070.s').read_text();fragment='glabel func_150B7B40\n'+asm.split('glabel func_150B7B40\n')[1].split('endlabel func_150B7B40')[0]+'.size func_150B7B40,.-func_150B7B40\n'
def verify_original():
 source=g.p/'caller-original.s';obj=source.with_suffix('.o');source.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(source)],cwd=g.f.parents[3]/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,(q.stdout,q.stderr)
 lookup={v[1]:v[2][1]for v in rows};assert struct.pack('>484I',*bound_blob(*payload(obj,'func_150B7B40'),lookup))==original
parent_words=list(struct.unpack('>484I',original));assert parent_words[(0x150B7D94-PARENT)//4]==0x0D42E170
SIGNATURES={0x15142314:3,0x151423D8:1,0x15143134:3,0x1515C244:4,0x150B82D0:6,0x1504715C:2,0x15046C80:4,0x1514C678:12,g.RNG:0,0x150ADA68:0,0x15132A4C:6,0x15151A38:3}
@dataclass(frozen=True)
class Case:
 base:g.Case;model:int=0;zero:int=0;floor:int=0;null:int=0
def cases():
 for model,zero,floor,profile,success,mutation in itertools.product((0,1),(0,1),(0,1),range(4),(0,1),(0,7)):
  seed=(model*11+zero*17+floor*19+profile*29+success*31+mutation*37)&255
  yield Case(g.Case(255 if seed&1 else 0,0,success,mutation,profile,8*(seed&1),seed,0x80000000|seed),model,zero,floor)
 yield Case(g.Case(),null=1)
def fixture(c):
 m=g.fixture(c.base)
 for a,n in((ACTOR,0x200),(MODEL,0x100)):m.update({a+i:(i*17+c.base.seed)&255 for i in range(n)})
 for off,v in((0x14,1.25),(0x18,2.5),(0x1c,3.75),(0x3c,1.5),(0x40,4.),(0xb8,5.),(0xc4,6.),(0x14c,(-.5,.75,2.,.5)[c.base.profile]),(0x150,(2.,.5,-1.,.75)[c.base.profile])):g.put(m,ACTOR+off,g.bits(v))
 g.put(m,ACTOR+0x1d4,MODEL if c.model else 0);g.put(m,ACTOR+0x184,0x12345678);g.put(m,ACTOR+0x76,0x4567,2)
 at=elf_slot_offset(elf,0x8009FD30,0x5c)
 m.update({0x8009FD30+i:b for i,b in enumerate(elf[at:at+0x5c])});return m
class Oracle(g.Oracle):
 def __init__(self,target,c):
  initial=fixture(c);connected=dict(zip(range(g.ENTRY,g.ENTRY+476,4),target));self.parent_case=c;self.active=False;self.boundaries=0;self.verified=0;self.parent_calls=[];self.parent_rng=self.parent_float=0
  super().__init__(parent_words,initial,c.base,entry=PARENT,connected=connected,arguments=(0 if c.null else ACTOR,0xABC00000|c.base.slot,c.base.context))
 def execute(self,w):
  if self.active and self.current_pc==CONTINUE:
   expected,s,result=self.expected;assert self.service.calls==s.calls and self.r[2]==result
   assert g.public(self.memory)==g.public(expected)
   assert g.data(self.memory,self.packet_home,112)==g.data(expected,self.packet_home,112)
   assert tuple(self.r[16:24])+tuple(self.r[28:])==self.helper_saved and tuple(self.f[20:])==self.helper_saved_fp
   self.parent_calls.extend(self.service.calls);self.verified+=1;self.active=False
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(4,5,7):
   value=self.f[w>>11&31];self.f[w>>6&31]=g.bits(math.sqrt(g.floating(value)))if fn==4 else value&0x7fffffff if fn==5 else value^0x80000000;return
  return super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   assert not self.active;self.active=True;self.boundaries+=1;self.helper_sp=self.r[29]-152;self.packet_home=self.r[29]-112
   argv=tuple(self.arguments(5));assert argv[0]==self.r[29]+0x190 and argv[1]==self.r[29]+0x18c and argv[2]==self.r[29]+0x188
   assert argv[3]==self.parent_case.base.slot and argv[4]==self.parent_case.base.context
   self.expected=g.reference(self.memory,self.parent_case.base,home=self.r[29],arguments=argv);self.service=g.Service(self.memory,self.parent_case.base)
   self.helper_saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.helper_saved_fp=tuple(self.f[20:]);return
  if self.active and self.r[29]==self.helper_sp:return super().record_call(t)
  assert t in SIGNATURES,hex(t);args=tuple(self.arguments(SIGNATURES[t]));observed=()
  if t in(0x15132A4C,0x15151A38):observed=g.data(self.memory,args[0],120 if t==0x15132A4C else 136)
  self.pending_parent=t,args;self.parent_calls.append((t,args,observed))
 def hook(self,t):
  if self.active and self.r[29]==self.helper_sp:return super().hook(t)
  c=self.parent_case;a=self.pending_parent[1];answer=0xDEADBEEF;fvalue=None
  def vector(at,values):
   for i,v in enumerate(values):g.put(self.memory,at+4*i,g.bits(v))
  if t==0x15142314:vector(a[2],(1.+a[1],2.+a[1],3.+a[1]))
  elif t==0x151423D8:fvalue=g.bits(((a[0]&255)-128)/128.)
  elif t==0x15143134:
   v=(a[0]-0x8009FD30)//12;vector(a[1],(0.,0.,0.)if c.zero else(1.+v*3,2.+v*3,3.+v*3))
  elif t==0x1515C244:vector(a[1],(1.25,2.5,3.75));g.put(self.memory,a[2],g.bits(0. if c.zero else 4.));g.put(self.memory,a[3],g.bits(0. if c.zero else 6.))
  elif t==0x150B82D0:pass # Other local helper remains an opaque six-argument provider.
  elif t==0x1504715C:
   for i in range(0x24):self.memory[a[0]+i]=0
   g.put(self.memory,a[0],g.bits(7.5))
  elif t==0x15046C80:g.put(self.memory,a[3],g.bits(7.5));answer=c.floor
  elif t==g.RNG:answer=(c.base.seed+self.parent_rng*0x13579bdf)&0xffffffff;self.parent_rng+=1
  elif t==0x150ADA68:fvalue=g.bits(.125+.0625*(self.parent_float%5));self.parent_float+=1
  elif t in(0x1514C678,0x15132A4C,0x15151A38):answer=0
  else:raise AssertionError(hex(t))
  count=SIGNATURES[t]
  for i in range(max(4,count)):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xffffffff
  if fvalue is not None:self.f[0]=fvalue
def main():
 verify_original()
 programs=g.streams();results={};reports=[]
 for stream_index,(label,words)in enumerate(programs):
  seen=set();target_seen=set();count=0;invocations=0
  for index,c in enumerate(cases()):
   m=Oracle(words,c).run();assert not m.active and m.boundaries==m.verified==int(not c.null)
   assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
   result=(m.memory,m.r,m.f,m.parent_calls)
   if stream_index==0:results[index]=result
   else:assert result==results[index],('whole parent',label,c)
   seen.update(m.visits&set(range(PARENT,PARENT+1936,4)));target_seen.update(m.visits&set(range(g.ENTRY,g.ENTRY+476,4)));count+=1;invocations+=m.verified
  assert len(target_seen)==119 and seen==set(range(PARENT,PARENT+1936,4))-{0x150B7D60}
  assert parent_words[(0x150B7D60-PARENT)//4]==0x3C013F80
  row=dict(stream=label,cases=count,complete_parent_words=484,parent_words_covered=len(seen),target_words_covered=len(target_seen),helper_invocations=invocations,full_parent_and_real_call_verified=True,other_providers_modeled=True);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,callers=reports,original_parent_GNU_and_ROM_verified=True,production_parent_unrestored=True,frozen_installed_parent_sha256=hashlib.sha256(installed_parent).hexdigest(),hardware_runtime_unclaimed=True,c_match_credit=0);(g.p/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
