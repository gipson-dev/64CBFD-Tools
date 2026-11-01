"""Carried actor initialization, live owner reload, real notification helper and dispatch."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
_alias_cache={}
ENTRY,HELPER,NESTED,STRIDE=0x1507266C,0x151B5BA0,0x151B4FE0,812
FIELDS=((0x65,1),(0x5C,4),(0x101,1),(0x104,1),(0x125,1),(0x218,4),(0xE4,2),(0xE6,2),(0x232,1),(0xEC,4),(0xF0,4),(0xDC,4),(0xE0,4))
@dataclass(frozen=True)
class Case:
 selected:int=1
 mode:int=1
 owner:int=0
 command:int=0x800112FF
 alias:int=0
 mutation:int=0
 owner_type:int=0x53
 carried_type:int=0x16
 phase:int=0

def symbols(i=0):
 p=(0x800CC2D0,0x02337FFC,0x0343FFFC)[i]
 return dict(D_800CC2D0=p,D_800D154C=(0x800D154C,p+0x40000,p+0x40004)[i],D_800D1580=(0x800D1580,p+0x41004,p+0x41008)[i],D_800C3E78=(0x800C3E78,p+0x42004,p+0x42008)[i],D_800BE616=(0x800BE616,p+0x43004,p+0x43008)[i],func_151B5BA0=(HELPER,0x17107FFC,0x1E108000)[i],func_151B4FE0=(NESTED,0x17117FFC,0x1E118000)[i])
def layout(c,index=0):
 s=symbols(index);target=s['D_800CC2D0']+c.selected*STRIDE
 if c.alias==1:s['D_800C3E78']=target+0x65
 if c.alias==2:s['D_800D1580']=target+0x5C
 if c.alias==3:s['D_800D154C']=target+0x218
 if c.alias==4:s['D_800BE616']=target+0x125
 return s
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for slot in set(range(26))|{c.selected,c.owner,(c.owner+1)&255}:
  a=s['D_800CC2D0']+slot*STRIDE;m.update({a+i:0xA5 for i in range(STRIDE)})
 m.update({0x90000+i:0xA5 for i in range(STRIDE)});m.update({0xA8000+i:0xA5 for i in range(16)})
 put(m,s['D_800D154C'],0x90000);m[0x90000+0x222]=c.selected
 m[s['D_800CC2D0']+c.owner*STRIDE+4]=c.owner_type;m[s['D_800CC2D0']+c.selected*STRIDE+4]=c.carried_type
 put(m,s['D_800D1580'],c.command);m[s['D_800C3E78']]=c.owner;m[s['D_800BE616']]=c.mode;put(m,s['D_800D154C'],0x90000)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-256<=a<STACK+256}
def active(c,s,m):return bool(m[s['D_800BE616']]or m[read(m,s['D_800D154C'])+0x222])
def effect(m,c,s,target):
 if c.mutation:
  put(m,s['D_800D154C'],0xC0000);put(m,s['D_800D1580'],0x89ABCDEF);m[s['D_800C3E78']]=0xE7;m[target+0x101]=0x88
 put(m,0xA8000,0x13579BDF)
def reference(c,s,initial,connected=False):
 m=dict(initial);calls=[];snapshot=None
 if active(c,s,m):
  target=s['D_800CC2D0']+m[read(m,s['D_800D154C'])+0x222]*STRIDE;command=read(m,s['D_800D1580']);parameter=(command>>16)-65536 if command&0x80000000 else command>>16
  vals=((m[s['D_800C3E78']]+1)&255,parameter&0xFFFFFFFF,4,0,255,0,0,0,command&255,0x3F800000,0x3F800000,0x3F800000,0x3F800000)
  for (offset,size),v in zip(FIELDS,vals):put(m,target+offset,v,size)
  owner=s['D_800CC2D0']+m[s['D_800C3E78']]*STRIDE;calls.append((s['func_151B5BA0'],(owner,target)));snapshot=tuple(read(m,target+offset,size)for offset,size in FIELDS)
  if not connected:effect(m,c,s,target)
  elif m[owner+4]==0x53 and m[target+4]==0x16:
   calls.append((s['func_151B4FE0'],(target,255,1)));effect(m,c,s,target)
 return public(m),calls,snapshot
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  self.c,self.s=c,s;self.snapshot=None
  super().__init__(words,memory,c,entry=entry,s={},arguments=(0x12345678,0x87654321),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):
  if t==ENTRY:self.calls.append((t,()));return
  assert t in (self.s['func_151B5BA0'],self.s['func_151B4FE0']),hex(t)
  args=tuple(self.arguments(2 if t==self.s['func_151B5BA0']else 3));self.calls.append((t,args))
  if t==self.s['func_151B5BA0']:self.snapshot=tuple(read(self.memory,args[1]+at,n)for at,n in FIELDS)
 def hook(self,t):
  args=self.calls[-1][1];target=args[1]if t==self.s['func_151B5BA0']else args[0];effect(self.memory,self.c,self.s,target)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xC0DEC0DE

def corpus(full=True):
 for slot,mode,owner,command in itertools.product(range(256)if full else(0,1,25,26,127,255),(0,1),(0,255),(0,0x7FFF1234,0x8001FFFF,0xFFFFFFFF)):
  yield Case(slot,mode,owner,command,mutation=(slot+owner)&1,phase=8 if slot&1 else 0)
 for alias,slot,owner in itertools.product(range(1,5),(0,1,25,255),(0,1,254,255)):
  yield Case(slot,1,owner,0x8001FFFF,alias,1)
 if full:
  for byte in range(256):yield Case(byte,byte,byte,(byte<<24)|(byte<<16)|byte)
  for byte in range(256):yield Case(byte%26,255,25,0xFFFF0000|byte)
def link(obj,label,entry,s,function='func_1507266C',count=53):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[function],relocs,function,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%count,sections(p.with_suffix('.elf'))['.text'][1][:count*4]))
def programs(index=0):
 s=symbols(index);entry=(ENTRY,0x17007FFC,0x1F00FFFC)[index]
 ps=[link(o/n,'initializer-program-%d-%d'%(index,j),entry,s)for j,n in enumerate(('original-func_1507266C.o','qualified-padded.o','make-shadow/src/game_981E0.c.o','selected-final.o'))]
 assert ps[0]==ps[1]==ps[2] and sum(a!=b for a,b in zip(ps[0],ps[3]))==4
 return s,entry,ps
def compare(c,index,ps,entry,connected=None):
 s=layout(c,index);initial=fixture(c,s);expected,calls,snapshot=reference(c,s,initial,connected is not None);models=[]
 # Alias layouts need their own relocated programs, preserving actual global overlap.
 if c.alias:
  key=(index,c.alias,c.selected)
  if key not in _alias_cache:
   _alias_cache[key]=[link(o/n,'alias-%d-%d-%d-%d'%(index,c.alias,c.selected,j),entry,s)for j,n in enumerate(('original-func_1507266C.o','qualified-padded.o','make-shadow/src/game_981E0.c.o','selected-final.o'))]
  ps=_alias_cache[key];assert ps[0]==ps[1]==ps[2]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,connected).run();assert public(m.memory)==expected and m.calls==calls and m.snapshot==snapshot,(c,index,m.calls,calls)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
  models.append(m)
 for m in models[1:3]:assert (m.memory,m.r,m.f,m.trace,m.calls,m.visits)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].calls,models[0].visits)
 assert models[-1].memory==models[0].memory and models[-1].trace==models[0].trace
 return models[0]
def guest():
 count=0;seen=set();retail=None
 for index in range(3):
  s,entry,ps=programs(index)
  for c in corpus(index==0):
   m=compare(c,index,ps,entry);seen.update(pc-entry for pc in m.visits);count+=1
  if not index:retail=ps
 assert seen==set(range(0,212,4)),sorted(set(range(0,212,4))-seen)
 return dict(cases=count,executions=count*4,rebases=3,all_53_words_executed=True,guarded_machine_states_and_traces_equal=True,raw_C_public_memory_calls_and_traces_equal=True,guarded_programs=3,raw_C_programs=1,all_selector_mode_owner_bytes=True,owner_command_current_and_mode_aliases=True),retail
def connected():
 text=(r/'conker/asm/nonmatchings/generated_1E3050/func_151B5BA0.s').read_text().split('endlabel func_151B5BA0')[0]+'endlabel func_151B5BA0\n';p=o/'original-notification.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+text+'.size func_151B5BA0,.-func_151B5BA0\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);count=0;nested=0
 for index in range(3):
  s,entry,ps=programs(index);helper=link(p.with_suffix('.o'),'notification-helper-%d'%index,s['func_151B5BA0'],s,'func_151B5BA0',18);code=dict(zip(range(s['func_151B5BA0'],s['func_151B5BA0']+72,4),helper))
  if index==0:assert helper==list(struct.unpack_from('>18I',(r/'conker/conker.us.bin').read_bytes(),0x1E3050))
  for slot,mode,owner,types,mutation in itertools.product((0,1,25),(0,1),(0,1),((0x53,0x16),(0x53,0x17),(0x54,0x16)),(0,1)):
   c=Case(slot,mode,owner,0x8000FFFF,mutation=mutation,owner_type=types[0],carried_type=types[1]);m=compare(c,index,ps,entry,code);nested+=any(t==s['func_151B4FE0']for t,a in m.calls);count+=1
 return dict(cases=count,executions=count*4,rebases=3,complete_original_notification_words=18,nested_paths=nested,owner_and_carried_identity_gates=True,nested_effect_helper_is_provider=True)
def faults(ps):
 count=0
 for c in (Case(0,0),Case(0,1,255),Case(25,1,0,mutation=1)):
  s=layout(c);initial=fixture(c,s);full=Oracle(ps[0],initial,c,s).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in ps[:3]:
    m=Oracle(words,initial,c,s);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    models.append((m.memory,m.r,m.f,m.calls,m.trace))
   assert models[0]==models[1]==models[2];count+=1
 return dict(prefixes=count,executions=count*3,all_machine_states_and_traces_equal=True,guest_access_order_only=True)
class ReturnPoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1506AEC8:self.owner.r[2]=self.owner.poison;self.owner.poisons+=1
  return super().__getitem__(pc)
def callers(ps):
 s=symbols();rom=(r/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>19I',rom,0x98360);count=0
 census=json.loads((o/'caller-census.json').read_text());assert census['aligned_ROM_JALs']==[]and census['aligned_ROM_pointer_literals']==[0x22B03C]
 for slot,mode,owner,changed in itertools.product((0,1,25),(0,1),(0,255),(0,1)):
  c=Case(slot,mode,owner,mutation=1);initial=fixture(c,s);actor,record=0xB0000,0xB1000;put(initial,actor+0x2D0,record);put(initial,record+0x28,0xB2000);put(initial,actor+0x1C4,0xB3000);put(initial,record+8,0x3F800000);initial[actor+0x138]=7;put(initial,0x8008657C,ENTRY)
  expected,calls,snapshot=reference(c,s,initial)
  if not changed:expected[actor+0x138]=8
  for words,poison in itertools.product(ps,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+212,4),words));m=Oracle(window,initial,c,s,0x1506AEB0,code);m.r[4]=96;m.r[30]=0x800863FC;m.r[17]=actor;m.r[18]=0xB2000+changed;m.poison=poison;m.poisons=0;m.code=ReturnPoisonCode(m.code,m);m.code.ends=(0x1506AEFC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Original dispatch boundary not reached')
   assert public(m.memory)==expected and m.calls==[(ENTRY,())]+calls and m.snapshot==snapshot and m.poisons==1 and m.r[2]==0xB3000
  count+=1
 return dict(cases=count,executions=count*16,callback_slot=96,original_window_words=19,return_poisons=4,return_ignored=True,full_dispatcher_reachability_claimed=False)

def native_cases():
 for slot,mode,owner,command in itertools.product(range(26),(0,1,255),(0,1,25),(0,0x7FFF12FF,0x80001280,0xFFFFFFFF)):yield Case(slot,mode,owner,command,mutation=(slot+owner)&1)
 for byte in range(256):yield Case(1,byte,0,0x80010000|byte)
 for byte,slot in itertools.product(range(256),(0,25)):yield Case(slot,1,25,0xFFFF0000|byte)
def digest(m,s):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 for v in (m[s['D_800BE616']],m[s['D_800C3E78']],read(m,s['D_800D1580']),int(read(m,s['D_800D154C'])!=0x90000),read(m,0xA8000)):mix(v)
 for slot in range(26):
  p=s['D_800CC2D0']+slot*STRIDE
  for at,n in FIELDS:mix(read(m,p+at,n))
 return h
def native():
 controls=(('mode_bypass',source.SELECTED.replace('D_800BE616 || D_800D154C->unk222','D_800D154C->unk222')),
 ('and_gate',source.SELECTED.replace('D_800BE616 || D_800D154C->unk222','D_800BE616 && D_800D154C->unk222')),
 ('unsigned_high',source.SELECTED.replace('parameter = D_800D1580 >> 16','parameter = (u32)D_800D1580 >> 16')),
 ('owner_link',source.SELECTED.replace('D_800C3E78 + 1','D_800C3E78')),
 ('stun_reset',source.SELECTED.replace('stunned = 0','stunned = 1')),
 ('halfword_reset',source.SELECTED.replace('unkE6 = 0','unkE6 = 1')),
 ('scale_reset',source.SELECTED.replace('unkEC = 1.0f','unkEC = 0.0f')),
 ('command_low',source.SELECTED.replace('unk232 = command','unk232 = command >> 8')))
 assert all(text!=source.SELECTED for name,text in controls)
 code=source.HEADERS+'\n'.join(text.replace('void func_1507266C(void)','void candidate_%d(void)'%j)for j,(name,text)in enumerate((('valid',source.SELECTED),)+controls))
 code+='''
struct127 D_800CC2D0[26],current,other;struct127*D_800D154C;u8 D_800BE616,D_800C3E78;s32 D_800D1580;
typedef char ActorSize[sizeof(struct127)==812?1:-1];
typedef struct{u32 slot,mode,owner,command,mutation,expected,calls;}Test;static const Test tests[]={
'''
 rows=[]
 for c in native_cases():
  s=symbols();expected,calls,_=reference(c,s,fixture(c,s));rows.append('{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in(c.selected,c.mode,c.owner,c.command,c.mutation,digest(expected,s),len(calls)))+'}')
 code+=',\n'.join(rows)+'''};
static const Test*active;static u32 calls,bad;static u32 mark;
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 floatBits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static u32 result(void){u32 h=2166136261u,i;struct127*p;h=mix(h,D_800BE616);h=mix(h,D_800C3E78);h=mix(h,D_800D1580);h=mix(h,D_800D154C!=&current);h=mix(h,mark);
for(i=0;i<26;i++){p=&D_800CC2D0[i];h=mix(h,p->unk65);h=mix(h,p->unk5C);h=mix(h,p->unk101);h=mix(h,p->stunned);h=mix(h,p->immune);h=mix(h,(u32)p->unk218);h=mix(h,(u16)p->unkE4);h=mix(h,(u16)p->unkE6);h=mix(h,p->unk232);h=mix(h,floatBits(p->unkEC));h=mix(h,floatBits(p->unkF0));h=mix(h,floatBits(p->unkDC));h=mix(h,floatBits(p->unkE0));}return h;}
void func_151B5BA0(struct127*owner,struct127*carried){calls++;if(owner!=&D_800CC2D0[active->owner]||carried!=&D_800CC2D0[active->slot])bad=1;if(active->mutation){D_800D154C=&other;D_800D1580=0x89ABCDEFu;D_800C3E78=0xE7;carried->unk101=0x88;}mark=0x13579BDFu;}
static void reset(const Test*t){u32 i;u8*p=(u8*)D_800CC2D0;for(i=0;i<sizeof(D_800CC2D0);i++)p[i]=0xA5;p=(u8*)&current;for(i=0;i<sizeof(current);i++)p[i]=0xA5;current.unk222=t->slot;D_800D154C=&current;D_800BE616=t->mode;D_800C3E78=t->owner;D_800D1580=t->command;calls=bad=0;mark=0xA5A5A5A5u;active=t;}
static u32 canaries(const Test*t){u32 i,k,off,allowed;u8*p=(u8*)D_800CC2D0;static const u32 offsets[]={0x65,0x5C,0x101,0x104,0x125,0x218,0xE4,0xE6,0x232,0xEC,0xF0,0xDC,0xE0};static const u32 sizes[]={1,4,1,1,1,4,2,2,1,4,4,4,4};for(i=0;i<sizeof(D_800CC2D0);i++){allowed=0;off=i%812;if((t->mode||t->slot)&&i/812==t->slot)for(k=0;k<13;k++)if(off>=offsets[k]&&off<offsets[k]+sizes[k])allowed=1;if(!allowed&&p[i]!=0xA5)return 0;}p=(u8*)&current;for(i=0;i<sizeof(current);i++)if(i!=0x222&&p[i]!=0xA5)return 0;return 1;}
static int run(void){u32 i,j,killed=0;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<9;j++){reset(&tests[i]);switch(j){case 0:candidate_0();break;case 1:candidate_1();break;case 2:candidate_2();break;case 3:candidate_3();break;case 4:candidate_4();break;case 5:candidate_5();break;case 6:candidate_6();break;case 7:candidate_7();break;default:candidate_8();break;}if(result()!=tests[i].expected||calls!=tests[i].calls||bad){if(!j)return 10;killed|=1u<<(j-1);}if(!j&&!canaries(&tests[i]))return 12;}return killed==255?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native-carried-initializer.c';p.write_text(code);reports=[]
 for profile in ('-O0','-O2','-O3'):
  exe=o/('native-carried-initializer'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);(o/('native-carried-initializer'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,background_canaries_preserved=True,valid_array_indices_only=True,controls=[name for name,text in controls],all_eight_controls_effective=True))
 return reports
def qualify(root,output,core):
 global r,o,source,_alias_cache
 _alias_cache={}
 r,o,source=Path(root),Path(output),core
 g,ps=guest();print('guest',g['cases'],flush=True)
 report=dict(guest=g,connected=connected(),faults=faults(ps),callers=callers(ps),native=native(),guards=4,helper_arguments=2)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
