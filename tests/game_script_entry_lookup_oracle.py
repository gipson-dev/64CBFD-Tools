"""Script lookup: complete-word IDs, address returns and bounded missing-ID spin."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.experiments import game_script_entry_lookup_match as source
from tools.tests import game_actor_phase_motion_oracle as phase
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
r=Path.cwd();o=r/source.BUILD
STACK=phase.STACK
ACTOR,RESOURCE,PRIMARY,STREAM=0x220000,0x230010,0x240000,0x250000
SYMS={n:int(n[2:],16)for n in('D_800D154C','D_800D1588','D_80086A88','D_8009A120')}
@dataclass(frozen=True)
class Case:
 kind:int=3
 key:int=77
 actor_id:int=0
 unused:int=0xA55A1234
 phase:int=0
 pointer:int=STREAM

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base,size in((ACTOR-16,0x360),(RESOURCE-32,64),(PRIMARY-16,64),(s['D_800D1588']-16,256*4+32),(s['D_80086A88']-16,64),(s['D_8009A120']-16,48),(STREAM-16,96)):
  m.update({base+i:(i*13+0x59)&255 for i in range(size)})
 put(m,s['D_800D154C'],ACTOR);put(m,ACTOR+4,c.actor_id,1)
 for i in range(256):put(m,s['D_800D1588']+4*i,0)
 put(m,s['D_800D1588']+4*c.actor_id,0 if c.kind==0 else RESOURCE)
 put(m,RESOURCE-16,0 if c.kind==1 else PRIMARY)
 key=c.key&255
 primary=[(STREAM+16,(key+1)&255),(STREAM+32,(key+2)&255),(c.pointer,key),(0,(key+7)&255)]
 global_rows=[(STREAM+48,(key+3)&255),(STREAM+64,(key+4)&255),(c.pointer,key),(0,(key+9)&255)]
 if c.kind==2:primary[0]=(c.pointer,key)
 elif c.kind==4:primary[0]=(0,key)
 elif c.kind in(5,6,7,8,9):primary=[(STREAM+16,(key+1)&255),(0,(key+2)&255),(0,(key+3)&255),(0,(key+4)&255)]
 elif c.kind==10:primary[0]=(STREAM+16,key)
 if c.kind==5:global_rows[0]=(c.pointer,key)
 elif c.kind==7:global_rows[2]=(0,key)
 elif c.kind==8:global_rows[2]=(0,(key+5)&255)
 elif c.kind==9:global_rows[0]=(0,key)
 for base,rows in((PRIMARY,primary),(s['D_80086A88'],global_rows)):
  for i,(pointer,identifier)in enumerate(rows):put(m,base+8*i,pointer);put(m,base+8*i+4,identifier,1)
 return m

def reference(initial,c,s=SYMS):
 m=dict(initial);put(m,STACK+c.phase,c.unused&0xFFFFFFFF)
 actor=read(m,s['D_800D154C']);identifier=read(m,actor+4,1)
 resource=read(m,s['D_800D1588']+identifier*4)
 if not resource:return m,s['D_8009A120']
 table=read(m,resource-16)
 if not table:return m,s['D_8009A120']
 key=c.key&0xFFFFFFFF
 for i in range(32):
  if read(m,table+8*i+4,1)==key:return m,read(m,table+8*i)
  if not read(m,table+8*i):break
 else:raise AssertionError('Unbounded fixture primary table')
 table=s['D_80086A88']
 for i in range(32):
  if read(m,table+8*i+4,1)==key:return m,read(m,table+8*i)
  if not read(m,table+8*i):return m,'spin'
 raise AssertionError('Unbounded fixture global table')

class SpinStop(Exception):pass
class Code(phase.faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.spin_pc:
   self.owner.spin_visits+=1
   if self.owner.spin_visits==2:raise SpinStop
  return super().__getitem__(pc)
class Oracle(phase.Oracle):
 def __init__(self,w,m,c=Case(),entry=source.ENTRY,s=SYMS,fault=None,connected=None):
  super().__init__(w,m,c,entry,s,connected,fault)
  self.r[4]=c.unused&0xFFFFFFFF;self.r[5]=c.key&0xFFFFFFFF
  self.spin_pc=next((entry+4*i for i,v in enumerate(w)if v==0x1000FFFF and i+1<len(w)and w[i+1]==0),None)
  self.spin_visits=0;self.spinning=False;self.code=Code(dict(self.code),self)
 def record_call(self,t):
  assert t==source.ENTRY,hex(t)
  self.calls.append((t,tuple(self.r[4:6])))
 def run(self):
  try:return super().run()
  except SpinStop:self.spinning=True;return self
def linked(obj,label,entry=source.ENTRY,s=SYMS,normalize=False):
 text,fs,rs=parse_object(obj);info=fs[source.FUNCTION]
 if normalize:
  raw,bindings=source.normalized_payload(*source.payload(obj));text=raw;info=dict(info,value=0,size=len(raw));rs=bindings
 asm,unknown=emit_function(text,info,rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 n=info['size']//4
 return list(struct.unpack('>%dI'%n,sections(p.with_suffix('.elf'))['.text'][1][:4*n]))
def images(label,entry=source.ENTRY,s=SYMS):
 names=('original-func_1507BB28.o','selected-final.o','qualified-padded.o','make-shadow/src/game_A28B0.c.o')
 result=[linked(o/name,label+'-'+str(i),entry,s,i==1)for i,name in enumerate(names)]
 assert all(w==result[0]for w in result)
 raw=linked(o/'selected-final.o',label+'-raw',entry,s)
 return result,raw
def compare(images,c,s=SYMS,entry=source.ENTRY,initial=None):
 words,raw=images;initial=fixture(c,s)if initial is None else initial;want,value=reference(initial,c,s)
 models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:
  assert m.memory==want and m.spinning==(value=='spin'),(c,'memory or spin')
  if value!='spin':assert m.r[2]==value,(c,'result',hex(m.r[2]),hex(value))
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
 original=models[0];plain=Oracle(raw,initial,c,entry,s).run()
 assert plain.memory==want and plain.trace==original.trace and plain.spinning==original.spinning,(c,'raw source observable order')
 if value!='spin':assert plain.r[2]==value
 for register in(*range(16,24),28,29,30,31):assert plain.r[register]==original.r[register]
 return original

def guest_suite():
 count=aliases=cuts=delays=spins=0;seen=set()
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if not j else dict(zip(SYMS,(0x81007FFC+j*0x10000,0x82008000+j*0x10000,0x8300FFFC+j*0x10000,0x84008004+j*0x10000)))
  roots=images('lookup-rebase-'+str(j),entry,s)
  for kind,key,actor_id,unused,sp in itertools.product(range(11),(0,127,128,250,255),(0,127,128,186,255),(0,0xFFFFFFFF),(0,8)):
   c=Case(kind,key,actor_id,unused,sp);m=compare(roots,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1;spins+=m.spinning
  if j==0:
   for key,pointer in itertools.product((0x100,0xFFFFFFFA,0x80000000,0xFFFFFFFF),(0x80000000,0xFFFFFFFF)):
    c=Case(3,key,pointer=pointer);m=compare(roots,c);spins+=m.spinning;count+=1
   for pointer in(0,1,0x80000000,0xFFFFFFFF):
    compare(roots,Case(2,pointer=pointer));count+=1
   for sp in(0,8):
    # The incoming A0 home may itself supply the current actor, the selected
    # resource slot, or the resource prefix's table pointer.
    c=Case(3,77,0,ACTOR,sp);s1=dict(SYMS,D_800D154C=STACK+sp);initial=fixture(c,s1);put(initial,STACK+sp,0)
    compare(images('lookup-home-actor-'+str(sp),s=s1),c,s1,initial=initial);aliases+=1
    c=Case(3,77,0,RESOURCE,sp);s1=dict(SYMS,D_800D1588=STACK+sp);initial=fixture(c,s1);put(initial,STACK+sp,0)
    compare(images('lookup-home-resource-'+str(sp),s=s1),c,s1,initial=initial);aliases+=1
    c=Case(3,77,0,PRIMARY,sp);initial=fixture(c);put(initial,SYMS['D_800D1588'],STACK+sp+16);put(initial,STACK+sp,0)
    compare(roots,c,initial=initial);aliases+=1
   for c in(Case(),Case(kind=0),Case(kind=5),Case(kind=8),Case(phase=8,kind=6)):
    initial=fixture(c);good=Oracle(roots[0][0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in roots[0]:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except phase.faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective access-prefix cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of)==(models[0].current_pc,models[0].delay_of)
     plain=Oracle(roots[1],initial,c,fault=cut)
     try:plain.run()
     except phase.faults.AccessBoundary:pass
     else:raise AssertionError('Ineffective raw-source cut')
     assert plain.memory==models[0].memory and plain.trace==models[0].trace
     cuts+=1;delays+=models[0].delay_of is not None
 unreachable=set(range(0,236,4))-seen
 assert unreachable=={0x34,0x4C,0xA0,0xC4},sorted(unreachable)
 return dict(cases=count,normalized_executions=4*count,raw_C_executions=count,retail_words=59,reachable_words=55,unreachable_offsets=[hex(x)for x in sorted(unreachable)],independent_rebases=3,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,bounded_spin_cases=spins,raw_source_return_memory_and_access_trace_equal=True,normalized_full_register_state_equal=True,full32_key_and_pointer_bits=True,native_out_of_array_or_unbounded_execution_claim=False)

def connected_suite():
 roots=images('lookup-retail-global');va,data=sections(o/'before-conker_build_conker.us.elf')['.game_data'];rows=[]
 for i in range(3):
  at=SYMS['D_80086A88']-va+i*8;rows.append((struct.unpack_from('>I',data,at)[0],data[at+4]))
 assert rows==[(0x8009A120,1),(0x8009A120,250),(0,0)]
 count=spins=0;prefixes=[]
 for key,sp in itertools.product((0,1,250,2,255,0xFFFFFFFA),(0,8)):
  c=Case(6,key,phase=sp);initial=fixture(c)
  initial.update({va+i:v for i,v in enumerate(data)})
  # Restore the synthetic primary resource selection after importing all
  # original data: only the real global table and stream are being connected.
  put(initial,SYMS['D_800D154C'],ACTOR);put(initial,SYMS['D_800D1588'],RESOURCE);put(initial,RESOURCE-16,PRIMARY)
  m=compare(roots,c,initial=initial);count+=1;spins+=m.spinning
  if not m.spinning and m.r[2]:
   stream=m.r[2];assert stream==0x8009A120
   command=read(m.memory,stream,1);arguments=tuple(read(m.memory,stream+i,1)for i in range(1,5))
   assert command==0x67 and arguments==(0x14,0x0F,0x19,0)
   prefixes.append((command,arguments))
 return dict(cases=count,normalized_executions=4*count,raw_C_executions=count,real_global_entries=3,nonnull_global_IDs=[1,250],matched_null_ID=0,bounded_missing_ID_spin_cases=spins,original_script_prefixes_checked=len(prefixes),script_record_bytes=5,full_script_interpreter_or_gameplay_claim=False)

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();opcode=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==opcode]
 pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 expected_sites=[0x83FE0,0x84224,0x84764,0x84920,0x849A0,0x84D5C,0x84D74,0x85314,0x86320,0x93E38,0xA32E8,0xA3F58,0xA6508,0xA6594,0xA71AC,0xA74C0,0xA85C8,0xA9170,0xB556C,0xC53E8,0xC5918,0xC628C,0x11B0E8,0x20C774,0x21BD14]
 assert sites==expected_sites and pointers==[],(sites,pointers)
 roots,raw=images('lookup-callers');count=0;windows={}
 for lane,(at,length)in enumerate(((0xA32E8,10),(0xA9170,4),(0xB556C,6),(0x83FE0,5))):
  start=at+0x14FD2B50;stop=start+4*length;words=list(struct.unpack_from('>%dI'%length,rom,at));windows[hex(start)]=length
  assert words[0]==opcode
  for kind,key,actor_id,sp in itertools.product((0,1,2,3,4,5,7,9),(1,250),(0,186),(0,8)):
   c=Case(kind,key,actor_id,4 if lane==3 else 0,sp)
   initial=fixture(c);registers={16:ACTOR};prepared=dict(initial)
   if lane==0:
    registers[3]=0x800D1891;put(initial,0x800D1891,key,1);prepared=dict(initial)
   elif lane==1:put(initial,ACTOR+0x232,key,1);prepared=dict(initial)
   elif lane==2:
    registers.update({1:0x800C0000,24:0x5A});put(initial,STACK+sp+0x1C,ACTOR)
    initial[0x800C3E78]=0;prepared=dict(initial);prepared[0x800C3E78]=0x5A
   else:registers[2]=key
   want,value=reference(prepared,c);assert value!='spin'
   put(want,ACTOR+0x218,(value-5)&0xFFFFFFFF if lane==0 else value)
   if lane in(1,3):put(want,ACTOR+0x21C,0,2)
   if lane==3:put(want,ACTOR+0x23A,0,1)
   models=[]
   for body in (*roots,raw):
    connected=dict(zip(range(source.ENTRY,source.ENTRY+4*len(body),4),body))
    m=Oracle(words,initial,c,start,connected=connected)
    m=phase.run_window(m,stop,registers)
    assert m.memory==want and m.calls==[(source.ENTRY,(c.unused,key))],(lane,c,'original caller memory/arguments',m.calls)
    assert m.r[2]==value and m.r[16]==ACTOR and m.r[29]==STACK+sp
    models.append(m)
   for m in models[1:4]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
   assert models[4].trace==models[0].trace
   count+=1
 return dict(cases=count,normalized_executions=4*count,raw_C_executions=count,original_window_words=windows,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,all25_sites_inventoried=True,representative_return_consumers=4,address_store_and_five_byte_backup_proven=True,nonzero_unused_argument_proven=True,full25_parents_or_gameplay_claim=False)

def native_harness(body):
 return source.HEADERS+r'''
typedef char pointer_is_four[sizeof(void *)==4?1:-1];
typedef char table_entry_is_eight[sizeof(ScriptLookupEntry)==8?1:-1];
typedef char table_key_is_four[__builtin_offsetof(ScriptLookupEntry,id)==4?1:-1];
typedef char script_record_is_five[sizeof(struct216)==5?1:-1];
struct127 *D_800D154C;
s32 D_800D1588[187];
ScriptLookupEntry D_80086A88[257];
struct216 D_8009A120;
static struct127 actor;
static ScriptLookupEntry primary[4];
static struct216 scripts[16];
static struct {ScriptLookupEntry *correct,*alternative;u8 reserved[8];u8 body[16];} resource;
''' + body+r'''
static int run_cases(void){
 unsigned cls,key,kind,i;u32 before=0;
 D_800D154C=&actor;
 for(i=0;i<sizeof(actor);i++)((u8 *)&actor)[i]=(u8)(i*13+0x59);
 for(i=0;i<sizeof(resource);i++)((u8 *)&resource)[i]=(u8)(i*7+0xA3);
 for(i=0;i<16;i++){unsigned j;for(j=0;j<5;j++)((u8 *)&scripts[i])[j]=(u8)(i*17+j);}
 for(cls=0;cls<187;cls++)for(key=0;key<256;key++)for(kind=0;kind<8;kind++){
  u32 expected,result,unused=(cls*1664525u+key*1013904223u+kind)^0xA55A1234u;
  for(i=0;i<187;i++)D_800D1588[i]=0;
  actor.id=(u8)cls;resource.correct=kind==1?NULL:primary;resource.alternative=D_80086A88;
  D_800D1588[cls]=kind==0?0:(s32)resource.body;
  for(i=0;i<4;i++){primary[i].script=&scripts[i];primary[i].id=(u8)(key+i+1);primary[i].reserved05[0]=0xA5;primary[i].reserved05[1]=0x5A;primary[i].reserved05[2]=0xC3;}
  primary[3].script=NULL;
  for(i=0;i<256;i++){D_80086A88[i].script=&scripts[8+i%8];D_80086A88[i].id=(u8)i;D_80086A88[i].reserved05[0]=0xA5;D_80086A88[i].reserved05[1]=0x5A;D_80086A88[i].reserved05[2]=0xC3;}
  D_80086A88[255].script=NULL;D_80086A88[256].script=&scripts[15];D_80086A88[256].id=0xAA;
  expected=(u32)&D_8009A120;
  if(kind==2){primary[0].id=(u8)key;expected=(u32)primary[0].script;}
  else if(kind==3){primary[2].id=(u8)key;expected=(u32)primary[2].script;}
  else if(kind==4){primary[0].id=(u8)key;primary[0].script=NULL;expected=0;}
  else if(kind==5){primary[0].script=NULL;expected=(u32)D_80086A88[key].script;}
  else if(kind==6){primary[3].id=(u8)key;expected=0;}
  else if(kind==7)expected=(u32)D_80086A88[key].script;
  if(!((key+kind)&63)){
   before=2166136261u;
   for(i=0;i<sizeof(primary);i++)before=(before^((u8 *)primary)[i])*16777619u;
   for(i=0;i<sizeof(D_80086A88);i++)before=(before^((u8 *)D_80086A88)[i])*16777619u;
  }
  result=(u32)func_1507BB28((s32)unused,(s32)key);
  if(result!=expected)return 74;
  if(D_800D154C!=&actor||actor.id!=cls||D_800D1588[cls]!=(kind==0?0:(s32)resource.body))return 75;
  if(!((key+kind)&63)){
   u32 after=2166136261u;
   for(i=0;i<sizeof(primary);i++)after=(after^((u8 *)primary)[i])*16777619u;
   for(i=0;i<sizeof(D_80086A88);i++)after=(after^((u8 *)D_80086A88)[i])*16777619u;
   if(before!=after)return 76;
  }
 }
 return 0;
}
void _start(void){int result=run_cases();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
def native_suite():
 body=source.SELECTED
 controls={
 'wrong-actor-table-slot':body.replace('D_800D1588[D_800D154C->id]','D_800D1588[(D_800D154C->id + 1) % 187]'),
 'wrong-resource-prefix':body.replace('resource - 0x10','resource - 0xC'),
 'wrong-default-address':body.replace('(s32)&D_8009A120','0'),
 'early-primary-fallback':body.replace('if (cursor->script == NULL)','if (cursor->script != NULL)'),
 'wrong-primary-index':body.replace('(s32)table[index].script','(s32)table[0].script'),
 'wrong-global-index':body.replace('(s32)D_80086A88[index].script','(s32)D_80086A88[(index + 1) & 255].script'),
 'unused-argument-affects-ID':body.replace('s32 index;','s32 index;\n    id = (id + (unused & 255)) & 255;'),
 }
 results=[]
 for label,opt,text,control in [('positive-'+opt,opt,body,False)for opt in('-O0','-O2','-O3')]+[(n,'-O2',v,True)for n,v in controls.items()]:
  assert not control or text!=body,label
  p=o/('native-'+label+'.c');p.write_text(native_harness(text));exe=p.with_suffix('')
  q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  # Controls retain a complete byte-key global fixture, so each must report a
  # semantic mismatch rather than relying on a timeout or memory trap.
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
  assert q.returncode==(74 if control else 0),(label,q.returncode,q.stdout,q.stderr)
  results.append(dict(name=label,optimization=opt,control=control,exit=q.returncode))
 return dict(positive_cases_each=187*256*8,profiles=['O0','O2','O3'],effective_controls=len(controls),controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all187_declared_actor_slots=True,all256_byte_IDs=True,all_eight_table_outcomes=True,unused_argument_full_bits=True,periodic_table_bytes_preserved=True,native_missing_ID_spin_or_64bit_pointer_claim=False,results=results)
