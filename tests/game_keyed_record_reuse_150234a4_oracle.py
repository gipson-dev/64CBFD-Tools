"""Three-slot lookup, wrapped keys, reset mutations and original pointer consumer."""
from dataclasses import dataclass,replace
import itertools,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RESET,RELEASE=0x150234A4,0x15023440,0x1516D2E0
BASE,END,DESC=0x800C3CA0,0x800C3D48,0x70000
u32=lambda n:n&0xFFFFFFFF
signed16=lambda n:((n&65535)^32768)-32768
KEYS=(0,1,32766,32767,32768,0xFFFF7FFF,0xFFFF8000,0xFFFFFFFE,0xFFFFFFFF,0x7FFFFFFF,0x80000000)
@dataclass(frozen=True)
class Case:
 key:int=1
 reset:int=1
 keys:tuple=(2,3,4)
 flags:tuple=(1,255,128)
 mutation:int=0
 phase:int=0
 seed:int=0
 alias:int=0
def symbols(index=0,c=Case()):
 base=(BASE,0x80027FE0,0x9000FFF0)[index]if not c.alias else STACK+c.phase-16
 return dict(D_800C3CA0=base,D_800C3D48=base+168,func_15023440=(RESET,0x17012340,0x1EABCD00)[index])
def fixture(c=Case(),s=None):
 s=symbols(c=c)if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)};base=s['D_800C3CA0']
 for a,n in((base-64,296),(DESC-16,64)):
  for i in range(n):m.setdefault(u32(a+i),(i*29+c.seed*11+0x5A)&255)
 for i in range(3):put(m,base+56*i,c.keys[i]&65535,2);m[base+56*i+12]=c.flags[i];put(m,base+56*i+52,0x50000+i*128)
 return m
def homes(m,sp):
 for i in range(4):put(m,sp+4*i,0xB5000000+i)
def effect(m,c,s,destination,home):
 base=s['D_800C3CA0']
 if c.mutation&1:
  for i in range(3):put(m,base+56*i,0x7600+i,2);m[base+56*i+12]^=255;put(m,base+56*i+52,0x61000+i*128)
 if c.mutation&2:put(m,destination,0x5555,2)
 if c.mutation&4:put(m,home,0xFFFF8001)
 if c.mutation&8:put(m,home-12,0)
def reference(initial,c=Case(),s=None,home=None,ra=0xDEAD0000,connected=False):
 s=symbols(c=c)if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-40;put(m,sp+20,ra)
 base,end=s['D_800C3CA0'],s['D_800C3D48'];entry=base;key=u32(c.key+1);existing=selected=0;calls=[]
 def reset(destination):
  calls.append((s['func_15023440'],(destination,1)))
  if connected:calls.append((RELEASE,(read(m,destination+52),)))
  effect(m,c,s,destination,home);put(m,destination+52,0);put(m,destination,0,2);homes(m,sp)
 for i in range(3):
  stored=u32(signed16(read(m,entry,2)))
  if stored==key:
   if c.reset and m[entry+12]:
    selected=base
    for a,v in((24,entry),(40,key),(28,selected),(32,existing)):put(m,sp+a,v)
    reset(selected);entry,key,selected,existing=(read(m,sp+a)for a in(24,40,28,32))
   else:existing=entry
   break
  if stored==0:
   selected=entry
   if c.reset and m[entry+12]:
    for a,v in((24,entry),(40,key),(28,selected),(32,existing)):put(m,sp+a,v)
    reset(selected);entry,key,selected,existing=(read(m,sp+a)for a in(24,40,28,32))
   break
  entry=u32(entry+56)
 else:assert entry==end
 if entry==end:
  selected=base
  for a,v in((28,selected),(40,key),(32,existing)):put(m,sp+a,v)
  reset(selected);key,selected,existing=(read(m,sp+a)for a in(40,28,32))
 if existing:value=existing
 else:
  if selected:put(m,selected,key&65535,2)
  value=selected
 return m,calls,value
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
  super().__init__(words,memory,c,entry=entry,s=symbols(c=c)if s is None else s,connected=connected,arguments=(u32(c.key),u32(c.reset)))
  self.before=self.r[:];self.reset_address=None
 def record_call(self,t):
  count=2 if t in(ENTRY,self.syms['func_15023440'])else 1 if t==RELEASE else None;assert count is not None,hex(t)
  args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==ENTRY:self.target_home=self.r[29]
  if t==self.syms['func_15023440']:self.reset_address=args[0];assert args[1]==1
 def hook(self,t):
  c,s=self.case,self.syms;destination=self.reset_address;assert destination is not None
  effect(self.memory,c,s,destination,self.target_home)
  if t==s['func_15023440']:put(self.memory,destination+52,0);put(self.memory,destination,0,2)
  else:assert t==RELEASE
  homes(self.memory,self.r[29])
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
class CallerCode(WindowCode):
 def __getitem__(self,pc):
  if pc in self.ends:self.owner.boundary=pc
  return super().__getitem__(pc)
def original_object(core,q,out):
 text=(out/'frozen/conker/asm/49D30.s').read_text();body=re.search(r'^glabel func_150234A4\n.*?(?=^glabel |\Z)',text,re.M|re.S).group()
 p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+body+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
 q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s):
 p=[list(core.bound_blob(q[n],q[r],s))for n,r in(('original','original_refs'),('raw','refs'),('normal','normal_refs'))];assert p[0]==p[2];return p
def cases():
 rows=[Case(key=k,reset=r,keys=ks,flags=tuple((sum(ks)+i*43)&255 for i in range(3)),seed=k&7)for ks,k,r in itertools.product(itertools.product((0,1,2,-1,-32768),repeat=3),KEYS,(0,0x80000000))]
 rows +=[Case(key=1+i,flags=tuple(b if j==i else 0 for j in range(3)))for b,i in itertools.product(range(256),range(3))]
 shapes=((2,3,4),(1,3,4),(1,2,4),(0,2,4),(1,0,4),(1,2,0))
 rows +=[Case(key=k,reset=r,keys=ks,mutation=m,phase=p)for ks,k,r,m,p in itertools.product(shapes,(0,1,0xFFFFFFFF),(0,1),(0,1,2,4,8,15),(0,8))]
 return rows
def guest(core,q):
 original_object(core,q,core.ROOT/core.BUILD);rows=[(c,symbols(c=c),ENTRY)for c in cases()];seen=set()
 for i in(1,2):rows.extend((Case(key=k,keys=ks,mutation=m),symbols(i),0x17508000 if i==1 else 0x1F117FFC)for k,ks,m in itertools.product((0,0xFFFFFFFF,0xFFFF7FFF),((1,2,3),(0,2,3),(2,3,4)),(0,15)))
 for c,s,entry in rows:
  initial=fixture(c,s);wanted,calls,value=reference(initial,c,s);models=[Oracle(w,initial,c,entry=entry,s=s).run()for w in programs(core,q,s)]
  assert all((m.memory,m.calls,m.r[2])==(wanted,calls,value)for m in models),(c,s)
  assert literal(models[0])==literal(models[2]);seen.update(pc-entry for pc in models[0].visits)
 assert seen==set(range(0,312,4))-{204},sorted(set(range(0,312,4))-seen)
 aliases=0
 for c in(Case(alias=1,key=1,mutation=m,keys=ks,phase=p)for m,ks,p in itertools.product((0,1,2,4,8,15),((2,3,4),(0,3,4)),(0,8))):
  s=symbols(c=c);initial=fixture(c,s);wanted,calls,value=reference(initial,c,s);models=[Oracle(w,initial,c,s=s).run()for w in programs(core,q,s)]
  assert all((m.memory,m.calls,m.r[2])==(wanted,calls,value)for m in models),c
  assert literal(models[0])==literal(models[2]);aliases+=1
 cuts=0
 for c in(Case(reset=0),Case(keys=(1,2,3),key=3,mutation=15),Case(keys=(1,0,3),mutation=4),Case(alias=1,mutation=2)):
  s=symbols(c=c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c,s=s).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in(ps[0],ps[2]):
    m=Oracle(w,initial,c,s=s);m.cut=cut
    try:m.run();raise AssertionError('Unfired lookup cut')
    except AccessBoundary:pass
    models.append(m)
   assert literal(models[0])==literal(models[1]);cuts+=1
 return dict(cases=len(rows),reached_words=77,unreachable_increment_offset='0xCC',alias_cases=aliases,fault_prefix_cuts=cuts,
             independent_complete_memory=True,raw_and_normalized_public_semantics=True,normalized_literal_state=True,
             all256_flag_bytes=True,wrapped_u32_key_and_signed16_comparison=True,guest_only_private_home_mutations=True)
def connections(core,q):
 rom=(core.ROOT/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(RESET,RESET+100,4),struct.unpack_from('>25I',rom,0x508F0)))
 public=lambda mem:{a:v for a,v in mem.items()if not STACK-2048<=a<STACK+1024};connected=0
 for c in(Case(key=k,keys=ks,mutation=m)for k,ks,m in itertools.product((0,1,0xFFFFFFFF,0xFFFF7FFF),((1,2,3),(2,3,4),(1,0,3)),(0,1,2,4,8,15))):
  s=symbols(c=c);initial=fixture(c,s);wanted,calls,value=reference(initial,c,s,connected=True);models=[Oracle(w,initial,c,s=s,connected=helper).run()for w in programs(core,q,s)]
  assert all((public(m.memory),m.calls,m.r[2])==(public(wanted),calls,value)for m in models),c
  assert literal(models[0])==literal(models[2]);connected+=1
 start,end,null=0x15024720,0x15024754,0x150265B0;window=struct.unpack_from('>13I',rom,0x51BD0);caller=0
 for c,flag in itertools.product((Case(key=k,keys=ks,mutation=m)for k,ks,m in itertools.product((0,1,0xFFFFFFFF),((1,2,3),(2,3,4),(1,0,3)),(0,1,4,8,15))),(0,1,128,255)):
  c=replace(c,reset=int(flag==0));s=symbols(c=c);initial=fixture(c,s);initial[DESC+4]=flag;put(initial,STACK+0x15C,c.key)
  wanted,calls,value=reference(initial,c,s,ra=0x15024744);models=[]
  for w in programs(core,q,s):
   code=dict(zip(range(ENTRY,ENTRY+312,4),w));code[end]=code[null]=0;m=Oracle(window,initial,c,entry=start,s=s,connected=code);m.r[18]=DESC;m.code=CallerCode(m.code,m);m.code.ends=(end,null)
   try:m.run();raise AssertionError('Missing pointer consumer boundary')
   except WindowBoundary:pass
   assert(m.memory,m.calls,m.r[2])==(wanted,[(ENTRY,(u32(c.key),c.reset)),*calls],value),(c,flag)
   assert m.r[16]==value and m.boundary==(end if value else null),(c,flag,m.r[16],value,m.boundary)
   models.append(m)
  assert literal(models[0])==literal(models[2]);caller+=1
 return dict(original_reset_cases=connected,original_reset_words=25,bounded_release_provider=True,caller_cases=caller,caller_words=13,
             caller_start=hex(start),caller_end=hex(end),null_branch=hex(null),pointer_return_consumed=True,whole_caller_not_qualified=True)

def native_text(core,selected=None):
 s=core.SELECTED if selected is None else selected
 return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
typedef struct {u32 before[4];struct163 rows[4];u32 after[4];} Backing;
static Backing backing,expected;
#define D_800C3CA0 backing.rows
#define D_800C3D48 backing.rows[3]
void func_15023440(struct163 *,s32);
'''+s+r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(struct163)==56&&__builtin_offsetof(struct163,unk0)==0&&__builtin_offsetof(struct163,unkC)==12&&__builtin_offsetof(struct163,unk34)==52)?1:-1];
static unsigned mode,calls,error,expectedCalls;static int wantedReset;static u8 objects[6][32];
static void fill(void*d,unsigned n,u8 value){u8*p=d;unsigned i;for(i=0;i<n;i++)p[i]=(u8)(value+i*17);}
static void bytes(void*d,const void*s,unsigned n){u8*p=d;const u8*q=s;unsigned i;for(i=0;i<n;i++)p[i]=q[i];}
static int equal(const void*a,const void*b,unsigned n){const u8*p=a,*q=b;unsigned i;for(i=0;i<n;i++)if(p[i]!=q[i])return 0;return 1;}
static void mutate(Backing*p,int index){unsigned i;
 if(mode&1)for(i=0;i<3;i++){p->rows[i].unk0=(s16)(0x7600+i);p->rows[i].unkC^=255;p->rows[i].unk34=objects[3+i];}
 if(mode&2)p->rows[index].unk0=0x5555;
 p->rows[index].unk34=0;p->rows[index].unk0=0;
}
void func_15023440(struct163*p,s32 reset){
 if(calls++!=0||wantedReset<0||p!=&backing.rows[wantedReset]||reset!=1){error=1;return;}
 mutate(&backing,wantedReset);
}
static int run(void){
 static const s16 values[]={0,1,2,-1,-32768};
 static const u32 keys[]={0,1,32766,32767,32768,0xFFFF7FFF,0xFFFF8000,0xFFFFFFFE,0xFFFFFFFF,0x7FFFFFFF,0x80000000};
 unsigned a,b,c,k,r,f,md,i,count=0,key;int chosen,existing;struct163*answer,*actual;
 for(a=0;a<5;a++)for(b=0;b<5;b++)for(c=0;c<5;c++)for(k=0;k<11;k++)for(r=0;r<2;r++)for(f=0;f<8;f++)for(md=0;md<4;md++){
  fill(&backing,sizeof(backing),0xA5);backing.rows[0].unk0=values[a];backing.rows[1].unk0=values[b];backing.rows[2].unk0=values[c];
  for(i=0;i<3;i++){backing.rows[i].unkC=(f&(1u<<i))?(u8)(128+i*43):0;backing.rows[i].unk34=objects[i];}
  bytes(&expected,&backing,sizeof(backing));mode=md;calls=error=0;wantedReset=-1;key=keys[k]+1u;chosen=existing=-1;
  for(i=0;i<3;i++){
   if((u32)(s32)backing.rows[i].unk0==key){if(r&&backing.rows[i].unkC){chosen=0;wantedReset=0;}else existing=(int)i;break;}
   if(backing.rows[i].unk0==0){chosen=(int)i;if(r&&backing.rows[i].unkC)wantedReset=(int)i;break;}
  }
  if(i==3){chosen=0;wantedReset=0;}
  expectedCalls=wantedReset>=0;
  if(expectedCalls)mutate(&expected,wantedReset);
  if(existing>=0)answer=&backing.rows[existing];else{if(chosen>=0)expected.rows[chosen].unk0=(s16)key;answer=chosen>=0?&backing.rows[chosen]:0;}
  actual=func_150234A4(keys[k],r?(s32)0x80000000:0);
  if(actual!=answer||calls!=expectedCalls||error)return 1;
  if(!equal(&backing,&expected,sizeof(backing)))return 2;
  count++;
 }
 return count==88000?0:3;
}
'''+START
def controls(core):
 s=core.SELECTED
 changes={
  'wrong_key_increment':('key++;','key += 2;'),
  'wrong_key_width':('key++;','key = (u16)(key + 1);'),
  'unsigned_stored_key':('(u32)(s32)entry->unk0','(u32)(u16)entry->unk0'),
  'wrong_match_reset_target':('                selected = D_800C3CA0;','                selected = entry;'),
  'wrong_match_flag':('if (reset && entry->unkC != 0)','if (reset && entry->unkC == 0)'),
  'wrong_reset_mode':('func_15023440(selected, 1);','func_15023440(selected, 0);'),
  'wrong_empty_test':('if (entry->unk0 == 0)','if (entry->unk0 == 1)'),
  'skip_empty_reset':('func_15023440(entry, 1);','(void)entry;'),
  'skip_existing_return':('return existing;','return selected;'),
  'skip_key_store':('selected->unk0 = key;','(void)key;'),
  'wrong_selected_key':('selected->unk0 = key;','selected->unk0 = key + 1;'),
  'wrong_pointer_return':('return selected;','return NULL;'),
 }
 assert all(a in s for a,b in changes.values())
 return {n:s.replace(a,b)for n,(a,b)in changes.items()}
def native(core,out):
 rows=[('valid-'+opt[1:],None,opt,True)for opt in('-O0','-O2','-O3')]+[(n,b,'-O2',False)for n,b in controls(core).items()];records=[]
 for name,body,opt,valid in rows:
  p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
  compile=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
  assert compile.returncode==0 and not compile.stdout and not compile.stderr,(name,compile.stdout,compile.stderr)
  run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
  assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
  records.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
 return dict(cases_per_profile=88000,profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),records=records,
             typed_objects_and_all_offsets=True,complete_table_and_canaries=True,backed_end_marker_at_table_plus168=True,
             private_frame_aliases_and_home_mutations_guest_only=True)
