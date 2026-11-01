"""First owner/tag match, full command byte, scan bounds and store prefixes."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments import game_owner_flag_command_match as source
r=o=None
ENTRY,STRIDE=0x1506D958,0x32C
@dataclass(frozen=True)
class Case:
 hit:int=0
 pattern:int=0
 high:int=0x80
 owner:int=0
 tag:int=0x47
 active:int=1
 flag:int=0xA5
 upper:int=0xA5A50000
 phase:int=0
def symbols(index=0):
 pool=(0x800CC2D0,0x02337FFC,0x0343FFFC)[index]
 return dict(D_800CC2D0=pool,D_800CC37B=pool+0xAB,D_800CC335=pool+0x65,D_800CC3D1=pool+0x101,D_800CC5FC=pool+STRIDE,D_800D121C=pool+25*STRIDE,D_800D1580=0x800D1580 if not index else pool+0x28004,D_800C3E78=0x800C3E78 if not index else pool+0x30004)
def fields(c,i):
 state=0 if c.pattern==0 else -1 if c.pattern==3 else 1
 tag=(c.tag^0x80)&255;link=(c.owner+2)&255
 if c.pattern in(2,3):tag=c.tag&255
 if c.pattern==3:link=(c.owner+1)&255
 if c.pattern==4:
  state=(0,1,-1)[i%3];tag=c.tag&255 if i%3==0 else(c.tag^1)&255;link=(c.owner+1 if i%3==1 else c.owner+2)&255
 if i==c.hit:state=c.active;tag=c.tag&255;link=(c.owner+1)&255
 return state&0xFFFFFFFF,tag,link,(c.flag+i*19)&255
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)}
 for i in range(26):
  a=s['D_800CC2D0']+i*STRIDE;state,tag,link,flag=fields(c,i);put(m,a,state)
  for at in(0x64,0x65,0x66,0xAA,0xAB,0xAC,0x100,0x101,0x102):m[a+at]=0xA5
  m[a+0xAB]=tag;m[a+0x65]=link;m[a+0x101]=flag
 put(m,s['D_800D1580'],(c.upper&0xFFFF0000)|((c.high&255)<<8)|(c.tag&255));m[s['D_800C3E78']]=c.owner&255
 return m
def reference(initial,s):
 m=dict(initial);command=read(m,s['D_800D1580']);tag=command&255;mask=(command>>8)&255;selected=None
 for i in range(25):
  a=s['D_800CC2D0']+i*STRIDE
  if read(m,a)!=0 and m[a+0xAB]==tag and m[a+0x65]==m[s['D_800C3E78']]+1:
   m[a+0x101]=(m[a+0x101]&254)|mask;selected=i;break
 return m,selected
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},arguments=(29,0x12345678),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):assert t==ENTRY;self.calls.append((t,()))
 def hook(self,t):raise AssertionError(('Unexpected helper',hex(t)))
def corpus():
 for hit,pattern,high,owner in itertools.product(range(-1,26),range(3),(0,1,255),(0,254,255)):
  yield Case(hit,pattern,high,owner,0x47,(-1,1,0x80000000)[(hit+owner)%3],phase=8 if hit&1 else 0)
 for hit,pattern,owner in itertools.product(range(-1,26),(3,4),(0,254,255)):yield Case(hit,pattern,0x80,owner)
 for high,hit in itertools.product(range(256),(0,1,24)):yield Case(hit,2,high,0,0xFF)
 for tag in range(256):yield Case(tag%25,1,(tag*13)&255,tag%255,tag,upper=0xFFFF0000 if tag&1 else 0)
 for owner in range(256):yield Case(owner%25,2,0x80,owner,0xEE)
 for hit in(0,1,2,24):yield Case(hit,0,255,0,0x47,0)
def boundary_corpus():
 for hit,pattern,high,owner in itertools.product((-1,0,1,2,23,24,25),range(5),(0,255),(0,255)):yield Case(hit,pattern,high,owner,0xFF,-1)
def compare(programs,c,s,entry=ENTRY):
 initial=fixture(c,s);expected,selected=reference(initial,s);models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry).run();assert m.memory==expected and not m.calls,(c,selected)
  assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f==m.before_f
  writes=[e for e in m.trace if e[0]=='W'];assert len(writes)==(0 if selected is None else 1 if selected==0 else 2),(c,selected,writes)
  if selected is not None:
   address=s['D_800CC2D0']+selected*STRIDE+0x101;assert all(e[1:3]==(address,1)for e in writes)
   assert writes[-1][3]==expected[address]
   if selected:assert writes[0][3]==(initial[address]&254)
  models.append(m)
 for m in models[1:]:assert(m.memory,m.r,m.f,m.trace,m.visits)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].visits)
 return models[0]
def guest():
 paths=('original-func_1506D958.o','selected-final.o','qualified-padded.o','make-shadow/src/game_981E0.c.o');count=0;seen=set();retail=None
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/n,'flags-program-%d-%d'%(index,i),entry,s)for i,n in enumerate(paths)];assert all(p==programs[0]for p in programs)
  for c in(corpus()if index==0 else boundary_corpus()):m=compare(programs,c,s,entry);seen.update(pc-entry for pc in m.visits);count+=1
  if not index:retail=programs
 assert set(range(0,288,4))-seen=={0xC8,0x10C},set(range(0,288,4))-seen
 return dict(cases=count,executions=count*4,body_words=72,frame=0,rebases=3,full_corpus_at_retail=True,boundary_corpus_at_other_rebases=True,all_70_reachable_words_executed=True,unreachable_duplicate_words=[0xC8,0x10C],single_primary_and_double_later_stores_verified=True,all_mask_tag_owner_bytes=True,all_machine_states_and_traces_equal=True),retail
def faults(programs):
 count=0;intermediate=0;s=symbols()
 for hit in(0,1,2,24):
  c=Case(hit,2,0x80,0,0xFF);initial=fixture(c,s);full=Oracle(programs[0],initial,c,s).run();writes=[i for i,e in enumerate(full.trace)if e[0]=='W']
  for cut in range(len(full.trace)):
   models=[]
   for program in programs:
    m=Oracle(program,initial,c,s);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Fault prefix did not stop')
    assert m.trace==full.trace[:cut]
    expected=dict(initial)
    for e in full.trace[:cut]:
     if e[0]=='W':put(expected,e[1],e[3],e[2])
    assert m.memory==expected;models.append(m)
   for m in models[1:]:assert(m.memory,m.r,m.f,m.trace)==(models[0].memory,models[0].r,models[0].f,models[0].trace)
   if hit and cut==writes[-1]:
    at=s['D_800CC2D0']+hit*STRIDE+0x101;assert models[0].memory[at]==(initial[at]&254);intermediate+=1
   count+=1
 assert intermediate==3
 return dict(prefixes=count,executions=count*4,intermediate_clear_observed_at_three_later_slots=True,scope='controlled guest access boundaries, not portable C fault handling')
class ReturnPoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1506AEC8:self.owner.r[2]=self.owner.poison;self.owner.return_poisons+=1
  return super().__getitem__(pc)
def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();body=struct.unpack_from('>19I',rom,0x98360);end=0x1506AEFC;count=0
 for hit,high,owner,changed in itertools.product((-1,0,1,24,25),(0,1,0x80,255),(0,255),(0,1)):
  c=Case(hit,2,high,owner);initial=fixture(c,s);actor=0xA0000;record=0xB0000
  put(initial,actor+0x2D0,record);put(initial,record+0x28,0xB1000);put(initial,actor+0x1C4,0xB2000);put(initial,record+8,0x3F800000);initial[actor+0x138]=7;put(initial,0x80086470,ENTRY)
  expected,_=reference(initial,s)
  if not changed:expected[actor+0x138]=8
  for program,poison in itertools.product(programs,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+288,4),program));code[end]=0;m=Oracle(body,initial,c,s,0x1506AEB0,code);m.r[4]=29;m.r[30]=0x800863FC;m.r[17]=actor;m.r[18]=0xB1000+changed;m.poison=poison;m.return_poisons=0
   m.code=ReturnPoisonCode(m.code,m);m.code.ends=(end,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original dispatch boundary not reached')
   assert m.memory==expected and m.calls==[(ENTRY,())]
   assert m.return_poisons==1 and m.r[2]==0xB2000
  count+=1
 census=json.loads((o/'caller-census.json').read_text());assert census['slot']==29 and census['aligned_ROM_pointer_literals']==[0x22AF30]and not census['aligned_ROM_JALs']
 return dict(cases=count,executions=count*16,original_window_words=19,callback_slot=29,return_poisons=4,return_ignored=True,full_dispatcher_reachability_claimed=False)
def controls():
 return (
 ('boolean-high-byte','flagBits = (D_800D1580 >> 8) & 0xFF','flagBits = (D_800D1580 >> 8) & 1'),
 ('wrong-match-byte','matchByte = D_800D1580 & 0xFF','matchByte = (D_800D1580 >> 16) & 0xFF'),
 ('positive-only-active','interaction_state != 0','interaction_state > 0'),
 ('wrapped-owner','D_800C3E78 + 1','(u8)(D_800C3E78 + 1)'),
 ('include-slot25','slot < 25','slot < 26'),
 ('continue-after-match','            return;','            /* keep scanning */'),
 ('wrong-clear-bit','unk101 &= ~1','unk101 &= ~2'))
def digest(m,s):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 mix(read(m,s['D_800D1580']));mix(m[s['D_800C3E78']])
 for i in range(26):
  a=s['D_800CC2D0']+i*STRIDE;mix(read(m,a))
  for at in(0x64,0x65,0x66,0xAA,0xAB,0xAC,0x100,0x101,0x102):mix(m[a+at])
 return h
def native():
 bodies=[source.SELECTED]
 for n,a,b in controls():assert a in source.SELECTED;bodies.append(source.SELECTED.replace(a,b))
 code=source.HEADERS+'\n'.join(b.replace('func_1506D958','candidate_'+str(i))for i,b in enumerate(bodies))
 code+='''
struct127 D_800CC2D0[26];s32 D_800D1580;u8 D_800C3E78;
typedef char ActorSize[sizeof(struct127)==812?1:-1];
typedef char LinkOffset[__builtin_offsetof(struct127,unk65)==0x65?1:-1];
typedef char TagOffset[__builtin_offsetof(struct127,unkAB)==0xAB?1:-1];
typedef char FlagOffset[__builtin_offsetof(struct127,unk101)==0x101?1:-1];
typedef struct{u32 hit,pattern,high,owner,tag,active,flag,upper,expected;}Test;
static const Test tests[]={
'''
 rows=[]
 for c in corpus():
  s=symbols();expected,_=reference(fixture(c,s),s)
  rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in(c.hit,c.pattern,c.high,c.owner,c.tag,c.active,c.flag,c.upper,digest(expected,s)))+'}')
 code+=',\n'.join(rows)+'''};
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 result(void){u32 h=2166136261u,i;u8*p;h=mix(h,D_800D1580);h=mix(h,D_800C3E78);
 for(i=0;i<26;i++){p=(u8*)&D_800CC2D0[i];h=mix(h,D_800CC2D0[i].interaction_state);h=mix(h,p[0x64]);h=mix(h,p[0x65]);h=mix(h,p[0x66]);h=mix(h,p[0xAA]);h=mix(h,p[0xAB]);h=mix(h,p[0xAC]);h=mix(h,p[0x100]);h=mix(h,p[0x101]);h=mix(h,p[0x102]);}return h;}
static void reset(const Test*t){u32 i,state,tag,link;for(i=0;i<26;i++){
 state=t->pattern==0?0:t->pattern==3?0xFFFFFFFFu:1;tag=(t->tag^0x80)&255;link=(t->owner+2)&255;
 if(t->pattern==2||t->pattern==3)tag=t->tag&255;if(t->pattern==3)link=(t->owner+1)&255;
 if(t->pattern==4){state=i%3==0?0:i%3==1?1:0xFFFFFFFFu;tag=i%3==0?t->tag&255:(t->tag^1)&255;link=(t->owner+(i%3==1?1:2))&255;}
 if(i==t->hit){state=t->active;tag=t->tag&255;link=(t->owner+1)&255;}
 D_800CC2D0[i].interaction_state=state;D_800CC2D0[i].unkAB=tag;D_800CC2D0[i].unk65=link;D_800CC2D0[i].unk101=t->flag+i*19;
 }D_800D1580=(t->upper&0xFFFF0000u)|((t->high&255)<<8)|(t->tag&255);D_800C3E78=t->owner;}
static int run(void){u32 i,j,killed=0,h;u8*p=(u8*)D_800CC2D0;for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=0xA5;
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<8;j++){reset(&tests[i]);switch(j){case 0:candidate_0();break;case 1:candidate_1();break;case 2:candidate_2();break;case 3:candidate_3();break;case 4:candidate_4();break;case 5:candidate_5();break;case 6:candidate_6();break;default:candidate_7();break;}h=result();if(h!=tests[i].expected){if(!j)return 10;killed|=1u<<(j-1);}}
 for(i=0;i<sizeof(D_800CC2D0);i++){j=i%812;if(j>=4&&j!=0x65&&j!=0xAB&&j!=0x101&&p[i]!=0xA5)return 12;}return killed==127?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-owner-flags.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-owner-flags'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-owner-flags'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,full_byte_masks_and_unwrapped_owner=True,background_canaries_preserved=True,controls=[n for n,_,_ in controls()],all_controls_effective=True))
 return reports
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();print('guest qualified',g['cases'],flush=True)
 report=dict(guest=g,faults=faults(programs),callers=callers(programs),native=native(),no_helper_calls=True)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def link(obj,label,entry,s,words=72):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_1506D958'],bindings,'func_1506D958',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_1506D958','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
