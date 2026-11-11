"""Exercise the original direct caller window with the connected target."""
import itertools,json,struct
from tools.tests import game_sequence_direction_1501fe68_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

WINDOW,END,ROM=0x1501F46C,0x1501F4BC,0x4C91C
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(4))))
  else:super().record_call(t)

def execute(ws,c):
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>12I',rom,ROM);memory=g.fixture(c);home=g.STACK+c.phase
 g.put(memory,home+0xF4,c.index);g.put(memory,home+0x128,c.percentage);g.put(memory,home+0x2E0,c.group)
 parent=0x70000;delta=0x30;g.put(memory,parent,g.OUTPUT-delta-0x10)
 code=dict(zip(range(g.ENTRY,g.ENTRY+384,4),ws));code[END]=0
 m=Caller(window,memory,c,entry=WINDOW,connected=code);m.r[12]=delta;m.r[13]=parent;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Caller continuation not reached')
 expected,calls,destination=g.reference(m.initial,c);assert g.public(m.memory)==g.public(expected),(c,'memory')
 assert m.calls[0]==(g.ENTRY,(c.index,c.percentage,g.OUTPUT,c.group)),(c,m.calls[0]);assert len(m.logical)==len(calls)
 for (ta,aa),(tb,ab) in zip(m.logical,calls):assert ta==tb and all(g.maybe(a,b)for a,b in zip(aa,ab))
 assert m.r[12]==delta and m.r[13]==parent and m.r[29]==home and m.r[31]==0x1501F490
 assert g.read(m.memory,home+0x9C)==delta and g.read(m.memory,home+0xA0)==parent
 return m

def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();sites=[];literals=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==g.ENTRY:literals.append(4*i)
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:sites.append(4*i)
 assert sites==[0x4C938] and not literals
 raw=g.words(g.out/'selected.o');normal=g.words(g.out/'target-generic.o');truth=struct.unpack_from('>96I',rom,g.p.ROM);pairs=0
 for count,flag,mutation,phase in itertools.product((0,1,2,3),(0,1),(0,1,2,8,15,16,31),(0,8)):
  c=g.Case(count=count,flag=flag,mutation=mutation,phase=phase,invalid=int(count<2));a,b,d=[execute(ws,c)for ws in(raw,normal,truth)]
  assert g.public(a.memory)==g.public(d.memory);assert(b.memory,b.r,b.f,b.calls,b.trace)==(d.memory,d.r,d.f,d.calls,d.trace);pairs+=1
 r=dict(caller_triples=pairs,caller_window_words=12,direct_J_JAL_ROM=sites,literal_pointers=literals,actual_parent='func_1501EC38',delay_store_and_continuation_reload_verified=True,full_parent_or_gameplay_qualified=False)
 (g.out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
