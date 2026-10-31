"""Settings record: ordered copy, unsigned weighted checksum and queued write."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess,hashlib
from tools.tests.game_view_render_pass_oracle import RenderOracle,STACK
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_settings_packet_write_match as source
r=Path.cwd();o=r/source.BUILD
F,OWNER,ENTRY,ROM='func_15007558','game_33990',0x15007558,0x34A08
SYMS=dict(D_800BE358=0x800BE358,D_800BE35A=0x800BE35A,
          D_800E0BE0=0x800E0BE0,D_800E0BFC=0x800E0BFC,
          D_8002AC5C=0x8002AC5C,D_800BE900=0x800BE900,func_151DCEF0=0x151DCEF0)
@dataclass(frozen=True)
class Case:
 pattern:int=0
 flag:int=0
 mode:int=0
 phase:int=0
 result:int=0
 ignored:int=0xFFFFFFFF
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base,size in((s['D_800BE358']-16,64),(s['D_800BE35A']-16,64),
                  (s['D_800E0BE0']-16,64),(s['D_8002AC5C']-4,12),(s['D_800BE900']-16,48)):
  m.update({base+i:(i*13+0x59)&255 for i in range(size)})
 for i in range(28):
  value=(0,255,128,127,(i*17+c.pattern)&255,1<<(i&7))[c.pattern%6]
  put(m,s['D_800E0BE0']+i,value,1)
 put(m,s['D_8002AC5C'],c.flag,1)
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+128}
def effects(m,c,s):
 if c.mode&1:put(m,s['D_8002AC5C'],255,1)
 if c.mode&2:
  for i in range(32):put(m,s['D_800BE358']+i,(i*23+0x71)&255,1)
 if c.mode&4:
  for i in range(28):put(m,s['D_800E0BE0']+i,(i*29+0x85)&255,1)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 for i in range(28):
  value=read(m,s['D_800E0BE0']+i,1)
  put(m,s['D_800BE358']+2+i,value,1)
 # Closed weighted sum over the post-copy bytes. The input domain bounds
 # this to 204..26979; a 16-bit wrap cannot actually occur in this routine.
 checksum=(204+sum(read(m,s['D_800BE35A']+i,1)*(1<<((i+2)%4))for i in range(28)))&65535
 put(m,s['D_800BE358'],checksum,2)
 if read(m,s['D_8002AC5C'],1)==0:
  calls.append((s['func_151DCEF0'],(s['D_800BE900'],0,s['D_800BE358'],32)))
  observations.append(tuple(read(m,s['D_800BE358']+i,1)for i in range(32)))
  effects(m,c,s)
 return m,calls,observations
class Oracle(RenderOracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,fault=None,connected=None):
  self.c,self.s,self.trace=c,s,[]
  super().__init__(w,m,phase=c.phase,entry=entry,arguments=(c.ignored,0x87654321,0x89ABCDEF,0x76543210),connected=connected,fault=fault)
  self.hi=self.lo=0
 def execute(self,word):
  if word>>26==32:
   self.own_instruction=True
   try:
    rs,rt=word>>21&31,word>>16&31;imm=word&65535
    if imm&32768:imm-=65536
    value=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
    self.r[rt]=(value if value<128 else value-256)&0xFFFFFFFF;self.r[0]=0
   finally:self.own_instruction=False
  elif word>>26==0 and word&63==4:
   rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
   self.r[rd]=(self.r[rt]<<(self.r[rs]&31))&0xFFFFFFFF;self.r[0]=0
  else:super().execute(word)
 def get(self,p,n):
  value=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,value))
  return value
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t==self.s['func_151DCEF0'],hex(t)
  args=tuple(self.r[4:8]);self.calls.append((t,args));self.events.append(('CALL',t,args))
  self.observations.append(tuple(read(self.memory,self.s['D_800BE358']+i,1)for i in range(32)))
 def hook(self,t):
  effects(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=self.c.result&0xFFFFFFFF
  self.hi,self.lo=0xA5000010,0xA5000011
def normalized(raw,bindings):
 assert len(raw)==236 and hashlib.sha256(raw).hexdigest()=='2d7422666bf39e7f4f4487b3aae9590d9493ddbc0afa249ae69235f8554cd4f3'
 words=list(struct.unpack('>59I',raw));rs=dict(bindings)
 for row in json.loads((o/'new-guard-rows.json').read_text()):
  at=int(row['offset'],0);fmt=lambda b:';'.join(k+':'+n for k,n in b)if b else '-'
  assert words[at//4]==int(row['expected'],0)and fmt(rs.get(at,[]))==row['expected_relocations']
  words[at//4]=int(row['replacement'],0)
  if row['replacement_relocations']=='-':rs.pop(at,None)
  else:rs[at]=[tuple(part.split(':',1))for part in row['replacement_relocations'].split(';')]
 result=struct.pack('>59I',*words)
 assert hashlib.sha256(result).hexdigest()=='65ab7c37e99216c2dee5f8abcee68cbde80db8450d9e7f65af632d0f2911e084'
 return result,rs
def linked(obj,label,entry=ENTRY,s=SYMS,normalize=False):
 text,fs,rs=parse_object(obj);info=fs[F]
 if normalize:
  start,size=info['value'],info['size']
  text,rs=normalized(text[start:start+size],{at-start:v for at,v in rs.items()if start<=at<start+size})
  info=dict(info,value=0,size=len(text))
 asm,unknown=emit_function(text,info,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm)
 p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>59I',sections(p.with_suffix('.elf'))['.text'][1][:236]))
def images(label,entry=ENTRY,s=SYMS):
 names=('original-func_15007558.o','selected-final.o','qualified-padded.o','make-shadow/src/game_33990.c.o')
 roots=[linked(o/n,label+'-'+str(i),entry,s,i==1)for i,n in enumerate(names)]
 assert all(w==roots[0]for w in roots)
 return roots,linked(o/'selected-final.o',label+'-raw',entry,s)
def compare(images,c,s=SYMS,entry=ENTRY):
 words,raw=images;initial=fixture(c,s);want,calls,observations=reference(initial,c,s)
 models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:
  assert public(m.memory)==public(want),(c,'public state')
  assert m.calls==calls and m.observations==observations,(c,'queue arguments/record')
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
 plain=Oracle(raw,initial,c,entry,s).run()
 assert complete(plain)==complete(models[0])and plain.trace==models[0].trace,(c,'raw C final state and access order')
 return models[0]
def guest_suite():
 count=cuts=delays=aliases=0;seen=set()
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  if not j:s=SYMS
  else:
   record=0x81007FFC+j*65536;settings=0x82008000+j*65536
   s=dict(D_800BE358=record,D_800BE35A=record+2,D_800E0BE0=settings,D_800E0BFC=settings+28,
          D_8002AC5C=0x8300FFFC+j*65536,D_800BE900=0x84008004+j*65536,func_151DCEF0=entry+0x10000)
  roots=images('settings-rebase-'+str(j),entry,s)
  for pattern,flag,mode,phase,result,ignored in itertools.product(range(6),(0,1,255),(0,7),(0,8),(0,0x80000000,0xFFFFFFFF),(0,0xFFFFFFFF)):
   c=Case(pattern,flag,mode,phase,result,ignored);m=compare(roots,c,s,entry)
   seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if not j:
   variants=[]
   for delta in(-2,-1,0,1,2):
    source=s['D_800BE358']+2+delta;variants.append(dict(s,D_800E0BE0=source,D_800E0BFC=source+28))
   variants.extend((dict(s,D_8002AC5C=s['D_800BE358']),dict(s,D_8002AC5C=s['D_800BE358']+3),dict(s,D_800BE35A=0x85008000)))
   for i,alias in enumerate(variants):
    root=images('settings-alias-'+str(i),s=alias)
    for pattern,flag in itertools.product((0,1,4),(0,1)):
     compare(root,Case(pattern,flag),alias);aliases+=1
   for c in(Case(),Case(flag=1),Case(pattern=1,mode=7,phase=8,result=0xFFFFFFFF)):
    initial=fixture(c);good=Oracle(roots[0][0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in roots[0]:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except AccessBoundary:pass
      else:raise AssertionError('Ineffective access-prefix cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of)==(models[0].current_pc,models[0].delay_of)
     plain=Oracle(roots[1],initial,c,fault=cut)
     try:plain.run()
     except AccessBoundary:pass
     else:raise AssertionError('Ineffective raw access-prefix cut')
     assert plain.memory==models[0].memory and plain.trace==models[0].trace
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
 return dict(cases=count,normalized_executions=count*4,raw_C_executions=count,retail_words=59,reachable_words=59,
             independent_rebases=3,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,
             raw_final_architectural_state_and_access_order_equal=True,normalized_prefix_state_equal=True,
             raw_prefix_memory_and_access_order_equal=True,copy_bytes=28,record_bytes=32,tail_bytes_preserved=2,
             checksum_range=[204,26979],volatile_status_stack_offset=24,frame=32,
             helper_or_EEPROM_hardware_claim=False)
def caller_suite():
 from tools.tests.game_actor_phase_motion_oracle import WindowStop,WindowCode
 rom=(o/'before-conker_conker.us.bin').read_bytes();target=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
 sites=[];pointers=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==target:sites.append(4*i)
  if w==ENTRY:pointers.append(4*i)
 assert sites==[0x49B94]and pointers==[],(sites,pointers)
 start,stop,after=0x1501C6E4,0x1501C6FC,0x1501C6EC
 window=list(struct.unpack_from('>6I',rom,start-(ENTRY-ROM)))
 class Caller(Oracle):
  def record_call(self,t):
   if t==ENTRY:self.calls.append((t,()));self.events.append(('CALL',t,()))
   else:super().record_call(t)
 roots,raw=images('settings-caller');count=0
 for pattern,flag,mode,phase,result,pointer in itertools.product((0,1,4),(0,1),(0,7),(0,8),(0,0xFFFFFFFF),(0,0x220000)):
  c=Case(pattern,flag,mode,phase,result);initial=fixture(c)
  put(initial,0x800BE3F0,pointer);put(initial,0x80082BB4,0xA5,1)
  want,calls,observations=reference(initial,c);put(want,0x80082BB4,0,1)
  calls=[(ENTRY,()),*calls];models=[]
  for body,poison in itertools.product((*roots,raw),(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
   m=Caller(window,initial,c,start,connected={ENTRY+4*i:w for i,w in enumerate(body)})
   m.stop_pc,m.poison_pc,m.poison_value=stop,after,poison;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowStop:pass
   else:raise AssertionError('Missing caller window stop')
   assert public(m.memory)==public(want)and m.calls==calls and m.observations==observations
   assert m.r[29]==STACK+phase and m.r[2]==pointer
   models.append(m)
  for m in models[1:]:assert complete(m)==complete(models[0])
  count+=1
 return dict(cases=count,normalized_executions=count*16,raw_executions=count*4,original_window_words=6,
             aligned_JAL_sites=sites,aligned_literal_pointers=pointers,return_poison_values=4,
             ignored_return_proven=True,no_argument_interface=True,caller_pointer_reload_and_state_clear=True,
             full_parent_or_hardware_claim=False)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
PREAMBLE=r'''
typedef union {u16 checksum; u8 bytes[32];} NativeRecord;
NativeRecord nativeRecord;
extern u8 D_800BE358[32] __attribute__((alias("nativeRecord")));
s8 D_800E0BE0[28];
__asm__(".globl D_800BE35A\n.set D_800BE35A, nativeRecord+2\n"
        ".globl D_800E0BFC\n.set D_800E0BFC, D_800E0BE0+28\n");
u8 D_8002AC5C;
OSMesgQueue D_800BE900;
static u8 observed[32];
static unsigned calls,mode;
static u32 statusValue;
static int failed;
s32 func_151DCEF0(OSMesgQueue *q,s32 address,void *buffer,s32 length) {
 unsigned i;
 if(q!=&D_800BE900||address!=0||buffer!=D_800BE358||length!=32)failed=1;
 ++calls;
 for(i=0;i<32;i++)observed[i]=nativeRecord.bytes[i];
 if(mode&1)D_8002AC5C=255;
 if(mode&2)for(i=0;i<32;i++)nativeRecord.bytes[i]=(u8)(i*23+0x71);
 if(mode&4)for(i=0;i<28;i++)D_800E0BE0[i]=(s8)(i*29+0x85);
 return (s32)statusValue;
}
'''
HARNESS=r'''
static int checkCase(unsigned pattern,unsigned position,unsigned value,u8 flag,unsigned effects,u32 result) {
 NativeRecord wanted,submitted;
 u8 source[28];u32 sum=204;unsigned i;
 calls=0;failed=0;mode=effects;statusValue=result;D_8002AC5C=flag;
 for(i=0;i<32;i++)wanted.bytes[i]=nativeRecord.bytes[i]=(u8)(i*13+0x59);
 for(i=0;i<28;i++) {
  u8 b=pattern==0?0:pattern==1?255:pattern==2?128:(u8)(i*17+0x71);
  if(i==position)b=(u8)value;
  source[i]=b;D_800E0BE0[i]=(s8)b;wanted.bytes[2+i]=b;
  sum+=(u32)b*(i%4==0?4:i%4==1?8:i%4==2?1:2);
 }
 wanted.checksum=(u16)sum;submitted=wanted;
 func_15007558();
 if(failed||calls!=(flag==0))return 1;
 if(flag==0) {
  for(i=0;i<32;i++)if(observed[i]!=submitted.bytes[i])return 1;
  if(effects&1)flag=255;
  if(effects&2)for(i=0;i<32;i++)wanted.bytes[i]=(u8)(i*23+0x71);
  if(effects&4)for(i=0;i<28;i++)source[i]=(u8)(i*29+0x85);
 }
 if(D_8002AC5C!=flag)return 1;
 for(i=0;i<32;i++)if(nativeRecord.bytes[i]!=wanted.bytes[i])return 1;
 for(i=0;i<28;i++)if((u8)D_800E0BE0[i]!=source[i])return 1;
 return 0;
}
static int run(void) {
 unsigned pattern,position,value,flag,effect,error;
 static const u8 gates[3]={0,1,255};
 static const u32 errors[4]={0,1,0xFFFFFFFFu,0x80000000u};
 for(pattern=0;pattern<4;pattern++)for(position=0;position<28;position++)
  for(value=0;value<256;value++)for(flag=0;flag<3;flag++)
   for(effect=0;effect<2;effect++)for(error=0;error<4;error++)
    if(checkCase(pattern,position,value,gates[flag],effect?7:0,errors[error]))return 1;
 return 0;
}
'''
def native_suite():
 selected=source.HEADERS+source.SELECTED;at=selected.index('/* Copy the settings')
 headers,body=selected[:at],selected[at:]
 controls={
  'copy-only27':body.replace('(u32)D_800E0BFC','((u32)D_800E0BFC - 1)'),
  'destination-off-by-one':body.replace('D_800BE358 + 2','D_800BE358 + 1'),
  'wrong-checksum-seed':body.replace('checksum = 0xCC','checksum = 0xCD'),
  'signed-checksum-byte':body.replace('checksum += *record++','checksum += ((u32)(s32)(s8)*record++)'),
  'wrong-shift-phase':body.replace('(index++ & 3)','((index++ - 1) & 3)'),
  'wrong-request-length':body.replace('D_800BE358, 32','D_800BE358, 31'),
  'inverted-gate':body.replace('D_8002AC5C == 0','D_8002AC5C != 0'),
  'clobber-tail-padding':body.replace('    if (D_8002AC5C','    D_800BE358[30] = D_800BE358[31] = 0;\n    if (D_8002AC5C'),
 }
 assert all(text!=body for text in controls.values());results=[]
 jobs=[('positive-'+opt,opt,body,False)for opt in('-O0','-O2','-O3')]
 jobs.extend((name,'-O2',text,True)for name,text in controls.items())
 for name,opt,text,control in jobs:
  p=o/('native-'+name);p.with_suffix('.c').write_text(headers+PREAMBLE+text+HARNESS+START)
  q=subprocess.run(native_command(opt)+['-Wno-unused-but-set-variable','-o',str(p),str(p.with_suffix('.c'))],capture_output=True,text=True)
  assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True)
  assert q.returncode==(1 if control else 0),(name,q.returncode,q.stderr)
  results.append(dict(name=name,optimization=opt,control=control,exit=q.returncode))
 return dict(positive_cases_each=688128,profiles=['O0','O2','O3'],effective_controls=8,controls_exit_by_semantic_mismatch=True,
             UBSan_trapping=True,all28_payload_positions_each256_byte_values=True,backgrounds=4,gate_values=3,
             return_patterns=4,callback_mutations=True,record_storage_union_backed=True,
             interior_and_one_past_labels=True,tail_padding_preserved=True,host_byte_order_not_guest_serialization=True,
             EEPROM_hardware_claim=False,results=results)

def dependency_native_suite():
 from unittest.mock import patch
 from tools.tests import game_save_slot_erase_oracle as previous
 before=(r/source.BUILD/'before-conker_src_game_33990.c').read_text()
 if previous.source.SELECTED.strip()not in before or previous.source.SELECTED.strip()not in source.recovered_owner(before):raise ValueError('Prior erase body changed')
 folder=o/'affected-erase-native';folder.mkdir(exist_ok=True)
 preamble=previous.PREAMBLE.replace('u8 D_800BE358[8];','u8 D_800BE358[32];')
 if preamble==previous.PREAMBLE:raise ValueError('Prior erase backing extent changed')
 with source.candidate_header(r,r/source.BUILD),patch.object(previous,'o',folder),patch.object(previous,'PREAMBLE',preamble):
  result=previous.native_suite()
 return dict(result,storage_bytes=32,prior_erase_body_identical=True,header_change_freshly_qualified=True)
