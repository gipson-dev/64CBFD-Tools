"""Ordinal actor-link lookup: original instruction execution and defined native C."""
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
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.experiments import game_related_actor_lookup_match as source
r=o=None
ENTRY,STRIDE=0x15072208,0x32C
@dataclass(frozen=True)
class Case:
 delta:int=0
 ordinal:int=0
 pattern:int=0
 hit:int=0
 phase:int=0

def symbols(index=0):
 base=(0x800CC2D0,0x02337FFC,0x0343FFFC)[index]
 return dict(D_800CC2D0=base,D_800CC335=base+0x65,D_800CC5FC=base+STRIDE,D_800D121C=base+25*STRIDE)

def owner_index(c):
 delta=((c.delta&0xFFFFFFFF)^0x80000000)-0x80000000
 return (abs(delta)//STRIDE)*(-1 if delta<0 else 1)+1

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)}
 index=owner_index(c)
 for slot in range(26):
  at=s['D_800CC2D0']+slot*STRIDE+0x65
  values=(index,index+1,index if slot%2 else index+1,slot+1,0x80,0xFF,index if slot==c.hit else index+1)
  m[at]=values[c.pattern]&255;m[at-1]=0xC3;m[at+1]=0x7E
 return m

def reference(m,c,s):
 matches=[s['D_800CC2D0']+i*STRIDE for i in range(25)if m[s['D_800CC2D0']+i*STRIDE+0x65]==owner_index(c)]
 ordinal=((c.ordinal&0xFFFFFFFF)^0x80000000)-0x80000000
 return matches[ordinal]if 0<=ordinal<len(matches)else 0

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s={},arguments=((s['D_800CC2D0']+c.delta)&0xFFFFFFFF,c.ordinal&0xFFFFFFFF),connected=connected)
  self.before_f=self.f[:]
 def record_call(self,t):
  assert t==ENTRY,hex(t)
  self.calls.append((t,tuple(self.arguments(2))))
 def hook(self,t):raise AssertionError(('Unexpected helper',hex(t)))

def corpus():
 for owner,ordinal,pattern in itertools.product((0,1,12,24,25,26),(0,1,12,24,25,-1,0x80000000,0x7FFFFFFF),range(6)):
  yield Case(owner*STRIDE,ordinal,pattern,0,8 if owner&1 else 0)
 for hit,ordinal in itertools.product(range(26),(0,1)):
  yield Case(24*STRIDE,ordinal,6,hit)
 # These byte deltas are guest instruction tests, outside portable array subtraction.
 for delta,ordinal,pattern in itertools.product((-1,-STRIDE,-2*STRIDE,127*STRIDE,254*STRIDE,255*STRIDE,STRIDE-1,STRIDE+1),(0,24,-1),range(6)):
  yield Case(delta,ordinal,pattern)

def compare(programs,c,s,entry):
 initial=fixture(c,s);expected=reference(initial,c,s);models=[]
 for program in programs:
  m=Oracle(program,initial,c,s,entry).run()
  assert m.r[2]==expected,(c,hex(m.r[2]),hex(expected))
  assert m.memory==initial and not m.calls and not any(x[0]=='W'for x in m.trace)
  assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f==m.before_f
  models.append(m)
 for m in models[1:]:assert (m.r,m.f,m.memory,m.trace,m.visits)==(models[0].r,models[0].f,models[0].memory,models[0].trace,models[0].visits)
 return models[0]

def guest():
 paths=('original-func_15072208.o','selected-final.o','qualified-padded.o','make-shadow/src/game_981E0.c.o');count=0;seen=set();retail=None
 for index,entry in enumerate((ENTRY,0x17007FFC,0x1F00FFFC)):
  s=symbols(index);programs=[link(o/name,'lookup-program-%d-%d'%(index,i),entry,s)for i,name in enumerate(paths)]
  assert all(p==programs[0]for p in programs)
  for c in corpus():
   m=compare(programs,c,s,entry);seen.update(pc-entry for pc in m.visits);count+=1
  if index==0:retail=programs
 unreachable={0x6C,0x8C,0xAC,0xCC}
 assert set(range(0,232,4))-seen==unreachable,(set(range(0,232,4))-seen)
 return dict(cases=count,executions=count*4,programs=4,body_words=58,frame=0,rebases=3,all_54_reachable_words_executed=True,unreachable_duplicate_count_updates=sorted(unreachable),guest_invalid_pointer_deltas_separate=True,all_machine_states_and_read_traces_equal=True,memory_unchanged=True),retail

def callers(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();s=symbols();count=0
 windows=((0x1501DF38,4),(0x1502E040,2),(0x1506DBDC,4),(0x1507B074,4),(0x15098A70,3),(0x150BDD58,2))
 for start,n in windows:
  body=struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0);end=start+n*4
  for owner,ordinal,pattern in itertools.product((0,12,24,25),(0,1,24,-1),(0,1,2,6)):
   actual_ordinal=ordinal if start==0x15098A70 else 0
   c=Case((0 if start==0x1501DF38 else owner)*STRIDE,actual_ordinal,pattern,24)
   initial=fixture(c,s);put(initial,0x800D154C,s['D_800CC2D0']+c.delta);put(initial,0xA0008,ordinal&0xFFFFFFFF)
   expected=reference(initial,c,s)
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+232,4),program));code[end]=0
    m=Oracle(body,initial,c,s,start,code);m.r[16]=0xA0000;m.r[17]=s['D_800CC2D0']+c.delta;m.r[14]=0x8A
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    assert m.r[2]==expected and m.calls==[(ENTRY,((s['D_800CC2D0']+c.delta)&0xFFFFFFFF,actual_ordinal&0xFFFFFFFF))],(hex(start),c,m.calls)
   count+=1
 # Execute the entire original eight-word zero-ordinal wrapper, including its frame.
 body=struct.unpack_from('>8I',rom,0x9F698)
 for c in (Case(i*STRIDE,0,p,24)for i,p in itertools.product((0,12,24,25),range(7))):
  initial=fixture(c,s);expected=reference(initial,c,s)
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+232,4),program));m=Oracle(body,initial,c,s,0x150721E8,code).run()
   assert m.r[2]==expected and m.r[29]==m.before[29]and m.r[31]==m.before[31]
   assert m.calls==[(ENTRY,(s['D_800CC2D0']+c.delta,0))]
  count+=1
 census=json.loads((o/'caller-census.json').read_text());assert len(census['aligned_ROM_JALs'])==7 and not census['aligned_pointer_literals']
 return dict(cases=count,executions=count*4,ROM_JAL_sites=7,bounded_call_windows=6,complete_original_wrapper_words=8,all_ROM_sites_covered=True,no_aligned_pointer_literals=True,scope='bounded interfaces and complete wrapper, not complete surrounding callers')

def controls():
 return (
 ('owner-off-by-one','owner - D_800CC2D0 + 1','owner - D_800CC2D0'),
 ('include-sentinel','slot < 25','slot < 26'),
 ('skip-first','slot = 0','slot = 1'),
 ('wrong-link','[slot].unk65','[slot].unk64'),
 ('wrong-ordinal','matchIndex == ordinal','matchIndex + 1 == ordinal'),
 ('unsigned-ordinal','s32 ordinal','u8 ordinal'))

def native():
 bodies=[source.SELECTED]
 for name,old,new in controls():assert old in source.SELECTED;bodies.append(source.SELECTED.replace(old,new))
 code=source.HEADERS+'\n'.join(body.replace('func_15072208','candidate_'+str(i))for i,body in enumerate(bodies))
 code+='''
struct127 D_800CC2D0[26];
typedef char SizeCheck[sizeof(struct127)==812?1:-1];
typedef char LinkCheck[__builtin_offsetof(struct127,unk65)==0x65?1:-1];
typedef struct {s32 owner,ordinal,pattern,hit,answer;} Test;
static const Test tests[]={
'''
 rows=[]
 for owner,ordinal,pattern,hit in itertools.product((0,1,12,24,25,26),(0,1,12,24,25,-1,256,0x7FFFFFFF),range(7),(0,24,25)):
  c=Case(owner*STRIDE,ordinal,pattern,hit);s=symbols();answer=reference(fixture(c,s),c,s);slot=-1 if not answer else (answer-s['D_800CC2D0'])//STRIDE
  rows.append('{%d,%d,%d,%d,%d}'%(owner,ordinal,pattern,hit,slot))
 code+=',\n'.join(rows)+'''};
static int run(void){unsigned i,j,k,mask=0;struct127 *answer,*wanted;unsigned char *bytes=(unsigned char*)D_800CC2D0;
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<7;j++){
  const Test *t=&tests[i];s32 index=t->owner+1;
  for(k=0;k<sizeof(D_800CC2D0);k++)bytes[k]=0xA5;
  for(k=0;k<26;k++){s32 value=index;switch(t->pattern){case 1:value=index+1;break;case 2:if(!(k&1))value=index+1;break;case 3:value=k+1;break;case 4:value=128;break;case 5:value=255;break;case 6:if(k!=(unsigned)t->hit)value=index+1;break;}D_800CC2D0[k].unk65=value;}
  wanted=t->answer<0?0:&D_800CC2D0[t->answer];
  switch(j){case 0:answer=candidate_0(&D_800CC2D0[t->owner],t->ordinal);break;case 1:answer=candidate_1(&D_800CC2D0[t->owner],t->ordinal);break;case 2:answer=candidate_2(&D_800CC2D0[t->owner],t->ordinal);break;case 3:answer=candidate_3(&D_800CC2D0[t->owner],t->ordinal);break;case 4:answer=candidate_4(&D_800CC2D0[t->owner],t->ordinal);break;case 5:answer=candidate_5(&D_800CC2D0[t->owner],t->ordinal);break;default:answer=candidate_6(&D_800CC2D0[t->owner],t->ordinal);break;}
  if(answer!=wanted){if(!j)return 10;mask|=1u<<(j-1);}
  for(k=0;k<sizeof(D_800CC2D0);k++)if(k%812!=0x65&&bytes[k]!=0xA5)return 12;
 }
 return mask==63?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-actor-lookup.c';path.write_text(code);reports=[]
 for profile in('-O0','-O2','-O3'):
  exe=o/('native-actor-lookup'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-actor-lookup'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(rows),UBSan=True,defined_array_subtraction=True,controls=[n for n,_,_ in controls()],all_controls_effective=True))
 return reports

def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,programs=guest();report=dict(guest=g,callers=callers(programs),native=native())
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def link(obj,label,entry,s,words=58):
 text,functions,bindings=parse_object(obj);asm,unknown=emit_function(text,functions['func_15072208'],bindings,'func_15072208',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(name,value)for name,value in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_15072208','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 data=sections(p.with_suffix('.elf'))['.text'][1][:words*4];return list(struct.unpack('>%dI'%words,data))
