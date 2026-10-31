"""Save-slot erase qualification; helper calls are bounded contracts."""
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

from tools.experiments import game_save_slot_erase_match as source
r=Path.cwd();o=r/source.BUILD
F,OWNER,ENTRY,ROM='func_1500707C','game_33990',0x1500707C,0x3452C
SYMS=dict(D_800BE358=0x800BE358,D_800BE3D8=0x800BE3D8,
          D_8002AC5C=0x8002AC5C,D_800BE900=0x800BE900,
          osWritebackDCacheAll=0x10024F10,func_151DD4E0=0x151DD4E0)

@dataclass(frozen=True)
class Case:
 key:int=-1
 mask:int=15
 flag:int=0
 mode:int=0
 phase:int=0
 error:int=0

def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base,size in((s['D_800BE358']-16,40),(s['D_800BE3D8']-16,40),
                  (s['D_8002AC5C']-4,12),(s['D_800BE900']-16,48)):
  m.update({base+i:(i*13+0x59)&255 for i in range(size)})
 for i in range(4):put(m,s['D_800BE3D8']+i,(c.key if c.mask>>i&1 else c.key+1)&255,1)
 put(m,s['D_8002AC5C'],c.flag,1)
 return m

def effects(m,c,s,number):
 # number 0 is the cache flush; positive numbers are EEPROM submissions.
 if number==0:
  if c.mode&1:put(m,s['D_8002AC5C'],0 if c.flag else 1,1)
  if c.mode&2:
   for i in range(4):put(m,s['D_800BE3D8']+i,(c.key+i)&255,1)
 else:
  if c.mode&4 and number==1:
   for i in range(1,4):put(m,s['D_800BE3D8']+i,c.key&255,1)
  if c.mode&8:
   put(m,s['D_8002AC5C'],255,1)
   for i in range(8):put(m,s['D_800BE358']+i,(number*19+i)&255,1)

def signed_byte(v):return v if v<128 else v-256
def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+128}
def public_trace(t):return [x for x in t if not STACK-512<=x[1]<STACK+128]
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];observations=[]
 for i in range(8):put(m,s['D_800BE358']+i,255,1)
 def call(target,args,number):
  calls.append((target,args))
  observations.append(tuple(read(m,s['D_800BE358']+i,1)for i in range(8)))
  effects(m,c,s,number)
 call(s['osWritebackDCacheAll'],(),0)
 if read(m,s['D_8002AC5C'],1)==0:
  number=0
  for slot in range(4):
   if (signed_byte(read(m,s['D_800BE3D8']+slot,1))&0xFFFFFFFF)==(c.key&0xFFFFFFFF):
    for block in(slot*16+4,slot*16+5):
     number+=1;call(s['func_151DD4E0'],(s['D_800BE900'],block,s['D_800BE358']),number)
 return m,calls,observations

class Oracle(RenderOracle):
 def __init__(self,w,m,c=Case(),entry=ENTRY,s=SYMS,fault=None,connected=None):
  self.c,self.s,self.trace,self.write_count=c,s,[],0
  super().__init__(w,m,phase=c.phase,entry=entry,arguments=(c.key&0xFFFFFFFF,),
                   connected=connected,fault=fault)
  self.hi=self.lo=0
 def execute(self,word):
  if word>>26==32:
   self.own_instruction=True
   try:
    rs,rt=word>>21&31,word>>16&31;imm=word&65535
    if imm&32768:imm-=65536
    value=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
    self.r[rt]=signed_byte(value)&0xFFFFFFFF;self.r[0]=0
   finally:self.own_instruction=False
  else:super().execute(word)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,target):
  assert target in(self.s['osWritebackDCacheAll'],self.s['func_151DD4E0']),hex(target)
  args=()if target==self.s['osWritebackDCacheAll']else tuple(self.r[4:7])
  self.calls.append((target,args));self.events.append(('CALL',target,args))
  self.observations.append(tuple(read(self.memory,self.s['D_800BE358']+i,1)for i in range(8)))
 def hook(self,target):
  if target==self.s['func_151DD4E0']:self.write_count+=1
  number=self.write_count if target==self.s['func_151DD4E0']else 0
  effects(self.memory,self.c,self.s,number)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=(self.c.error+number*0x10001)&0xFFFFFFFF
  self.hi,self.lo=0xA5000010,0xA5000011

def normalized(raw,bindings):
 assert len(raw)==228 and hashlib.sha256(raw).hexdigest()=='3f6f480b148c0303afdac7b8243f36fa47048a1517a197be3294489891be1699'
 rows={int(row['offset'],0):row for row in json.loads((o/'new-guard-rows.json').read_text())}
 out=[];rs={}
 fmt=lambda b:';'.join(k+':'+n for k,n in b)if b else '-'
 for i,word in enumerate(struct.unpack('>57I',raw)):
  at=4*i;row=rows.get(at);rel=bindings.get(at,[])
  if row:
   assert word==int(row['expected'],0)and row['expected_relocations']==fmt(rel)
   if row['omit']=='true':assert not rel;continue
   word=int(row['replacement'],0)
   assert row['replacement_relocations']==fmt(rel)
  if rel:rs[len(out)*4]=rel
  out.append(word)
  if row and row['insert_after']:out.append(int(row['insert_after'],0))
 result=struct.pack('>59I',*out)
 assert hashlib.sha256(result).hexdigest()=='047ff116ddd5b4f0f59de2657b4c4d4becd5ff87ac154de8410627769b88d824'
 return result,rs

def linked(obj,label,entry=ENTRY,s=SYMS,normalize=False):
 text,fs,rs=parse_object(obj);info=fs[F]
 if normalize:
  start,size=info['value'],info['size']
  raw=text[start:start+size];rel={at-start:v for at,v in rs.items()if start<=at<start+size}
  text,rs=normalized(raw,rel);info=dict(info,value=0,size=len(text))
 asm,unknown=emit_function(text,info,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm)
 p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 size=info['size'];return list(struct.unpack('>%dI'%(size//4),sections(p.with_suffix('.elf'))['.text'][1][:size]))

def images(label,entry=ENTRY,s=SYMS):
 names=('original-func_1500707C.o','selected-final.o','qualified-padded.o','make-shadow/src/game_33990.c.o')
 roots=[linked(o/n,label+'-'+str(i),entry,s,i==1)for i,n in enumerate(names)]
 assert all(w==roots[0]for w in roots)
 return roots,linked(o/'selected-final.o',label+'-raw',entry,s)

def compare(images,c,s=SYMS,entry=ENTRY):
 words,raw=images;initial=fixture(c,s);want,calls,observations=reference(initial,c,s)
 models=[Oracle(w,initial,c,entry,s).run()for w in words]
 for m in models:
  assert public(m.memory)==public(want),(c,'public state')
  assert m.calls==calls and m.observations==observations,(c,'ordered submissions',m.calls,calls)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
 plain=Oracle(raw,initial,c,entry,s).run()
 assert public(plain.memory)==public(want)and plain.calls==calls and plain.observations==observations,(c,'raw C semantics')
 assert public_trace(plain.trace)==public_trace(models[0].trace),(c,'raw public access order')
 for reg in(*range(16,24),28,29,30,31):assert plain.r[reg]==models[0].r[reg],(c,'callee register',reg)
 return models[0]

def guest_suite():
 count=cuts=delays=aliases=0;seen=set()
 for j,entry in enumerate((ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if not j else dict(zip(SYMS,(0x81007FFC+j*65536,0x82008000+j*65536,0x8300FFFC+j*65536,0x84008004+j*65536,entry+0x10000,entry+0x20000)))
  roots=images('erase-rebase-'+str(j),entry,s)
  for key,mask,flag,mode,phase in itertools.product((-128,-1,0,1,127,128,255,0x80000000),range(16),(0,1,255),(0,1,6,12),(0,8)):
   c=Case(key,mask,flag,mode,phase,(key*0x1010101)&0xFFFFFFFF)
   m=compare(roots,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if j==0:
   for buffer,flag in((SYMS['D_800BE3D8'],SYMS['D_8002AC5C']),(SYMS['D_800BE358'],SYMS['D_800BE358']+3)):
    alias=dict(s,D_800BE358=buffer,D_8002AC5C=flag)
    root=images('erase-alias-'+str(aliases),s=alias)
    for key,mode in itertools.product((-1,0,127),(0,1,6,12)):
     compare(root,Case(key,15,0,mode),alias);aliases+=1
   for c in(Case(),Case(flag=1),Case(key=127,mask=1,mode=12),Case(key=-128,mask=15,phase=8)):
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
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
 return dict(cases=count,normalized_executions=count*4,raw_C_executions=count,retail_words=59,reachable_words=59,independent_rebases=3,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,all_registers_and_stack_equal_after_normalization=True,raw_public_state_calls_and_access_order_equal=True,raw_stack_spill_layout_difference=True,void_return_not_compared_as_C_value=True,callee_argument_homes_clobbered=True,write_errors_ignored=True,helper_or_physical_EEPROM_claim=False)

def caller_suite():
 from tools.tests.game_actor_phase_motion_oracle import WindowStop,WindowCode
 rom=(o/'before-conker_conker.us.bin').read_bytes();target=0x0C000000|((ENTRY>>2)&0x3FFFFFF)
 sites=[];pointers=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==target:sites.append(4*i)
  if w==ENTRY:pointers.append(4*i)
 assert sites==[0x49B54]and pointers==[],(sites,pointers)
 start,stop,after=0x1501C6A0,0x1501C6EC,0x1501C6AC
 window=list(struct.unpack_from('>5I',rom,start-(ENTRY-ROM)))
 class Caller(Oracle):
  def record_call(self,t):
   if t==ENTRY:
    self.calls.append((t,(self.r[4],)));self.events.append(('CALL',t,(self.r[4],)))
   else:super().record_call(t)
 roots,raw=images('erase-caller');count=0
 for key,mask,flag,mode,phase in itertools.product((0,1,7,63,127,128,250,255),(0,1,15),(0,1),(0,12),(0,8)):
  c=Case(signed_byte(key),mask,flag,mode,phase,0xFFFEFFFF)
  initial=fixture(c);put(initial,0x800BE3EC,key,1);want,calls,observations=reference(initial,c)
  calls=[(ENTRY,(c.key&0xFFFFFFFF,)),*calls];models=[]
  for body,poison in itertools.product(roots,(0,0xFFFFFFFF,0x7FFFFFFF,0x12345678)):
   m=Caller(window,initial,c,start,connected={ENTRY+4*i:w for i,w in enumerate(body)})
   m.stop_pc,m.poison_pc,m.poison_value=stop,after,poison
   m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowStop:pass
   else:raise AssertionError('Missing caller window stop')
   assert public(m.memory)==public(want)and m.calls==calls and m.observations==observations
   assert m.r[29]==STACK+phase and m.r[2]==poison
   models.append(m)
  # With V0 poisoned at the unused-return branch, all architectural state
  # including the complete saved frame must agree across normalized images.
  for i in range(4):
   for j in range(1,4):assert complete(models[i])==complete(models[4*j+i])
  m=Caller(window,initial,c,start,connected={ENTRY+4*i:w for i,w in enumerate(raw)})
  m.stop_pc,m.poison_pc,m.poison_value=stop,after,0xDEADBEEF;m.code=WindowCode(dict(m.code),m)
  try:m.run()
  except WindowStop:pass
  else:raise AssertionError('Missing raw caller window stop')
  assert public(m.memory)==public(want)and m.calls==calls and m.observations==observations
  assert m.r[29]==STACK+phase and m.r[2]==0xDEADBEEF
  count+=1
 return dict(cases=count,normalized_executions=count*16,raw_executions=count,
             original_window_words=5,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,
             return_poison_values=4,ignored_return_proven=True,signed_delay_slot_argument=True,
             full_parent_or_hardware_claim=False)


from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
PREAMBLE=r'''
u8 D_800BE358[8];
MenuResetSentinels D_800BE3D8;
u8 D_8002AC5C;
OSMesgQueue D_800BE900;
typedef struct {u8 data[8]; s8 slots[4]; u8 flag;} State;
typedef struct {u32 target,queue,block,buffer; u8 data[8];} Call;
static Call actual[9],expected[9];
static unsigned count,writes,wantCount;
static s32 keyValue;
static u32 errorValue;
static unsigned effectMode;
static int failed;

static void capture(State *s) {
 unsigned i;
 for(i=0;i<8;i++)s->data[i]=D_800BE358[i];
 for(i=0;i<4;i++)s->slots[i]=((s8 *)&D_800BE3D8)[i];
 s->flag=D_8002AC5C;
}
static void install(State *s) {
 unsigned i;
 for(i=0;i<8;i++)D_800BE358[i]=s->data[i];
 for(i=0;i<4;i++)((s8 *)&D_800BE3D8)[i]=s->slots[i];
 D_8002AC5C=s->flag;
}
static void mutation(State *s,unsigned number,u8 initialFlag) {
 unsigned i;
 if(number==0) {
  if(effectMode&1)s->flag=initialFlag?0:1;
  if(effectMode&2)for(i=0;i<4;i++)s->slots[i]=(s8)((u32)keyValue+i);
 } else {
  if((effectMode&4)&&number==1)for(i=1;i<4;i++)s->slots[i]=(s8)keyValue;
  if(effectMode&8) {
   s->flag=255;
   for(i=0;i<8;i++)s->data[i]=(u8)(number*19+i);
  }
 }
}
static void logCall(Call *call,State *s,unsigned target,unsigned block) {
 unsigned i;
 call->target=target;call->queue=(u32)&D_800BE900;
 call->block=block;call->buffer=(u32)D_800BE358;
 for(i=0;i<8;i++)call->data[i]=s->data[i];
}
void osWritebackDCacheAll(void) {
 State s;capture(&s);
 if(count>=9){failed=1;return;}
 logCall(&actual[count++],&s,0,0);
 mutation(&s,0,s.flag);install(&s);
}
s32 func_151DD4E0(OSMesgQueue *queue,u8 block,u8 *buffer) {
 State s;capture(&s);
 if(queue!=&D_800BE900||buffer!=D_800BE358||count>=9){failed=1;return -1;}
 logCall(&actual[count++],&s,1,block);
 ++writes;mutation(&s,writes,0);install(&s);
 return (s32)(errorValue+writes*0x10001u);
}
'''

HARNESS=r'''
static void model(State *s) {
 unsigned i,n=0,b;
 for(i=0;i<8;i++)s->data[i]=255;
 logCall(&expected[wantCount++],s,0,0);
 mutation(s,0,s->flag);
 if(s->flag)return;
 for(i=0;i<4;i++) {
  if((s32)s->slots[i]!=keyValue)continue;
  for(b=4;b<=5;b++) {
   logCall(&expected[wantCount++],s,1,i*16+b);
   mutation(s,++n,0);
  }
 }
}
static int checkCase(s32 key,unsigned mask,u8 flag,unsigned mode,u32 error) {
 unsigned i,j;State want,got;
 keyValue=key;effectMode=mode;errorValue=error;count=writes=wantCount=0;failed=0;
 for(i=0;i<8;i++)want.data[i]=(u8)(i*17+0x59);
 for(i=0;i<4;i++)want.slots[i]=(s8)((u32)key+((mask>>i&1)?0:1));
 want.flag=flag;install(&want);model(&want);
 func_1500707C(key);capture(&got);
 if(failed||count!=wantCount)return 1;
 for(i=0;i<8;i++)if(got.data[i]!=want.data[i])return 1;
 for(i=0;i<4;i++)if(got.slots[i]!=want.slots[i])return 1;
 if(got.flag!=want.flag)return 1;
 for(i=0;i<count;i++) {
  if(actual[i].target!=expected[i].target||actual[i].block!=expected[i].block||
     actual[i].queue!=expected[i].queue||actual[i].buffer!=expected[i].buffer)return 1;
  for(j=0;j<8;j++)if(actual[i].data[j]!=expected[i].data[j])return 1;
 }
 return 0;
}
static int run(void) {
 unsigned raw,wide,mask,flag,mode,error;
 static const u8 flags[3]={0,1,255};
 static const unsigned modes[6]={0,1,2,4,8,12};
 static const u32 errors[4]={0,0xFFFFFFFFu,0xFFFEFFFFu,0x80000000u};
 static const s32 extra[4]={(s32)0x80000000u,0x7FFFFFFF,256,-129};
 for(raw=0;raw<256;raw++)for(wide=0;wide<2;wide++)
  for(mask=0;mask<16;mask++)for(flag=0;flag<3;flag++)
   for(mode=0;mode<6;mode++)for(error=0;error<4;error++) {
    s32 key=wide?(s32)raw:(s32)(s8)raw;
    if(checkCase(key,mask,flags[flag],modes[mode],errors[error]))return 1;
   }
 for(raw=0;raw<4;raw++)for(mask=0;mask<16;mask++)for(flag=0;flag<3;flag++)
  for(mode=0;mode<6;mode++)for(error=0;error<4;error++)
   if(checkCase(extra[raw],mask,flags[flag],modes[mode],errors[error]))return 1;
 return 0;
}
'''

def native_suite():
 selected=source.HEADERS+source.SELECTED
 at=selected.index('/* Erase both');headers,body=selected[:at],selected[at:]
 controls={
  'unsigned-slot-id':body.replace('slot == *entry','slot == (u8)*entry'),
  'only-seven-fill-bytes':body.replace('i < 8','i < 7'),
  'skip-cache-flush':body.replace('    osWritebackDCacheAll();',''),
  'inverted-storage-gate':body.replace('D_8002AC5C == 0','D_8002AC5C != 0'),
  'only-first-three-slots':body.replace('i != 4','i != 3'),
  'wrong-second-block':body.replace('(u8)(block + 1)','(u8)block'),
  'abort-after-first-error':body.replace('                func_151DD4E0','                if (status != 0) return;\n                func_151DD4E0'),
 }
 assert all(s!=body for s in controls.values())
 results=[]
 jobs=[('positive-'+opt,opt,body,False)for opt in('-O0','-O2','-O3')]
 jobs.extend((name,'-O2',s,True)for name,s in controls.items())
 for name,opt,s,control in jobs:
  p=o/('native-'+name);p.with_suffix('.c').write_text(headers+PREAMBLE+s+HARNESS+START)
  command=native_command(opt)+['-Wno-unused-but-set-variable','-o',str(p),str(p.with_suffix('.c'))]
  q=subprocess.run(command,capture_output=True,text=True);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==(1 if control else 0),(name,q.returncode,q.stderr)
  results.append(dict(name=name,optimization=opt,control=control,exit=q.returncode))
 return dict(positive_cases_each=594432,profiles=['O0','O2','O3'],effective_controls=len(controls),
             controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,
             all256_signed_and_unsigned_slot_ID_forms=True,all16_slot_match_masks=True,
             callback_mutations=True,all_write_statuses_ignored=True,
             physical_EEPROM_or_SI_protocol_claim=False,results=results)
