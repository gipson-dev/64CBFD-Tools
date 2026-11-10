"""Actual float callback window and complete original graphics-helper chain."""
import itertools,json,struct
from tools.tests import game_view_split_borders_151103c8_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
TABLE,DESCRIPTOR,STATE=0x800891D8,0x800B0DF0,0x70000
WINDOW,END=0x15110244,0x15110288
PROVIDERS=((g.FILL,188),(g.SCISSOR,496),(g.RECT,152),(0x1501A680,76))
def original(rom,a,n):return struct.unpack_from('>%dI'%(n//4),rom,a-0x15000000+0x2D4B0)
def dispatcher(rom,elf,ws,c):
 memory=g.fixture(c);g.put(memory,DESCRIPTOR,STATE);g.put(memory,STATE+8,0,1);at=elf_slot_offset(elf,TABLE,20);memory.update({TABLE+i:b for i,b in enumerate(elf[at:at+20])});assert g.read(memory,TABLE)==g.ENTRY
 code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code[END]=0;m=g.Oracle(original(rom,WINDOW,END-WINDOW),memory,c,entry=WINDOW,connected=code);m.f[12],m.f[14],m.f[18]=c.homes;m.f[16],m.f[2],m.f[0]=0x12345678,0x87654321,0x3F800001;m.r[2]=0x11223344;m.code=WindowCode(m.code,m);m.code.ends=(END,);m.initial=dict(m.memory)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing callback continuation')
 expected,calls,result,valid=g.reference(m.initial,c);assert valid;assert m.calls==[(g.ENTRY,(g.cursor(c),*c.homes))]+calls;assert g.public(m.memory)==g.public(expected);assert m.r[4]==m.r[2]==result
 for at,value in((0x10,0x12345678),(0x14,0x87654321),(0x18,0x3F800001),(0x1C,0x11223344)):assert g.read(m.memory,g.STACK+c.phase+at)==value
 return m
def census(rom):
 literals=[];direct=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==g.ENTRY:literals.append(4*i)
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:direct.append(4*i)
 assert literals==[0x22DC98]and not direct
 return dict(table=TABLE,slot=0,literal_ROM=literals,direct_J_JAL=direct,actual_JALR=0x1511027C,float_argument_transfers=True,returned_cursor_copied_to_A0=True,original_total_parameter_count_not_proven=True,ignored_stack_words_preserved=True)
def packed_rectangle(left,top,right,bottom,width,height):
 left=max(left,2);top=max(top,0);right=min(right,width-2);bottom=min(bottom,height)
 return 0xF6000000|((right&1023)<<14)|((bottom&1023)<<2),((left&1023)<<14)|((top&1023)<<2)
def real_reference(initial,c):
 m=dict(initial);p=g.cursor(c);w=g.signed(g.read(m,g.symbols()['D_800BE620']));h=g.signed(g.read(m,g.symbols()['D_800BE624']));v=g.selected(c);left=g.signed(g.trunc(g.floating(g.read(m,v+0x2C))));top=g.signed(g.trunc(g.floating(g.read(m,v+0x24))));right=g.signed(g.trunc(g.rounded(g.floating(g.read(m,v+0x30))-1.)));bottom=g.signed(g.trunc(g.floating(g.read(m,v+0x28))))
 r,green,b=[g.read(m,g.symbols()['D_800DBEA8']+i,1)for i in range(3)];color=((r<<8)&0xF800)|((green<<3)&0x7C0)|((b>>2)&0x3E)|1;page=g.read(m,0x800BE9C0,1);fb=g.read(m,0x8002AAE8+4*page)
 pairs=[(0xE7000000,0),(0xEF302C0F,4),(0xFF100000|((w-1)&4095),fb),(0xF7000000,(color<<16)|color),packed_rectangle(left,top,right,bottom,w,h)]
 if g.read(m,0x80082FA0)!=0 and g.read(m,0x80082FA4)==0:
  pairs.extend([(0xE7000000,0),(0xE7000000,0),(0xED008000,(((w-2)*4&4095)<<12)|(h*4&4095)),(0xF7000000,0x00010001),packed_rectangle(0,(h>>1)-6,w,(h>>1)+6,w,h)])
  if g.read(m,0x80082FA0)!=1:pairs.append(packed_rectangle((w>>1)-1,0,(w>>1)+1,h,w,h))
 for i,(a,b)in enumerate(pairs):g.put(m,p+8*i,a);g.put(m,p+8*i+4,b)
 return m,p+8*len(pairs)
class RealOracle(g.Oracle):
 def execute(self,w):
  if w>>26==17 and w>>21&31==20 and w&63==32:self.f[w>>6&31]=g.bits(float(g.signed(self.f[w>>11&31])))
  else:super().execute(w)
 def record_call(self,t):
  if t==0x1501A680:
   args=(self.r[4],);self.calls.append((t,args));self.events.append(('CALL',t,args))
  else:super().record_call(t)
 def hook(self,t):raise AssertionError(('Real graphics helper not connected',hex(t)))
def real_helpers(rom,elf,programs):
 code={};seen=set();pairs=0
 for a,n in PROVIDERS:
  data=original(rom,a,n);at=elf_slot_offset(elf,a,n);assert elf[at:at+n]==struct.pack('>%dI'%len(data),*data),(hex(a),'helper differs');code.update(zip(range(a,a+n,4),data))
 for index,mode,page,shape in itertools.product((0,1,3),(0,1,2,0xFFFFFFFF),(0,1),range(3)):
  w,h=((292,216),(640,480),(1024,1024))[shape];c=g.Case(index=index,mode=mode,width=w,height=h,view=tuple(map(g.bits,(-3.5,1.75,w+10.,h+10.))),colors=(255,128,shape));memory=g.fixture(c);g.put(memory,0x800BE9C0,page,1)
  for i in range(2):g.put(memory,0x8002AAE8+4*i,0x80200000+i*0x100000)
  expected,result=real_reference(memory,c);models=[]
  for ws in programs:
   m=RealOracle(ws,memory,c,connected=code);m.run();assert g.public(m.memory)==g.public(expected),(index,mode,page,shape,'real-packets');assert m.r[2]==result,(index,mode,page,shape,'real-cursor');models.append(m);seen.update(pc for pc in m.visits if any(a<=pc<a+n for a,n in PROVIDERS))
  a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1
 return dict(pairs=pairs,provider_words=sum(n//4 for a,n in PROVIDERS),covered_provider_words=len(seen),all_original_providers_currently_byte_exact=True,independent_complete_command_packets=True,scissor_full_frame_path_only=True,FCSR_or_hardware_qualified=False)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();programs=(g.words(g.out/'selected.o'),original(rom,g.ENTRY,380));pairs=0;seen=set()
 for i,(index,mode,mu,after,returns,phase)in enumerate(itertools.product((0,1,3),(0,1,2),(0,15),(0,1,2),(0,1),(0,8))):
  c=g.Case(index=index,mode=mode,mutation=mu,after=after,returns=returns,phase=phase,seed=i%7);a,b=[dispatcher(rom,elf,ws,c)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1;seen.update(pc for pc in a.visits if WINDOW<=pc<END)
 report=dict(census=census(rom),callback_pairs=pairs,callback_window_words=len(seen),real_helpers=real_helpers(rom,elf,programs),current_parent_placeholder_unchanged=True,full_parent_or_gameplay_qualified=False);(g.out/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
