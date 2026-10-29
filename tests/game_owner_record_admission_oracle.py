"""Direct owner-record allocation/admission, cleanup and result forwarding."""
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
r=Path.cwd();o=r/'conker/build/game-owner-record-admission-match';F='func_151ACA60';ENTRY=0x151ACA60;TABLE=0x800CC2D0;OUTPUT=0x50000;MARK=0x70000
SYMS=dict(func_15167A68=0x15167A68,func_151ACB38=0x151ACB38,func_1516979C=0x1516979C,D_800CC2D0=TABLE)
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(n^0x80000000)-0x80000000
def quotient(n):return u32((abs(n)//812)*(-1 if n<0 else 1))
@dataclass(frozen=True)
class Case:
 owner:int=TABLE
 scale:int=0x7FC12345
 size:int=0
 outcome:int=1
 admit:int=1
 mutation:int=0
 phase:int=0
 identity:int=0x87
def answer(c):return(0,OUTPUT,c.owner)[c.outcome]
def args(c):return(c.owner,c.scale,c.size)
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base in(OUTPUT-64,MARK):m.update({base+i:(i*29+0x59)&255 for i in range(256)})
 if c.owner:
  m.update({u32(c.owner+i):(i*29+0x59)&255 for i in range(-64,256)});m[c.owner+0x3B]=c.identity
 return m
def alloc_effect(m,c):
 if c.owner and c.mutation==1:m[c.owner+0x3B]=0xE1
 out=answer(c)
 if out:
  m[out]=0x30;put(m,out+8,0x12345678);put(m,out+16,0x11223344);put(m,out+20,0x55667788)
 put(m,MARK,0xA110CA7E)
def admission_effect(m,c,admitted,connected=False):
 if admitted:m[answer(c)+24]=1
 if not connected and c.mutation==2:m[c.owner+0x3B]=0x80
def free_effect(m,c):put(m,answer(c)+8,0xDEADCAFE);put(m,MARK,0xF4EE0001)
def reference(initial,c,s=SYMS,connected=False):
 m=dict(initial);calls=[];out=0;released=[]
 if not c.owner:return m,calls,out,released
 a=(48,0,u32(c.size+48),1,255,1);calls.append((s['func_15167A68'],a));alloc_effect(m,c);out=answer(c)
 if not out:return m,calls,0,released
 calls.append((s['func_151ACB38'],(c.owner,out+24)));admitted=(m[c.owner+59]==1)if connected else bool(c.admit);admission_effect(m,c,admitted,connected)
 if not admitted:
  released.append(bytes(m[out+i]for i in range(48)));calls.append((s['func_1516979C'],(out,)));free_effect(m,c);return m,calls,0,released
 index=quotient(signed(u32(c.owner-s['D_800CC2D0'])));put(m,out+28,c.owner);identity=m[c.owner+59];put(m,out+36,index);m[out+32]=identity;put(m,out+16,1);put(m,out+20,0);put(m,out+40,c.scale)
 return m,calls,out,released
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.release_observations=[];super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=args(c))
 def record_call(self,t):
  counts={self.syms['func_15167A68']:6,self.syms['func_151ACB38']:2,self.syms['func_1516979C']:1,ENTRY:3,0x1514EC1C:3};assert t in counts,hex(t);a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_1516979C']:self.release_observations.append(bytes(self.memory[a[0]+i]for i in range(48)))
 def hook(self,t):
  c=self.case;s=self.syms
  if t==0x1514EC1C:assert self.r[29]==STACK+c.phase;put(self.memory,MARK+4,0xF04A4D00);value=0xDEADBEEF
  else:
   assert self.r[29]==STACK+c.phase-48;assert read(self.memory,self.r[29]+32)==self.before[16];assert read(self.memory,self.r[29]+36)==getattr(self,'expected_target_ra',self.before[31])
   if t==s['func_15167A68']:alloc_effect(self.memory,c);value=answer(c)
   elif t==s['func_151ACB38']:admission_effect(self.memory,c,bool(c.admit));value=c.admit
   else:assert t==s['func_1516979C'];free_effect(self.memory,c);value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
OWNERS=(0,TABLE-812,TABLE,TABLE+25*812,TABLE+7,u32(TABLE+0x80000000))
def cases():
 for a in itertools.product(OWNERS,(0,0x80000000,0x3F800000,0x7FC12345,0xFF800000),(0,0xFFFFFFFF,0x7FFFFFFF,0xFFFFFFD0),range(3),(0,1),range(3),(0,8)):
  c=Case(*a)
  if c.outcome==2 and c.owner&3:continue
  yield c
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.release_observations)
def verify(m,initial,c,s=SYMS,connected=False):
 want,calls,out,released=reference(initial,c,s,connected);assert(public(m.memory),m.calls,m.r[2],m.release_observations)==(public(want),calls,out,released),c
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+216,4));print(dict(cases=count,covered_words=len(visited)),flush=True)
 prefixes=0
 for c in(Case(owner=0),Case(outcome=0),Case(admit=0,mutation=2),Case(),Case(owner=TABLE-812,outcome=2,mutation=1,phase=8)):
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
 sparse=0;c=Case(owner=0);initial={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
 for words in programs:m=Oracle(words,initial,c).run();assert m.calls==[]and m.r[2]==0;sparse+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(func_15167A68=0x10007FF0+k*0x10000,func_151ACB38=0x10008000+k*0x10000,func_1516979C=0x1000FFF0+k*0x10000,D_800CC2D0=0x80018004+k*0x100000);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)]
  for owner,outcome,admit,phase in itertools.product((0,TABLE-812,TABLE),(0,1,2),(0,1),(0,8)):
   c=Case(owner=owner,outcome=outcome,admit=admit,phase=phase);initial=fixture(c)
   for words in ps:verify(Oracle(words,initial,c,s,entry).run(),initial,c,s)
   rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(0x151ACB38,0x151ACB60,4),struct.unpack_from('>10I',rom,0x1D9FE8)));connected_count=0
 for identity,outcome,mu,phase in itertools.product((0,1,255),(0,1,2),(0,1),(0,8)):
  c=Case(identity=identity,outcome=outcome,mutation=mu,phase=phase);initial=fixture(c)
  for words in programs:verify(Oracle(words,initial,c,connected=helper).run(),initial,c,connected=True)
  connected_count+=1
 window=list(struct.unpack_from('>8I',rom,0x17AEB8));caller_count=0
 for owner,outcome,admit,phase in itertools.product((0,TABLE),(0,1,2),(0,1),(0,8)):
  c=Case(owner=owner,scale=0x41A00000,size=0,outcome=outcome,admit=admit,phase=phase);initial=fixture(c);put(initial,STACK+phase+24,owner);want,calls,out,released=reference(initial,c);put(want,MARK+4,0xF04A4D00)
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));code[0x1514DA28]=0;m=Oracle(window,initial,c,entry=0x1514DA08,connected=code);m.expected_target_ra=0x1514DA18;m.code=WindowCode(m.code,m);m.code.ends=(0x1514DA28,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing original result-forwarding boundary')
   assert(public(m.memory),m.calls,m.release_observations)==(public(want),[(ENTRY,args(c))]+calls+[(0x1514EC1C,(out,owner,20))],released)
  caller_count+=1
 q=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,frame=48,guards=0,insertions=0,omissions=0,literal_full_state_equal=True,size_addition_wraps32=True,index_subtraction_wraps32=True,signed_index_division_truncates_zero=True,alias_output_and_owner=True,cleanup_boundary_observations=True,scale_bitcopy=True,providers_bounded=True,access_prefix_pairs=prefixes,sparse_null_executions=sparse,rebase_layouts=3,rebase_cases=rebased,original_admission_helper_cases=connected_count,original_admission_helper_words=10,original_caller_windows=[dict(entry='0x1514DA08',ROM='0x17AEB8',words=8,cases=caller_count,result_forwarded=True,complete_parent_claimed=False)],complete_allocator_or_free_or_parent_claimed=False)
 return q


import sys
from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 q=sys.modules[__name__]
 F='func_151ACA60';prefix=selected[:selected.index('/* Allocate')];body=selected[selected.index('/* Allocate'):]
 mutants=dict(wrong_class=body.replace('func_15167A68(0x30,','func_15167A68(0x31,'),wrong_size=body.replace('+ 0x30U','+ 0x20U'),omit_cleanup=body.replace('func_1516979C(record);','(void)0;'),wrong_admission=body.replace('record + 0x18) == 0','record + 0x18) != 0'),freed_result=body.replace('func_1516979C(record);\n        return 0;','func_1516979C(record);\n        return (s32)record;'),wrong_stride=body.replace('/ 0x32C','/ 0x330'),wrong_identity=body.replace('= owner[0x3B]','= record[0x3B]'),wrong_scale_offset=body.replace('*(f32 *)(record + 0x28)','*(f32 *)(record + 0x2C)'));assert all(v!=body for v in mutants.values())
 text=prefix+r'''
 typedef struct{u32 hasOwner,offset,scale,size,outcome,admit,mutation,index;} Fixture;
 static const Fixture*current;u8 D_800CC2D0[812*26+256] __attribute__((aligned(8)));static u8 output[128] __attribute__((aligned(8))),expectedOwner[256] __attribute__((aligned(8))),expectedOutput[128] __attribute__((aligned(8)));static u8*ownerPtr;static s32 allocations,admissions,releases,badArgs;static u32 marker;
 static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
 static s32 isNan(u32 u){return(u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu)!=0;}
 static u8*answer(void){return current->outcome==0?NULL:current->outcome==1?output:ownerPtr;}
 static void initialize(u8*p){p[0]=0x30;*(u32*)(p+8)=0x12345678;*(u32*)(p+16)=0x11223344;*(u32*)(p+20)=0x55667788;}
 void*func_15167A68(s32 type,s32 mode,s32 size,s32 flag,u8 priority,s32 last){u8*out;allocations++;if(type!=48||mode!=0||(u32)size!=current->size+48U||flag!=1||priority!=255||last!=1)badArgs=1;if(current->mutation==1)ownerPtr[59]=0xE1;out=answer();if(out)initialize(out);marker=0xA110CA7E;return out;}
 s32 func_151ACB38(u8*owner,u8*admission){admissions++;if(owner!=ownerPtr||admission!=answer()+24)badArgs=1;if(current->admit)*admission=1;if(current->mutation==2)ownerPtr[59]=0x80;return(s32)current->admit;}
 void func_1516979C(void*p){u8*out=p;releases++;if(out!=answer()||*(u32*)(out+16)!=0x11223344||*(u32*)(out+20)!=0x55667788)badArgs=1;*(u32*)(out+8)=0xDEADCAFE;marker=0xF4EE0001;}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items());cases=[c for c in q.cases()if c.phase==0 and(c.owner==0 or 0<=c.owner-q.TABLE<=25*812+7)];rows=[]
 for c in cases:rows.append((int(bool(c.owner)),c.owner-q.TABLE if c.owner else 0,c.scale,c.size,c.outcome,c.admit,c.mutation,q.quotient(q.signed(q.u32(c.owner-q.TABLE)))if c.owner else 0))
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+','.join('0x%08Xu'%x for x in row)+'}'for row in rows)+'\n};\n'
 text+=r'''
 typedef s32(*Fn)(u8*,f32,s32);
 static s32 check(Fn fn){s32 n,i;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;u8*eout=NULL;u8*actual;u32 result,wantMarker=0;current=c;ownerPtr=c->hasOwner?D_800CC2D0+c->offset:NULL;
  for(i=0;i<256;i++){expectedOwner[i]=(u8)(i*29+0x59);if(ownerPtr)ownerPtr[i]=expectedOwner[i];}for(i=0;i<128;i++)output[i]=expectedOutput[i]=(u8)(i*29+0x59);if(ownerPtr)ownerPtr[59]=expectedOwner[59]=0x87;allocations=admissions=releases=badArgs=0;marker=0;
  result=(u32)fn(ownerPtr,asFloat(c->scale),(s32)c->size);actual=c->hasOwner?answer():NULL;if(badArgs||allocations!=(s32)c->hasOwner||admissions!=(c->hasOwner&&c->outcome)||releases!=(c->hasOwner&&c->outcome&&!c->admit)||result!=(u32)((c->hasOwner&&c->outcome&&c->admit)?actual:NULL))return 1;
  if(c->hasOwner){wantMarker=0xA110CA7E;if(c->mutation==1)expectedOwner[59]=0xE1;if(c->outcome){eout=c->outcome==1?expectedOutput:expectedOwner;initialize(eout);if(c->admit)eout[24]=1;if(c->mutation==2)expectedOwner[59]=0x80;if(!c->admit){*(u32*)(eout+8)=0xDEADCAFE;wantMarker=0xF4EE0001;}else{*(u32*)(eout+28)=(u32)ownerPtr;eout[32]=expectedOwner[59];*(u32*)(eout+36)=c->index;*(u32*)(eout+16)=1;*(u32*)(eout+20)=0;*(u32*)(eout+40)=c->scale;if(isNan(c->scale)&&isNan(*(u32*)(actual+40)))*(u32*)(eout+40)=*(u32*)(actual+40);}}}
  if(marker!=wantMarker)return 2;for(i=0;i<128;i++)if(output[i]!=expectedOutput[i])return 3;if(ownerPtr)for(i=0;i<256;i++)if(ownerPtr[i]!=expectedOwner[i])return 4;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(cases)))
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text
