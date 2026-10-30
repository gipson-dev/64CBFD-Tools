"""Live pair release, shared byte references and the original caller interfaces."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-resource-pair-release-match';F='func_150843AC';ENTRY=0x150843AC;BODY=220;OWNER=0x30000;LIST=0x60000;ALTLIST=0x61000;SHARED=0x50000;OTHER=0x51000;THIRD=0x52000
SYMS=dict(D_800D19A0=0x800D19A0,D_800D1F80=0x800D1F80,func_100043B4=0x100043B4)
u32=lambda x:x&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 first:int=SHARED
 second:int=OTHER
 identity:int=1
 count:int=2
 slot:int=0
 mutation:int=0
 phase:int=0
 invalid_list:int=0
def pair(c):return u32(OWNER+u32(c.slot*8)+0x28C)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({OWNER+i:(i*29+0x59)&255 for i in range(0x400)})
 for i in range(14):put(m,OWNER+0x28C+4*i,0)
 for i in range(256):put(m,s['D_800D19A0']+4*i,SHARED);m[s['D_800D1F80']+i]=(i*7+3)&255;m[LIST+i]=i;m[ALTLIST+i]=255-i
 put(m,OWNER+0x2C4,0 if c.invalid_list else LIST);put(m,pair(c),c.first);put(m,pair(c)+4,c.second);m[u32(LIST+c.slot)]=c.identity;m[s['D_800D1F80']+c.identity]=c.count;return m
def effect(m,c,ordinal,s=SYMS):
 if ordinal:return
 if c.mutation&1:put(m,pair(c),THIRD);put(m,pair(c)+4,SHARED)
 if c.mutation&2:put(m,s['D_800D19A0']+4*c.identity,OTHER);m[s['D_800D1F80']+c.identity]=129
 if c.mutation&4:m[u32(LIST+c.slot)]=c.identity^1;put(m,OWNER+0x2C4,ALTLIST)
 if c.mutation&8:m[s['D_800D1F80']+c.identity]=0
 if c.mutation&16:put(m,pair(c)+4,0)
def reference(initial,c,s=SYMS):
 m=dict(initial);calls=[];cursor=pair(c)
 if not read(m,cursor)and not read(m,cursor+4):return m,calls
 identity=m[u32(read(m,OWNER+0x2C4)+c.slot)]
 for offset in(0,4):
  resource=read(m,cursor+offset)
  if resource:
   if resource!=read(m,s['D_800D19A0']+4*identity):calls.append((s['func_100043B4'],(resource,3)));effect(m,c,len(calls)-1,s)
   else:p=s['D_800D1F80']+identity;m[p]=(m[p]-1)&255
   put(m,cursor+offset,0)
 return m,calls
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def cases():
 pointers=(0,SHARED,OTHER,THIRD);rows=[Case(first=a,second=b,identity=i,count=n,slot=slot,mutation=mu,phase=p)for a,b,i,n,slot,mu,p in itertools.product(pointers,pointers,(0,1,186,255),(0,1,255),(0,6),(0,1,2,4,8,16,31),(0,8))]
 rows.extend(Case(first=0,second=0,identity=i,invalid_list=1)for i in range(256));rows.extend(Case(first=OTHER,second=SHARED,identity=i,count=i,mutation=mu)for i,mu in itertools.product(range(256),(0,31)))
 rows.extend(Case(first=a,second=b,slot=slot,mutation=mu)for a,b,slot,mu in itertools.product((0,SHARED,OTHER),(0,SHARED,OTHER),(0xFFFFFFFF,0x80000000,0x7FFFFFFF),(0,31)))
 return tuple(dict.fromkeys(rows))
def native_safe(c):return c.slot in(0,6)and not c.phase and c.identity<187
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(OWNER,c.slot));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(self.syms['func_100043B4'],ENTRY);a=tuple(self.arguments(2));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==self.syms['func_100043B4'];effect(self.memory,self.case,len([x for x in self.calls if x[0]==t])-1,self.syms)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 unreachable={ENTRY+0x9C};assert visited==set(range(ENTRY,ENTRY+BODY,4))-unreachable
 # The old duplicate byte load has no branch target and follows the forced
 # delay slot of the unconditional branch at+0x94. Keep its literal word.
 assert ps[0][37]==0x10000005 and ps[0][38]==0xAE00028C and ps[0][39]==0x904D0000
 targets={i+1+(((w&65535)^32768)-32768)for i,w in enumerate(ps[0])if w>>26 in(1,4,5,6,7,20,21,22,23)};assert 39 not in targets;prefixes=0
 for c in(Case(first=0,second=0,invalid_list=1),Case(first=OTHER,second=SHARED,mutation=31),Case(first=SHARED,second=SHARED,count=0)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800D19A0=0x80007FF0+k*0x100000,D_800D1F80=0x8001FFF0+k*0x100000,func_100043B4=0x10008000+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for first,second,mu in itertools.product((0,SHARED,OTHER),(0,SHARED,OTHER),(0,31)):
   c=Case(first=first,second=second,mutation=mu);initial=fixture(c,s);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 aliases=0
 for component,first,second in itertools.product((0,4),(SHARED,OTHER),(0,SHARED,OTHER)):
  c=Case(first=first,second=second,identity=1);s=dict(SYMS,D_800D1F80=pair(c)+component-c.identity);programs=[linked(p,'alias-'+str(aliases)+'-'+str(i),s)for i,p in enumerate(objects)];initial=fixture(c,s);machines=[]
  for words in programs:m=Oracle(words,initial,c,s);m.run();verify(m,initial,c,s);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();windows=[]
 for pc,off,n,end,recordreg in((0x1508437C,0xB182C,3,0x15084388,18),(0x15084B3C,0xB1FEC,2,0x15084B44,None)):
  words=struct.unpack_from('>%dI'%n,rom,off);assert words[-2:]==(0x0D4210EB,0x02002825);cc=0
  for a,b,slot,mu in itertools.product((0,SHARED,OTHER),(0,SHARED,OTHER),(0,6),(0,31)):
   c=Case(first=a,second=b,slot=slot,mutation=mu);initial=fixture(c);machines=[]
   for program in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[end]=0;m=Oracle(words,initial,c,entry=pc,connected=code);m.r[16]=slot
    if recordreg is not None:m.r[recordreg]=OWNER
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    want,calls=reference(initial,c);assert(public(m.memory),m.calls)==(public(want),[(ENTRY,(OWNER,slot))]+calls);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);cc+=1
  windows.append(dict(entry=hex(pc),ROM=hex(off),words=n,cases=cc,end=hex(end),A0_precondition='record in S2'if recordreg else 'record already in A0',A1_delay='slot in S0',full_parent_claimed=False))
 return dict(cases=count,executions=count*3,covered_words=54,compiler_words=55,unreachable_offsets=[156],unreachable_duplicate_load_preserved=True,slot_words=55,alignment_words=0,frame=48,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_reference_byte_pair_alias_cases=aliases,caller_windows=windows,signed_slot_extremes_guest_only=True,helper_is_bounded_provider=True,literal_full_state_equal=True,private_only=True,installed=False,matching_credit=0)


from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):
 return dict(wrong_mode=body.replace('(s32 *)resource, 3','(s32 *)resource, 2'),wrong_pair_stride=body.replace('slot * 8','slot * 4').replace('slot << 3','slot << 2'),wrong_count=body.replace(']--;',']++;'),missing_clear=body.replace('*(u8 **)(cursor + 0x28C) = NULL;',';'),one_resource=body.replace('limit = 8','limit = 4'),wrong_identity=body.replace('[slot];','[0];'),cached_shared=body.replace('    cursor =','    cached = D_800D19A0[identity];\n    cursor =').replace('    u8 *resource;','    u8 *resource;\n    u8 *cached;').replace('resource != D_800D19A0[identity]','resource != cached'),cached_second=body.replace('    u8 *resource;','    u8 *resource;\n    u8 *cached;').replace('    cursor =','    cached = *(u8 **)((s32)record + slot * 8 + 0x290);\n    cursor =').replace('resource = *(u8 **)(cursor + 0x28C);','resource = offset ? cached : *(u8 **)(cursor + 0x28C);'),reloaded_identity=body.replace('            resource =','            identity = (*(u8 **)(record + 0x2C4))[slot];\n            resource ='))

def native_harness(selected):
 head,body=selected.split('/* Release',1);body='/* Release'+body;bad=controls(body);assert all(v!=body for v in bad.values())
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct {u32 first,second,identity,count,slot,mutation,invalid,calls,args[2],pairs[14],shared,countAfter,listByte,alt;} Fixture;
static const Fixture *current;static u32 stage,bad;
static u8 owner[0x400] __attribute__((aligned(8))),list[16],altList[16],shared[8] __attribute__((aligned(8))),other[8] __attribute__((aligned(8))),third[8] __attribute__((aligned(8)));
u8 *D_800D19A0[256];u8 D_800D1F80[256];
static u8 *decode(u32 n){return n==0?NULL:n==1?shared:n==2?other:third;}
void func_100043B4(s32 *resource,u32 mode){u32 k=stage++;if(k>=current->calls||k>=2||resource!=(s32*)decode(current->args[k])||mode!=3)bad=1;
 if(k==0){u8 **pair=(u8**)(owner+0x28C+current->slot*8);u32 mu=current->mutation;if(mu&1){pair[0]=third;pair[1]=shared;}if(mu&2){D_800D19A0[current->identity]=other;D_800D1F80[current->identity]=129;}if(mu&4){list[current->slot]=(u8)(current->identity^1);*(u8**)(owner+0x2C4)=altList;}if(mu&8)D_800D1F80[current->identity]=0;if(mu&16)pair[1]=NULL;}}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items());rows=[];encode=lambda v:{0:0,SHARED:1,OTHER:2,THIRD:3}[v]
 for c in cases():
  if not native_safe(c):continue
  want,calls=reference(fixture(c),c);args=[encode(a[0])for _,a in calls]+[0,0]
  values=[encode(c.first),encode(c.second),c.identity,c.count,c.slot,c.mutation,c.invalid_list,len(calls)]
  arr=lambda v:'{'+','.join(str(x)for x in v)+'}'
  tail=[encode(read(want,SYMS['D_800D19A0']+4*c.identity)),want[SYMS['D_800D1F80']+c.identity],want[LIST+c.slot],int(read(want,OWNER+0x2C4)==ALTLIST)]
  rows.append('{'+','.join(map(str,values))+','+arr(args[:2])+','+arr([encode(read(want,OWNER+0x28C+4*i))for i in range(14)])+','+','.join(map(str,tail))+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Release)(u8*,s32);
static s32 check(Release fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;stage=bad=0;
 for(i=0;i<0x400;i++)owner[i]=(u8)(i*29+0x59);for(i=0;i<14;i++)*(u8**)(owner+0x28C+4*i)=NULL;
 for(i=0;i<256;i++){D_800D19A0[i]=shared;D_800D1F80[i]=(u8)(i*7+3);}for(i=0;i<16;i++){list[i]=(u8)i;altList[i]=(u8)(255-i);}
 *(u8**)(owner+0x2C4)=current->invalid?NULL:list;*(u8**)(owner+0x28C+current->slot*8)=decode(current->first);*(u8**)(owner+0x290+current->slot*8)=decode(current->second);list[current->slot]=(u8)current->identity;D_800D1F80[current->identity]=(u8)current->count;
 fn(owner,current->slot);if(bad||stage!=current->calls)return 1;
 for(i=0;i<14;i++)if(*(u8**)(owner+0x28C+4*i)!=decode(current->pairs[i]))return 2;
 if(*(u8**)(owner+0x2C4)!=(current->alt?altList:current->invalid?NULL:list))return 3;
 for(i=0;i<256;i++){if(D_800D19A0[i]!=(i==current->identity?decode(current->shared):shared))return 4;if(D_800D1F80[i]!=(u8)(i==current->identity?current->countAfter:i*7+3))return 5;}
 for(i=0;i<16;i++){if(list[i]!=(u8)(i==current->slot?current->listByte:i)||altList[i]!=(u8)(255-i))return 6;}
 for(i=0;i<0x400;i++)if((i<0x28C||i>=0x2C8)&&owner[i]!=(u8)(i*29+0x59))return 7;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u8*,s32)',slot_domain=[0,6],identity_domain='0..186',native_table_backing=256,integer_address_domain='32-bit static objects below INT_MAX with bounded offsets',all_owner_pair_list_table_and_count_bytes_checked=True,helper_is_bounded_provider=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
