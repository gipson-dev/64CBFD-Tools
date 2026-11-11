"""Connect three original JAL windows to raw and normalized radial bodies."""
import itertools,json,struct
from dataclasses import replace
from tools.experiments import game_radial_dispatch_1514c2f0_match as p
from tools.tests import game_radial_dispatch_1514c2f0_oracle as g
from tools.experiments import game_radial_dispatch_1514c2f0_match as n
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
class Caller(g.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:self.target_arguments=(self.f[12],self.f[14],self.r[6],self.r[7],*self.arguments(12)[4:])
  else:super().record_call(t)
def execute(ws,c,which):
 rom=(p.root/'conker/conker.us.bin').read_bytes();windows=((0x150C1344,0xEE7F4,7,0x150C1360),(0x150C1690,0xEEB40,8,0x150C16B0),(0x150C1B1C,0xEEFCC,7,0x150C1B38));entry,offset,count,end=windows[which];window=struct.unpack_from('>%dI'%count,rom,offset);code=dict(zip(range(p.ENTRY,p.ENTRY+384,4),ws));code[end]=0;m=Caller(window,c,entry=entry,connected=code);home=g.STACK+c.phase
 for off,value in ((16,c.start),(20,c.step&0xFFFFFFFF),(24,c.count),(28,c.selector),(32,c.arg8),(36,c.arg9),(40,c.arg10),(44,c.arg11)):g.put(m.memory,home+off,value&0xFFFFFFFF)
 m.f[14]=c.y;m.f[8]=c.arg9;m.r[7]=c.radius
 if which==0:g.put(m.memory,home+0x12C,c.x);g.put(m.memory,home+0x134,c.z)
 elif which==1:g.put(m.memory,home+0x40,c.z);m.r[4]=c.arg11;m.f[4]=0
 else:m.r[2]=c.step&0xFFFFFFFF;m.r[3]=c.start;g.put(m.memory,home+0x12C,c.z)
 m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(end,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Caller continuation not reached')
 want,calls=g.reference(m.initial,c);public=lambda x:{a:v for a,v in x.items()if not g.STACK-1024<=a<g.STACK+1024};assert public(m.memory)==public(want)and m.calls==calls,(which,c,m.calls,calls)
 args=m.target_arguments;assert args[:4]==(c.x,c.y,c.z,c.radius)and (args[4]&255)==c.start and (args[5]&255)==(c.step&255)and (args[6]&65535)==(c.count&65535)and (args[7]&255)==c.selector and args[8:]==(c.arg8,c.arg9,c.arg10,c.arg11)
 return m
def main():
 rom=(p.root/'conker/conker.us.bin').read_bytes();raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs);lookup={r[1]:r[2][1]for r in symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};syms={name:lookup[name]for es in refs.values()for _,name in es};programs=(p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms),struct.unpack_from('>96I',rom,p.ROM));total=0
 for which,mode,fail,mutation,phase in itertools.product(range(3),(0,1),(0,100),(0,1,2,4,8,15),(0,8)):
  c=g.Case(start=250 if which==2 else 0,step=3,count=25 if which==1 else 3,selector=2 if which==1 else 0,arg8=0,arg9=0 if which==1 else g.bits(.75),arg10=0,radius=g.bits(80.)if which==1 else g.bits(2.),mode=mode,fail=fail,mutation=mutation,phase=phase);a,b,d=[execute(ws,c,which)for ws in programs];public=lambda x:{k:v for k,v in x.items()if not g.STACK-1024<=k<g.STACK+1024};assert public(a.memory)==public(d.memory)and (b.memory,b.r,b.f,b.calls,b.trace)==(d.memory,d.r,d.f,d.calls,d.trace);total+=1
 r=dict(caller_triples=total,original_windows=3,window_words=[7,8,7],return_unused_in_bounded_continuations=True,full_parents_not_qualified=True,source_installed=False);(p.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
