"""Aligned zero-tail reconstruction: bounded guest and native contracts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode
r=o=source=None
ENTRY=0x1509B950
SIZES={'allocate_memory':4,'bcopy':3,'bzero':2,'func_10004074':1}
@dataclass(frozen=True)
class Case:
 length:int=24
 tail:int=8
 residue:int=0
 mutation:int=0
 outcome:int=1
 alias:int=0
 phase:int=0
 seed:int=0

def symbols(i=0):
 return dict(zip(SIZES,((0x10003C40,0x10023A10,0x100226F0,0x10004074),(0x17007FFC,0x17108000,0x1720FFFC,0x17318000),(0x1E007FFC,0x1D008000,0x1C00FFFC,0x1B018000))[i]))
def addresses(c):
 p=0x80000+c.residue
 return p,(p if c.alias==1 else p+16 if c.alias==2 else 0xA0000)
def public(m):return {a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
def fixture(c):
 p,q=addresses(c);n=max(192,c.length+32,c.tail+32)
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for base in set((p,q)):
  m.update({(base+i)&0xFFFFFFFF:(i*29+c.seed*11+0x5A)&255 for i in range(-16,n)})
 for off,v in ((0,0x1234),(2,0xABCD),(4,c.length),(6,c.tail),(8,0x8001),(10,0xFFFF)):put(m,p+off,v,2)
 return m
def effect(m,c,name,a):
 p,q=addresses(c)
 if name=='allocate_memory':
  if c.mutation&1:put(m,p+4,24,2);put(m,p+6,3,2);put(m,p+10,32,2)
  return q if c.outcome else 0
 if name=='bcopy':
  data=bytes(m[(a[0]+i)&0xFFFFFFFF]for i in range(a[2]))
  for i,b in enumerate(data):m[(a[1]+i)&0xFFFFFFFF]=b
  if c.mutation&2:put(m,q+10,48,2);put(m,q+6,5,2)
 elif name=='bzero':
  for i in range(a[1]):m[(a[0]+i)&0xFFFFFFFF]=0
 elif name!='func_10004074':raise AssertionError(name)
 return 0xC0DEC0DE
def reference(c,s,initial):
 m=dict(initial);p,q=addresses(c);length=read(m,p+4,2);tail=read(m,p+6,2)
 off=length+8-((p+length)&7);size=off+tail
 put(m,p+4,size,2);put(m,p+10,off,2);put(m,p+4,size-((p+size)&7)+8,2)
 calls=[]
 def call(name,a):
  calls.append((s[name],a));return effect(m,c,name,a)
 result=call('allocate_memory',(read(m,p+4,2),255,2,0))
 if not result:return public(m),calls,None
 call('bcopy',(p,result,read(m,p+4,2)))
 call('bzero',(result+read(m,result+10,2),read(m,result+6,2)))
 call('func_10004074',(p,))
 return public(m),calls,result
class LoopWitness(Exception):pass
class LoopCode(dict):
 def __init__(self,code,owner,loop):super().__init__(code);self.owner=owner;self.loop=loop;self.hits=0
 def __getitem__(self,pc):
  if pc==self.loop:
   self.hits+=1
   if self.hits==3:raise LoopWitness
  self.owner.current_pc=pc
  return super().__getitem__(pc)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None,argument=None):
  self.c,self.s=c,s;self.names={v:k for k,v in s.items()};self.p,self.q=addresses(c)
  super().__init__(words,memory,c,entry=entry,s={},arguments=(self.p if argument is None else argument,),connected=connected)
  self.before_f=self.f[:]
 def record_call(self,t):
  n=1 if t==ENTRY else SIZES[self.names[t]]
  self.calls.append((t,tuple(self.arguments(n))))
 def hook(self,t):
  a=self.calls[-1][1];v=effect(self.memory,self.c,self.names[t],a)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in (1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=v
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs['func_1509B950'],relocs,'func_1509B950',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_1509B950','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>45I',sections(p.with_suffix('.elf'))['.text'][1][:180]))
def programs(index):
 s=symbols(index);entry=(ENTRY,0x17038000,0x1F00FFFC)[index]
 ps=[link(o/n,'zero-tail-program-%d-%d'%(index,j),entry,s)for j,n in enumerate(('original-func_1509B950.o','qualified-padded.o','make-shadow/src/game_C8950.c.o','selected-final.o'))]
 assert ps[0]==ps[1]==ps[2]and sum(a!=b for a,b in zip(ps[0],ps[3]))==6
 return s,entry,ps
def corpus():
 for length,tail,residue,mutation in itertools.product((12,13,15,16,17,23,24,25,31,32,63,127),(0,1,7,8,9,31),(0,2,4,6),(0,1,2,3)):
  yield Case(length,tail,residue,mutation,seed=(length+tail)&3,phase=8 if length&1 else 0)
 for length,tail in itertools.product((0,1,0x7FFF,0x8000,0xFFF0,0xFFF8,0xFFFF),(0,1,7,8,0x7FFF,0xFFFF)):
  # Allocate enough provider memory for large zero ranges; these are guest-only.
  yield Case(length,tail,mutation=1)
 for alias,residue,mutation in itertools.product((1,2),(0,2,4,6),range(4)):yield Case(32,16,residue,mutation,alias=alias)
def compare(c,s,entry,ps):
 initial=fixture(c);expected,calls,result=reference(c,s,initial);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry).run();assert(public(m.memory),m.calls,m.r[2])==(expected,calls,result),(c,m.calls,calls,m.r[2],result)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
  models.append(m)
 for m in models[1:3]:assert(m.memory,m.r,m.f,m.trace,m.calls)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].calls)
 assert models[3].memory==models[0].memory and models[3].trace==models[0].trace
 return models[0]
def guest():
 count=0;seen=set()
 for i in range(3):
  s,entry,ps=programs(i)
  cases=corpus()if i==0 else(Case(n,t,a,m)for n,t,a,m in itertools.product((12,15,24,63),(0,7,8),(0,6),range(4)))
  for c in cases:
   model=compare(c,s,entry,ps);seen.update(pc-entry for pc in model.visits);count+=1
  for c in(Case(12,0,outcome=0),Case(24,8,6,3,outcome=0)):
   initial=fixture(c);expected,calls,result=reference(c,s,initial)
   for words in ps:
    m=Oracle(words,initial,c,s,entry);m.code=LoopCode(m.code,m,entry+0x6C)
    try:m.run()
    except LoopWitness:pass
    else:raise AssertionError('Missing explicit allocation-failure loop witness')
    assert public(m.memory)==expected and m.calls==calls and m.code.hits==3 and m.r[29]==m.before[29]-32
    seen.update(pc-entry for pc in m.visits)
 assert seen==set(range(0,180,4)),sorted(set(range(0,180,4))-seen)
 return dict(cases=count,executions=count*4,rebases=3,all_45_words_executed=True,raw_C_public_memory_calls_and_traces_equal=True,guarded_full_state_and_trace_equal=True,allocation_failure_cases=6,allocation_failure_executions=24,explicit_three_visit_loop_witness=True,large_halfword_boundaries_guest_only=True),programs(0)[2]
def faults(ps):
 count=0
 for c in(Case(12,0),Case(24,8,6,3),Case(32,16,alias=1)):
  s=symbols();initial=fixture(c);full=Oracle(ps[0],initial,c,s).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in ps[:3]:
    m=Oracle(words,initial,c,s);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    models.append((m.memory,m.r,m.f,m.calls,m.trace))
   assert models[0]==models[1]==models[2];count+=1
 return dict(prefixes=count,executions=count*3,guarded_machine_states_equal=True,guest_instruction_access_order_only=True)

class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==0x1509B940:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
class CallerOracle(Oracle):
 def record_call(self,t):
  if t==0x1502B5C8:self.calls.append((t,tuple(self.arguments(4))))
  else:super().record_call(t)
 def hook(self,t):
  if t!=0x1502B5C8:return super().hook(t)
  self.names[t]='allocate_memory'
  # Loader provider returns the preinitialized source; it does not append a tail.
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.r[2]=self.p
def callers(ps):
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>21I',rom,0xC8DAC);count=0
 census=json.loads((o/'caller-census.json').read_text());assert census['aligned_ROM_JALs']==[0xC8DE8]and not census['aligned_ROM_Js']and not census['aligned_ROM_pointer_literals']
 for arg,mutation,residue in itertools.product((0,1,0x7FFF,0x8000,0xFFFF,0xABCDEF81),range(4),(0,6)):
  c=Case(24,8,residue,mutation);initial=fixture(c);put(initial,0x800BE9F0,0x89ABCDEF);p,q=addresses(c)
  prepared=dict(initial);put(prepared,p,read(prepared,p,2)|(arg&65535),2);put(prepared,p+2,0xCDEF,2)
  expected,calls,result=reference(c,symbols(),prepared);signed=((arg&65535)^32768)-32768
  calls=[(0x1502B5C8,(STACK-8,2,20,signed&0xFFFFFFFF)),(ENTRY,(p,))]+calls
  for body,poison in itertools.product(ps,(0,1,0x80000000,0xFFFFFFFF)):
   code=dict(zip(range(ENTRY,ENTRY+180,4),body));m=CallerOracle(words,initial,c,symbols(),entry=0x1509B8FC,connected=code,argument=arg);m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=()
   m.run();assert public(m.memory)==expected and m.calls==calls and m.poison_hits==1 and m.r[2]==poison,(c,arg,m.calls,calls)
   assert m.r[29]==m.before[29]and m.r[31]==m.before[31]
  count+=1
 return dict(cases=count,executions=count*16,complete_original_words=21,loader_is_provider=True,return_poisons=4,caller_does_not_consume_target_return=True,void_return_register_not_constrained=True)

class AllocationOracle(Oracle):
 def record_call(self,t):
  if t==0x10003C6C:self.calls.append((t,tuple(self.arguments(5))))
  else:super().record_call(t)
 def hook(self,t):
  if t!=0x10003C6C:return super().hook(t)
  a=self.calls[-1][1];assert a[3]==0
  self.names[t]='allocate_memory';return super().hook(t)
def allocation_wrapper(ps):
 rom=(r/'conker/conker.us.bin').read_bytes();wrapper=struct.unpack_from('>11I',rom,0x3C40);code=dict(zip(range(0x10003C40,0x10003C6C,4),wrapper));count=0
 for length,tail,residue,mutation in itertools.product((12,15,24,127),(0,1,8),(0,6),range(4)):
  c=Case(length,tail,residue,mutation);initial=fixture(c);expected,calls,result=reference(c,symbols(),initial)
  args=calls[0][1];calls=calls[:1]+[(0x10003C6C,(args[0],args[1],args[2],0,args[3]))]+calls[1:]
  for words in ps:
   m=AllocationOracle(words,initial,c,symbols(),connected=code).run();assert(public(m.memory),m.calls,m.r[2])==(expected,calls,result)
  count+=1
 return dict(cases=count,executions=count*4,complete_original_allocate_memory_words=11,inner_heap_allocator_is_provider=True)

def native_digest(m,c):
 p,q=addresses(c);h=2166136261
 for base in(p,q):
  for i in range(6):h=((h^read(m,base+2*i,2))*16777619)&0xFFFFFFFF
  for i in range(12,192):h=((h^m[base+i])*16777619)&0xFFFFFFFF
 return h
def native():
 controls=(('round_first',source.SELECTED.replace('alignmentPadding = 8 -','alignmentPadding = (8 -').replace('block->unk4) & 7);','block->unk4) & 7)) & 7;',1)),
 ('wrong_flags',source.SELECTED.replace('255, 2, 0','255, 1, 0')),
 ('cached_copy_size',source.SELECTED.replace('bcopy(block, copy, block->unk4);','bcopy(block, copy, newSize);')),
 ('cached_zero_offset',source.SELECTED.replace('(u8 *)copy + copy->unkA','(u8 *)copy + tailOffset')),
 ('cached_zero_size',source.SELECTED.replace('copy->unk6);','tailSize);')),
 ('missing_release',source.SELECTED.replace('    func_10004074(block);','')),
 ('wrong_return',source.SELECTED.replace('return copy;','return block;')),
 ('wrong_offset',source.SELECTED.replace('block->unkA = tailOffset;','block->unkA = tailOffset + 1;')))
 assert all(text!=source.SELECTED for name,text in controls)
 code=source.HEADERS+'\n'.join(text.replace('func_1509B950(', 'candidate_%d('%i)for i,(name,text)in enumerate((('valid',source.SELECTED),)+controls))
 cases=[Case(n,t,mutation=m,seed=seed)for n,t,m,seed in itertools.product((12,13,15,16,17,23,24,25,31,32,63,127),(0,1,7,8,9,31),range(4),(0,3))]
 rows=[]
 for c in cases:
  expected,calls,result=reference(c,symbols(),fixture(c));rows.append('{'+','.join(str(v)+'u'for v in(c.length,c.tail,c.mutation,c.seed,native_digest(expected,c),calls[0][1][0]))+'}')
 code+='''
typedef union { struct248 header; u8 bytes[256]; } Buffer;
static Buffer original __attribute__((aligned(16))), destination __attribute__((aligned(16)));
typedef struct{u32 length,tail,mutation,seed,digest,allocation;}Test;
static const Test tests[]={'''+',\n'.join(rows)+'''};
static const Test *active;static u32 ordinal,bad;
static void half(u8*p,u32 off,u32 value){*(u16*)(p+off)=value;}
s32 allocate_memory(s32 size,s32 color,s32 side,s32 flags){
 if(ordinal++!=0||(u32)size!=active->allocation||color!=255||side!=2||flags!=0)bad=1;
 if(active->mutation&1){original.header.unk4=24;original.header.unk6=3;original.header.unkA=32;}
 return(s32)&destination.header;
}
void bcopy(const void*src,void*dst,int n){int i;u8*output=dst;const u8*input=src;
 if(ordinal++!=1||src!=&original.header||dst!=&destination.header||n!=original.header.unk4)bad=1;
 for(i=0;i<n;i++)output[i]=input[i];
 if(active->mutation&2){destination.header.unkA=48;destination.header.unk6=5;}
}
void bzero(void*dst,int n){int i;u8*p=dst;
 if(ordinal++!=2||p!=destination.bytes+destination.header.unkA||n!=destination.header.unk6)bad=1;
 for(i=0;i<n;i++)p[i]=0;
}
void func_10004074(void*p){if(ordinal++!=3||p!=&original.header)bad=1;}
static u32 digest(void){u32 h=2166136261u,b,i;Buffer*p;for(b=0;b<2;b++){p=b?&destination:&original;for(i=0;i<6;i++)h=(h^((u16*)&p->header)[i])*16777619u;for(i=12;i<192;i++)h=(h^p->bytes[i])*16777619u;}return h;}
static void reset(const Test*t){u32 i;active=t;ordinal=bad=0;for(i=0;i<256;i++){original.bytes[i]=(i*29+t->seed*11+0x5A)&255;destination.bytes[i]=original.bytes[i];}original.header.unk0=0x1234;original.header.unk2=0xABCD;original.header.unk4=t->length;original.header.unk6=t->tail;original.header.unk8=0x8001;original.header.unkA=0xFFFF;
 /* Untouched destination header uses the guest fixture's numerical halfwords. */
 for(i=0;i<6;i++)half(destination.bytes,2*i,(((2*i*29+t->seed*11+0x5A)&255)<<8)|(((2*i+1)*29+t->seed*11+0x5A)&255));
}
static int run(void){u32 i,j,killed=0,k;struct248*result;
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<9;j++){reset(&tests[i]);switch(j){case 0:result=candidate_0(&original.header);break;case 1:result=candidate_1(&original.header);break;case 2:result=candidate_2(&original.header);break;case 3:result=candidate_3(&original.header);break;case 4:result=candidate_4(&original.header);break;case 5:result=candidate_5(&original.header);break;case 6:result=candidate_6(&original.header);break;case 7:result=candidate_7(&original.header);break;default:result=candidate_8(&original.header);break;}
 if(bad||ordinal!=4||result!=&destination.header||digest()!=tests[i].digest){if(!j)return 10;killed|=1u<<(j-1);}
 if(!j)for(k=192;k<256;k++)if(original.bytes[k]!=((k*29+tests[i].seed*11+0x5A)&255)||destination.bytes[k]!=original.bytes[k])return 12;
 }return killed==255?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native-zero-tail.c';p.write_text(code);reports=[]
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-zero-tail'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);(o/('native'+opt+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
  reports.append(dict(profile=opt,cases=len(cases),UBSan=True,controls=[n for n,t in controls],all_eight_controls_effective=True,canaries=True,defined_small_disjoint_buffers_only=True))
 return reports
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,ps=guest();print('guest',g,flush=True)
 report=dict(guest=g,faults=faults(ps),callers=callers(ps),allocation_wrapper=allocation_wrapper(ps),native=native(),installed=False,matching_credit=0)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
