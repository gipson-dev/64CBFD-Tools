"""Private halfword approach: independent arithmetic, guest access order and ABI."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,random,re,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-record-halfword-approach-151193F4-match';F='func_151193F4';ENTRY=0x151193F4;RECORD=0x22000;COMMAND=0x30000;TABLE=0x80088C90
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 current:int=0
 origin:int=0
 step:int=1
 packed:int=0
 scale:int=1
 flags:int=0xFF
 phase:int=0
 seed:int=0
 base:int=RECORD

def fixture(c):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-256,256)};m.update({c.base+i:(i*13+c.seed)&255 for i in range(-16,0xA0)})
 for off,v,n in((0x12,c.current,2),(0x84,c.origin,4),(0x7C,c.step,4),(0x3C,c.packed,4),(0x80,c.scale,4),(0x73,c.flags,1)):put(m,c.base+off,u32(v)&((1<<(8*n))-1),n)
 return m

def reference(initial,c):
 m=dict(initial);a=c.base
 if read(m,a+0x84)==0:put(m,a+0x84,u32(half(read(m,a+0x12,2)))|0x80000000)
 step=signed(read(m,a+0x7C))
 if step:
  product=signed(u32((read(m,a+0x3C)>>16)*read(m,a+0x80)))
  quotient=(abs(product)//256)*(-1 if product<0 else 1)
  target=quotient+half(read(m,a+0x84));current=half(read(m,a+0x12,2));m[a+0x73]&=252
  if target==current:m[a+0x73]|=3
  else:
   distance=abs(current-target)
   result=target if distance<step else current+step if current<target else current-step
   put(m,a+0x12,result&65535,2)
 return m

class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,fault=None):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(c.base,),connected=connected);self.trace=[];self.root_fault=fault
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target==ENTRY,hex(target);args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):raise AssertionError(('unbounded helper',target))

def corpus():
 values=(0,1,-1,255,-256,32767,-32768)
 for current,origin,step,scale,rate in itertools.product(values,(0,0x80000000,0x1234FFFF),(-1,0,1,32767,0x7FFFFFFF,0x80000000),(0,1,0xFFFFFFFF),(0,1,65535)):
  yield Case(current,origin,step,rate<<16|0xA5,scale,(current+step)&255,8*((scale+rate)&1))
 for flags in range(256):
  for c in (Case(current=17,origin=0x8000000A,step=7,packed=0x10000,scale=256),Case(current=10,origin=0x8000000A,step=1),Case(current=10,step=0)):
   yield Case(**dict(c.__dict__,flags=flags))
 # Negative-product fractions distinguish signed truncation from arithmetic shift.
 for scale in (-1,-255,-256,-257,0x80000000,0x7FFFFFFF):
  for current in values:yield Case(current=current,origin=0x80000001,step=13,packed=0x10000,scale=scale)
 rng=random.Random(0x151193F4)
 for i in range(1024):yield Case(rng.randrange(65536),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.randrange(256),8*(i&1),i&255,STACK-0x80 if i%7==0 else RECORD)

def words(name):
 raw,rs=payload(o/name,F);assert not rs;return list(struct.unpack('>'+str(len(raw)//4)+'I',raw))

def guest_suite():
 images=[words('original-'+F+'.o'),words('selected-final.o'),words('qualified-padded.o')];visits=set();cases=0
 for c in corpus():
  initial=fixture(c);want=reference(initial,c);models=[]
  for w in images:
   m=Oracle(w,initial,c);before=m.r.copy();m.run();assert m.memory==want,(c,m.memory,want);assert not m.calls
   for reg in (*range(16,24),28,29,30,31):
    assert m.r[reg]==before[reg],(reg,c)
   models.append(m)
  assert models[0].trace==models[1].trace==models[2].trace,c
  assert (models[0].r,models[0].f,models[0].lo,models[0].hi,models[0].events)==(models[2].r,models[2].f,models[2].lo,models[2].hi,models[2].events),c
  visits.update(models[0].visits);cases+=1
 assert visits==set(range(ENTRY,ENTRY+224,4)),[hex(a)for a in set(range(ENTRY,ENTRY+224,4))-visits]
 cuts=delay=0
 for c in (Case(),Case(current=-32768,step=0),Case(current=17,origin=0x8000000A,step=7,packed=0x10000,scale=256),Case(current=10,origin=0x8000000A),Case(current=0,origin=0x80000001,scale=-1,packed=0x10000)):
  base=Oracle(images[0],fixture(c),c).run()
  for cut in range(base.root_accesses):
   pair=[]
   for w in images:
    m=Oracle(w,fixture(c),c,fault=cut)
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('missing fault',cut))
    pair.append(m)
   assert pair[0].memory==pair[1].memory==pair[2].memory and pair[0].trace==pair[1].trace==pair[2].trace,(c,cut)
   assert(pair[0].r,pair[0].f,pair[0].hi,pair[0].lo,pair[0].delay_of)==(pair[2].r,pair[2].f,pair[2].hi,pair[2].lo,pair[2].delay_of)
   cuts+=1;delay+=pair[0].delay_of is not None
 return dict(cases=cases,executions=cases*3,covered_words=len(visits),access_prefix_cases=cuts,delay_slot_cuts=delay,raw_public_memory_and_access_order_equal=True,normalized_complete_register_state_equal=True,callee_saved_and_SP_fixed=True,portable_fault_or_hardware_claim=False)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc==self.owner.window_end:raise WindowBoundary
  return super().__getitem__(pc)

def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();install=list(struct.unpack_from('>22I',rom,0xCC06C));call=list(struct.unpack_from('>5I',rom,0x141390))
 for ws,path,va in ((install,'conker/asm/CBDB0.s',0x1509EBBC),(call,'conker/asm/13D350.s',0x15113EE0)):
  literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/path).read_text())};assert ws==[literal[va+i*4]for i in range(len(ws))]
 assert rom[0x22D918:0x22D924]==struct.pack('>III',ENTRY,0,0)
 initial=fixture(Case());put(initial,COMMAND+8,38)
 for i,b in enumerate(rom[0x22D918:0x22D924]):initial[TABLE+38*12+i]=b
 m=Oracle(install,initial,entry=0x1509EBBC);m.r[2]=RECORD;m.r[16]=COMMAND;m.window_end=0x1509ED5C;m.code=WindowCode(dict(m.code),m)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('installation window did not stop')
 assert(read(m.memory,RECORD+0x38),read(m.memory,RECORD+0x78),m.memory[RECORD+0x92])==(ENTRY,0,0)
 cases=0
 for c in itertools.islice(corpus(),0,None,47):
  initial=fixture(c);put(initial,c.base+0x38,ENTRY);want=reference(initial,c)
  for name in ('original-'+F+'.o','selected-final.o','qualified-padded.o'):
   ws=words(name);m=Oracle(call,initial,c,entry=0x15113EE0,connected={ENTRY+i*4:w for i,w in enumerate(ws)});m.r[16]=c.base;m.r[30]=10;m.window_end=0x15113EF4;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller window did not stop')
   assert m.memory==want and m.calls==[(ENTRY,(c.base,))]and m.r[30]==11,c
  cases+=1
 for path,name in (('conker/src/game/generated_CBDB0.c','func_1509E900'),('conker/src/game/generated_13D350.c','func_15113E54')):assert 's32 '+name+'() {\n    return 0;\n}'in(r/path).read_text()
 return dict(original_install_words=22,original_indirect_words=5,slot=38,table_pointer_ROM='0x22D918',table_pointer_VA='0x80088E58',cases=cases,A0_record_void_return_contract=True,original_windows_only=True,current_dispatcher_and_installer_still_stubs=True,full_parent_acceptance=False)

def controls(source):
 return dict(unsigned_current=source.replace('*(s16 *)(record + 0x12);','*(u16 *)(record + 0x12);'),unsigned_origin=source.replace('origin = (s16)origin;','origin = (u16)origin;'),wrong_rate=source.replace('>> 16) & 0xFFFF','>> 8) & 0xFFFF'),unsigned_product=source.replace('(s32)((u32)rate * (u32)scale) / 256','((u32)rate * (u32)scale) / 256'),floor_division=source.replace('(s32)((u32)rate * (u32)scale) / 256','((s32)((u32)rate * (u32)scale) >> 8)'),wrong_direction=source.replace('(u32)current + (u32)step','(u32)current - (u32)step'),wrong_flags=source.replace('record[0x73] &= ~3;','record[0x73] &= ~7;'),missing_arrived=source.replace('record[0x73] |= 3;','record[0x73] |= 0;'),missing_origin_tag=source.replace('current | 0x80000000','current'))

def compiled_controls():
 source=(o/'selected-semantic-input.c').read_text();rows={}
 cases=list(corpus())
 for name,body in controls(source).items():
  assert body!=source;obj,diag=compile_owner(r,o,body,'control-'+name);assert not diag
  raw,rs=payload(obj,F);assert not rs;ws=struct.unpack('>'+str(len(raw)//4)+'I',raw)
  for index,c in enumerate(cases):
   initial=fixture(c)
   if Oracle(ws,initial,c).run().memory!=reference(initial,c):rows[name]=index;break
  else:raise AssertionError(('ineffective compiled control',name))
 return dict(effective_IDO_controls=rows,count=len(rows))

def native_source(source):
 text='''#include <ultra64.h>
typedef struct { u8 p0[0x12]; s16 current; u8 p14[0x28]; u32 packed; u8 p40[0x33]; u8 flags; u8 p74[8]; s32 step; u32 scale; s32 origin; } Record;
typedef char ABI[(sizeof(void*)==4 && sizeof(Record)==0x88 && __builtin_offsetof(Record,flags)==0x73 && __builtin_offsetof(Record,step)==0x7C && __builtin_offsetof(Record,scale)==0x80 && __builtin_offsetof(Record,origin)==0x84)?1:-1];
static struct {u32 left[4];Record record;u32 right[4];} actual,expected;
'''
 for name,body in dict(selected=source,**controls(source)).items():text+=body.replace('#include <ultra64.h>','').replace('void '+F,'static void '+name)+'\n'
 text+='''
typedef void(*Update)(u8*);
static u32 random_value=0x151193F4u;
static u32 next(void){random_value=random_value*1664525u+1013904223u;return random_value;}
static int check(Update fn){u32 n,mode,i;u8*p=(u8*)&actual,*q=(u8*)&expected;Record*t=&actual.record,*e=&expected.record;s32 current,origin,product,target,quotient,step;u32 magnitude;
 random_value=0x151193F4u;
 for(n=0;n<65536;n++)for(mode=0;mode<8;mode++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n+mode);
  t->current=(s16)n;t->origin=mode&1?(s32)next():0;t->step=(s32)(mode==0?0:mode==1?1:mode==2?0xFFFFFFFFu:next());t->packed=next();t->scale=mode==3?0xFFFFFFFFu:mode==4?0x80000000u:next();t->flags=(u8)(n+mode);
  if(n<256){t->current=mode&1?0:17;t->origin=mode&2?(s32)0x8000000Au:0;t->step=mode&4?0:7;t->packed=0x10000;t->scale=mode&1?0xFFFFFFFFu:256;t->flags=(u8)n;}
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];current=e->current;
  if(e->origin==0)e->origin=(s32)((u32)current|0x80000000u);
  step=e->step;
  if(step!=0){
   product=(s32)((e->packed>>16)*e->scale);
   quotient=product/256;origin=(s16)e->origin;target=quotient+origin;e->flags&=252;
   if(target==current)e->flags|=3;
   else {magnitude=(u32)(current<target?target-current:current-target);
    if(step>0&&magnitude<(u32)step)e->current=(s16)target;
    else e->current=(s16)(current<target?(u32)current+(u32)step:(u32)current-(u32)step);
   }
  }
  fn((u8*)t);for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 0;
 }
 return 1;
}
int run(void){if(!check(selected))return 1;
'''
 for i,name in enumerate(controls(source),2):text+='if(check('+name+'))return '+str(i)+';\n'
 return text+'return 0;}\n'+START

def native_suite():
 source=(o/'selected-semantic-input.c').read_text();profiles={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_source(source));binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=r,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
  z=subprocess.run([str(binary)],timeout=60);assert z.returncode==0,(opt,z.returncode);profiles[opt]=dict(exit=0,UBSan=True,cases=524288)
 return dict(cases_per_profile=524288,all_signed_halfwords=True,all_flag_bytes=True,negative_controls=len(controls(source)),profiles=profiles)

def symbolic_suite():
 """Exact DAG equality in a closed integer leaf; all branch outcomes, no SMT assumptions."""
 import copy
 images=[words('original-'+F+'.o'),words('selected-final.o')]
 def expr(op,*args):
  if op in ('or','and','add','mul','eq'):args=tuple(sorted(args,key=repr))
  if all(isinstance(v,int)for v in args):
   a=args[0];b=args[1]if len(args)>1 else 0
   return u32({'or':lambda:a|b,'and':lambda:a&b,'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,'sll':lambda:a<<b,'sra':lambda:signed(a)>>b,'slt':lambda:int(signed(a)<signed(b)),'eq':lambda:int(a==b),'nonnegative':lambda:int(signed(a)>=0)}[op]())
  if op in ('or','add')and 0 in args:return next(a for a in args if a!=0)
  if op=='sub'and args[1]==0:return args[0]
  return(op,*args)
 class State:
  def __init__(self,ws):
   self.ws=ws;self.pc=0;self.reg=[0]+[('input-register',i)for i in range(1,32)];self.mem={};self.trace=[];self.hi=('input-HI',);self.lo=('input-LO',);self.cover=set()
  def execute(self,pc):
   w=self.ws[pc//4];self.cover.add(pc);op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63;imm=w&65535;si=(imm^32768)-32768
   a,b=self.reg[rs],self.reg[rt]
   if op in (35,33,36,43,41,40):
    assert a==('input-register',4),('non-record memory base',pc,a)
    size={35:4,33:2,36:1,43:4,41:2,40:1}[op];key=(si,size)
    if op in (35,33,36):
     v=self.mem.get(key,('input-memory',si,size));self.trace.append(('read',si,size,v));self.reg[rt]=expr('sra',expr('sll',v,16),16)if op==33 else v
    else:
     v=expr('and',b,(1<<(8*size))-1)if size<4 else b;self.mem[key]=v;self.trace.append(('write',si,size,v))
   elif op==15:self.reg[rt]=u32(imm<<16)
   elif op==9:self.reg[rt]=expr('add',a,u32(si))
   elif op==12:self.reg[rt]=expr('and',a,imm)
   elif op==13:self.reg[rt]=expr('or',a,imm)
   elif op==0:
    if fn==0:self.reg[rd]=expr('sll',b,w>>6&31)
    elif fn==3:self.reg[rd]=expr('sra',b,w>>6&31)
    elif fn in (33,35,37,42):self.reg[rd]=expr({33:'add',35:'sub',37:'or',42:'slt'}[fn],a,b)
    elif fn==25:self.lo=expr('mul',a,b);self.hi=('mul-high-unsigned',*sorted((a,b),key=repr))
    elif fn==18:self.reg[rd]=self.lo
    else:raise AssertionError(('unhandled own operation',pc,hex(w)))
   else:raise AssertionError(('unhandled own operation',pc,hex(w)))
   self.reg[0]=0
  def next_branch(self):
   while True:
    pc=self.pc;w=self.ws[pc//4];op=w>>26;rs=w>>21&31;rt=w>>16&31
    if op==0 and w&63==8:
     assert rs==31;self.cover.add(pc);self.execute(pc+4);return('return',)
    if op in (4,5,20,21,1):
     a,b=self.reg[rs],self.reg[rt];si=((w&65535)^32768)-32768;self.cover.add(pc)
     predicate=expr('nonnegative',a)if op==1 else expr('eq',a,b)
     assert op!=1 or rt==1,('not bgez',pc)
     return('branch',predicate,op,pc+4+si*4,pc+8,pc)
    self.execute(pc);self.pc+=4
  def advance(self,info,taken):
   _,_,op,target,fall,pc=info
   if op in (5,21):taken=not taken
   if op not in (20,21)or taken:self.execute(pc+4)
   self.pc=target if taken else fall
 frontier=[(State(images[0]),State(images[1]))];paths=branches=0;covered=[set(),set()]
 while frontier:
  left,right=frontier.pop();a=left.next_branch();b=right.next_branch()
  assert a==b,('branch DAG mismatch',a,b)
  assert left.trace==right.trace and left.mem==right.mem,('memory expression mismatch',a)
  for i,m in enumerate((left,right)):covered[i].update(m.cover)
  if a[0]=='return':
   for reg in (*range(16,24),28,29,30,31):assert left.reg[reg]==right.reg[reg]==('input-register',reg)
   assert (left.lo,left.hi)==(right.lo,right.hi);paths+=1
  else:
   branches+=1
   choices=(bool(a[1]),)if isinstance(a[1],int)else(False,True)
   for choice in choices:
    l=copy.deepcopy(left);q=copy.deepcopy(right);l.advance(a,choice);q.advance(b,choice);frontier.append((l,q))
 assert covered[0]==covered[1]==set(range(0,224,4))
 return dict(all_branch_outcomes_explored=True,terminal_paths=paths,conditional_nodes=branches,covered_words=56,exact_expression_DAG_memory_trace=True,callee_saved_SP_RA_and_HILO_equal=True,temporary_GPR_equality_claimed=False,arithmetic_domain='32-bit wrapping integer DAGs with arithmetic right shifts',constraints_or_sampling_used=False,scope='closed frameless integer leaf with record-relative disjoint fields')

def guard_suite():
 import csv,io
 from tools.pad_generated_object import emit_padded_assembly
 guards=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();assert len(guards)==32 and(o/'proposed-guards.csv').read_bytes().startswith(before)
 obj=o/'after-owner.o';assembly=r/'conker/asm/142560.s'
 def write(rows,name):
  s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=tuple(guards[0]),lineterminator='\n');w.writerows(rows);p=o/name;p.write_bytes(before+s.getvalue().encode());return p
 count=0
 for i,row in enumerate(guards):
  rows=[dict(x)for x in guards];rows[i]['expected']='0x%08X'%(int(row['expected'],16)^1);p=write(rows,'negative-guard-'+str(i)+'.csv')
  try:emit_padded_assembly(obj,assembly,word_patches_path=p,filename='generated_142560')
  except ValueError:count+=1
  else:raise AssertionError(('padder accepted incorrect preimage',i))
 for name,field,value in [('relocation','expected_relocations','R_MIPS_LO16:func_151193F4'),('foreign-function','function','func_151193AC')]:
  rows=[dict(x)for x in guards];rows[0][field]=value;p=write(rows,'negative-guard-'+name+'.csv')
  try:emit_padded_assembly(obj,assembly,word_patches_path=p,filename='generated_142560')
  except ValueError:count+=1
  else:raise AssertionError(('padder accepted invalid scope/binding',name))
 emitted=emit_padded_assembly(obj,assembly,word_patches_path=o/'proposed-guards.csv',filename='generated_142560');assert emitted==(o/'qualified-padded.s').read_text()
 return dict(guards=32,actual_padder_rejections=count,per_word_preimage_rejections=32,relocation_and_function_scope_rejections=2,insertions=0,omissions=0,inherited_prefix_preserved=True)
