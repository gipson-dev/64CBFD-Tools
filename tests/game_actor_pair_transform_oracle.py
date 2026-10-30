"""Actor point pair: literal scheduling proof and bounded connected transform protocol."""
from pathlib import Path
from dataclasses import dataclass,replace
from collections import Counter
import csv,io,itertools,json,struct,subprocess,sys
from tools.experiments import game_actor_pair_transform_match as source
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
PRIMARY,SECONDARY,CONVERT,TRANSFORM,TRANSLATE,FLAG=0x15145EA4,0x151D4408,0x151EFEB8,0x150A7960,0x15142314,0x800C3E90
ACTOR,MATRIX,FIRST,SECOND=0x28000,0x40000,0x30000,0x30020
SYMS=dict(func_15145EA4=PRIMARY,func_151D4408=SECONDARY)
FLOATS=(0,0x80000000,0x3F800000,0xBF800000,1,0x007FFFFF,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345,0xFFC12345)
PAIRS=(((0x3F800000,0x40000000,0x40400000),(0x40800000,0x40C00000,0x41000000)),((0,0x80000000,1),(0x80000000,0,2)),((0x4B800000,0xBF800000,0x00800000),(0x4B800000,0x3F800000,0x007FFFFF)),((0xC1200000,0x41200000,0x3F000000),(0x41200000,0xC1200000,0xBF000000)))
u32=lambda v:v&0xFFFFFFFF
bits=lambda v:struct.unpack('>I',struct.pack('>f',v))[0]
floating=lambda v:struct.unpack('>f',struct.pack('>I',v))[0]
@dataclass(frozen=True)
class Case:
 first:int=FIRST
 second:int=SECOND
 root_delta:int=0
 joint:int=0xABCD0081
 kind:int=0xDEAD00FF
 mode:int=0x87654321
 scale:int=0x7FA12345
 matrix:int=MATRIX
 tag:int=0
 pattern:int=0
 inputs:int=0
 flag:int=0
 mutation:int=0
 phase:int=0

def home(c):return STACK+c.phase+c.root_delta

def args(c):return(ACTOR,0 if c.inputs==1 else c.first,0 if c.inputs==2 else c.second,u32(c.joint),c.scale,u32(c.kind),u32(c.mode))

def block(m,p,n):return bytes(m[p+i]for i in range(n))

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,4096)}
 for base,n in((ACTOR,0x220),(c.first,16),(c.second,16),(MATRIX,0x4040)):
  m.update({base+i:(i*13+0xA5)&255 for i in range(-16,n)})
 put(m,ACTOR+0x1D4,c.matrix);put(m,ACTOR+0x74,c.tag,1);put(m,FLAG,c.flag,1)
 for i,p in enumerate((c.first,c.second)):
  for j in range(3):put(m,p+j*4,(0x80000000 if(i+j)&1 else 0)if c.inputs==3 else bits(float(i*4+j+1)))
 for i,v in enumerate(args(c)[4:],4):put(m,home(c)+i*4,v)
 return m

def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+4096}

def outputs(c):return PAIRS[c.pattern%len(PAIRS)]

def mutate(m,c):
 if c.mutation&1:put(m,ACTOR+0x1D4,MATRIX+0x80);put(m,ACTOR+0x74,15,1)
 if c.mutation&2:
  for off,v in((16,0xFFC12345),(20,0x12345680),(24,0x89ABCDEF)):put(m,home(c)+off,v)

def expected(c):
 origin,end=outputs(c);direction=tuple(bits(floating(b)-floating(a))for a,b in zip(origin,end))
 scale,kind,mode=(0xFFC12345,0x80,0x89ABCDEF)if c.mutation&2 else(c.scale,c.kind&255,u32(c.mode))
 return origin,direction,(u32(c.matrix+((c.joint&255)<<6)),ACTOR,scale,kind,mode)

def linked(obj,label,entry=ENTRY,s=SYMS,function=F):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def helpers():
 rom=(r/'conker/conker.us.bin').read_bytes();return dict(zip(range(PRIMARY,PRIMARY+117*4,4),struct.unpack_from('>117I',rom,0x173354)))

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,arguments=None):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.packets=[];self.primary_packets=[];self.lower=0
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=arguments or args(c),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:]
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
  counts={self.syms['func_15145EA4']:4,self.syms['func_151D4408']:7,CONVERT:2,TRANSFORM:7,TRANSLATE:3,ENTRY:7}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_15145EA4']:
   self.primary_packets.append((a,tuple(read(self.memory,a[0]+i*4)for i in range(2)),tuple(read(self.memory,a[1]+i*4)for i in range(2))))
  if t==self.syms['func_151D4408']:
   self.packets.append((tuple(read(self.memory,a[0]+i*4)for i in range(3)),tuple(read(self.memory,a[1]+i*4)for i in range(3)),a[2:]))
 def hook(self,t):
  c=self.c;a=self.calls[-1][1]
  if t==self.syms['func_15145EA4']:
   assert a[3]==2,('primary-count',a[3])
   for i,vector in enumerate(outputs(c)):
    dest=read(self.memory,a[1]+i*4)
    for j,v in enumerate(vector):put(self.memory,dest+j*4,v)
   mutate(self.memory,c)
  elif t==CONVERT:
   assert a[1]==u32(c.matrix+((c.joint&255)<<6))
   for i in range(16):put(self.memory,a[0]+i*4,bits(float(i+1)))
  elif t in(TRANSFORM,TRANSLATE):
   i=self.lower;assert i<2;src=args(c)[1+i];zero=not src or all(floating(read(self.memory,src+j*4))==0.0 for j in range(3))
   assert t==(TRANSLATE if zero else TRANSFORM),(hex(t),c)
   if t==TRANSLATE:assert a[:2]==(u32(c.matrix+((c.joint&255)<<6)),0);dest=a[2];dests=tuple(dest+j*4 for j in range(3))
   else:
    assert a[1:4]==tuple(read(self.memory,src+j*4)for j in range(3))
    assert a[0]==(home(c)-88-160+92 if c.flag else u32(c.matrix+((c.joint&255)<<6)))
    dests=a[4:]
   for p,v in zip(dests,outputs(c)[i]):put(self.memory,p,v)
   self.lower+=1
   if self.lower==2:mutate(self.memory,c)
  elif t==self.syms['func_151D4408']:
   assert len(self.packets)==1
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=0x76543210

def final_state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.calls,m.visits,m.packets,m.primary_packets)

def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.packets,m.primary_packets)

def check(m,c,connected=False):
 active=c.matrix!=0 and c.tag&15!=15
 assert len(m.primary_packets)==len(m.packets)==int(active),c
 if active:
  a,inputs,outs=m.primary_packets[0];sp=home(c)-88
  assert(a,inputs,outs)==((sp+52,sp+44,u32(c.matrix+((c.joint&255)<<6)),2),args(c)[1:3],(sp+76,sp+64)),c
  assert m.packets==[expected(c)],(c,m.packets,expected(c))
  if connected:assert m.lower==2
  want=fixture(c);mutate(want,c);assert public(m.memory)==public(want),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f

def cases():
 for n in range(256):
  for phase in(0,8):yield Case(joint=0xABCD0000|n,kind=0xBEEF0000|((n*73)&255),tag=n,phase=phase,scale=FLOATS[n%len(FLOATS)],pattern=n%4,inputs=n%4,flag=n%3,mutation=n%4)
 for matrix,tag,pattern,inputs,flag,mutation,phase in itertools.product((0,MATRIX),(0,15,255),range(4),range(4),(0,1,255),range(4),(0,8)):
  yield Case(matrix=matrix,tag=tag,pattern=pattern,inputs=inputs,flag=flag,mutation=mutation,phase=phase)

def guest_suite():
 original=linked(o/('original-'+F+'.o'),'guest-original');raw=linked(o/'selected-final.o','guest-raw');normalized=linked(o/'qualified-padded.o','guest-normalized');visits=set();helper_visits=set();n=0
 for i,c in enumerate(cases()):
  connected=helpers()if i%5==0 else None;models=[Oracle(w,fixture(c),c,connected=connected).run()for w in(original,raw,normalized)]
  for m in models:check(m,c,bool(connected))
  assert final_state(models[0])==final_state(models[1])==final_state(models[2]),c
  assert state(models[0])==state(models[2]),c
  visits.update(models[0].visits&set(range(ENTRY,ENTRY+228,4)));helper_visits.update(models[0].visits&set(helpers())if connected else set());n+=1
 assert len(visits)==57
 cuts=delays=0
 for c in(Case(matrix=0),Case(tag=15),Case(),Case(mutation=3,phase=8)):
  model=Oracle(original,fixture(c),c).run()
  for cut in range(model.accesses):
   ms=[Oracle(w,fixture(c),c)for w in(original,normalized)]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective access cutoff')
   assert state(ms[0])==state(ms[1]),(c,cut);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for j,entry in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  syms={k:entry+0x20000+i*0x10000 for i,k in enumerate(SYMS)};ws=[linked(obj,'rebased-%d-%d'%(j,i),entry=entry,s=syms)for i,obj in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))]
  for c in(Case(),Case(matrix=0),Case(tag=15),Case(mutation=3,phase=8)):
   ms=[Oracle(w,fixture(c),c,entry=entry,s=syms).run()for w in ws]
   for m in ms:check(m,c)
   assert final_state(ms[0])==final_state(ms[1])==final_state(ms[2]);assert state(ms[0])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),primary_original_words=117,primary_words_visited=len(helper_visits),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,all_joint_and_kind_bytes=True,all_actor_tag_bytes=True,raw_final_state_equal=True,retail_normalized_full_trace_and_fault_prefix_equal=True,raw_private_access_order_equal_claimed=False,opaque_secondary=True,bounded_conversion_transform_translation=True)

def guard_suite():
 from tools.pad_generated_object import emit_padded_assembly
 rows=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();assert len(rows)==8
 columns=next(csv.reader(io.StringIO(before.decode())));count=0
 for i in range(8):
  for field in('expected','expected_relocations'):
   bad=[dict(v)for v in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else'R_MIPS_26:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(bad);p=o/('bad-guards-%d-%s.csv'%(i,field));p.write_bytes(before+stream.getvalue().encode())
   try:emit_padded_assembly(o/'after-owner.o',r/source.ASM,source.OWNER,word_patches_path=p)
   except ValueError:pass
   else:raise AssertionError('Ineffective padder control')
   count+=1
 def dag(words):
  g=[('g',i)for i in range(32)];g[29]=('sp',0);f=[('f',i)for i in range(32)];mem={};reads=[];writes=[]
  def address(reg,imm):assert g[reg][0]=='sp';return g[reg][1]+imm
  def load(at,n):reads.append((at,n));return tuple(mem.get(at+i,('byte',at+i))for i in range(n))
  def store(at,v):writes.append((at,4));mem.update({at+i:('part',v,i)for i in range(4)})
  for w in words:
   op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31;imm=((w&65535)^32768)-32768
   if op==9:g[rt]=('sp',address(rs,imm))
   elif op in(35,36):g[rt]=('load',load(address(rs,imm),4 if op==35 else 1))
   elif op==49:f[rt]=('load',load(address(rs,imm),4))
   elif op==57:store(address(rs,imm),f[rt])
   elif op==17 and rs==16 and w&63==1:f[(w>>6)&31]=('sub.s',f[rd],f[rt])
   else:raise AssertionError(hex(w))
  return g,f,mem,sorted(reads),sorted(writes)
 raw,_=source.checked_payload(*source.payload(o/'selected-final.o'));truth,_=source.payload(o/('original-'+F+'.o'));a=struct.unpack('>57I',raw);b=struct.unpack('>57I',truth)
 assert [i for i,(x,y)in enumerate(zip(a,b))if x!=y]==[39,41,42,43,44,45,46,47]
 assert a[40]==b[40]==0x46062201 and Counter(a[39:48])==Counter(b[39:48])and dag(a[39:48])==dag(b[39:48])
 *_,reads,writes=dag(a[39:48]);assert reads==[(60,4),(104,4),(111,1),(112,4)]and writes==[(68,4),(72,4)]
 assert all(set(range(p,p+n)).isdisjoint(range(q,q+k))for p,n in reads for q,k in writes)
 bad=list(a[39:48]);bad[1]^=1<<16
 assert dag(bad)!=dag(b[39:48])
 return dict(guards=8,actual_padder_rejections=count,closed_windows=[[156,192]],all32_GPR_and_FPR_DAGs_equal=True,final_symbolic_memory_equal=True,instruction_multisets_equal=True,read_ranges=[list(x)for x in reads],write_ranges=[list(x)for x in writes],all_stack_transfers_disjoint=True,arithmetic_word40_fixed=True,semantic_DAG_negative_controls=1,insertions=0,omissions=0,raw_fault_prefix_equality_claimed=False)

def controls(body):
 edits={
 'extra-actor-gate':('actor->unk1D4 != NULL','actor->unk1D4 != NULL && actor->unk74 != 0'),
 'tag-mask':('(actor->unk74 & 0xF) != 0xF','(actor->unk74 & 0x7) != 0x7'),
 'joint-width':('((u8)joint << 6)','((u16)joint << 6)'),
 'matrix-stride':('((u8)joint << 6)','((u8)joint << 5)'),
 'point-count':('matrix, 2);','matrix, 1);'),
 'input-pair':('inputs[0] = (struct17 *)first;','inputs[0] = (struct17 *)second;'),
 'output-pair':('outputs[0] = &origin;\n        outputs[1] = &direction;','outputs[0] = &direction;\n        outputs[1] = &origin;'),
 'reverse-subtraction':('direction.unk0 -= origin.unk0;','direction.unk0 = origin.unk0 - direction.unk0;'),
 'addition':('direction.unk8 -= origin.unk8;','direction.unk8 += origin.unk8;'),
 'scale':('actor, scale,','actor, 0.0f,'),
 'kind-width':('(u8)kind, mode','kind, mode'),
 'kind-zero':('(u8)kind, mode','0, mode'),
 'mode-zero':('(u8)kind, mode','(u8)kind, 0'),
 'cached-matrix':('&direction, matrix,','&direction, (u8 *)actor->unk1D4 + ((u8)joint << 6),'),
 'skip-secondary':('func_151D4408(&origin, &direction, matrix, (u8 *)actor, scale, (u8)kind, mode);','(void)0;')}
 result={}
 for n,(a,b)in edits.items():assert body.count(a)==1,(n,a);result[n]=body.replace(a,b,1)
 return result

def compiled_controls():
 effective={};corpus=list(itertools.islice(cases(),64))+[Case(joint=0x100),Case(joint=0x100,tag=15),Case(mutation=3)]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);source.check_owner_diagnostics(diag);words=linked(obj,'IDO-control-linked-'+name)
  for c in corpus:
   m=Oracle(words,fixture(c),c)
   try:m.run()
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]=='primary-count',(name,e)
    effective[name]='primary count violation';break
   try:check(m,c)
   except AssertionError:effective[name]='independent packet/gate/state disagreement';break
  else:raise AssertionError('Ineffective IDO control: '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_errors_counted=False)

def native_harness(body):
 text=(r/'conker/src/game_16EE20.c').read_text();a,b=source.function_span(text,'func_15145EA4');primary=text[a:b].replace('void func_15145EA4(','static void actualMatrixList(')
 pairs=','.join('{'+','.join('{'+','.join('0x%Xu'%v for v in point)+'}'for point in pair)+'}'for pair in PAIRS)
 floats=','.join('0x%Xu'%v for v in FLOATS)
 return source.HEADERS+'''\nextern u8 D_800C3E90;
void func_150A7960(f32 (*)[4],f32,f32,f32,f32 *,f32 *,f32 *);
void func_15142314(u8 *,s32,f32 *);
'''+primary+'\n'+body+r'''
typedef char ActorMatrixOffset[__builtin_offsetof(struct127,unk1D4)==0x1D4?1:-1];
typedef char ActorTagOffset[__builtin_offsetof(struct127,unk74)==0x74?1:-1];
typedef char PointBytes[sizeof(struct17)==12?1:-1];
static u32 word(const f32*p){union{f32 f;u32 u;}v;v.f=*p;return v.u;}
static f32 value(u32 n){union{f32 f;u32 u;}v;v.u=n;return v.f;}
u8 D_800C3E90;static struct127 actor,expectedActor;static struct17 first,second;
static u32 matrices[16384];static struct17 *wantFirst,*wantSecond,*out[2];
static u8 *wantMatrix;static u32 convertedAddress;static int primaryCalls,secondaryCalls,lowerCalls,conversionCalls,error,pattern,mutateActor;
static u32 wantScale,wantKind,wantMode;static const u32 pairs[4][2][3]={PAIRS};static const u32 floats[12]={FLOATS};
static void assign(struct17*p,int index){p->unk0=value(pairs[pattern][index][0]);p->unk4=value(pairs[pattern][index][1]);p->unk8=value(pairs[pattern][index][2]);}
static int zeroPoint(struct17*p){return !p||(p->unk0==0.0f&&p->unk4==0.0f&&p->unk8==0.0f);}
static void afterLower(void){lowerCalls++;if(lowerCalls==2&&mutateActor){actor.unk1D4=(struct255*)((u8*)matrices+128);actor.unk74=15;}}
void guMtxL2F(f32 mf[4][4],Mtx*m){int i,j;conversionCalls++;if((u8*)m!=wantMatrix)error=1;convertedAddress=(u32)mf;for(i=0;i<4;i++)for(j=0;j<4;j++)mf[i][j]=(f32)(i*4+j+1);}
void func_150A7960(f32 (*matrix)[4],f32 x,f32 y,f32 z,f32*ox,f32*oy,f32*oz){
 struct17*p=lowerCalls?wantSecond:wantFirst;int i=lowerCalls;
 if(i>1){error=2;return;}if(zeroPoint(p)||word(&x)!=word(&p->unk0)||word(&y)!=word(&p->unk4)||word(&z)!=word(&p->unk8)||
 (u32)matrix!=(D_800C3E90?convertedAddress:(u32)wantMatrix)||ox!=&out[i]->unk0||oy!=&out[i]->unk4||oz!=&out[i]->unk8)error=2;
 *ox=value(pairs[pattern][i][0]);*oy=value(pairs[pattern][i][1]);*oz=value(pairs[pattern][i][2]);afterLower();
}
void func_15142314(u8*matrix,s32 index,f32*destination){int i=lowerCalls;struct17*p=i?wantSecond:wantFirst;if(i>1){error=3;return;}
 if(!zeroPoint(p)||matrix!=wantMatrix||index!=0||destination!=&out[i]->unk0)error=3;assign(out[i],i);afterLower();}
__attribute__((noinline)) void func_15145EA4(struct17**input,struct17**output,u8*matrix,s32 count){
 primaryCalls++;if(count!=2||input[0]!=wantFirst||input[1]!=wantSecond||matrix!=wantMatrix||output[0]==output[1])error=4;
 out[0]=output[0];out[1]=output[1];assign(out[0],0);assign(out[1],1);actualMatrixList(input,output,matrix,count);
}
__attribute__((noinline)) void func_151D4408(struct17*origin,struct17*direction,void*matrix,u8*owner,f32 scale,s32 kind,s32 mode){int j;f32 *a=&origin->unk0,*d=&direction->unk0;
 secondaryCalls++;if(primaryCalls!=1||lowerCalls!=2||matrix!=wantMatrix||owner!=(u8*)&actor||word(&scale)!=wantScale||(u32)kind!=wantKind||(u32)mode!=wantMode)error=5;
 for(j=0;j<3;j++){f32 expected=value(pairs[pattern][1][j])-value(pairs[pattern][0][j]);if(word(a+j)!=pairs[pattern][0][j]||word(d+j)!=word(&expected))error=6;}
}
static int run(void){u32 n,i;int present,t,p,flag,input,mutation,active;union{u32 u;f32 f;}scaleValue;u8*a=(u8*)&actor,*e=(u8*)&expectedActor;
 for(n=0;n<256;n++)for(present=0;present<2;present++)for(t=0;t<4;t++)for(p=0;p<4;p++)for(flag=0;flag<3;flag++)for(input=0;input<4;input++)for(mutation=0;mutation<2;mutation++){
 for(i=0;i<sizeof(actor);i++)a[i]=(u8)(i*13+n);actor.unk1D4=present?(struct255*)matrices:NULL;actor.unk74=(u8)(t==0?n:t==1?15:t==2?0x10:255);
 for(i=0;i<sizeof(actor);i++)e[i]=a[i];active=present&&((actor.unk74&15)!=15);pattern=p;mutateActor=mutation;
 wantFirst=input==1?NULL:&first;wantSecond=input==2?NULL:&second;first.unk0=input==3?0.0f:1.0f;first.unk4=input==3?-0.0f:2.0f;first.unk8=input==3?0.0f:3.0f;
 second.unk0=input==3?-0.0f:5.0f;second.unk4=input==3?0.0f:6.0f;second.unk8=input==3?-0.0f:7.0f;
 wantMatrix=(u8*)matrices+n*64;wantScale=floats[n%12];wantKind=n;wantMode=0x87650000u|n;D_800C3E90=flag==2?255:(u8)flag;
 primaryCalls=secondaryCalls=lowerCalls=conversionCalls=error=0;scaleValue.u=wantScale;func_151D5714(&actor,(f32*)wantFirst,(f32*)wantSecond,(s32)(0x100+n),scaleValue.f,(s32)(0xBEEF0000u|n),(s32)wantMode);
 if(error)return error;if(primaryCalls!=active||secondaryCalls!=active||lowerCalls!=2*active||conversionCalls!=(active&&flag!=0))return 7;
 if(active&&mutation){expectedActor.unk1D4=(struct255*)((u8*)matrices+128);expectedActor.unk74=15;}for(i=0;i<sizeof(actor);i++)if(a[i]!=e[i])return 8;
 }
 return 0;}
'''.replace('PAIRS',pairs).replace('FLOATS',floats)+START

def native_suite():
 profiles={};effective={}
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr);profiles[opt]=dict(exit=0,cases=196608,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,9)and not q.stdout and not q.stderr,(name,q.returncode);effective[name]=q.returncode
 return dict(cases_per_profile=196608,profiles=profiles,SDK32_layout=True,real_primary_C=True,all_joint_kind_and_tag_bytes=True,float_bit_patterns=12,finite_point_pair_patterns=4,negative_controls=len(effective),effective_native_controls=effective,all_actor_bytes_checked=True,portable_private_stack_alias_claimed=False,secondary_effects_or_hardware_claimed=False)

def caller_suite():
 from tools.match_progress import load_elf_functions
 original=linked(o/('original-'+F+'.o'),'caller-target-original');raw=linked(o/'selected-final.o','caller-target-raw');normalized=linked(o/'qualified-padded.o','caller-target-normalized')
 before=source.snapshot(o);rom=before['conker/conker.us.bin'];fs,_,_=load_elf_functions(str(o/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');visits=set();count=0
 locations=((0x150714E8,0x9E998,0x800A2148,0x800A2154,0x80088BB0),(0x15071888,0x9ED38,0x800A1FB0,0x800A1FBC,0x80088B90))
 for entry,at,first,second,joint in locations:
  words=list(struct.unpack_from('>23I',rom,at));name='func_%08X'%entry;assert fs[name]==words,(name,'Current C caller is not retail exact')
  assert words[0]==0x27BDFFD8 and words[-3:]==[0x27BD0028,0x03E00008,0]
  for n,phase,mutation,inputs in itertools.product(range(16),(0,8),range(4),(0,3)):
   c=Case(first=first,second=second,root_delta=-40,joint=n*17,kind=255,mode=1,scale=0x3F800000 if entry==locations[0][0]else FLOATS[n%12],tag=n,phase=phase,mutation=mutation,inputs=inputs,flag=n%3,pattern=n%4)
   mem=fixture(c);put(mem,0x800D154C,ACTOR);put(mem,joint,c.joint,1);put(mem,0x80099F30,c.scale)
   ms=[]
   for body in(original,raw,normalized):
    connected=helpers();connected.update(zip(range(ENTRY,ENTRY+228,4),body));m=Oracle(words,mem,c,entry=entry,connected=connected,arguments=(0xFEDCBA98,)).run();ms.append(m)
    active=c.matrix!=0 and c.tag&15!=15;assert len(m.packets)==int(active);assert m.packets==([expected(c)]if active else[]),c
    if active:
     a,sources,destinations=m.primary_packets[0];sp=home(c)-88;assert(a,sources,destinations)==((sp+52,sp+44,u32(c.matrix+((c.joint&255)<<6)),2),args(c)[1:3],(sp+76,sp+64))
    assert m.calls[0]==(ENTRY,args(c)),(name,c,m.calls[0],args(c))
   assert final_state(ms[0])==final_state(ms[1])==final_state(ms[2]);assert state(ms[0])==state(ms[2]);visits.update(ms[0].visits&set(range(entry,entry+92,4)));count+=1
 assert len(visits)==46
 jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')]
 assert calls==[0x9E9DC,0x9ED7C]and not pointers
 header=(r/'conker/include/functions.h').read_text();assert 'void func_151D5714(struct127*, f32*, f32*, s32, f32, s32, s32);'in header
 return dict(cases=count,original_complete_wrappers=2,words_each=23,current_linked_C_callers_equal_retail=True,caller_words_visited=len(visits),root_frame_inside_wrapper=88,wrapper_frame=40,aligned_ROM_JALs=['0x9E9DC','0x9ED7C'],aligned_literal_pointers=0,public_header_unchanged=True,full_parent_or_hardware_claimed=False)
