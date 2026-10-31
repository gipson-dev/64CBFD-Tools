"""EEPROM request entry: captured arguments, clock aliases and unsigned SDK64 ABI.

Integer, timer and polling services are bounded providers. Native C uses disjoint
typed globals; deliberately aliased linker symbols are guest-machine extensions.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess,csv,io
from tools.experiments import game_eeprom_request_timer_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
SYMS=dict(func_151DCFD8=0x151DCFD8,__ll_mul=0x10026968,__ull_div=0x10026868,osSetTimer=0x10024A40,D_800E0A20=0x800E0A20,D_800E0A24=0x800E0A24,D_800E0A28=0x800E0A28,D_800E0A2C=0x800E0A2C,D_8002BD10=0x8002BD10,D_8002BD14=0x8002BD14,D_80042A58=0x80042A58,__osEepromTimerQ=0x80042A78,D_80042A90=0x80042A90)
u32=lambda n:n&0xFFFFFFFF
u64=lambda n:n&0xFFFFFFFFFFFFFFFF
CLOCKS=(0,1,83,84,1000000,0xFFFFFFFF,0x100000000,0x7FFFFFFFFFFFFFFF,0x8000000000000000,0xFFFFFFFFFFFFFFFF)
@dataclass(frozen=True)
class Case:
 clock:int=0x3B9AC9FF
 polls:int=0
 mode:int=0
 address:int=0xA5B60044
 length:int=112
 queue:int=0x30000
 buffer:int=0x40000
 result:int=0x89ABCDEF
 phase:int=0
 alias:int=0
def symbols(c,s=SYMS):
 s=dict(s)
 if c.alias:
  s['D_8002BD10']=s['D_800E0A20']if c.alias==1 else s['D_800E0A28']
  s['D_8002BD14']=s['D_8002BD10']+4
 return s
def fixture(c,s=SYMS):
 s=symbols(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,512)}
 for name,n in(('D_800E0A20',24),('D_8002BD10',8),('D_80042A58',64),('__osEepromTimerQ',24),('D_80042A90',4)):
  m.update({s[name]+i:(i*13+0xA5)&255 for i in range(-8,n+8)})
 put(m,s['D_8002BD10'],c.clock,8);return m
def public(m):return {a:v for a,v in m.items()if not STACK-2048<=a<STACK+512}
def observation(m,s):return tuple(read(m,s[n],1 if n=='D_800E0A24'else 4)for n in('D_800E0A20','D_800E0A24','D_800E0A28','D_800E0A2C'))+(read(m,s['D_8002BD10'],8),)
def effect(m,c,s,kind):
 if kind=='poll'and c.mode&1:
  put(m,s['D_8002BD10'],u64(read(m,s['D_8002BD10'],8)^0x102030405060708),8);put(m,s['D_800E0A20'],0x76543210)
 if kind=='mul'and c.mode&2:put(m,s['D_800E0A2C'],0x87654321)
 if kind=='timer'and c.mode&2:
  put(m,s['D_8002BD10'],0xFEDCBA9876543210,8);put(m,s['D_800E0A28'],0x76543210)
def reference(c,s=SYMS,initial=None):
 s=symbols(c,s);m=fixture(c,s)if initial is None else dict(initial);calls=[];obs=[]
 for i in range(c.polls+1):calls.append((s['func_151DCFD8'],(1,)));effect(m,c,s,'poll')
 put(m,s['D_800E0A20'],c.queue);put(m,s['D_800E0A24'],c.address&255,1);put(m,s['D_800E0A28'],c.buffer)
 # The emitted root captures both clock words before its length store in the
 # multiply call delay slot. Aliased linker fixtures retain that exact order.
 clock=read(m,s['D_8002BD10'],8);put(m,s['D_800E0A2C'],u32(c.length));obs.append(observation(m,s))
 calls.append((s['__ll_mul'],(0,12000,clock>>32,clock&0xFFFFFFFF)));product=u64(12000*clock);effect(m,c,s,'mul')
 calls.append((s['__ull_div'],(product>>32,product&0xFFFFFFFF,0,1000000)));deadline=product//1000000
 args=(s['D_80042A58'],deadline>>32,deadline&0xFFFFFFFF,0,0,s['__osEepromTimerQ'],s['D_80042A90']);calls.append((s['osSetTimer'],args));obs.append(observation(m,s));effect(m,c,s,'timer')
 return m,calls,obs
def linked(obj,label,entry=ENTRY,s=SYMS,pair_isolated=False):
 source.validate_alias(s);text,fs,rs=parse_object(obj);f=fs[F]
 if pair_isolated:
  source.checked_payload(*source.payload(obj));s=dict(s,D_8002BD10_high_pair=s['D_8002BD10']);rs={k:list(v)for k,v in rs.items()}
  for at,kind in((100,'R_MIPS_HI16'),(112,'R_MIPS_LO16')):
   key=f['value']+at;assert rs[key]==[(kind,'D_8002BD10')];rs[key]=[(kind,'D_8002BD10_high_pair')]
  assert struct.unpack_from('>I',text,f['value']+100)[0]==0x3C060000 and struct.unpack_from('>I',text,f['value']+112)[0]==0x8CC60000
 asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.c=c;self.syms=symbols(c,s);self.cut=None;self.accesses=0;self.trace=[];self.poll_count=0;self.observations=[]
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.queue,u32(c.address),c.buffer,u32(c.length)),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:]
 def execute(self,w):
  if w>>26==0 and w&63==4:
   rs,rt,rd=w>>21&31,w>>16&31,w>>11&31;self.r[rd]=u32(self.r[rt]<<(self.r[rs]&31));self.r[0]=0
  else:super().execute(w)
 def access(self):
  if self.own_instruction:
   if self.accesses==self.cut:raise faults.AccessBoundary
   self.accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  s=self.syms;counts={s['func_151DCFD8']:1,s['__ll_mul']:4,s['__ull_div']:4,s['osSetTimer']:8,ENTRY:4}
  assert t in counts,('unbounded-call',hex(t));a=tuple(map(u32,self.arguments(counts[t])))
  if t==s['osSetTimer']:a=(a[0],*a[2:])
  self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in(s['__ll_mul'],s['osSetTimer']):self.observations.append(observation(self.memory,s))
 def hook(self,t):
  c,s=self.c,self.syms;a=self.calls[-1][1];high=None
  if t==s['func_151DCFD8']:
   assert a==(1,),('poll-mode',a);self.poll_count+=1;assert self.poll_count<256,'Unexpected nonterminating mutation';v=(1,0x80000000,7)[(self.poll_count-1)%3]if self.poll_count<=c.polls else 0;effect(self.memory,c,s,'poll')
  elif t in(s['__ll_mul'],s['__ull_div']):
   left=(a[0]<<32)|a[1];right=(a[2]<<32)|a[3];v=u64(left*right)if t==s['__ll_mul']else left//right;high=v>>32;v&=0xFFFFFFFF
   if t==s['__ll_mul']:effect(self.memory,c,s,'mul')
  else:assert t==s['osSetTimer'];v=u32(c.result);effect(self.memory,c,s,'timer')
  for i in range(4):self.put(self.r[29]+i*4,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=high if high is not None else v
  if high is not None:self.r[3]=v
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.observations
def check(m,c,s=SYMS):
 want,calls,obs=reference(c,s)
 assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),('public-or-ABI',c)
 assert m.r[2]==u32(c.result),('result',m.r[2],c.result)
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f,('saved-registers',c)
def corpus():
 for clock,polls,mode,address,length in itertools.product(CLOCKS,(0,1,3,7),range(4),(0,0xA5B600FF),(0,112,-1)):
  yield Case(clock,polls,mode,address,length,result=u32(clock),phase=8*(polls&1))
 for byte in range(256):yield Case(address=byte|0x89ABCD00,length=(0x80000000,0x7FFFFFFF)[byte&1],polls=byte%4,clock=u64(byte*0x1020304050607),queue=0 if byte&1 else 0x80000000,buffer=u32(byte*0x1020304),mode=byte%4)
 for alias,clock,polls,mode in itertools.product((1,2),CLOCKS,(0,3),(0,3)):yield Case(clock,polls,mode,alias=alias)
def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();n=0
 alias_images={a:[linked(p,'alias-%d-%d'%(a,j),s=symbols(Case(alias=a)))for j,p in enumerate(objects)]for a in(1,2)}
 for c in corpus():
  images=ws if not c.alias else alias_images[c.alias]
  ms=[Oracle(w,fixture(c),c).run()for w in images]
  for m in ms:check(m,c)
  assert state(ms[0])==state(ms[2]),c;visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));n+=1
 assert len(visits)==58
 cuts=delays=0
 for c in(Case(),Case(polls=3,mode=3,address=0xFFFFFFFF),Case(alias=2,mode=3)):
  ss=symbols(c);bw=[linked(p,'fault-%d-%d'%(c.alias,j),s=ss)for j,p in enumerate(objects)];baseline=Oracle(bw[0],fixture(c),c).run()
  for cut in range(baseline.accesses):
   ms=[Oracle(w,fixture(c),c)for w in(bw[0],bw[2])]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective fault cutoff')
   assert state(ms[0])==state(ms[1]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=negative=0
 for i,clock in enumerate((0x60007FFC,0x6000FFF8,0x60018000)):
  entry=0x17007FFC+i*0x10000;s=dict(SYMS,D_8002BD10=clock,D_8002BD14=clock+4);s.update({n:entry+0x20000+j*0x10000 for j,n in enumerate(('func_151DCFD8','__ll_mul','__ull_div','osSetTimer'))})
  literal=linked(objects[1],'literal-raw-'+str(i),entry,s)
  if i==0:
   effective=((literal[25]&65535)<<16)+((literal[28]&65535)^32768)-32768;assert effective==clock+0x10000;negative+=1
  bw=[linked(p,'rebase-%d-%d'%(i,j),entry,s,pair_isolated=j==1)for j,p in enumerate(objects)]
  for c in(Case(clock=0xFFFFFFFFFFFFFFFF),Case(polls=3,mode=3),Case(address=0x80000000)):
   ms=[Oracle(w,fixture(c,s),c,entry,s).run()for w in bw]
   for m in ms:check(m,c,s)
   assert state(ms[0])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,raw_GNU_carry_negative_controls=negative,raw_rebase_high_pair_isolated=True,raw_instruction_words_unchanged=True,original_normalized_literal_bindings=True,original_normalized_full_state_trace_fault_context_equal=True,raw_public_memory_calls_and_result_equal=True,raw_fault_schedule_equated=False,clock_global_aliases_guest_only=True,bounded_integer_poll_and_timer_providers=True)
def guard_suite():
 raw,rs=source.payload(o/'selected-final.o');assert source.normalized_payload(raw,rs)==source.payload(o/('original-'+F+'.o'));before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();fields=csv.DictReader(io.StringIO(before.decode())).fieldnames;n=0
 for i,row in enumerate(source.NEW_GUARDS):
  for kind in('expected','expected_relocations'):
   rows=[dict(x)for x in source.NEW_GUARDS];rows[i][kind]='0x%08X'%(int(row['expected'],0)^1)if kind=='expected'else'R_MIPS_26:foreign';buf=io.StringIO(newline='');csv.DictWriter(buf,fields,lineterminator='\n').writerows(rows);p=o/('guard-%d-%s.csv'%(i,kind));p.write_bytes(before+buf.getvalue().encode())
   try:source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=p)
   except ValueError:n+=1
   else:raise AssertionError('Ineffective actual padder guard control')
 for delta in(0,8):
  try:source.validate_alias(dict(SYMS,D_8002BD14=SYMS['D_8002BD10']+delta))
  except ValueError:pass
  else:raise AssertionError('Ineffective alias validation')
 for hi,byte in itertools.product((0,1,0x7FFFFF,0xFFFFFF),range(256)):
  word=(hi<<8)|byte;assert(word&255)==int.from_bytes(word.to_bytes(4,'big')[3:4],'big')
 words=struct.unpack('>58I',raw);assert words[15]==0x8FAF002C and words[20]==0xA02F0000 and all((w>>21&31)!=15 and not(w>>26 not in(0,2,3,4,5,15)and(w>>16&31)==15)for w in words[16:20])
 return dict(guards=3,insertions=0,omissions=0,actual_padder_rejections=n,invalid_alias_controls=2,alias_addend=4,byte_home_identity_cases=1024,load_low_byte_used_only_by_store_before_provider_clobber=True,one_width_word_and_one_alias_immediate_changed=True)
def controls(body):
 edits={'single-poll':('while (func_151DCFD8','if (func_151DCFD8'),'poll-mode':('func_151DCFD8(1)','func_151DCFD8(0)'),'queue':('D_800E0A20 = queue','D_800E0A20 = NULL'),'address':('(u8)address','(u8)((u32)address + 1u)'),'buffer':('D_800E0A28 = buffer','D_800E0A28 = NULL'),'length':('D_800E0A2C = length','D_800E0A2C = 0'),'period':('12000ULL','12001ULL'),'divisor':('1000000ULL','100000ULL'),'narrow-clock':('12000ULL * D_8002BD10','12000ULL * (u32)D_8002BD10'),'interval':('0, &__osEepromTimerQ','1, &__osEepromTimerQ'),'message':('&D_80042A90);','NULL);')}
 out={}
 for name,(a,b)in edits.items():assert body.count(a)==1,(name,a);out[name]=body.replace(a,b,1)
 out['result']=body.replace('return osSetTimer(','return (osSetTimer(').replace('&D_80042A90);','&D_80042A90), 0);');return out
def compiled_controls():
 result={};cases=(Case(clock=0x123456789ABCDEF0,polls=3,mode=3),Case(clock=0x123456789ABCDEF0,length=-1,address=0xFFFFFFFF),Case())
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag;w=linked(obj,'IDO-linked-'+name,entry=0x17001000)
  for c in cases:
   try:m=Oracle(w,fixture(c),c,entry=0x17001000).run();check(m,c)
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]in('public-or-ABI','result','poll-mode'),(name,e);result[name]='semantic/ABI disagreement';break
  else:raise AssertionError('Ineffective compiled control '+name)
 return dict(successful_IDO_compiles=len(result),effective_semantic_controls=result,compiler_or_interpreter_failures_counted=False)

def caller_suite():
 from tools.tests import game_save_checksum_submit_oracle as save
 rom=source.snapshot(o)['conker/conker.us.bin'];parent=list(struct.unpack_from('>56I',rom,0x34810));before=(o/'before-conker_build_conker.us.elf').read_bytes();at=source.elf_slot_offset(before,save.ENTRY,224);assert before[at:at+224]==struct.pack('>56I',*parent)
 jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')];assert calls==[0x344F0,0x348D4,0x34AD8]and not pointers
 text=(r/'conker/src/game_33990.c').read_text();assert 's32 func_151DCEF0(OSMesgQueue *, s32, void *, s32);'in text and 'result = func_151DCEF0(&D_800BE900, 0x44, &D_800BE2F0, 0x70);'in text
 images=[linked(p,'caller-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];n=0;seen=set()
 for clock,polls,result,phase,flag in itertools.product(CLOCKS,(0,3),(0,0xFFFFFFFF),(0,8),(0,1)):
  c=Case(clock,polls,3,68,112,save.SYMS['D_800BE900'],save.SYMS['D_800BE2F0'],result,phase);sc=save.Case(pattern=3,flag=flag,phase=phase);initial=fixture(c);initial.update(save.fixture(sc));want,_,_=save.reference(initial,sc);expected_calls=[]
  if not flag:
   want,more,_=reference(c,initial=want);expected_calls=[(ENTRY,(c.queue,68,c.buffer,112))]+more
  ms=[]
  for w in images:
   conn=dict(zip(range(ENTRY,ENTRY+232,4),w));m=Oracle(parent,initial,c,save.ENTRY,connected=conn).run();assert(public(m.memory),m.calls)==(public(want),expected_calls),('caller-state',c,flag)
   if not flag:assert read(m.memory,STACK+phase-8)==result,('caller-result-store',)
   ms.append(m)
  assert state(ms[0])==state(ms[2]);seen.update(ms[0].visits&set(range(save.ENTRY,save.ENTRY+224,4)));n+=1
 assert len(seen)==56
 from tools.tests.game_linked_actor_request_oracle import BoundaryCode,WindowBoundary
 windows=((0x15007018,0x344C8,13,0x1500704C,0x4C),(0x15007604,0x34AB4,12,0x15007634,0x18));wn=0
 for which,(entry,offset,words,stop,result_at)in enumerate(windows):
  window=list(struct.unpack_from('>%dI'%words,rom,offset));assert (window[-3]if which==0 else window[-3])>>26==3
  indices=range(256)if which==0 else range(8)
  for index,result,gate,phase in itertools.product(indices,(0,0xFFFFFFFF),(0,1),(0,8)):
   c=Case(CLOCKS[index%10],index%4,3,((index*16+4)&255)if which==0 else 0,128 if which==0 else 32,0x800BE900,0x800BE358,result,phase)
   initial=fixture(c);initial.update(save.fixture(save.Case(flag=gate,phase=phase)));put(initial,STACK+phase+0x44,index)
   want=dict(initial)
   if which==1:put(want,0x800BE358,0xBA98,2)
   expected_calls=[]
   if not gate:want,more,_=reference(c,initial=want);expected_calls=[(ENTRY,(c.queue,c.address,c.buffer,c.length))]+more
   ms=[]
   for w in images:
    conn=dict(zip(range(ENTRY,ENTRY+232,4),w));m=Oracle(window,initial,c,entry,connected=conn);m.r[11]=gate;m.r[13]=0xFEDCBA98;m.window_stop=stop;m.code=BoundaryCode(m.code,m)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not stop at its reviewed boundary')
    assert(public(m.memory),m.calls)==(public(want),expected_calls),('window-state',which,c,gate)
    assert read(m.memory,STACK+phase+result_at)==(result if not gate else read(initial,STACK+phase+result_at)),('window-result-store',which)
    ms.append(m)
   assert state(ms[0])==state(ms[2]);wn+=1
 return dict(original_caller_words=56,caller_words_visited=len(seen),cases=n,additional_window_words=[13,12],additional_window_cases=wn,aligned_ROM_JALs=calls,aligned_literal_pointers=pointers,all_four_arguments_checked=True,signed_result_stored_at_parent_SP24_and_SP76=True,caller_source_and_linked_body_unchanged=True,other_two_parent_bodies_still_placeholders=True,full_other_parents_claimed=False,integer_poll_timer_providers_bounded=True)


def native_harness(body):
 return source.HEADERS+r'''
OSMesgQueue *D_800E0A20;u8 D_800E0A24;u8 *D_800E0A28;s32 D_800E0A2C;u64 D_8002BD10;
OSTimer D_80042A58;OSMesg D_80042A90;OSMesgQueue __osEepromTimerQ;
typedef char PointerBytes[sizeof(void*)==4?1:-1];typedef char ClockBytes[sizeof(u64)==8?1:-1];
typedef struct {OSMesgQueue *queue;u8 address;u8 *buffer;s32 length;u64 clock;} State;
static State expected;static u32 polls,wantPolls,mode,error,timers;static s32 status;static u64 deadline;
static u64 clocks[10]={0,1,83,84,1000000,0xFFFFFFFFULL,0x100000000ULL,0x7FFFFFFFFFFFFFFFULL,0x8000000000000000ULL,0xFFFFFFFFFFFFFFFFULL};
static u64 product(u64 n){u64 out=0;u32 k=12000;while(k){if(k&1)out+=n;n<<=1;k>>=1;}return out;}
static u64 divide(u64 n){u64 q=0;u32 rem=0;int i;for(i=63;i>=0;i--){rem=(rem<<1)|(u32)((n>>i)&1);q<<=1;if(rem>=1000000){rem-=1000000;q|=1;}}return q;}
static int same(void){return D_800E0A20==expected.queue&&D_800E0A24==expected.address&&D_800E0A28==expected.buffer&&D_800E0A2C==expected.length&&D_8002BD10==expected.clock;}
__attribute__((noinline)) s32 func_151DCFD8(s32 request){u32 nonzero;polls++;if(request!=1)error=1;nonzero=polls<=wantPolls;if(mode&1){D_8002BD10^=0x102030405060708ULL;D_800E0A20=(OSMesgQueue*)0x76543210u;}return nonzero?(s32)((polls&1)?0x80000000u:7):0;}
__attribute__((noinline)) int osSetTimer(OSTimer *timer,OSTime value,OSTime interval,OSMesgQueue *queue,OSMesg message){timers++;if(timer!=&D_80042A58||value!=deadline||interval||queue!=&__osEepromTimerQ||message!=&D_80042A90||!same())error=2;if(mode&2){D_8002BD10=0xFEDCBA9876543210ULL;D_800E0A28=(u8*)0x76543210u;}return status;}
'''+body+r'''
static int one(u32 n){u32 i;u8 *p;OSMesgQueue *queue=(n&1)?NULL:&__osEepromTimerQ;void *buffer=(n&2)?(void*)&D_8002BD10:(void*)&D_800E0A2C;s32 address=(s32)((n*0x1020304u&0xFFFFFF00u)|(n&255u));s32 length=(n&4)?(s32)0x80000000u:(s32)(n*0x10203u);s32 result;s32 (*entry)(OSMesgQueue*,s32,void*,s32)=func_151DCEF0;
D_800E0A20=(OSMesgQueue*)0x12345678u;D_800E0A24=0xA5;D_800E0A28=(u8*)0x87654321u;D_800E0A2C=-17;D_8002BD10=clocks[n%10]^((u64)n<<32);p=(u8*)&D_80042A58;for(i=0;i<sizeof(D_80042A58);i++)p[i]=(u8)(i*13+0xA5);p=(u8*)&__osEepromTimerQ;for(i=0;i<sizeof(__osEepromTimerQ);i++)p[i]=(u8)(i*7+0x5A);D_80042A90=(OSMesg)0x87654321u;
expected.queue=D_800E0A20;expected.address=D_800E0A24;expected.buffer=D_800E0A28;expected.length=D_800E0A2C;expected.clock=D_8002BD10;
for(i=0;i<=wantPolls;i++)if(mode&1){expected.clock^=0x102030405060708ULL;expected.queue=(OSMesgQueue*)0x76543210u;}
expected.queue=queue;expected.address=(u8)(u32)address;expected.buffer=buffer;expected.length=length;deadline=divide(product(expected.clock));polls=timers=error=0;status=(s32)(n*0x1020304u+0x80000000u);
result=entry(queue,address,buffer,length);if(error||polls!=wantPolls+1||timers!=1)return 1;if(result!=status)return 2;if(mode&2){expected.clock=0xFEDCBA9876543210ULL;expected.buffer=(u8*)0x76543210u;}if(!same())return 3;
p=(u8*)&D_80042A58;for(i=0;i<sizeof(D_80042A58);i++)if(p[i]!=(u8)(i*13+0xA5))return 4;p=(u8*)&__osEepromTimerQ;for(i=0;i<sizeof(__osEepromTimerQ);i++)if(p[i]!=(u8)(i*7+0x5A))return 4;if(D_80042A90!=(OSMesg)0x87654321u)return 4;return 0;}
static int run(void){u32 n;int result;for(n=0;n<4096;n++)for(wantPolls=0;wantPolls<4;wantPolls++)for(mode=0;mode<4;mode++){result=one(n);if(result)return result;}return 0;}
'''+START

def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');runtime=Path('/lib/i386-linux-gnu/libgcc_s.so.1');assert runtime.is_file();q=subprocess.run([x for x in native_command(opt)if x!='-static']+['-mstackrealign',str(p),str(runtime),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=65536,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in(1,2,3,4),(name,code);effective[name]=code
 return dict(cases_per_profile=65536,profiles=profiles,SDK32_layout=True,existing_shared_libgcc_arithmetic=True,native_abi_not_o32=True,signed_return_checked=True,all_address_low_bytes_and_high_patterns=True,disjoint_typed_globals=True,integer_pointer_values_not_dereferenced=True,independent_shift_add_and_bit_division_reference=True,negative_controls=len(effective),effective_native_controls=effective,unchanged_timer_queue_message_canaries_checked=True)
