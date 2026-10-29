"""Literal owner packet factory model, result lifetime and original caller."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-owner-default-lifetime-match';F='func_150B53D0';ENTRY=0x150B53D0;OWNER=0x30000;OUTPUT=0x50000;MARK=0x70000;SCRIPT=0x80000
SYMS=dict(func_15149130=0x15149130,memcpy=0x10022EC0,func_151D2AB0=0x151D2AB0)
u32=lambda n:n&0xFFFFFFFF
s16=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 owner:int=OWNER
 lifetime:int=0xABCDFFFF
 priority:int=0x123400E1
 mode:int=0x80000001
 outcome:int=1
 mutation:int=0
 phase:int=0
def answer(c):return(0,OUTPUT,OWNER-40)[c.outcome]
def args(c):return tuple(map(u32,(c.owner,c.lifetime,c.priority,c.mode)))
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,1024)}
 for base in(OWNER-64,OUTPUT-64,MARK,SCRIPT):m.update({base+i:(i*29+0x59)&255 for i in range(256)})
 if c.owner:m[c.owner+0x3B]=0xE1
 return m
def effect(m,c,which):
 if c.mutation and c.owner:m[c.owner+0x3B]=0x5A if which==0 else 0xA7
 if which==0 and c.mutation==2:
  for i in range(4):put(m,STACK+c.phase+4*i,0xABCDEF00+i)
 if which==1 and c.mutation==3:put(m,answer(c)+40,0x2468ACE0)
 put(m,MARK,0xB16B00B0+which)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];packet=None;out=0
 if c.owner:
  home=STACK+c.phase;p=home-20;put(m,p,c.owner);m[p+4]=m[c.owner+0x3B];put(m,p+8,0);put(m,p+12,0)
  life=s16(c.lifetime);a=tuple(map(u32,(300 if life==-1 else life,-1,36,-1,0 if life==-1 else 1,35,16,c.priority&255,c.mode)));calls.append((s['func_15149130'],a));effect(m,c,0);out=answer(c)
  if out:
   initialize(m,out);packet=bytes(m[p+i]for i in range(16));calls.append((s['memcpy'],(out+40,p,16)))
   for i,b in enumerate(packet):m[out+40+i]=b
   calls.append((s['func_151D2AB0'],(6,)));effect(m,c,1)
 return m,calls,out,packet
def initialize(m,out):
 put(m,out+14,0x1234,2)
 for i in range(16):m[out+16+i]=(i*7+0x29)&255
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+1024}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.packet_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c))
 def record_call(self,t):
  counts={self.syms['func_15149130']:9,self.syms['memcpy']:3,self.syms['func_151D2AB0']:1,ENTRY:4};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['memcpy']:self.packet_observations.append(bytes(self.memory[a[1]+i]for i in range(a[2])))
 def hook(self,t):
  c=self.case;assert self.r[29]==STACK+c.phase-80;assert read(self.memory,self.r[29]+44)==getattr(self,'expected_target_ra',self.before[31]);a=self.calls[-1][1]
  if t==self.syms['func_15149130']:
   effect(self.memory,c,0);value=answer(c)
   if value:initialize(self.memory,value)
  elif t==self.syms['memcpy']:
   assert a[2]==16;data=bytes(self.memory[a[1]+i]for i in range(16))
   for i,b in enumerate(data):self.memory[a[0]+i]=b
   value=0xBAD0C0DE
  else:assert t==self.syms['func_151D2AB0'];effect(self.memory,c,1);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
LIFETIMES=(0,1,32767,32768,65534,65535,0xABCD8000,0xABCDFFFF,0xFFFFFFFF,0x80000000)
def cases():
 for a in itertools.product((0,OWNER),LIFETIMES,(0,127,128,0x123400FF),(0,0x80000001),range(3),range(4),(0,8)):yield Case(*a)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.packet_observations)
def verify(m,initial,c,s=SYMS):
 want,calls,out,packet=reference(initial,c,s);assert(public(m.memory),m.calls,m.r[2],m.packet_observations)==(public(want),calls,out,[]if packet is None else[packet]),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));print(dict(cases=count,covered_words=len(visited)),flush=True)
 prefixes=0
 for c in(Case(owner=0),Case(outcome=0),Case(),Case(lifetime=0xABCD8000,outcome=2,mutation=3,phase=8),Case(mutation=2)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,(entry,factory,copy,enable)in enumerate(((0x15001000,0x10007FF0,0x10008000,0x1000FFF0),(0x1F008000,0x1F108000,0x1000FFF0,0x10007FF0),(0x1000FFF0,0x10008000,0x10007FF0,0x10001000))):
  s=dict(func_15149130=factory,memcpy=copy,func_151D2AB0=enable);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for a in itertools.product((0,OWNER),(0xABCDFFFF,0xABCD8000),(0,1,2),(0,2,3),(0,8)):
   c=Case(owner=a[0],lifetime=a[1],outcome=a[2],mutation=a[3],phase=a[4]);initial=fixture(c)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>7I',rom,0xCA9C8));total=0
 for a in itertools.product((0,OWNER),(0,0xFFFF,0x8000),(0,1,2),(0,3),(0,8)):
  c=Case(owner=a[0],lifetime=u32(s16(a[1])),priority=255,mode=1,outcome=a[2],mutation=a[3],phase=a[4]);initial=fixture(c);put(initial,SCRIPT+10,c.lifetime,2);put(initial,STACK+c.phase+0xC4,0x12345678);want,calls,out,packet=reference(initial,c)
  for words in programs:
   connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[0x1509D76C]=0;m=Oracle(window,initial,c,entry=0x1509D518,connected=connected);m.r[16]=SCRIPT;m.r[2]=c.owner;m.before=m.r[:];m.expected_target_ra=0x1509D52C;m.code=WindowCode(m.code,m);m.code.ends=(0x1509D76C,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(public(m.memory),m.calls,m.r[2],m.packet_observations)==(public(want),[(ENTRY,args(c))]+calls,0x12345678,[]if packet is None else[packet])
  total+=1
 q=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,frame=80,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,packet_bytes=16,uninitialized_packet_padding_value_claimed=False,providers_bounded=True,result_survives_both_helpers=True,signed16_lifetime_and_u8_priority=True,owner_and_output_aliases=True,helper_mutations=True,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,original_caller_windows=[dict(entry='0x1509D518',ROM='0xCA9C8',words=7,cases=total,result_register_ignored=True,complete_parent_claimed=False)],hardware_or_complete_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_150B53D0';prefix=selected[:selected.index('/* Create')];body=selected[selected.index('/* Create'):]
 mutants=dict(wrong_default=body.replace('? 300 :','? 299 :'),wrong_flag=body.replace('lifetime == -1 ? 0 : 1','lifetime == -1 ? 1 : 0'),wrong_size=body.replace('sizeof(payload), priority','15, priority'),omit_copy=body.replace('memcpy(created + 0x28, &payload, sizeof(payload));','(void)0;'),omit_enable=body.replace('func_151D2AB0(6);','(void)0;'),lost_result=body.replace('return created;','return NULL;'),wrong_result=body.replace('return created;','return created == NULL ? NULL : created + 1;'),late_owner_id=body.replace('        memcpy(created +','        payload.ownerId = owner[0x3B];\n        memcpy(created +'));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
 typedef struct{u32 owner,lifetime,priority,mode,outcome,mutation; s32 effective;u32 flag;} Fixture;
 static const Fixture*current;static u8 ownerStorage[256] __attribute__((aligned(8))),outputStorage[256] __attribute__((aligned(8))),expectedOwner[256] __attribute__((aligned(8))),expectedOutput[256] __attribute__((aligned(8)));
 static u8*ownerData=ownerStorage+64;static u8*outputData=outputStorage+64;static s32 factories,copies,enables,badArgs;
 static u8*answer(void){return current->outcome==0?NULL:current->outcome==1?outputData:ownerData-40;}
 static void initialize(u8*out){s32 i;*(u16*)(out+14)=0x1234;for(i=0;i<16;i++)out[16+i]=(u8)(i*7+0x29);}
 void *func_15149130(s16 life,s8 a,s8 type,s8 b,u8 flag,u8 c,s32 size,u8 priority,s32 mode){u8*out;factories++;
  if(life!=current->effective||a!=-1||type!=36||b!=-1||flag!=current->flag||c!=35||size!=16||priority!=(current->priority&255)||(u32)mode!=current->mode)badArgs=1;
  if(current->mutation)ownerData[0x3B]=0x5A;out=answer();if(out)initialize(out);return out;}
 void *memcpy(void*dst,const void*src,u32 n){u8*d=dst;const u8*s=src;u32 i;copies++;if(n!=16||d!=answer()+40)badArgs=1;if(n>16)n=16;for(i=0;i<n;i++)d[i]=s[i];return (void*)0xBAD0C0DE;}
 void func_151D2AB0(s32 n){enables++;if(n!=6||copies!=1)badArgs=1;if(current->mutation)ownerData[0x3B]=0xA7;if(current->mutation==3)*(u32*)(answer()+40)=0x2468ACE0;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0];rows=[]
 for c in cases:rows.append((int(bool(c.owner)),c.lifetime,c.priority,c.mode,c.outcome,c.mutation,300 if q.s16(c.lifetime)==-1 else q.s16(c.lifetime),int(q.s16(c.lifetime)!=-1)))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join(str(x)if i==6 else'0x%08Xu'%x for i,x in enumerate(row))+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef void*(*Fn)(u8*,s16,u8,s32);
 static s32 check(Fn fn){s32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;u8*eout=NULL;u8*actualOut;void*result;current=c;
  for(i=0;i<256;i++)ownerStorage[i]=outputStorage[i]=expectedOwner[i]=expectedOutput[i]=(u8)(i*29+0x59);
  ownerData[0x3B]=expectedOwner[64+0x3B]=0xE1;factories=copies=enables=badArgs=0;
  result=fn(c->owner?ownerData:NULL,(s16)c->lifetime,(u8)c->priority,(s32)c->mode);actualOut=c->owner?answer():NULL;
  if(badArgs||result!=actualOut||factories!=(s32)c->owner||copies!=(c->owner&&c->outcome)||enables!=(c->owner&&c->outcome))return 1;
  if(c->owner){if(c->mutation)expectedOwner[64+0x3B]=0x5A;
   if(c->outcome){eout=c->outcome==1?expectedOutput+64:expectedOwner+24;initialize(eout);*(u32*)(eout+40)=(u32)ownerData;eout[44]=0xE1;*(u32*)(eout+48)=0;*(u32*)(eout+52)=0;if(c->mutation)expectedOwner[64+0x3B]=0xA7;if(c->mutation==3)*(u32*)(eout+40)=0x2468ACE0;}}
  for(i=0;i<256;i++){if(!(eout&&(expectedOwner+i==eout+45||expectedOwner+i==eout+46||expectedOwner+i==eout+47))&&ownerStorage[i]!=expectedOwner[i])return 2;
  if(!(eout&&(expectedOutput+i==eout+45||expectedOutput+i==eout+46||expectedOutput+i==eout+47))&&outputStorage[i]!=expectedOutput[i])return 3;}
  }return 0;}
 static int run(void){if(sizeof(void*)!=4||sizeof(OwnerDefaultLifetimePayload)!=16)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
