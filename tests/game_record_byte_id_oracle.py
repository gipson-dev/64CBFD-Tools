"""Private immutable-table equivalence and three original caller windows."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_record_byte_id_match as source
ENTRY=0x15004BF0;COUNT,BASE,START=0x800DBEF0,0x800DBEF4,0x800DBF00;RECORDS,OUTPUT=0x30000,0x50000
words=lambda entry,n:list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))
def configure(root,output,obj):
 global r,o,rom,truth,raw_object
 r,o,raw_object=root,output,obj;rom=(r/'conker/conker.us.bin').read_bytes();truth=words(ENTRY,60)
@dataclass(frozen=True)
class Case:
 descending:int=0
 reserved:int=0
 count:int=4
 pattern:int=0
 phase:int=0

def ids(c):
 n=max(0,c.count)
 if c.pattern==0:return [0]*n
 if c.pattern==1:return [(i+1)&255 for i in range(n)]
 if c.pattern==2:return [1]*n
 if c.pattern==3:return [(255-i)&255 for i in range(n)]
 return [(2*i+1)&255 for i in range(n)]

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)};put(m,COUNT,c.count);put(m,BASE,RECORDS);m[START]=c.reserved;m[OUTPUT+0x72]=0x59
 for i,value in enumerate(ids(c)):m[RECORDS+i*0xA0+0x72]=value
 return m

def reference(c,descending=None):
 descending=c.descending if descending is None else descending
 if not descending:
  used=set(ids(c)[c.reserved:]);return next((v for v in range(1,256) if v not in used),255)
 limit=255-c.reserved;used=set(ids(c));return next((v for v in range(limit,0,-1) if v not in used),limit)

def public(m):return {a:v for a,v in m.items() if not STACK-128<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,program,initial,c,entry=ENTRY,connected=None):super().__init__(program,initial,c,entry=entry,s={},connected=connected,arguments=(c.descending&0xFFFFFFFF,))
 def record_call(self,t):assert t==ENTRY;self.calls.append((t,(self.r[4],)))
 def hook(self,t):raise AssertionError(('Unexpected service',hex(t)))

# The inherited 50k step cap is insufficient for the bounded 256-record
# saturation fixture. Clone its exact run loop locally with a one-million cap;
# no shared interpreter file is modified.
import inspect,textwrap
runner=textwrap.dedent(inspect.getsource(FactoryOracle.run));assert runner.count('range(50000)')==1
namespace=dict(FactoryOracle.run.__globals__);exec(compile(runner.replace('range(50000)','range(1000000)'),'<bounded-byte-id-run>','exec'),namespace);Oracle.run=namespace['run']
def run_suite():
 text,fs,rs=parse_object(raw_object);syms=dict(D_800DBEF0=COUNT,D_800DBEF4=BASE,D_800DBF00=START);asm,unknown=emit_function(text,fs['func_15004BF0'],rs,'func_15004BF0',syms);assert not unknown;p=o/'raw-linked'
 p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x15004BF0 : SUBALIGN(4) { *(.text) } }\n'+'\n'.join('%s = 0x%X;'%(k,v) for k,v in syms.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_15004BF0','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 raw=list(struct.unpack('>60I',sections(p.with_suffix('.elf'))['.text'][1][:240]));cases=[Case(*v) for v in itertools.product((0,1,-1,0x100),(0,1,2,127,254,255),(-1,0,1,4,16),range(5))];cases.extend([Case(d,0,256,pat) for d,pat in itertools.product((0,1),(1,3))]);seen=set();roots=0
 for c in cases:
  initial=fixture(c);expected=reference(c)
  for program in (truth,raw):
   m=Oracle(program,initial,c);m.run();assert m.r[2]==expected and public(m.memory)==public(initial) and not m.calls,(c,m.r[2],expected);seen.update(m.visits)
  roots+=1
 windows=[(0x15003F90,5,1,0x15003FA4),(0x150041A4,3,1,0x150041B0),(0x15004518,8,0,0x15004538)];caller_cases=0
 for entry,n,descending,end in windows:
  for reserved,pattern in itertools.product((0,1,255),(0,1,3)):
   c=Case(0xBAD0,reserved,16,pattern);initial=fixture(c);result=reference(c,descending);baseline=None
   for program in (truth,raw):
    code=dict(zip(range(ENTRY,ENTRY+240,4),program));m=Oracle(words(entry,n),initial,c,entry=entry,connected=code);m.r[16]=OUTPUT;m.r[19]=BASE;m.r[21]=0;m.r[17]=123;m.r[9]=0x12345678;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not stop at its fixed boundary')
    target=RECORDS if entry==0x15004518 else OUTPUT;assert m.memory[target+0x72]==result and m.calls==[(ENTRY,(descending,))]
    if entry==0x15004518:assert m.r[17]==124 and m.r[8]==16
    observed=(public(m.memory),m.calls)
    if baseline is None:baseline=observed
    else:assert observed==baseline
   caller_cases+=1
 # Empty tables never dereference a missing record base, including signed negative count.
 sparse=0
 for c in (Case(0,0,-1),Case(1,255,0),Case(0,255,16)):
  initial=fixture(c);initial={a:v for a,v in initial.items() if not (a==BASE or BASE<a<BASE+4 or RECORDS<=a<OUTPUT)}
  for program in (truth,raw):
   m=Oracle(program,initial,c);m.run();assert m.r[2]==reference(c);sparse+=1
 report=dict(private_only=True,installed=False,matching_credit=0,root_cases=roots,root_executions=roots*2,retail_reachable_words=len(seen&set(range(ENTRY,ENTRY+240,4))),caller_windows=[dict(entry=hex(a),words=n,descending=d) for a,n,d,end in windows],caller_cases=caller_cases,caller_executions=caller_cases*2,all_three_actual_calls_consume_result_as_byte=True,saturation_cases=4,sparse_executions=sparse,raw_payload_not_exact=False,relocation_offsets_not_yet_matched=False,immutable_table_domain=True,remaining=['source/register/relocation recovery','native32 and controls','alias/access-order/rebases','Make/strict image and adoption gates'])
 return report

def run_rebases():
 global COUNT,BASE,START
 original=(COUNT,BASE,START);cases=0
 profiles=[(0x15004BF0,original),(0x1ABC0000,(0x31008000,0x41007FFC,0x5100FFFF)),
           (0x151FFFF0,(0x3200FFFC,0x42008000,0x52000000))]
 try:
  for number,(entry,addresses) in enumerate(profiles):
   COUNT,BASE,START=addresses;programs=[]
   for label,obj in (('raw',raw_object),('retail',r/source.BUILD/'original-func_15004BF0.o')):
    path=o/('rebase-%d-%s'%(number,label));script=path.with_suffix('.ld')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+
                     '\n'.join('%s = 0x%X;'%(n,v) for n,v in zip(('D_800DBEF0','D_800DBEF4','D_800DBF00'),addresses)))
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15004BF0','-o',str(path.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
    data=sections(path.with_suffix('.elf'))['.text'][1][:240];programs.append(list(struct.unpack('>60I',data)))
   assert programs[0]==programs[1]
   for c in (Case(0,0,16,1),Case(1,1,4,3),Case(0,255,0,0)):
    initial=fixture(c);expected=reference(c)
    for program in programs:
     m=Oracle(program,initial,c,entry=entry);m.run();assert m.r[2]==expected and public(m.memory)==public(initial)
    cases+=1
 finally:COUNT,BASE,START=original
 return dict(profiles=len(profiles),cases=cases,executions=cases*2,independent_global_addresses=True,
             signed_low16_carries=True,entire_rebased_payloads_identical=True)

def run_prefixes_and_alias():
 global START
 from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
 program=list(struct.unpack('>60I',sections(o/'raw-linked.elf')['.text'][1][:240]));prefixes=0
 for c in (Case(0,0,4,1),Case(1,0,4,3),Case(0,255,0,0),Case(1,255,4,0)):
  initial=fixture(c);complete=Oracle(truth,initial,c);complete.run()
  for cut in range(len(complete.trace)):
   pair=[]
   for code in (truth,program):
    m=Oracle(code,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Byte-ID access-prefix control did not fire')
    pair.append(m)
   assert pair[0].trace==pair[1].trace and public(pair[0].memory)==public(pair[1].memory)
   prefixes+=1
 prior=START
 try:
  START=RECORDS+0x72;c=Case(0,0,4,1);initial=fixture(c);pair=[]
  alias_programs=[]
  for label,obj in (('raw',raw_object),('retail',r/source.BUILD/'original-func_15004BF0.o')):
   path=o/('alias-'+label);script=path.with_suffix('.ld')
   script.write_text('SECTIONS { .text 0x15004BF0 : SUBALIGN(4) { *(.text) } }\n'+
                    '\n'.join('%s = 0x%X;'%(n,v) for n,v in zip(('D_800DBEF0','D_800DBEF4','D_800DBF00'),(COUNT,BASE,START))))
   subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15004BF0','-o',str(path.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
   alias_programs.append(list(struct.unpack('>60I',sections(path.with_suffix('.elf'))['.text'][1][:240])))
  for code in alias_programs:
   m=Oracle(code,initial,c);m.run();pair.append(m)
  assert pair[0].r[2]==pair[1].r[2] and pair[0].trace==pair[1].trace and public(pair[0].memory)==public(pair[1].memory)
 finally:START=prior
 return dict(fired_prefix_cases=prefixes,executions=prefixes*2,guest_start_byte_record_aliases=1,
             portable_C_fault_or_overlap_semantics_claimed=False)
