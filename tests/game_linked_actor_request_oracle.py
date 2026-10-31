"""Linked actor cleanup scan with original recursive provider and bounded services."""
from pathlib import Path
from dataclasses import dataclass,replace
import csv,io,itertools,json,struct,subprocess
from tools.experiments import game_linked_actor_request_match as source
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
BASE,STRIDE,HELPER=0x800CC2D0,0x32C,0x15060F28
END=BASE+25*STRIDE
SYMS=dict(D_800CC2D0=BASE,D_800D121C=END,func_15060F28=HELPER)
COUNTS={0x1514D310:1,0x151695F0:2,0x15084558:1,0x1504AF10:3,0x1503E260:1,
 0x10004074:1,0x1516972C:1,0x100043B4:2,0x10010AA8:1,0x150303E4:1,
 0x15060D54:1,0x15188AD0:1,0x1505F188:1}
FINISH=0x1505F188
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
def quotient(n):return(abs(signed(n))//812)*(-1 if signed(n)<0 else 1)
@dataclass(frozen=True)
class Case:
 owner_delta:int=0
 request:int=0
 pattern:int=0
 mutation:int=0
 tree:int=0
 phase:int=0
def owner(c,s=SYMS):return u32(s['D_800CC2D0']+c.owner_delta)
def fixture(c,s=SYMS):
 base=s['D_800CC2D0'];m={STACK+i:(i*17+0xA5)&255 for i in range(-4096,512)}
 m.update({base+i:(i*13+0x35)&255 for i in range(-16,26*812+16)})
 slot=quotient(c.owner_delta)+1
 for i in range(26):
  p=base+i*812;active=(False,True,i%2==0,i==24,i<3,i%3==1)[c.pattern%6]
  put(m,p,int(active and i<25));put(m,p+5,2 if i%2 else 3,1);put(m,p+0x65,((slot if c.pattern%6 in(1,3,4)or i%3 else slot+1)&255),1);put(m,p+0x127,255 if c.pattern%6 in(1,3,4)or i%4 else 254,1);put(m,p+0x13F,255,1)
  for off in(0x144,0x260,0x264,0x268,0x26C,0x1D8,0x2D4,0x304,0x308,0x30C,0x310,0x314,0x2D0,0x324,0x31C):put(m,p+off,0)
 if c.tree:
  for i in range(25):put(m,base+i*812,0);put(m,base+i*812+0x65,255,1)
  put(m,base,1);put(m,base+5,0,1)
  for i in range(1,5):
   p=base+i*812;put(m,p,1);put(m,p+5,0 if c.tree==1 else 2,1);put(m,p+0x65,i if c.tree==1 else 1,1);put(m,p+0x127,255,1)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-4096<=p<STACK+512}
def mutate(m,c,actor,s,ordinal):
 base=s['D_800CC2D0'];i=(actor-base)//812;target=base+min(i+1,24)*812;slot=quotient(c.owner_delta)+1
 if ordinal==1:
  if c.mutation==1:put(m,target,1);put(m,target+0x65,slot&255,1);put(m,target+0x127,255,1)
  elif c.mutation==2:put(m,base+24*812+0x127,254,1)
  elif c.mutation==3:put(m,base+24*812+0x65,(slot+1)&255,1)
 put(m,actor,0)
def reference(c,s=SYMS,start_helper=False):
 m=fixture(c,s);base=s['D_800CC2D0'];calls=[];finished=[]
 def scan(p):
  slot=quotient(u32(p-base))+1
  for i in range(25):
   a=base+i*812
   if read(m,a)and m[a+0x65]==slot and m[a+0x127]==255:cleanup(a)
 def cleanup(a):
  calls.append((s['func_15060F28'],(a,u32(c.request))));assert len(calls)<64,'Fixture must be an acyclic ownership tree'
  if m[a+5]not in(2,3):scan(a)
  finished.append(a);mutate(m,c,a,s,len(finished))
 if start_helper:cleanup(owner(c,s))
 else:scan(owner(c,s))
 return m,calls,finished
def linked(obj,label,entry=ENTRY,s=SYMS,pair_isolated=False):
 source.validate_alias(s);text,fs,rs=parse_object(obj);f=fs[F]
 if pair_isolated:
  source.checked_payload(*source.payload(obj));s=dict(s,D_800CC2D0_pair_s6=s['D_800CC2D0']);rs={at:list(v)for at,v in rs.items()}
  for at,kind in((48,'R_MIPS_HI16'),(60,'R_MIPS_LO16')):
   key=f['value']+at;assert rs[key]==[(kind,'D_800CC2D0')];rs[key]=[(kind,'D_800CC2D0_pair_s6')]
  assert struct.unpack_from('>I',text,f['value']+48)[0]==0x3C160000 and struct.unpack_from('>I',text,f['value']+60)[0]==0x26D64F4C
 asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def helper_words():
 rom=(r/'conker/conker.us.bin').read_bytes();return dict(zip(range(HELPER,HELPER+176*4,4),struct.unpack_from('>176I',rom,0x8E3D8)))
class WindowBoundary(Exception):pass
class BoundaryCode(dict):
 def __init__(self,values,model):super().__init__(values);self.inner=values;self.model=model
 def __getitem__(self,pc):
  m=self.model
  if pc==m.window_stop and m.r[29]==STACK+m.c.phase:m.current_pc=pc;m.delay_of=None;raise WindowBoundary
  return self.inner[pc]
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.cleanups=[];self.finished=[];self.window_stop=None
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(owner(c,s),u32(c.request)),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:];self.code=BoundaryCode(self.code,self)
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
 def execute(self,w):
  if w>>26==32:
   rs,rt,imm=w>>21&31,w>>16&31,((w&65535)^32768)-32768;old=self.own_instruction;self.own_instruction=True
   try:self.r[rt]=u32((self.get(u32(self.r[rs]+imm),1)^128)-128);self.r[0]=0
   finally:self.own_instruction=old
  else:super().execute(w)
 def record_call(self,t):
  count=2 if t in(ENTRY,self.syms['func_15060F28'])else COUNTS.get(t);assert count is not None,('unknown-call',hex(t));a=tuple(map(u32,self.arguments(count)));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_15060F28']:
   self.cleanups.append((t,a));assert len(self.cleanups)<64,('cyclic-fixture',)
   assert a[1]==u32(self.c.request),('request',a)
 def hook(self,t):
  a=self.calls[-1][1]
  if t==self.syms['func_15060F28']:
   assert not self.c.tree,('recursive-provider-not-connected',);self.finished.append(a[0]);mutate(self.memory,self.c,a[0],self.syms,len(self.finished))
  elif t==FINISH:
   self.finished.append(a[0]);mutate(self.memory,self.c,a[0],self.syms,len(self.finished))
  else:
   assert t in COUNTS,('unbounded-provider',hex(t))
   if t==0x151695F0:assert a[1]==0,('provider-mode',a)
   if t==0x1504AF10:assert a[1:]==(1,0),('request-one-provider',a)
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=0x76543210
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.cleanups,m.finished)
def check(m,c,s=SYMS):
 want,calls,finished=reference(c,s);assert m.cleanups==calls,('cleanup-sequence',c,m.cleanups,calls);assert m.finished==finished,('cleanup-order',)
 assert public(m.memory)==public(want),('public',c)
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f
def corpus():
 for n in range(256):yield Case((n%26)*812,(0,1,2,0x80000000,0xFFFFFFFF)[n%5],n%6,n%4,0,8*(n&1))
 for delta,pattern,mutation,phase_ in itertools.product((-813,-812,-811,-1,0,1,811,812,19488,20300,20301,127*812,128*812,254*812,255*812,-128*812,0x7FFFFFFF,0x80000000),range(6),range(4),(0,8)):
  yield Case(delta,0x87654321,pattern,mutation,0,phase_)
 for tree,request,phase_ in itertools.product((1,2),(0,1,2,0xFFFFFFFF),(0,8)):yield Case(0,request,0,0,tree,phase_)
def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();hv=set();n=0
 for i,c in enumerate(corpus()):
  conn=helper_words()if c.tree or i%7==0 else None;ms=[Oracle(w,fixture(c),c,connected=conn).run()for w in ws]
  for m in ms:check(m,c)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c;visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));hv.update(ms[0].visits&set(helper_words())if conn else set());n+=1
 expected_reachable=set(range(ENTRY,ENTRY+232,4))-{ENTRY+i*4 for i in(30,34,35,36)}
 assert visits==expected_reachable,(len(visits),expected_reachable-visits,visits-expected_reachable)
 cuts=delays=0
 for c in(Case(pattern=0),Case(pattern=3,mutation=1,phase=8),Case(-1,pattern=4)):
  model=Oracle(ws[0],fixture(c),c).run()
  for cut in range(model.accesses):
   ms=[Oracle(w,fixture(c),c)for w in ws]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective access cutoff')
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0;literal_raw_carry_failures=0
 for j,(entry,base)in enumerate(((0x17007FFC,0x81007FFC),(0x2500FFFC,0x8200FFF0),(0x15008000,0x8300B0B4))):
  s=dict(D_800CC2D0=base,D_800D121C=base+20300,func_15060F28=entry+0x20000);bw=[linked(p,'rebase-%d-%d'%(j,i),entry,s,pair_isolated=(i==1))for i,p in enumerate(objects)]
  literal=linked(o/'selected-final.o','literal-raw-rebase-'+str(j),entry,s);end_value=u32(((literal[12]&65535)<<16)+(((literal[15]&65535)^32768)-32768));literal_raw_carry_failures+=int(end_value!=s['D_800D121C'])
  for c in(Case(pattern=1),Case(-1,pattern=4,mutation=3),Case(24*812,pattern=3,phase=8)):
   ms=[Oracle(w,fixture(c,s),c,entry,s).run()for w in bw]
   for m in ms:check(m,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 assert literal_raw_carry_failures==1
 return dict(cases=n,executions=n*3,body_words=58,reachable_words_visited=len(visits),unreachable_division_trap_path_words=[30,34,35,36],original_helper_words=176,helper_words_visited=len(hv),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,raw_GNU_HI_LO_carry_negative_controls=literal_raw_carry_failures,raw_rebase_uses_per_register_pair_symbol_isolation=True,raw_instruction_words_unchanged=True,original_and_normalized_rebases_use_literal_bindings=True,complete_memory_registers_trace_fault_context_equal=True,recursive_chain_and_star=True,SDK32_address_difference=True,lower_cleanup_services_bounded=True)
def guard_suite():
 rows=source.NEW_GUARDS;before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(before.decode())));count=0
 for i in range(2):
  for field in('expected','expected_relocations'):
   bad=[dict(v)for v in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else'R_MIPS_LO16:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(bad);p=o/('bad-guard-%d-%s.csv'%(i,field));p.write_bytes(before+stream.getvalue().encode())
   try:source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,source.OWNER,word_patches_path=p)
   except ValueError:pass
   else:raise AssertionError('Ineffective actual padder preimage control')
   count+=1
 source.validate_alias(SYMS)
 try:source.validate_alias(dict(SYMS,D_800D121C=END+4))
 except ValueError:pass
 else:raise AssertionError('Ineffective alias relation control')
 for base in(0x81007FFC,0x8200FFF0,0x8300B0B4,0x800CC2D0):
  end=base+20300;hi=lambda n:(n+0x8000)>>16;lo=lambda n:((n&65535)^32768)-32768
  assert u32((hi(base+20300)<<16)+lo(base+20300))==end
  assert u32((hi(end)<<16)+lo(end))==end
 return dict(guards=2,instruction_words_changed=1,actual_padder_rejections=count,HI_LO_binding_changes=2,alias_addend=20300,required_relation='D_800D121C == D_800CC2D0 + 25*812',GNU_rebase_layouts=3,additional_arithmetic_carry_layouts=4,invalid_alias_control=1,inherited_prefix_preserved=True,insertions=0,omissions=0)
def controls(body):
 edits={'scan-count':('index < 25','index < 24'),'start-slot':('index = 0','index = 1'),'active-gate':('record->interaction_state != 0','record->interaction_state == 0'),'owner-one-based':('sizeof(struct127) + 1','sizeof(struct127) + 0'),'owner-stride':('/ (s32)sizeof(struct127)','/ 811'),'unsigned-difference':('(s32)((u32)owner - (u32)D_800CC2D0) / (s32)sizeof(struct127)','(s32)(((u32)owner - (u32)D_800CC2D0) / (u32)sizeof(struct127))'),'signed-owner-byte':('record->unk65 ==','(s8)record->unk65 =='),'wrong-owner-field':('record->unk65 ==','record->unique_id =='),'tag-gate':('record->unk127 == 255','record->unk127 == 254'),'request-zero':('func_15060F28(record, request);','func_15060F28(record, 0);'),'skip-call':('func_15060F28(record, request);','(void)0;'),'extra-request-gate':('record->interaction_state != 0','request != 0 && record->interaction_state != 0')}
 result={}
 for n,(a,b)in edits.items():assert body.count(a)==1,(n,a);result[n]=body.replace(a,b,1)
 return result
def compiled_controls():
 for byte in range(256):
  m=Oracle([0],fixture(Case()));m.r[16]=BASE;put(m.memory,BASE+0x65,byte,1);m.execute(0x82080065);assert m.r[8]==u32(byte if byte<128 else byte-256)
 effective={};cases=[c for c in corpus()if not c.tree]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag;w=linked(obj,'IDO-linked-'+name)
  for c in cases:
   try:m=Oracle(w,fixture(c),c).run();check(m,c)
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]in('request','cleanup-sequence','cleanup-order','public'),(name,e);effective[name]='independent sequence or state disagreement';break
  else:raise AssertionError('Ineffective semantic control '+name)
 return dict(successful_IDO_compiles=len(effective),signed_byte_interpreter_cases=256,effective_semantic_controls=effective,compiler_or_interpreter_failures_counted=False)
def native_harness(body):
 return source.HEADERS+'\n'+body+r'''
typedef char ActorBytes[sizeof(struct127)==812?1:-1];
typedef char OwnerByte[__builtin_offsetof(struct127,unk65)==0x65?1:-1];
typedef char TagByte[__builtin_offsetof(struct127,unk127)==0x127?1:-1];
typedef char SDKPointer[sizeof(void*)==4?1:-1];
struct127 D_800CC2D0[26];static struct127 expected[26];
static s32 delta;static u32 request,pattern,mutation,tree;static int actualCalls,expectedCalls,actualFinishes,expectedFinishes,error;
static int actualLog[64],expectedLog[64],actualFinishLog[64],expectedFinishLog[64];
static const u32 requests[8]={0,1,2,3,255,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
static const s32 exterior[18]={-813,-812,-811,-1,0,1,811,812,19488,20300,20301,127*812,128*812,254*812,255*812,-128*812,0x7FFFFFFF,(s32)0x80000000u};
static s32 slotOf(s32 d){return d/812+1;}
static void mutationEffect(struct127*p,int index,int ordinal){int target=index<24?index+1:24;s32 slot=slotOf(delta);
 if(ordinal==1){if(mutation==1){p[target].interaction_state=1;p[target].unk65=(u8)slot;p[target].unk127=255;}
 else if(mutation==2)p[24].unk127=254;else if(mutation==3)p[24].unk65=(u8)(slot+1);}
 p[index].interaction_state=0;
}
static void refScan(s32 ownerDelta);
static void refCleanup(int index){if(expectedCalls>=64){error=1;return;}expectedLog[expectedCalls++]=index;
 if(expected[index].unk5!=2&&expected[index].unk5!=3)refScan(index*812);
 if(expectedFinishes>=64){error=1;return;}expectedFinishLog[expectedFinishes++]=index;mutationEffect(expected,index,expectedFinishes);}
static void refScan(s32 ownerDelta){int i;s32 slot=slotOf(ownerDelta);for(i=0;i<25;i++)if(expected[i].interaction_state&&expected[i].unk65==slot&&expected[i].unk127==255)refCleanup(i);}
__attribute__((noinline)) void func_15060F28(struct127*p,s32 value){int index=(s32)((u32)p-(u32)D_800CC2D0)/812;
 if(index<0||index>=25||(u32)value!=request||actualCalls>=64){error=2;return;}actualLog[actualCalls++]=index;
 if(p->unk5!=2&&p->unk5!=3)func_150626EC(p,value);
 if(actualFinishes>=64){error=2;return;}actualFinishLog[actualFinishes++]=index;mutationEffect(D_800CC2D0,index,actualFinishes);}
static int runCase(void){int i,j,active;s32 slot=slotOf(delta);u8*a=(u8*)D_800CC2D0,*e=(u8*)expected;struct127*p;
 for(i=0;i<(int)sizeof(D_800CC2D0);i++)a[i]=(u8)(i*13+0x35);
 for(i=0;i<26;i++){p=&D_800CC2D0[i];active=pattern==0?0:pattern==1?1:pattern==2?i%2==0:pattern==3?i==24:pattern==4?i<3:i%3==1;
 p->interaction_state=active&&i<25;p->unk5=i%2?2:3;p->unk65=(u8)(slot+((pattern==1||pattern==3||pattern==4||i%3)?0:1));p->unk127=(pattern==1||pattern==3||pattern==4||i%4)?255:254;
 }
 if(tree){for(i=0;i<25;i++){D_800CC2D0[i].interaction_state=0;D_800CC2D0[i].unk65=255;}D_800CC2D0[0].interaction_state=1;D_800CC2D0[0].unk5=0;
 for(i=1;i<5;i++){p=&D_800CC2D0[i];p->interaction_state=1;p->unk5=tree==1?0:2;p->unk65=(u8)(tree==1?i:1);p->unk127=255;}}
 for(i=0;i<(int)sizeof(expected);i++)e[i]=a[i];actualCalls=expectedCalls=actualFinishes=expectedFinishes=error=0;
 refScan(delta);func_150626EC((struct127*)((u32)D_800CC2D0+(u32)delta),(s32)request);
 if(error)return error;if(actualCalls!=expectedCalls||actualFinishes!=expectedFinishes)return 3;
 for(i=0;i<actualCalls;i++)if(actualLog[i]!=expectedLog[i])return 4;for(i=0;i<actualFinishes;i++)if(actualFinishLog[i]!=expectedFinishLog[i])return 4;
 for(j=0;j<(int)sizeof(expected);j++)if(a[j]!=e[j])return 5;return 0;
}
static int run(void){int n,k,result;
 tree=0;for(n=0;n<256;n++)for(k=0;k<8;k++)for(mutation=0;mutation<4;mutation++){
 delta=(n%26)*812;pattern=n%6;request=requests[k];result=runCase();if(result)return result;}
 for(n=0;n<18;n++)for(pattern=0;pattern<6;pattern++)for(mutation=0;mutation<4;mutation++){
 delta=exterior[n];request=0x87654321u;result=runCase();if(result)return result;}
 for(tree=1;tree<3;tree++)for(k=0;k<8;k++){delta=0;pattern=0;mutation=0;request=requests[k];result=runCase();if(result)return result;}
 return 0;}
'''+START
def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=8640,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in range(1,6),(name,code);effective[name]=code
 return dict(cases_per_profile=8640,profiles=profiles,SDK32_layout=True,all26_owner_slots=True,negative_unaligned_and_extreme_owner_addresses=True,request_bit_patterns=8,recursive_chain_and_star=True,all26_record_bytes_checked=True,negative_controls=len(effective),effective_native_controls=effective,provider_is_independent_bounded_cleanup_model=True)
def caller_suite():
 rom=source.snapshot(o)['conker/conker.us.bin'];jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')];assert calls==[0x8E428]and not pointers
 ws=[linked(p,'caller-target-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];window=list(struct.unpack_from('>4I',rom,0x8E424));assert window==[0x02202025,0x0D4189BB,0x02002825,0x24010001];n=0;helper_cases=0;helper_visits=set()
 for delta,request,pattern,mutation,phase_ in itertools.product((0,24*812,25*812,-1),(0,1,2,0xFFFFFFFF),(0,1,3,4),(0,1,2,3),(0,8)):
  c=Case(delta,request,pattern,mutation,0,phase_);ms=[]
  for body in ws:
   conn=helper_words();conn.update(zip(range(ENTRY,ENTRY+232,4),body));m=Oracle(window+[0],fixture(c),c,entry=0x15060F74,connected=conn);m.r[17]=owner(c);m.r[16]=u32(request);m.before=m.r[:];m.window_stop=0x15060F84
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   want,expected,finished=reference(c);assert m.cleanups==expected and m.finished==finished and public(m.memory)==public(want)
   assert m.calls[0]==(ENTRY,(owner(c),u32(request)))and m.r[1]==1 and m.r[29]==STACK+phase_ and m.r[16]==u32(request)and m.r[17]==owner(c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);n+=1
 original_helper=list(struct.unpack_from('>176I',rom,0x8E3D8))
 for tree,request,phase_ in itertools.product((1,2),(0,1,2,0xFFFFFFFF),(0,8)):
  c=Case(0,request,0,0,tree,phase_);ms=[]
  for body in ws:
   conn=dict(zip(range(ENTRY,ENTRY+232,4),body));m=Oracle(original_helper,fixture(c),c,entry=HELPER,connected=conn);m.cleanups=[(HELPER,(owner(c),u32(request)))];m.run();want,expected,finished=reference(c,start_helper=True)
   assert m.cleanups==expected and m.finished==finished and public(m.memory)==public(want);assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24];ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);helper_visits.update(ms[0].visits&set(range(HELPER,HELPER+704,4)));helper_cases+=1
 return dict(window_cases=n,original_window_words=4,aligned_ROM_JALs=['0x8e428'],aligned_literal_pointers=0,owner_and_request_marshalling_checked=True,return_value_ignored=True,original_helper_entry_cases=helper_cases,original_helper_words=176,helper_entry_words_visited=len(helper_visits),recursive_chain_and_star=True,lower_services_bounded=True,full_resource_or_hardware_claimed=False)
