"""Mode/category byte semantics with explicit helper mutations and caller windows."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
r=o=source=None
ENTRY,FIRST,MODE=0x151645C4,0x1515F170,0x1511172C
A,B,SCRIPT=0xA0000,0xB0000,0x90000
FIELDS=('D_800DCDD0','D_800BE9F0','D_800DCD20','D_800B0DF0','D_800886F0','D_800886F4','D_800886F8')
DEFAULT=dict(zip(FIELDS,(0x800DCDD0,0x800BE9F0,0x800DCD20,0x800B0DF0,0x800886F0,0x800886F4,0x800886F8)))
CATEGORIES=(0,6,7,11,12,41,57,255,0x10006,0x80000000,0xFFFFFFFF)
@dataclass(frozen=True)
class Case:
 mode:int=0
 category:int=6
 mutation:int=0
 alias:int=0
 phase:int=0
def symbols(index=0):
 if not index:return dict(DEFAULT,func_1515F170=FIRST,func_1511172C=MODE)
 base=(0x02237FFC,0x0233FFFC)[index-1]
 offsets=(0,4,0x8004,0x10004,0x18004,0x20004,0x28004)
 return dict(zip(FIELDS,(base+offset for offset in offsets)),func_1515F170=FIRST,func_1511172C=MODE)
def fixture(c,s):
 s=dict(s)
 if c.alias==1:s['D_800DCD20']=s['D_800886F0'if c.mode&255 else'D_800886F8']+1
 if c.alias==4:s['D_800DCDD0']=s['D_800BE9F0']+3
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
 for base,n in((A,128),(B,128),(SCRIPT,16),*((v-8,24)for name,v in s.items()if name in FIELDS)):
  assert not STACK-512<=base<STACK+256
  m.update({base+i:(i*13+0x59)&255 for i in range(n)})
 for name,values in(('D_800886F0',(0x11,0x22,0x33)),('D_800886F4',(0x44,0x88,0xCC)),('D_800886F8',(0xFE,0x80,1))):
  for i,v in enumerate(values):m[s[name]+i]=v
 m[s['D_800DCDD0']]=0x55;put(m,s['D_800BE9F0'],c.category)
 pointer=A
 if c.alias==2:pointer=s['D_800886F4']-4
 if c.alias==3:
  assert c.mutation==0;pointer=(s['D_800B0DF0']-5)&0xFFFFFFFF
  red=0x44 if c.mode&255 else 255;next_pointer=(red<<24)|(pointer&0xFFFFFF)
  for i in range(32):m[(next_pointer+i)&0xFFFFFFFF]=(i*13+0x59)&255
 put(m,s['D_800B0DF0'],pointer);m[SCRIPT+5]=c.mode&255
 return m,s
def effect(m,c,s,tag,n):
 if not c.mutation&(1 if tag==0 else 2):return
 put(m,s['D_800BE9F0'],0x61230000+n);m[s['D_800DCDD0']]=0xA0+tag
 for name,start,step in(('D_800886F0',0x21,13),('D_800886F4',0x43,11),('D_800886F8',0x65,17)):
  for i in range(3):m[s[name]+i]=(tag*64+n*7+start+i*step)&255
 put(m,s['D_800B0DF0'],(A,B)[(tag+n)&1])
def reference(initial,c,s):
 m=dict(initial);enabled=c.mode&255;m[s['D_800DCDD0']]=enabled;category=read(m,s['D_800BE9F0']);calls=[]
 def call(tag,args):
  target=(s['func_1515F170'],s['func_1511172C'])[tag];calls.append((target,args));effect(m,c,s,tag,len(calls))
 def tint(name):
  rgb=[m[s[name]+i]for i in range(3)]
  for i,v in enumerate(rgb):m[s['D_800DCD20']+i]=v
 if enabled:
  if category==11:call(1,(4,))
  elif category in(6,57):
   if category==6:call(0,(10,1));call(1,(4,))
   tint('D_800886F0')
   for i in range(3):
    target=read(m,s['D_800B0DF0']);value=m[s['D_800886F4']+i];m[(target+5+i)&0xFFFFFFFF]=value
 else:
  if category in(6,7,12,57):
   if category==6:call(0,(10,0))
   call(1,(6,));tint('D_800886F8')
   for i in range(3):m[(read(m,s['D_800B0DF0'])+5+i)&0xFFFFFFFF]=255
  elif category==11:call(1,(6,))
  elif category==41:call(1,(1,))
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None,caller=None):
  self.c,self.s,self.service_count=c,s,0
  super().__init__(words,memory,c,entry=entry,s={},arguments=(c.mode&0xFFFFFFFF,),connected=connected)
  self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==14:
   self.r[w>>16&31]=(self.r[w>>21&31]^(w&65535))&0xFFFFFFFF;self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  counts={self.s['func_1515F170']:2,self.s['func_1511172C']:1,ENTRY:1};assert t in counts,hex(t)
  a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t!=ENTRY:self.service_count+=1
 def hook(self,t):
  assert t in(self.s['func_1515F170'],self.s['func_1511172C']);tag=0 if t==self.s['func_1515F170']else 1
  effect(self.memory,self.c,self.s,tag,self.service_count)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
def link(obj,label,entry,s,words=108):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_151645C4'],bindings,'func_151645C4',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151645C4','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def compare(programs,c,s,entry=ENTRY):
 initial,s=fixture(c,s);expected,calls=reference(initial,c,s);models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry).run();assert public(m.memory)==public(expected)and m.calls==calls,(c,'state/calls')
  assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 for m in models[1:]:assert m.memory==models[0].memory and m.r==models[0].r and m.f==models[0].f and m.trace==models[0].trace
 return models[0]
def guest():
 paths=('original-func_151645C4.o','selected-final.o','qualified-padded.o','make-shadow/src/game_18D770.c.o');count=0;seen=set();program_sets=[]
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/name,'mode-program-%d-%d'%(index,i),entry,s)for i,name in enumerate(paths)];assert all(p==programs[0]for p in programs);program_sets.append(programs)
  if not index:
   for mode,category in itertools.product(range(256),CATEGORIES):
    m=compare(programs,Case(mode,category),s,entry);seen.update(pc-entry for pc in m.visits);count+=1
  for mode,category,mutation,alias,phase in itertools.product((0,1,0x80,0x100,0x101),(6,7,11,12,41,57,255),(0,3),(0,1,2,4),(0,8)):
   c=Case(mode,category,mutation,alias,phase)
   # Alias-specific symbol values are independently linked; never mutate data addresses behind a program.
   if alias:
    _,adjusted=fixture(c,s);tag='alias-%d-%d-%d'%(index,alias,bool(mode&255));alias_paths=[o/('mode-alias-%s-%d.elf'%(tag,i))for i in range(4)]
    if not all(p.exists()for p in alias_paths):
     alt=[link(o/name,'mode-alias-%s-%d'%(tag,i),entry,adjusted)for i,name in enumerate(paths)]
    else:alt=[list(struct.unpack('>108I',sections(p)['.text'][1][:432]))for p in alias_paths]
   else:alt=programs
   compare(alt,c,s,entry);count+=1
  for mode,category in((1,57),(0,7)):
   compare(programs,Case(mode,category,0,3,0),s,entry);count+=1
 assert set(range(0,432,4))<=seen
 return dict(cases=count,executions=count*4,programs=4,body_words=108,alignment_words=3,all_body_words_reached=True,root_and_global_rebases=3,all_256_low_bytes=True,ordered_live_byte_aliases=True,helper_mutations=True,all_public_memory_canaries_saved_state=True,all_machine_states_and_traces_equal=True),program_sets[0]
def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();count=0
 windows=((0x15025290,4,0x150265B4),(0x1509D9A0,7,0x1509DBB0),(0x1500E594,8,0x1500E5B4))
 for wi,(start,n,end)in enumerate(windows):
  body=list(struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0))
  for mode,category,mutation,phase in itertools.product((0,1,6,0x80,0x7F,0x106,0xFFFFFFFF),(6,7,11,12,41,57,255),(0,3),(0,8)):
   c=Case(mode,category,mutation,0,phase);initial,s0=fixture(c,s);effective=mode&255 if wi==0 else int(mode==6)if wi==1 else int((mode&0x80)==0);actual=replace(c,mode=effective);expected,calls=reference(initial,actual,s0)
   if wi==2:
    for memory in(initial,expected):put(memory,0x800D2E4C,SCRIPT);memory[SCRIPT+4]=mode&255
   put(initial,STACK+phase+0x44,mode);put(expected,STACK+phase+0x44,mode);put(initial,STACK+phase+0x14,0xDEAD0000);put(expected,STACK+phase+0x14,0xDEAD0000)
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+432,4),program));code[end]=0;m=Oracle(body,initial,actual,s0,start,code)
    m.r[18]=SCRIPT;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Mode caller stop not reached')
    assert public(m.memory)==public(expected)and m.calls==[(ENTRY,(effective,))]+calls
    assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30))
    if wi==0:assert m.r[2]==1
   count+=1
 return dict(windows=3,cases=count,executions=count*4,full_caller_reachability_claimed=False,script_unsigned_byte_and_fullword_equality_argument_forms=True,inverted_bit_128_argument_form=True,first_caller_overwrites_return_with_one=True)
def digest(memory,calls,s):
 values=[memory[s['D_800DCDD0']],read(memory,s['D_800BE9F0']),int(read(memory,s['D_800B0DF0'])==B)]
 for name in('D_800886F0','D_800886F4','D_800886F8','D_800DCD20'):values.extend(memory[s[name]+i]for i in range(3))
 for base in(A,B):values.extend(memory[base+i]for i in range(128))
 values.append(len(calls))
 for target,args in calls:values.extend((0 if target==FIRST else 1,args[0],args[1]if len(args)==2 else 0))
 h=2166136261
 for value in values:h=((h^(value&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def guest_controls():
 body=source.SELECTED.replace('void func_151645C4(u8 enabled) {','void func_151645C4(u8 enabled) {\n    struct104 *colorObject;')
 body=body.replace('D_800B0DF0->unk5 =','colorObject = D_800B0DF0;\n                colorObject->unk5 =').replace('D_800B0DF0->unk6','colorObject->unk6').replace('D_800B0DF0->unk7','colorObject->unk7')
 obj,diag=compile_owner(r,o,source.HEADERS+body,'public-cached-object-negative');assert not diag
 assert source.payload(obj)==source.payload(o/'cached-object-negative.o'),'Fresh negative-control code or bindings changed'
 controls=[('partial_struct_copy',o/'mode-return-return-struct.o',Case(1,57,0,1)),('cached_object_pointer',obj,Case(1,57,0,3))];reports=[]
 for name,obj,c in controls:
  initial,s=fixture(c,symbols());expected,calls=reference(initial,c,s);words=len(source.payload(obj)[0])//4
  program=link(obj,'negative-'+name,ENTRY,s,words);m=Oracle(program,initial,c,s).run()
  assert m.calls==calls and public(m.memory)!=public(expected),(name,'Ineffective compiled byte-alias control')
  reports.append(dict(name=name,compiled=True,words=words,public_memory_control_effective=True))
 return reports
def native():
 changes=[('fullword_mode','u8 enabled','u32 enabled'),('missing_mode','D_800DCDD0 = enabled;','(void)enabled;'),('wrong_enabled_mode','func_1511172C(4);','func_1511172C(6);'),('missing_first_helper','func_1515F170(10, 1);','(void)enabled;'),('wrong_white','D_800B0DF0->unk6 = 0xFF;','D_800B0DF0->unk6 = 0xFE;'),('wrong_tint','CATEGORY_MODE_TINT.unk1 = D_800886F8.unk1;','CATEGORY_MODE_TINT.unk1 = D_800886F0.unk1;')]
 bodies=[source.SELECTED]
 for name,old,new in changes:assert old in source.SELECTED;bodies.append(source.SELECTED.replace(old,new))
 code=source.HEADERS+'\n'.join(body.replace('func_151645C4','candidate_'+str(i))for i,body in enumerate(bodies))
 code+='''
struct100 D_800886F0,D_800886F4,D_800886F8,D_800DCD20;
struct104 *D_800B0DF0;
u8 D_800DCDD0; s32 D_800BE9F0;
typedef union {struct104 value;u8 bytes[128];} Object;
static Object objects[2];static u32 mutation,call_count,call_log[2][3];
static void effect(u32 tag){u32 i,n=call_count;
 if(!(mutation&(tag?2:1)))return;D_800BE9F0=0x61230000u+n;D_800DCDD0=0xA0+tag;
 for(i=0;i<3;i++){((u8*)&D_800886F0)[i]=(tag*64+n*7+0x21+i*13)&255;((u8*)&D_800886F4)[i]=(tag*64+n*7+0x43+i*11)&255;((u8*)&D_800886F8)[i]=(tag*64+n*7+0x65+i*17)&255;}
 D_800B0DF0=&objects[(tag+n)&1].value;}
void func_1515F170(s32 category,u8 enabled){call_log[call_count][0]=0;call_log[call_count][1]=category;call_log[call_count][2]=enabled;call_count++;effect(0);}
void func_1511172C(s32 mode){call_log[call_count][0]=1;call_log[call_count][1]=mode;call_log[call_count][2]=0;call_count++;effect(1);}
typedef struct {u32 mode,category,mutation,expected;} Test;
static const Test tests[]={
'''
 rows=[]
 modes=list(range(256))+[0x100,0x101,0xFFFFFF00,0xFFFFFFFF]
 for mode,category,mutate in itertools.product(modes,CATEGORIES,(0,3)):
  c=Case(mode,category,mutate);initial,s=fixture(c,symbols());expected,calls=reference(initial,c,s);rows.append('{0x%Xu,0x%Xu,%d,0x%Xu}'%(mode,category,mutate,digest(expected,calls,s)))
 code+=',\n'.join(rows)+'''};
static u32 mix(u32 h,u32 v){return(h^v)*16777619u;}
static u32 result(void){u32 h=2166136261u,i,j;u8 *p;h=mix(h,D_800DCDD0);h=mix(h,(u32)D_800BE9F0);h=mix(h,D_800B0DF0==&objects[1].value);
 p=(u8*)&D_800886F0;for(i=0;i<3;i++)h=mix(h,p[i]);p=(u8*)&D_800886F4;for(i=0;i<3;i++)h=mix(h,p[i]);p=(u8*)&D_800886F8;for(i=0;i<3;i++)h=mix(h,p[i]);p=(u8*)&D_800DCD20;for(i=0;i<3;i++)h=mix(h,p[i]);
 for(j=0;j<2;j++)for(i=0;i<128;i++)h=mix(h,objects[j].bytes[i]);h=mix(h,call_count);for(j=0;j<call_count;j++)for(i=0;i<3;i++)h=mix(h,call_log[j][i]);return h;}
static void reset(const Test *t){u32 i,j;for(j=0;j<2;j++)for(i=0;i<128;i++)objects[j].bytes[i]=(i*13+0x59)&255;
 D_800886F0.unk0=0x11;D_800886F0.unk1=0x22;D_800886F0.unk2=0x33;D_800886F4.unk0=0x44;D_800886F4.unk1=0x88;D_800886F4.unk2=0xCC;D_800886F8.unk0=0xFE;D_800886F8.unk1=0x80;D_800886F8.unk2=1;
 D_800DCD20.unk0=0xC1;D_800DCD20.unk1=0xCE;D_800DCD20.unk2=0xDB;
 D_800DCDD0=0x55;D_800BE9F0=(s32)t->category;D_800B0DF0=&objects[0].value;mutation=t->mutation;call_count=0;}
static int run(void){u32 i,j,killed=0,h;
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<7;j++){
 reset(&tests[i]);switch(j){case 0:candidate_0(tests[i].mode);break;case 1:candidate_1(tests[i].mode);break;case 2:candidate_2(tests[i].mode);break;case 3:candidate_3(tests[i].mode);break;case 4:candidate_4(tests[i].mode);break;case 5:candidate_5(tests[i].mode);break;default:candidate_6(tests[i].mode);break;}
 h=result();if(h!=tests[i].expected){if(!j)return 10;killed|=1u<<(j-1);}}
 return killed==63?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-category-mode.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-category-mode'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-category-mode'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,all_256_low_bytes=True,negative_controls=[name for name,_,_ in changes],all_controls_effective=True))
 return reports
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();report=dict(guest=g,callers=callers(programs),guest_controls=guest_controls(),native=native(),helper_providers_explicit=True)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
