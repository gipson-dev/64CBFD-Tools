"""Menu dispatch: all selector bytes, original command helpers and frame caller."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode
from tools.tests import test_game_frame_layer_dispatch as frame
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,MARK=0x150B6BC0,0x70000
CASES=(1,2,4,5,6,7,8,9,10)
HELPERS=(0x150B6C90,0x150B6D34,0x150B6D78,0x150B7484,0x150B7560,0x150B765C,0x150B77A8,0x150B768C,0x150B791C)
@dataclass(frozen=True)
class Case:
 selector:int=1
 view:int=0x87654321
 mutation:int=0
 poison:int=0xC0DEC0DE
 phase:int=0
def symbols(i=0):
 s=dict(D_800D9890=(0x800D9890,0x03407FFC,0x02408000)[i],jtbl_8009FD00_game=(0x8009FD00,0x03418000,0x02427FFC)[i])
 s['jtbl_8009FD00']=s['jtbl_8009FD00_game']
 for j,t in enumerate(HELPERS):s['func_%08X'%t]=t if not i else 0x17140000+0x10000*i+0x100*j
 s['func_150B76BC']=0x150B76BC
 return s
def public(m):return {a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def fixture(c,s,entry=ENTRY):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 for base,n in((s['D_800D9890']-8,20),(s['jtbl_8009FD00_game'],48),(MARK,32),(0x800D9898,32)):
  m.update({base+i:0xA5 for i in range(n)})
 m[s['D_800D9890']]=c.selector
 for i,at in enumerate(source.TABLE_OFFSETS):put(m,s['jtbl_8009FD00_game']+4*i,entry+at)
 put(m,s['jtbl_8009FD00_game']+40,0);put(m,s['jtbl_8009FD00_game']+44,0)
 for j in range(3):m.update({0x90000+j*0x100+i:0xA5 for i in range(64)});put(m,0x800D98AC+4*j,0)
 return m
def ordinal(t,s):return next(i+1 for i,h in enumerate(HELPERS)if t==s['func_%08X'%h])
def effect(m,c,s,t):
 if t==s['func_150B76BC']:put(m,MARK,0x13579BDF);m[s['D_800D9890']]=(c.selector+97)&255;return
 put(m,MARK,ordinal(t,s));put(m,MARK+4,c.poison)
 if c.mutation&1:m[s['D_800D9890']]=(c.selector+97)&255
 if c.mutation&2:put(m,s['jtbl_8009FD00_game'],ENTRY+192)
def reference(c,s,initial,connected=False):
 m=dict(initial);calls=[]
 if c.selector in CASES:
  target=s['func_%08X'%HELPERS[CASES.index(c.selector)]];calls.append((target,()))
  if connected and c.selector==2:
   for j in range(3):
    p=read(m,0x800D98AC+4*j)
    if p:put(m,p+0x20,1)
   m[s['D_800D9890']]=3
  elif connected and c.selector in(7,9):
   calls.append((s['func_150B76BC'],(60,1)if c.selector==7 else(230,2)));effect(m,c,s,s['func_150B76BC']);m[s['D_800D9890']]=3
  else:effect(m,c,s,target)
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  self.c,self.s=c,s
  super().__init__(words,memory,c,entry=entry,s={},arguments=(c.view,),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):self.calls.append((t,tuple(self.arguments(2))if t==self.s['func_150B76BC']else()))
 def hook(self,t):
  effect(self.memory,self.c,self.s,t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.c.poison
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);relocs={at:[(k,source.RODATA_SYMBOL if n=='.rodata'else n)for k,n in uses]for at,uses in relocs.items()};assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);
 if unknown:
  assert unknown==['.L150B6C80'],unknown
  rows=[v for v in source.symbol_rows(obj.read_bytes())if v[1]=='.L150B6C80'];assert len(rows)==1 and rows[0][2][1]-fs[source.FUNCTION]['value']==192
  s=dict(s,**{'.L150B6C80':entry+192})
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>52I',sections(p.with_suffix('.elf'))['.text'][1][:208]))
def programs(i):
 s=symbols(i);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 ps=[link(o/n,'dispatch-program-%d-%d'%(i,j),entry,s)for j,n in enumerate(('original-func_150B6BC0.o','qualified-padded.o','make-shadow/src/game/generated_E4070.c.o','selected-final.o'))]
 assert ps[0]==ps[1]==ps[2]==ps[3]
 return s,entry,ps
def compare(c,s,entry,ps,initial=None,connected=None):
 initial=fixture(c,s,entry)if initial is None else initial;expected,calls=reference(c,s,initial,connected is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,connected).run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 for m in models[1:]:assert(m.memory,m.r,m.f,m.trace,m.calls)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].calls)
 return models[0]
def guest():
 count=0;seen=set()
 for i in range(3):
  s,entry,ps=programs(i)
  for selector,view,mode in itertools.product(range(256),(0,1,0x80000000,0xFFFFFFFF),range(4)if i==0 else(0,3)):
   c=Case(selector,view,mode,poison=view^0xC0DEC0DE,phase=8 if view&1 else 0);m=compare(c,s,entry,ps);seen.update(pc-entry for pc in m.visits);count+=1
 assert seen==set(range(0,208,4)),sorted(set(range(0,208,4))-seen)
 return dict(cases=count,executions=count*4,rebases=3,all_52_words_executed=True,all_four_programs_full_state_and_trace_equal=True,all_selector_bytes=True,helper_state_mutation_does_not_redispatch=True),programs(0)[2]
def faults(ps):
 total=0
 for c in(Case(0),Case(3),Case(1,mutation=3),Case(10,mutation=3)):
  s=symbols();initial=fixture(c,s);full=Oracle(ps[0],initial,c,s).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in ps:
    m=Oracle(words,initial,c,s);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    models.append((m.memory,m.r,m.f,m.calls,m.trace))
   assert all(v==models[0]for v in models);total+=1
 return dict(prefixes=total,executions=total*4,all_programs_machine_states_equal=True,guest_instruction_access_order_only=True)
def connected(ps):
 rom=(r/'conker/conker.us.bin').read_bytes();code={};sizes=((0x150B6D34,0xE41E4,17),(0x150B765C,0xE4B0C,12),(0x150B768C,0xE4B3C,12));count=0;seen=set()
 for va,off,n in sizes:code.update(zip(range(va,va+4*n,4),struct.unpack_from('>%dI'%n,rom,off)))
 for selector,mask,view in itertools.product((2,7,9),range(8),(0,0x80000000)):
  c=Case(selector,view,3);s=symbols();initial=fixture(c,s)
  for j in range(3):put(initial,0x800D98AC+4*j,0x90000+j*0x100 if mask>>j&1 else 0)
  m=compare(c,s,ENTRY,ps,initial,code);seen.update(m.visits);count+=1
 for va,off,n in sizes:assert all(va+4*j in seen for j in range(n))
 return dict(cases=count,executions=count*4,original_helper_words=[17,12,12],all_41_helper_words_executed=True,descriptor_constructor_is_provider=True,other_command_bodies_are_providers=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x15174A58:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==ENTRY:self.calls.append((t,tuple(self.arguments(1))));return
  names=frame.CALLEES
  if t in(frame.SYMBOLS[n]for n in names):self.calls.append((t,tuple(self.arguments(2))if t==frame.SYMBOLS[names[1]]else()));return
  super().record_call(t)
 def hook(self,t):
  if t in(frame.SYMBOLS[n]for n in frame.CALLEES):
   kind=next(i for i,n in enumerate(frame.CALLEES)if frame.SYMBOLS[n]==t);frame.effect(self.memory,frame.SYMBOLS,self.fc,kind,STACK+self.c.phase)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
   self.r[2]=0xA5000002;return
  super().hook(t)
def callers(ps):
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>43I',rom,0x1A1EA8);census=json.loads((o/'caller-census.json').read_text());assert not census['aligned_ROM_JALs']and not census['aligned_ROM_Js']and census['aligned_ROM_pointer_literals']==[0x2317D8];count=0;seen=set()
 for selector,view,gate,mode in itertools.product((0,1,2,3,7,9,10,255),(0,0x80000000),(0,1),(0,4)):
  c=Case(selector,view,1,poison=0xC0DEC0DE);fc=frame.Case(selector=5,disabled=gate,clock=0xFFFFFFFF,accumulator=0xFFFF,view=view,mode=mode);initial=frame.fixture(fc);initial.update(fixture(c,symbols()));put(initial,frame.SYMBOLS['D_800B0DF0'],frame.ROWS[0]);initial[frame.ROWS[0]+11]=5;put(initial,frame.SYMBOLS['D_8008CD04']+20,ENTRY)
  # fixture() owns only disjoint root globals/stack; preserve frame argument homes.
  expected=dict(initial);put(expected,STACK,fc.unused);put(expected,STACK+4,view);calls=[]
  for k in range(3):
   target=frame.SYMBOLS[frame.CALLEES[k]];a=(read(expected,frame.SYMBOLS['D_800B0E00']),read(expected,frame.SYMBOLS['D_800B0E00']+4))if k==1 else();calls.append((target,a));frame.effect(expected,frame.SYMBOLS,fc,k,STACK)
  expected,rootcalls=reference(c,symbols(),expected);calls.append((ENTRY,(view,)));calls.extend(rootcalls)
  if not expected[frame.SYMBOLS['D_800BE616']]:
   for k in(3,4):calls.append((frame.SYMBOLS[frame.CALLEES[k]],()));frame.effect(expected,frame.SYMBOLS,fc,k,STACK)
  put(expected,frame.SYMBOLS['D_800CBD4E'],read(expected,frame.SYMBOLS['D_800CBD4E'],2)+(read(expected,frame.SYMBOLS['D_800BE9E4'])<<6),2)
  for body,poison in itertools.product(ps,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+208,4),body));m=CallerOracle(words,initial,c,symbols(),0x151749F8,code);m.fc=fc;m.r[4]=fc.unused;m.r[5]=view;m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=();m.run();assert public(m.memory)==public(expected)and m.calls==calls and m.poison_hits==1,(c,gate,mode,m.calls,calls);seen.update(m.visits)
  count+=1
 assert all(0x151749F8+4*j in seen for j in range(43))
 return dict(cases=count,executions=count*16,complete_original_caller_words=43,all_43_words_executed=True,frame_callback_slot=5,return_poisons=4,void_result_ignored=True,other_frame_providers_are_bounded=True)
def native():
 selected=source.SELECTED
 controls=(('dispatch_idle_three',selected.replace('    case 3:\n        break;','    case 3:\n        func_150B6D78();\n        break;')if '    case 3:'in selected else selected.replace('    default: break;','    case 3: func_150B6D78(); break;\n    default: break;')),
 ('missing_ten',selected.replace('        func_150B791C();','')),
 ('wrong_eight',selected.replace('        func_150B77A8();','        func_150B768C();')),
 ('fallthrough_one',selected.replace('func_150B6C90();\n        break;','func_150B6C90(); /* fall through */')),
 ('missing_two',selected.replace('        func_150B6D34();','')),
 ('duplicate_five',selected.replace('        func_150B7484();','        func_150B7484();\n        func_150B7484();')),
 ('masked_selector',selected.replace('switch (D_800D9890)','switch (D_800D9890 & 7)')),
 ('shifted_selector',selected.replace('switch (D_800D9890)','switch (D_800D9890 + 1)')))
 assert all(text!=selected for name,text in controls)
 code=source.HEADERS+'\n'.join(text.replace('func_150B6BC0(', 'candidate_%d('%i)for i,(name,text)in enumerate((('valid',selected),)+controls))
 code+='''
u8 D_800D9890;static u32 calls,mark,mode,poison;
static u32 before=0x13572468u,after=0x24681357u;
static s32 invoke(u32 id){calls++;mark=id;if(mode)D_800D9890=(u8)(D_800D9890+97);return(s32)poison;}
'''
 for i,t in enumerate(HELPERS):code+=('%s func_%08X(void){%s}\n'%('void'if i<4 else's32',t,('invoke(%d);'%(i+1))if i<4 else('return invoke(%d);'%(i+1))))
 code+='''
static int run(void){u32 s,v,m,j,killed=0,expected,final;static const u32 views[]={0,1,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu,0xFFFF8000u,0x12345678u,0x87654321u};
for(s=0;s<256;s++)for(v=0;v<8;v++)for(m=0;m<2;m++)for(j=0;j<9;j++){
 D_800D9890=s;calls=0;mark=0xA5A5A5A5u;mode=m;poison=views[v]^0xC0DEC0DEu;
 switch(j){case 0:candidate_0((s32)views[v]);break;case 1:candidate_1((s32)views[v]);break;case 2:candidate_2((s32)views[v]);break;case 3:candidate_3((s32)views[v]);break;case 4:candidate_4((s32)views[v]);break;case 5:candidate_5((s32)views[v]);break;case 6:candidate_6((s32)views[v]);break;case 7:candidate_7((s32)views[v]);break;default:candidate_8((s32)views[v]);break;}
 expected=0;switch(s){case 1:expected=1;break;case 2:expected=2;break;case 4:expected=3;break;case 5:expected=4;break;case 6:expected=5;break;case 7:expected=6;break;case 8:expected=7;break;case 9:expected=8;break;case 10:expected=9;break;}
 final=expected&&m?(s+97)&255:s;
 if(calls!=(expected?1u:0u)||mark!=(expected?expected:0xA5A5A5A5u)||D_800D9890!=final){if(!j)return 10;killed|=1u<<(j-1);}
 if(before!=0x13572468u||after!=0x24681357u)return 12;
}return killed==255?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native-dispatch.c';p.write_text(code);reports=[]
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-dispatch'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);(o/('native'+opt+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
  reports.append(dict(profile=opt,cases=4096,UBSan=True,controls=[n for n,t in controls],all_eight_controls_effective=True,canaries=True,all_selector_bytes=True))
 return reports
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,ps=guest();print('guest',g,flush=True)
 report=dict(guest=g,faults=faults(ps),connected=connected(ps),callers=callers(ps),native=native(),guards=0,installed=False,matching_credit=0)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
