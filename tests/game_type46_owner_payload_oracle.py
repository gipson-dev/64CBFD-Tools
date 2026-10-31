"""Type46 owner callback: guest ordering, original dispatcher and native payload ABI.

Automatic padding is compared only in the seeded guest model. Native tests
check initialized fields, service ordering, captured identity and fences.
Providers are bounded except in the explicitly connected retail-helper cases.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.experiments import game_type46_owner_payload_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests import game_type46_distance_record_oracle as distance
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
put,read,STACK=distance.put,distance.read,distance.STACK
ACTOR,RECORD=distance.ACTOR,distance.RECORD
FACTORY,COPY,FINAL=0x150C5370,0x10022EC0,0x1514EC1C
SYMS=dict(D_800A5DE4=0x800A5DE4,D_800A5DE8=0x800A5DE8,D_800A5DEC=0x800A5DEC,D_800A5DF0=0x800A5DF0,func_150C5370=FACTORY,memcpy=COPY,func_1514EC1C=FINAL)
r=Path.cwd();o=r/source.BUILD
POINTS=((0,0x80000000,0x3F800000),(0x3FA00000,0xC1900000,0x42C80000),(1,0x80000001,0x00800000),(0x7F800000,0xFF800000,0x7FC12345))
@dataclass(frozen=True)
class Case:
 allocated:bool=True
 mode:int=0
 uid:int=167
 point:tuple=POINTS[1]
 phase:int=0
 record:int=RECORD
 owner:int=ACTOR

def constants():
 elf=(o/'before-conker_build_conker.us.elf').read_bytes()
 return struct.unpack_from('>4I',elf,source.elf_slot_offset(elf,0x800A5DE4,16))

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(c.owner,c.record):m.update({base+i:(i*13+0x59)&255 for i in range(-16,256)})
 m[c.owner+0x3B]=c.uid
 for i,v in enumerate(c.point):put(m,c.owner+20+4*i,v)
 for n,v in zip(('D_800A5DE4','D_800A5DE8','D_800A5DEC','D_800A5DF0'),constants()):put(m,s[n],v)
 return m

def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}

def mutate(m,c,bit):
 if c.mode&bit:
  m[c.owner+0x3B]^=255
  for i in range(3):put(m,c.owner+20+4*i,0x40000000+i)

def packets(initial,c,s=SYMS):
 sp=STACK+c.phase-88
 descriptor=bytearray(initial[sp+52+i]for i in range(36))
 descriptor[:12]=b''.join(struct.pack('>I',read(initial,s[n]))for n in ('D_800A5DE4','D_800A5DE8','D_800A5DEC'))
 descriptor[12:24]=b''.join(struct.pack('>I',v)for v in c.point)
 descriptor[24]=1;descriptor[28:32]=struct.pack('>I',read(initial,s['D_800A5DF0']));descriptor[32]=1
 payload=bytearray(initial[sp+28+i]for i in range(20))
 struct.pack_into('>I',payload,0,c.owner);payload[4]=c.uid;payload[5]=6
 struct.pack_into('>3I',payload,8,0,0xC3340000,0x429A0000)
 return bytes(descriptor),bytes(payload)

def reference(initial,c,s=SYMS):
 m=dict(initial);d,p=packets(initial,c,s);sp=STACK+c.phase-88
 calls=[(s['func_150C5370'],(sp+52,20))];mutate(m,c,1)
 if c.allocated:
  m.update({c.record+24+i:v for i,v in enumerate(d)})
  calls.append((s['memcpy'],(c.record+200,sp+28,20)))
  m.update({c.record+200+i:v for i,v in enumerate(p)});mutate(m,c,2)
  calls.append((s['func_1514EC1C'],(c.record,c.owner,21)))
 return m,calls,d,p

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS):
  self.c,self.s=c,s;self.packets=[];self.trace=[]
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.owner,))
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  sizes={self.s['func_150C5370']:2,self.s['memcpy']:3,self.s['func_1514EC1C']:3}
  assert t in sizes,hex(t)
  args=self.arguments(sizes[t]);self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==self.s['func_150C5370']:self.packets.append(bytes(self.memory[args[0]+i]for i in range(36)))
  if t==self.s['memcpy']:self.packets.append(bytes(self.memory[args[1]+i]for i in range(args[2])))
 def hook(self,t):
  args=self.calls[-1][1];result=0xC0DEC0DE
  if t==self.s['func_150C5370']:
   assert args[1]==20
   mutate(self.memory,self.c,1);result=self.c.record if self.c.allocated else 0
   if result:self.memory.update({result+24+i:v for i,v in enumerate(self.packets[0])})
  elif t==self.s['memcpy']:
   distance.copy_bytes(self.memory,*args);mutate(self.memory,self.c,2);result=args[0]
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,result

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[source.FUNCTION];asm,unknown=emit_function(text,f,rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def guest_suite():
 truth=list(struct.unpack_from('>58I',(o/'before-conker_conker.us.bin').read_bytes(),source.ROM));cases=0;seen=set();cuts=delaycuts=0;rebases=0;aliases=0
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  syms=SYMS if j==0 else dict(zip(SYMS,(0x81007FFC+j*0x10000,0x82008000+j*0x10000,0x8300FFFC+j*0x10000,0x84000000+j*0x10000,entry+0x10000,entry+0x20000,entry+0x30000)))
  images=[linked(o/n,'rebase-%d-%d'%(j,k),entry,syms)for k,n in enumerate(('original-func_1514D564.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_179F30.c.o'))]
  assert all(w==images[0]for w in images)
  if j==0:assert images[0]==truth
  rebases+=1
  for allocated,mode,uid,point,phase in itertools.product((False,True),range(4),(0,1,127,128,255),POINTS,(0,8)):
   c=Case(allocated,mode,uid,point,phase);initial=fixture(c,syms);expected,calls,d,p=reference(initial,c,syms);pair=[]
   for words in images[:2]:
    m=Oracle(words,initial,c,entry,syms).run();assert public(m.memory)==public(expected),(c,'public');assert m.calls==calls,(c,m.calls,calls);assert m.packets==([d,p]if allocated else[d]);pair.append(m)
   assert complete(pair[0])==complete(pair[1])and pair[0].trace==pair[1].trace
   seen.update(m.visits);cases+=1
  if j==0:
   for owner,record,mode,phase in itertools.product((ACTOR,STACK+128),(ACTOR,ACTOR-24,STACK-512),range(4),(0,8)):
    c=Case(owner=owner,record=record,mode=mode,phase=phase);initial=fixture(c);expected,calls,d,p=reference(initial,c)
    models=[Oracle(w,initial,c).run()for w in images[:2]]
    assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace
    assert public(models[0].memory)==public(expected)and models[0].calls==calls
    assert models[0].packets==[d,p];aliases+=1
   for allocated in (False,True):
    c=Case(allocated=allocated,mode=3);initial=fixture(c);good=Oracle(images[0],initial,c).run()
    for cut in range(good.root_accesses):
     pair=[]
     for words in images[:2]:
      m=Oracle(words,initial,c);m.root_fault=cut
      try:m.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('Unfired guest fault')
      assert m.root_accesses==cut;pair.append(m)
     assert complete(pair[0])==complete(pair[1])and pair[0].trace==pair[1].trace
     assert(pair[0].current_pc,pair[0].delay_of)==(pair[1].current_pc,pair[1].delay_of)
     cuts+=1;delaycuts+=pair[0].delay_of is not None
 return dict(cases=cases,executions=cases*2,guest_alias_cases=aliases,rebases=rebases,visited_words=len(seen&set(range(source.ENTRY,source.ENTRY+232,4))),fault_cuts=cuts,delay_fault_cuts=delaycuts,all_four_images_equal=True,seeded_guest_padding=True,captured_owner_identity=True,opaque_services=True,portable_overlap_claim=False)

class CallerOracle(TimingOracle):
 def __init__(self,words,memory,flags,returned,phase=0):
  self.flags,self.returned=flags,returned
  super().__init__(words,memory,phase=phase,entry=0x1514D15C,arguments=(ACTOR,))
 def record_call(self,t):
  sizes={0x15155FD4:1,0x15155780:2,0x1514EE70:1,0x1514CA80:4,source.ENTRY:1}
  assert t in sizes,hex(t);args=self.arguments(sizes[t]);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  args=self.calls[-1][1];result=self.returned
  if t==0x15155FD4:result=0
  elif t==0x1514CA80:
   for p in args[1:]:put(self.memory,p,0)
   result=self.flags
  elif t==source.ENTRY:assert args==(ACTOR,)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=result

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();words=list(struct.unpack_from('>109I',rom,0x17A60C));allwords=struct.unpack('>%dI'%(len(rom)//4),rom)
 assert [i*4 for i,w in enumerate(allwords)if w==source.ENTRY]==[0x22F570]
 assert not any(w in (0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in allwords)
 assert tuple(struct.unpack_from('>23I',rom,0x22F530))[16]==source.ENTRY
 cases=0;seen=set();sites=set()
 for flags,select,ret,phase,blocked in itertools.product(range(8),(0,16),(0,1,0x80000000,0xFFFFFFFF),(0,8),(False,True)):
  m=fixture(Case(phase=phase));put(m,ACTOR+0x2F4,int(blocked));put(m,0x8008AACC,0x1514EE70);m[0x800BE616]=1
  put(m,0x8008AA70,0);put(m,0x8008AA70+16*4,source.ENTRY)
  m[0x800A5ED8]=select;m[0x800A5EC0]=select;put(m,0x8008AB90,0x300000);m[0x300000]=select
  q=CallerOracle(words,m,flags,ret,phase).run();expected=0 if blocked or flags==0 else 1
  assert q.r[2]==expected,(flags,select,ret,blocked,q.r[2]);seen.update(q.visits)
  n=sum(t==source.ENTRY for t,args in q.calls)
  assert n==(0 if blocked or select==0 else int(bool(flags&4))+int(bool(flags&2))+int(bool(flags&2 and flags&1)))
  sites.update(pc for pc in q.visits if pc in (0x1514D264,0x1514D2A4,0x1514D2F0));cases+=1
 assert sites=={0x1514D264,0x1514D2A4,0x1514D2F0}
 return dict(cases=cases,original_dispatcher_words=109,callback_sites=sorted(hex(x)for x in sites),one_owner_argument=True,callback_return_ignored=True,unique_table_slot=16,literal_pointer_ROM='0x22F570',no_direct_JAL=True)

def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();connected={}
 for va,at,n in ((FACTORY,0xF2820,48),(0x15167A68,0x194F18,28),(0x15168A4C,0x195EFC,20),(COPY,0x22EC0,11),(0x15143E64,0x171314,12)):
  body=struct.unpack_from('>%dI'%n,rom,at);assert tuple(struct.unpack_from('>%dI'%n,elf,source.elf_slot_offset(elf,va,n*4)))==body
  connected.update({va+i*4:w for i,w in enumerate(body)})
 images=[list(struct.unpack_from('>58I',rom,source.ROM)),linked(o/'selected-final.o','connected-selected')];cases=0;seen=set()
 for allocated,oldhead,phase,point in itertools.product((False,True),(0,distance.HEAD),(0,8),distance.POINTS[:3]):
  c=distance.Case(allocated=allocated,oldhead=oldhead,phase=phase,point=point);initial=distance.fixture(c)
  initial.update({SYMS['D_800A5DE4']+i:v for i,v in enumerate(struct.pack('>4I',*constants()))})
  models=[distance.DistanceOracle(w,initial,c,entry=source.ENTRY,connected=connected,arguments=(ACTOR,)).run()for w in images]
  a,b=models;assert complete(a)==complete(b)and a.trace==b.trace;seen.update(a.visits)
  root=Case(allocated=allocated,uid=167,point=point[:3],phase=phase);d,p=packets(initial,root)
  assert a.target_entries==[(STACK+phase-36,20)]
  if allocated:
   assert a.copy_packets==[d,p]
   assert bytes(a.memory[RECORD+24+i]for i in range(36))==d
   assert bytes(a.memory[RECORD+200+i]for i in range(20))==p
   assert a.calls[-1]==(FINAL,(RECORD,ACTOR,21))
  else:assert len(a.calls)==3
  cases+=1
 assert len(seen&set(range(source.ENTRY,source.ENTRY+232,4)))==58
 assert len(seen&set(connected))==119
 return dict(cases=cases,executions=cases*2,root_words=58,provider_and_helper_words=119,original_factory_initializer_memcpy_sqrt=True,original_padding_and_constants=True,heap_and_final_service_bounded=True,gameplay_and_hardware_claim=False)

def controls():
 b=source.SELECTED
 changes={'wrong_id':('owner[0x3B]','owner[0x3A]'),'wrong_command':('payload.command = 6','payload.command = 5'),'wrong_zero':('payload.zero = 0.0f','payload.zero = 1.0f'),'wrong_lower':('-180.0f','-179.0f'),'wrong_upper':('77.0f','76.0f'),'wrong_enabled':('descriptor.enabled = 1','descriptor.enabled = 0'),'wrong_mode':('descriptor.mode = 1','descriptor.mode = 0'),'wrong_scale':('descriptor.scale = D_800A5DF0','descriptor.scale = D_800A5DEC'),'wrong_size':('&descriptor, 0x14','&descriptor, 0x10'),'short_copy':('&payload, 0x14','&payload, 0x10'),'wrong_destination':('record + 0xC8','record + 0xC4'),'wrong_event':('(s32)owner, 0x15','(s32)owner, 0x14')}
 out={n:b.replace(a,z)for n,(a,z)in changes.items()};assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(OwnerEffectPayload)==20&&sizeof(OwnerEffectDescriptor)==36&&__builtin_offsetof(OwnerEffectPayload,zero)==8&&__builtin_offsetof(OwnerEffectDescriptor,scale)==28)?1:-1];
typedef struct {u8 pad0[20]; f32 point[3]; u8 pad20[27];u8 id;u8 rest[196];} Owner;
static Owner actor;
static union {u32 align;u8 bytes[256];} actual;
static u8 expected[256];static u32 fail,mode,uid,point,phase,error,count;
static u32 patterns[]={0,0x80000000u,0x3F800000u,0xC1900000u,1,0x80000001u,0x7F800000u,0x7FC12345u};
f32 D_800A5DE4,D_800A5DE8,D_800A5DEC,D_800A5DF0;
static void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 value(const void*p){u32 v;bytes(&v,p,4);return v;}
static void mutate(u32 bit){u32 i,v=0x40000000u;if(mode&bit){actor.id^=255;for(i=0;i<3;i++)bytes(&actor.point[i],&v,4);}}
Type46DistanceRecord *func_150C5370(const Type46DistancePayload*p,u32 n){
 const u8*b=(const u8*)p;u32 i;
 if(phase++||n!=20)error=1;
 for(i=0;i<3;i++)if(value(b+4*i)!=value((&D_800A5DE4)+i)||value(b+12+4*i)!=patterns[(point+i)%8])error=1;
 if(b[24]!=1||b[32]!=1||value(b+28)!=value(&D_800A5DF0))error=1;
 mutate(1);return fail?NULL:(Type46DistanceRecord*)actual.bytes;
}
void *memcpy(void*d,const void*s,size_t n){
 const u8*b=(const u8*)s;u32 i;
 if(phase++!=1||d!=actual.bytes+200||n!=20)error=1;
 if(value(b)!=(u32)&actor||b[4]!=uid||b[5]!=6||value(b+8)!=0||value(b+12)!=0xC3340000u||value(b+16)!=0x429A0000u)error=1;
 if(d==actual.bytes+200&&n<=20){bytes(d,s,n);for(i=0;i<n;i++)if(i!=6&&i!=7)expected[200+i]=b[i];}
 mutate(2);return d;
}
s32 func_1514EC1C(s32 record,s32 owner,s16 command){if(phase++!=2||(u32)record!=(u32)actual.bytes||(u32)owner!=(u32)&actor||command!=21)error=1;return (s32)0xC0DEC0DEu;}
'''
 # Independent objects are read separately; do not assume adjacent C globals.
 t=t.replace('value((&D_800A5DE4)+i)','(i==0?value(&D_800A5DE4):i==1?value(&D_800A5DE8):value(&D_800A5DEC))')
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+'\n'
 t+=r'''
typedef void(*Callback)(u8*);
static int check(Callback fn){u32 i,v;
 for(uid=0;uid<256;uid++)for(point=0;point<8;point++)for(fail=0;fail<2;fail++)for(mode=0;mode<4;mode++){
  for(i=0;i<256;i++)actual.bytes[i]=expected[i]=(u8)(i*17+uid);
  bytes(&actor,expected,sizeof(actor));actor.id=(u8)uid;
  for(i=0;i<3;i++){v=patterns[(point+i)%8];bytes(&actor.point[i],&v,4);}
  v=0x3FA00000u;bytes(&D_800A5DE4,&v,4);v=0xC1900000u;bytes(&D_800A5DE8,&v,4);v=0x42C80000u;bytes(&D_800A5DEC,&v,4);v=0x3F000000u;bytes(&D_800A5DF0,&v,4);
  phase=error=0;fn((u8*)&actor);
  if(error||phase!=(fail?1:3))return 1;
  for(i=0;i<256;i++)if((i!=206&&i!=207)&&actual.bytes[i]!=expected[i])return 1;
  count++;
 }return 0;
}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(%s))return %d;\n'%(name,20+i)
 return t+'return 0;}\n'+START

def native_suite():
 unit=o/'native-root.c';unit.write_text(native_harness())
 for opt in('O0','O2','O3'):
  exe=o/('native-root-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=16384,effective_controls=12,UBSan_trapping=True,all_256_owner_ids=True,float_bits_copied=True,padding_value_claim=False,initialized_fields_and_storage_fences=True,provider_owner_mutations=True)
