"""Selector record coordinate payload: independent public bytes and literal execution."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-point-selector-payload-1500A7E8-match';F='func_1500A7E8';ENTRY=0x1500A7E8
ACTOR,EFFECT,RECORD,RECORDS=0x22000,0x24000,0x26000,0x28000
LOOKUP,FACTORY,COPY,PARENT,TABLE,ALLOC=0x151149AC,0x1516037C,0x10022EC0,0x1500A94C,0x80082BFC,0x15167A68
SYMS=dict(D_80082BF4=0x80082BF4,func_151149AC=LOOKUP,func_1516037C=FACTORY,memcpy=COPY)
signed16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 command:int=80
 found:bool=True
 allocated:bool=True
 seed:int=0
 mode:int=0
 destination:int=0
 phase:int=0
 private:int=0

def output(c,record=RECORD):return(EFFECT,ACTOR,record-16)[c.destination]
def coords(c):return(-32768,-1,32767)if c.seed==0 else tuple(signed16(c.seed*257+i*19357)for i in range(3))
def store_coords(m,p,values):
 for i,v in enumerate(values):put(m,p+16+i*2,v&65535,2)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-2048,512)}
 for base in(ACTOR,EFFECT,RECORD,RECORDS):m.update({base+i:(i*13+c.seed)&255 for i in range(-64,1024)})
 for i in range(6):m[s['D_80082BF4']+i]=(2+i)if c.seed==0 else(c.seed+i*71)&255
 store_coords(m,RECORD,coords(c));return m
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}
def lookup_effect(m,c,s,record=RECORD):
 if c.mode&1:store_coords(m,record,(-20000,123,30000))
 if c.mode&2:
  for i in range(6):m[s['D_80082BF4']+i]^=255
 if c.private&1:put(m,STACK+c.phase,ACTOR+128)
def factory_effect(m,c,record=RECORD):
 if c.mode&4:store_coords(m,record,(-30000,0,32767));m[ACTOR+3]^=85
def packet(m,p):return struct.pack('>III',0xC3C80000,0x40800000,p)+b''.join(struct.pack('>I',bits(float(signed16(read(m,p+16+i*2,2)))))for i in range(3))
def reference(initial,c,s=SYMS,entered=None):
 m=dict(initial);entered=STACK+c.phase if entered is None else entered;sp=entered-80;selected=m[s['D_80082BF4']+c.command-80];calls=[(s['func_151149AC'],(selected,))];lookup_effect(m,c,s);observations=[]
 if c.found:
  p=sp+48;h=sp+72;data=packet(m,RECORD)
  for i,v in enumerate(data):m[p+i]=v
  m[h]=0;m[h+1]=23;put(m,h+2,300,2);m[h+4]=0
  actor=read(m,STACK+c.phase)if c.private&1 else ACTOR
  calls.append((s['func_1516037C'],(h,actor,24,255,1)));observations.append((bytes(m[h+i]for i in range(6)),data));factory_effect(m,c)
  if c.allocated:
   dest=output(c)+24;calls.append((s['memcpy'],(dest,p,24)))
   for i,v in enumerate(data):m[dest+i]=v
 return m,calls,observations

class Oracle(RayOracle):
 def __init__(self,words,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None,record=RECORD,callbacks=()):
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,c.command&0xffffffff),connected=connected)
  self.case=c;self.syms=s;self.trace=[];self.packets=[];self.record=record;self.callbacks=set(callbacks)
 def get(self,address,size):
  v=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,v))
  return v
 def put(self,address,value,size):
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  s=self.syms;n={s['func_151149AC']:1,s['func_1516037C']:5,s['memcpy']:3,ENTRY:2,ALLOC:6}.get(target,2 if target in self.callbacks else None)
  assert n is not None,('Unbounded provider',hex(target));args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==s['func_1516037C']:
   h=self.r[4];self.packets.append((bytes(self.memory[h+i]for i in range(6)),bytes(self.memory[h-24+i]for i in range(24))))
 def hook(self,target):
  c=self.case;s=self.syms;value=0
  if target==s['func_151149AC']:lookup_effect(self.memory,c,s,self.record);value=self.record if c.found else 0
  elif target==s['func_1516037C']:factory_effect(self.memory,c,self.record);value=output(c,self.record)if c.allocated else 0
  elif target==s['memcpy']:
   a,b,n=self.arguments(3);assert n in(6,24);data=[self.memory[b+i]for i in range(n)]
   for i,v in enumerate(data):self.memory[a+i]=v
   value=a
  elif target==ALLOC:value=output(c,self.record)if c.allocated else 0
  else:assert target in self.callbacks
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.packets,m.condition)
def verify(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.packets)==(public(want),calls,obs),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.saved_f
def cases():
 for seed,command in itertools.product(range(256),range(80,86)):yield Case(seed=seed,command=command)
 for command,found,allocated,mode,destination,phase in itertools.product(range(80,86),(False,True),(False,True),range(8),range(3),(0,8)):yield Case(command=command,found=found,allocated=allocated,mode=mode,destination=destination,phase=phase,seed=command*7&255)
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visited;prefixes=delays=0
 for c in(Case(found=False),Case(allocated=False),Case(),Case(command=85,seed=255,mode=7,destination=2,phase=8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.root_accesses):
   ms=[]
   for words in programs:
    m=Oracle(words,initial,c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Unfired access cut',cut))
    assert m.root_accesses==cut;ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of)==(ms[2].current_pc,ms[2].delay_of);prefixes+=1;delays+=ms[0].delay_of is not None
 lazy=0
 for found,allocated in((False,False),(True,False)):
  c=Case(found=found,allocated=allocated);initial=fixture(c)
  for i in range(64):initial.pop(EFFECT+i,None)
  if not found:
   for i in range(22):initial.pop(RECORD+i,None)
  for words in programs:Oracle(words,initial,c).run()
  lazy+=1
 private=0
 for command,found,phase in itertools.product((80,85),(False,True),(0,8)):
  c=Case(command=command,found=found,phase=phase,private=1);initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);private+=1
 rebased=0
 for k,(entry,ids)in enumerate(((0x17007FFC,0x80017FFC),(0x2500FFFC,0x80028000),(0x15008000,0x8001FFFC))):
  s=dict(D_80082BF4=ids,func_151149AC=entry+0x10004,func_1516037C=entry+0x20008,memcpy=entry+0x3000C);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for command,found,allocated,phase in itertools.product(range(80,86),(False,True),(False,True),(0,8)):
   c=Case(command=command,found=found,allocated=allocated,phase=phase,mode=7);initial=fixture(c,s);ms=[]
   for words in ps:m=Oracle(words,initial,c,s,entry).run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 return dict(cases=count,executions=count*3,covered_words=56,body_words=56,frame=80,guards=0,complete_state_and_trace_equal=True,independent_public_packet_reference=True,access_prefix_pairs=prefixes,delay_slot_cuts=delays,lazy_unmapped_failure_paths=lazy,private_home_cases=private,rebase_layouts=3,rebase_cases=rebased,portable_fault_private_home_FCSR_claimed=False)

def integration_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>17I',rom,0x37DFC));lookup=list(struct.unpack_from('>28I',rom,0x141E5C));factory=list(struct.unpack_from('>32I',rom,0x18D82C));table=list(struct.unpack_from('>89I',rom,0x2276BC));assert table[80:86]==[ENTRY]*6
 programs=[linked(p,'integration-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];visited=set();count=0;coverage=set();seen=set()
 for command,lookup_case,allocated,phase,dest in itertools.product((-1,0,*range(80,86),89),range(6),(False,True),(0,8),(0,2)):
  c=Case(command=command,allocated=allocated,phase=phase,destination=dest);initial=fixture(c);chosen=2+(command-80)if command in range(80,86)else 2
  n=(-1,0,3,3,3,3)[lookup_case];hit=(-1,-1,0,1,2,-1)[lookup_case];record=RECORDS+max(hit,0)*0xA0
  put(initial,0x800DBEF0,n&0xffffffff);put(initial,0x800DBEF4,RECORDS)
  for j in range(3):initial[RECORDS+j*0xA0+0x72]=chosen if j==hit else(200+j);store_coords(initial,RECORDS+j*0xA0,(-32768+j,17-j,32767-j))
  for j,w in enumerate(table):put(initial,TABLE+j*4,w)
  ms=[]
  for words in programs:
   connected={base+i*4:w for base,body in((ENTRY,words),(LOOKUP,lookup),(FACTORY,factory))for i,w in enumerate(body)};m=Oracle(parent,initial,c,entry=PARENT,connected=connected,record=record).run();ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);m=ms[0];visited.update(m.visits);coverage.update(pc for pc in m.visits if LOOKUP<=pc<LOOKUP+112 or FACTORY<=pc<FACTORY+128);expected=dict(initial)
  if command in range(80,86):
   seen.add(command);assert m.calls[:2]==[(ENTRY,(ACTOR,command)),(LOOKUP,(chosen,))]
   if hit>=0:
    h=STACK+phase-24-8;p=h-24;data=packet(initial,record);header=bytes((0,23,1,44,0,initial[h+5]));assert m.packets==[(header,data)]and(ALLOC,(53,1,48,1,255,1))in m.calls
    if allocated:
     destp=output(c,record)
     for j,v in enumerate(header):expected[destp+14+j]=v
     put(expected,destp+20,ACTOR)
     for j,v in enumerate(data):expected[destp+24+j]=v
    else:assert not any(t==COPY for t,args in m.calls)
   else:assert len(m.calls)==2 and not m.packets
  else:assert not m.calls
  assert public(m.memory)==public(expected),(c,lookup_case);count+=1
 # Null selector exercises lookup's early return; caller's null callback path is independent.
 for null_selector in(False,True):
  c=Case(command=80);initial=fixture(c)
  for j,w in enumerate(table):put(initial,TABLE+j*4,0 if not null_selector else w)
  if null_selector:initial[SYMS['D_80082BF4']]=0
  ms=[]
  for words in programs:
   connected={base+i*4:w for base,body in((ENTRY,words),(LOOKUP,lookup),(FACTORY,factory))for i,w in enumerate(body)};m=Oracle(parent,initial,c,entry=PARENT,connected=connected).run();ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2])and public(ms[0].memory)==public(initial);visited.update(ms[0].visits);coverage.update(ms[0].visits)
  assert len(ms[0].calls)==(2 if null_selector else 0);count+=1
 assert seen==set(range(80,86))and set(range(PARENT,PARENT+68,4))<=visited
 assert set(range(LOOKUP,LOOKUP+112,4))<=coverage and set(range(FACTORY,FACTORY+128,4))<=coverage
 return dict(cases=count,programs=3,callback_slots=sorted(seen),parent_words=17,parent_covered_words=len(set(range(PARENT,PARENT+68,4))&visited),lookup_words=28,lookup_covered_words=len(set(range(LOOKUP,LOOKUP+112,4))&coverage),factory_words=32,factory_covered_words=len(set(range(FACTORY,FACTORY+128,4))&coverage),current_lookup_matches=False,current_factory_matches=True,complete_original_dispatcher=True,bounded_providers=['func_15167A68','memcpy'],signed_count_and_search_first_middle_last_missing=True)

def controls(selected):
 return dict(wrong_selector=selected.replace('command - 0x50','0'),wrong_lower=selected.replace('-400.0f','-200.0f'),wrong_scale=selected.replace('4.0f','5.0f'),unsigned_x=selected.replace('*(s16 *)(payload.record + 0x10)','*(u16 *)(payload.record + 0x10)'),wrong_y=selected.replace('payload.record + 0x12','payload.record + 0x10'),wrong_z=selected.replace('payload.record + 0x14','payload.record + 0x12'),wrong_kind=selected.replace('= 23;','= 22;'),wrong_duration=selected.replace('= 300;','= 299;'),wrong_size=selected.replace('sizeof(payload), 255','sizeof(payload)-4, 255'),wrong_slot=selected.replace(', 255,',', 254,'),wrong_context=selected.replace(', 255, 1',', 255, 0'),skip_copy=selected.replace('if (effect != NULL)','if (effect == NULL)'),short_copy=selected.replace('&payload, sizeof(payload));','&payload, sizeof(payload)-4);'),wrong_destination=selected.replace('+ 0x18','+ 0x14'))

def compiled_controls(selected):
 effective=[]
 for name,text in controls(selected).items():
  assert text!=selected;obj,diag=compile_owner(r,o,text,'negative-'+name);assert not diag;words=linked(obj,'negative-link-'+name);failed=False
  for c in(Case(),Case(command=85,seed=255),Case(found=False),Case(allocated=False),Case(mode=7,destination=2)):
   initial=fixture(c)
   try:m=Oracle(words,initial,c).run();verify(m,initial,c)
   except(AssertionError,KeyError):failed=True;break
  assert failed,('Ineffective control',name);effective.append(name)
 return dict(effective_IDO_controls=effective,count=len(effective))

def native_harness(selected):
 head=selected[:selected.index('/* Resolve')];body=selected[selected.index('/* Resolve'):];t=head+r'''
EffectPointIds36680 D_80082BF4;
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(UnkB060C)==24&&sizeof(Header)==6&&sizeof(EffectPointIds36680)==6&&__builtin_offsetof(UnkB060C,record)==8&&__builtin_offsetof(UnkB060C,unk14)==20&&__builtin_offsetof(Header,unk2)==2)?1:-1];
static union {u32 align;u8 b[256];} actor,record,effect,ea,er,ee;
static u32 mode,seed,calls,error,found,allocated,wantedId,destination;static u8 *wantedDest;static UnkB060C expectedPayload;
static s16 *coord(u8*p,u32 i){return (s16*)(p+16+i*2);}
static void lookup_effect(u8*p){u32 i;if(mode&1){*coord(p,0)=-20000;*coord(p,1)=123;*coord(p,2)=30000;}if(mode&2)for(i=0;i<6;i++)D_80082BF4.values[i]^=255;}
__attribute__((noinline)) u8 *func_151149AC(u8 id){calls++;if(calls!=1||id!=wantedId)error=1;lookup_effect(record.b);return found?record.b:0;}
__attribute__((noinline)) struct225 *func_1516037C(Header*h,struct226*a,s32 size,u8 slot,s32 context){calls++;if(calls!=2||h->unk0||h->unk1!=23||h->unk2!=300||h->unk4||a!=(struct226*)actor.b||size!=24||slot!=255||context!=1)error=1;if(mode&4){*coord(record.b,0)=-30000;*coord(record.b,1)=0;*coord(record.b,2)=32767;actor.b[3]^=85;}return allocated?(struct225*)wantedDest:0;}
__attribute__((noinline)) void *memcpy(void*a,const void*b,u32 n){u32 i;calls++;if(calls!=3||a!=wantedDest+24||n!=24){error=1;return a;}for(i=0;i<n;i++)((u8*)a)[i]=((const u8*)b)[i];return a;}
'''
 for name,text in dict(selected=body,**{n:b[b.index('/* Resolve'):]for n,b in controls(selected).items()}).items():t+=text.replace('void '+F,'void test_'+name)+'\n'
 t+=r'''
typedef void(*Fn)(struct226*,s32);
static int check(Fn fn){u32 i,j,k,command,flags,wantCalls;u8 oldIds[6],*out,*ep;
 for(seed=0;seed<256;seed++)for(command=80;command<86;command++)for(flags=0;flags<96;flags++){
  found=flags&1;allocated=(flags>>1)&1;mode=(flags>>2)&7;destination=flags/32;
  for(i=0;i<256;i++){actor.b[i]=ea.b[i]=(u8)(i*13+seed);record.b[i]=er.b[i]=(u8)(i*17+seed);effect.b[i]=ee.b[i]=(u8)(i*19+seed);}
  for(i=0;i<3;i++){s16 v=seed?(s16)(seed*257+i*19357):(i==0?-32768:i==1?-1:32767);*coord(record.b,i)=*coord(er.b,i)=v;}
  for(i=0;i<6;i++)oldIds[i]=D_80082BF4.values[i]=seed?(u8)(seed+i*71):(u8)(i+2);wantedId=oldIds[command-80];
  if(mode&1){*coord(er.b,0)=-20000;*coord(er.b,1)=123;*coord(er.b,2)=30000;}
  expectedPayload.unk0=-400.0f;expectedPayload.unk4=4.0f;expectedPayload.record=record.b;expectedPayload.unkC=(f32)*coord(er.b,0);expectedPayload.unk10=(f32)*coord(er.b,1);expectedPayload.unk14=(f32)*coord(er.b,2);
  wantedDest=destination==0?effect.b+32:destination==1?actor.b+32:record.b;out=destination==0?ee.b+32:destination==1?ea.b+32:er.b;
  if(found){if(mode&4){*coord(er.b,0)=-30000;*coord(er.b,1)=0;*coord(er.b,2)=32767;ea.b[3]^=85;}if(allocated){ep=(u8*)&expectedPayload;for(i=0;i<24;i++)out[24+i]=ep[i];}}
  wantCalls=1+(found?1+allocated:0);calls=error=0;fn((struct226*)actor.b,(s32)command);if(error||calls!=wantCalls)return 1;
  for(j=0;j<256;j++)if(actor.b[j]!=ea.b[j]||record.b[j]!=er.b[j]||effect.b[j]!=ee.b[j])return 1;
  for(k=0;k<6;k++)if(D_80082BF4.values[k]!=(u8)(oldIds[k]^((mode&2)?255:0)))return 1;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''
 for i,name in enumerate(controls(selected)):t+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START
def run_native(selected):
 p=o/'native-v1.c';p.write_text(native_harness(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-v1'+opt);cmd=native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)];build=subprocess.run(cmd,cwd=r,capture_output=True,text=True);assert build.returncode==0,(opt,build.stdout,build.stderr);run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stdout,run.stderr);profiles[opt]=dict(exit=run.returncode,cases=147456,UBSan=True)
 return dict(cases=147456,negative_controls=len(controls(selected)),profiles=profiles,finite_signed_coordinates_and_lookup_mutation=True,all_selector_bytes=True,output_aliases=True,SDK_ABI=True,portable_private_home_fault_FCSR_claimed=False)
