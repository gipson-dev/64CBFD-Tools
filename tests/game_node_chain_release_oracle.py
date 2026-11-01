"""Snapshot-based child-chain cleanup and live owner-list detachment contracts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,OWNER,NODES,PARENT,MARK=0x151D3130,0x80000,0x90000,0xB0000,0xB1000
ITERATOR,FREE,DEFER,GENERIC=0x151696DC,0x15169804,0x15169824,0x17208000
signed=lambda v:(v^128)-128
@dataclass(frozen=True)
class Case:
 count:int=3
 owner_kind:int=1
 kind:int=0
 mutation:int=0
 seed:int=0
 phase:int=0
def node(i):return NODES+i*0x100
def symbols(i=0):
 children=(0x8008FC48,0x03407FE8,0x02407FEC)[i]
 return dict(D_8008FC48=children,D_8008FC5C=children+20,func_1516972C=(0x1516972C,0x17147FFC,0x18148000)[i],func_1514EDF0=(0x1514EDF0,0x17157FFC,0x18158000)[i],owner_callback=0x17301000+i*0x10000,node_callback=0x17302000+i*0x10000,node_alternate=0x17303000+i*0x10000)
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for base,n,seed in((OWNER,40,c.seed),(node(0),68,c.seed),(node(1),68,c.seed+1),(node(2),68,c.seed+2),(MARK,4,0)):
  m.update({base+i:(i*29+seed*11+0x5A)&255 for i in range(n)})
 for i in range(-128,128):put(m,s['D_8008FC48']+4*i,s['node_callback'])
 # Owner and child arrays share the original contiguous boundary.
 for i in range(256):put(m,s['D_8008FC5C']+4*i,0)
 put(m,s['D_8008FC5C']+4*c.owner_kind,s['owner_callback']if c.owner_kind else 0)
 put(m,OWNER+0x10,PARENT);m[OWNER+0x1D]=c.owner_kind;put(m,OWNER+0x24,node(0)if c.count else 0)
 for i in range(3):
  m[node(i)]=1;m[node(i)+0x2A]=c.kind&255;put(m,node(i)+0x2C,OWNER);put(m,node(i)+0x40,node(i+1)if i+1<c.count else 0)
 for kind in range(4):put(m,0x8008B4D0+52*kind,GENERIC if kind==3 else 0)
 return m
def public(m):return {a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
def effect(m,c,s,role,a):
 if role=='owner'and c.mutation&1:
  put(m,OWNER+0x24,node(1)if c.count>1 else 0);put(m,OWNER+0x10,PARENT+4)
 elif role=='node':
  p=a[0]
  if c.mutation&2:put(m,p+0x40,0);m[p+0x2A]=255;put(m,p+0x2C,0xDEADBEEF)
  if c.mutation&8:
   following=read(m,p+0x40)
   if following:m[following+0x2A]=0
   put(m,s['D_8008FC48'],s['node_alternate']);put(m,OWNER+0x10,PARENT+8)
 elif role=='release'and c.mutation&4:
  put(m,a[0]+0x40,a[0]);put(m,OWNER+0x24,0);put(m,OWNER+0x10,PARENT+12)
 elif role=='detach':put(m,MARK,0x13579BDF)
def reference(c,s,initial,connected=False):
 m=dict(initial);calls=[]
 def call(t,a,role):calls.append((t,a));effect(m,c,s,role,a)
 cb=read(m,s['D_8008FC5C']+4*m[OWNER+0x1D])
 if cb:call(cb,(OWNER,),'owner')
 p=read(m,OWNER+0x24);seen=set()
 while p:
  assert p not in seen;seen.add(p);nextp=read(m,p+0x40);kind=signed(m[p+0x2A])
  if kind!=-1:call(read(m,s['D_8008FC48']+4*kind),(p,p+0x34),'node')
  put(m,p+0x2C,0)
  if connected:
   calls.append((s['func_1516972C'],(p,)));call(ITERATOR,(p,),'release')
   kind=m[p]
   if kind>=2:
    cb=read(m,0x8008B4D0+52*kind);call(cb if cb else FREE,(p,),'nested')
  else:call(s['func_1516972C'],(p,),'release')
  p=nextp
 call(s['func_1514EDF0'],(OWNER,read(m,OWNER+0x10)),'detach')
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry=ENTRY,connected=None):
  self.c,self.s=c,s;self.observed_zero=[]
  super().__init__(words,memory,c,entry=entry,s={},arguments=(OWNER,),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):
  if t==ENTRY:argc=1
  elif t==self.s['func_1514EDF0']:argc=2
  elif t in(self.s['func_1516972C'],ITERATOR,FREE,DEFER,GENERIC):argc=1
  else:argc=1 if self.r[4]==OWNER else 2
  a=tuple(self.arguments(argc));self.calls.append((t,a))
  if t==self.s['func_1516972C']:self.observed_zero.append(read(self.memory,a[0]+0x2C));assert not self.observed_zero[-1]
 def hook(self,t):
  a=self.calls[-1][1]
  role='detach'if t==self.s['func_1514EDF0']else'release'if t in(self.s['func_1516972C'],ITERATOR)else'nested'if t in(FREE,DEFER,GENERIC)else'owner'if a[0]==OWNER else'node'
  effect(self.memory,self.c,self.s,role,a)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xC0DEC0DE
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs['func_151D3130'],relocs,'func_151D3130',s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_151D3130','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>49I',sections(p.with_suffix('.elf'))['.text'][1][:196]))
def programs(i):
 s=symbols(i);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 ps=[link(o/n,'chain-program-%d-%d'%(i,j),entry,s)for j,n in enumerate(('original-func_151D3130.o','qualified-padded.o','make-shadow/src/game_1FFF60.c.o','selected-final.o'))]
 assert ps[0]==ps[1]==ps[2]and sum(a!=b for a,b in zip(ps[0],ps[3]))==3
 return s,entry,ps
def compare(c,s,entry,ps,connected=None,initial=None):
 initial=fixture(c,s)if initial is None else initial;expected,calls=reference(c,s,initial,connected is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,connected).run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];models.append(m)
 for m in models[1:3]:assert(m.memory,m.r,m.f,m.trace,m.calls)==(models[0].memory,models[0].r,models[0].f,models[0].trace,models[0].calls)
 assert models[3].memory==models[0].memory and models[3].trace==models[0].trace
 return models[0]
def guest():
 count=0;seen=set()
 for i in range(3):
  s,entry,ps=programs(i)
  for n,owner,kind,mutation in itertools.product((0,1,3),(0,1),(-128,-2,-1,0,1,4),range(16)if i==0 else(0,3,12,15)):
   c=Case(n,owner,kind,mutation,seed=mutation&1,phase=8 if mutation&1 else 0);m=compare(c,s,entry,ps);seen.update(pc-entry for pc in m.visits);count+=1
  if not i:
   for k in range(256):
    c=Case(0,k);m=compare(c,s,entry,ps);seen.update(pc-entry for pc in m.visits);count+=1
 assert seen==set(range(0,196,4)),sorted(set(range(0,196,4))-seen)
 return dict(cases=count,executions=count*4,rebases=3,all_49_words_executed=True,guarded_full_state_and_trace_equal=True,raw_C_public_memory_calls_and_traces_equal=True,all_owner_selector_bytes=True,signed_child_boundary_indices_guest_only=True),programs(0)[2]
def faults(ps):
 total=0
 for c in(Case(0,0),Case(3,1,-1,15),Case(3,1,0,14)):
  s=symbols();initial=fixture(c,s);full=Oracle(ps[0],initial,c,s).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in ps[:3]:
    m=Oracle(words,initial,c,s);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing access boundary')
    models.append((m.memory,m.r,m.f,m.calls,m.trace))
   assert models[0]==models[1]==models[2];total+=1
 return dict(prefixes=total,executions=total*3,guarded_machine_states_equal=True,guest_instruction_access_order_only=True)
def connected(ps):
 s=symbols();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>28I',rom,0x196BDC);code=dict(zip(range(s['func_1516972C'],s['func_1516972C']+112,4),words));count=0;seen=set()
 for n,kind,typ,mutation in itertools.product((1,3),(-1,0,4),(0,1,2,3),(0,4,10,14)):
  c=Case(n,1,kind,mutation);initial=fixture(c,s)
  for i in range(3):initial[node(i)]=typ
  m=compare(c,s,ENTRY,ps,code,initial);seen.update(pc for pc in m.visits if s['func_1516972C']<=pc<s['func_1516972C']+112);count+=1
 assert len(seen)==28
 return dict(cases=count,executions=count*4,complete_original_generic_release_words=28,all_28_helper_words_executed=True,iterator_and_nested_free_are_providers=True,final_detach_is_provider=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==self.owner.poison_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
def callers(ps):
 rom=(r/'conker/conker.us.bin').read_bytes();census=json.loads((o/'caller-census.json').read_text());assert census['aligned_ROM_JALs']==[0x2006B0,0x2006DC]and not census['aligned_ROM_Js']and not census['aligned_ROM_pointer_literals'];count=0
 for call in census['callers']:
  words=struct.unpack_from('>11I',rom,call['ROM'])
  for n,kind,mutation in itertools.product((0,1,3),(-1,0),(0,7,14)):
   c=Case(n,1,kind,mutation);initial=fixture(c,symbols());expected,calls=reference(c,symbols(),initial);calls=[(ENTRY,(OWNER,))]+calls+[(call['final'],(OWNER,))]
   for body,poison in itertools.product(ps,(0,1,0x80000000,0xFFFFFFFF)):
    code=dict(zip(range(ENTRY,ENTRY+196,4),body));m=Oracle(words,initial,c,symbols(),call['entry'],code);m.poison=poison;m.poison_hits=0;m.poison_pc=call['entry']+20;m.code=PoisonCode(m.code,m);m.code.ends=();m.run()
    assert public(m.memory)==expected and m.calls==calls and m.poison_hits==1 and m.r[2]==0xC0DEC0DE
   count+=1
 return dict(cases=count,executions=count*16,complete_original_wrappers=2,words_per_wrapper=11,return_poisons=4,void_return_ignored=True,final_owner_release_providers=True)
def norm(p):
 if p==0:return 0
 if p==OWNER:return 1
 for i in range(3):
  if p==node(i):return 10+i
  if p==node(i)+0x34:return 20+i
 if PARENT<=p<=PARENT+12:return 100+(p-PARENT)//4
 raise AssertionError(hex(p))
def native_digest(m,s,calls):
 h=2166136261
 def mix(v):
  nonlocal h
  h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 for base,n,pointers in((OWNER,40,(0x10,0x24)),)+tuple((node(i),68,(0x2C,0x40))for i in range(3)):
  i=0
  while i<n:
   if i in pointers:mix(norm(read(m,base+i)));i+=4
   else:mix(m[base+i]);i+=1
 mix(read(m,MARK));mix(3 if read(m,s['D_8008FC48'])==s['node_alternate']else 2)
 roles={s['owner_callback']:1,s['node_callback']:2,s['node_alternate']:3,s['func_1516972C']:4,s['func_1514EDF0']:5}
 for t,a in calls:mix(roles[t]);mix(norm(a[0]));mix(norm(a[1])if len(a)>1 else 0)
 return h
def native():
 selected=source.SELECTED
 cached=selected.replace('    ReleaseChainNode *next;','    ReleaseChainNode *next;\n    void *listOwner = owner->listOwner;').replace('(u8 *)owner->listOwner','(u8 *)listOwner')
 controls=(('cached_head',selected.replace('    callback =','    node = owner->head;\n    callback =',1).replace('    node = owner->head;\n    callbacks =','    callbacks =')),
 ('late_next',selected.replace('next = node->next;','').replace('func_1516972C((struct102 *)node);','func_1516972C((struct102 *)node);\n        next = node->next;')),
 ('skip_kind_zero',selected.replace('node->releaseKind != skipKind','(node->releaseKind != skipKind) && (node->releaseKind != 0)')),
 ('missing_owner_clear',selected.replace('node->owner = NULL;','')),
 ('wrong_payload',selected.replace('node, node->payload','node, node->payload + 1')),
 ('cached_list_owner',cached),
 ('missing_owner_callback',selected.replace('        callback(owner);','')),
 ('missing_detach',selected.replace('    func_1514EDF0((s32)owner, (u8 *)owner->listOwner);','')))
 assert all(text!=selected for name,text in controls)
 code=source.HEADERS+'\n'.join(text.replace('func_151D3130(', 'candidate_%d('%i)for i,(name,text)in enumerate((('valid',selected),)+controls))
 cases=[Case(n,owner,kind,m,seed=seed)for n,owner,kind,m,seed in itertools.product(range(4),range(2),(-1,0,1,2,3,4),range(16),range(2))];rows=[]
 for c in cases:
  s=symbols();initial=fixture(c,s);expected,calls=reference(c,s,initial);rows.append('{'+','.join(str(v)+'u'for v in(c.count,c.owner_kind,c.kind&255,c.mutation,c.seed,native_digest(expected,s,calls)))+'}')
 code+='''
typedef char NodeSize[sizeof(ReleaseChainNode)==68?1:-1];
typedef char OwnerSize[sizeof(ReleaseChainOwner)==40?1:-1];
ReleaseOwnerCallback D_8008FC5C[2];ReleaseNodeCallback D_8008FC48[5];
typedef struct{u32 before;ReleaseChainOwner value;u32 after;}OwnerBuffer;
typedef struct{u32 before;ReleaseChainNode value;u32 after;}NodeBuffer;
static OwnerBuffer ownerBuffer;static NodeBuffer nodeBuffers[3];static u8 parent[16];
typedef struct{u32 count,ownerKind,kind,mutation,seed,expected;}Test;
static const Test tests[]={'''+',\n'.join(rows)+'''};
static const Test*active;static u32 bad,ordinal,mark,callHash;
static void mix(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 id(const void*p){u32 i;if(!p)return 0;if(p==&ownerBuffer.value)return 1;for(i=0;i<3;i++){if(p==&nodeBuffers[i].value)return 10+i;if(p==nodeBuffers[i].value.payload)return 20+i;}for(i=0;i<4;i++)if(p==parent+4*i)return 100+i;bad=1;return 999;}
static void event(u32 role,const void*a,const void*b){mix(&callHash,role);mix(&callHash,id(a));mix(&callHash,id(b));ordinal++;}
static void ownerCallback(ReleaseChainOwner*p){event(1,p,0);if(p!=&ownerBuffer.value)bad=1;if(active->mutation&1){p->head=active->count>1?&nodeBuffers[1].value:0;p->listOwner=parent+4;}}
static void childAlternate(ReleaseChainNode*,void*);
static void childEffect(ReleaseChainNode*p,void*payload,u32 role){event(role,p,payload);if(payload!=p->payload)bad=1;if(active->mutation&2){p->next=0;p->releaseKind=-1;p->owner=(void*)0xDEADBEEFu;}if(active->mutation&8){if(p->next)p->next->releaseKind=0;D_8008FC48[0]=childAlternate;ownerBuffer.value.listOwner=parent+8;}}
static void childCallback(ReleaseChainNode*p,void*payload){childEffect(p,payload,2);}
static void childAlternate(ReleaseChainNode*p,void*payload){childEffect(p,payload,3);}
void func_1516972C(struct102*opaque){ReleaseChainNode*p=(ReleaseChainNode*)opaque;event(4,p,0);if(p->owner)bad=1;if(active->mutation&4){p->next=p;ownerBuffer.value.head=0;ownerBuffer.value.listOwner=parent+12;}
 /* A broken late-next control must terminate and be detected. Valid cases use <=8 calls. */
 if(ordinal>32){bad=1;p->next=0;}
}
void func_1514EDF0(s32 key,u8*listOwner){event(5,(void*)key,listOwner);if((void*)key!=&ownerBuffer.value||listOwner!=ownerBuffer.value.listOwner)bad=1;mark=0x13579BDFu;}
static void fill(u8*p,u32 n,u32 seed){u32 i;for(i=0;i<n;i++)p[i]=(i*29+seed*11+0x5A)&255;}
static void reset(const Test*t){u32 i;active=t;bad=ordinal=0;callHash=2166136261u;mark=0x5A7794B1u;ownerBuffer.before=ownerBuffer.after=0x13572468u;fill((u8*)&ownerBuffer.value,40,t->seed);ownerBuffer.value.listOwner=parent;ownerBuffer.value.releaseKind=t->ownerKind;ownerBuffer.value.head=t->count?&nodeBuffers[0].value:0;
 for(i=0;i<3;i++){ReleaseChainNode*p=&nodeBuffers[i].value;nodeBuffers[i].before=nodeBuffers[i].after=0x13572468u;fill((u8*)p,68,t->seed+i);p->retained[0]=1;p->releaseKind=(s8)t->kind;p->owner=&ownerBuffer.value;p->next=i+1<t->count?&nodeBuffers[i+1].value:0;}
 D_8008FC5C[0]=0;D_8008FC5C[1]=ownerCallback;for(i=0;i<5;i++)D_8008FC48[i]=childCallback;}
static void bufferDigest(u32*h,u8*p,u32 n,u32 first,u32 second){u32 i=0;while(i<n){if(i==first||i==second){void*value=*(void**)(p+i);mix(h,id(value));i+=4;}else{mix(h,p[i]);i++;}}}
static u32 digest(void){u32 h=2166136261u,i;bufferDigest(&h,(u8*)&ownerBuffer.value,40,0x10,0x24);for(i=0;i<3;i++)bufferDigest(&h,(u8*)&nodeBuffers[i].value,68,0x2C,0x40);mix(&h,mark);mix(&h,D_8008FC48[0]==childAlternate?3:2);return h;}
static int run(void){u32 i,j,k,killed=0,h;for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<9;j++){reset(&tests[i]);switch(j){case 0:candidate_0(&ownerBuffer.value);break;case 1:candidate_1(&ownerBuffer.value);break;case 2:candidate_2(&ownerBuffer.value);break;case 3:candidate_3(&ownerBuffer.value);break;case 4:candidate_4(&ownerBuffer.value);break;case 5:candidate_5(&ownerBuffer.value);break;case 6:candidate_6(&ownerBuffer.value);break;case 7:candidate_7(&ownerBuffer.value);break;default:candidate_8(&ownerBuffer.value);break;}
 h=digest();
 /* Append the observed call sequence to the memory digest without assuming its length. */
 if(h!=tests[i].expectedMemory||callHash!=tests[i].expectedCalls||bad){if(!j)return 10;killed|=1u<<(j-1);}
 if(!j){if(ownerBuffer.before!=0x13572468u||ownerBuffer.after!=0x13572468u)return 12;for(k=0;k<3;k++)if(nodeBuffers[k].before!=0x13572468u||nodeBuffers[k].after!=0x13572468u)return 12;}
 }return killed==255?0:11;}
'''
 # Store independent numerical memory and call digests rather than combining host pointers.
 code=code.replace('seed,expected;}Test','seed,expectedMemory,expectedCalls;}Test')
 old=',\n'.join(rows);new=[]
 for c in cases:
  s=symbols();expected,calls=reference(c,s,fixture(c,s));memoryHash=native_digest(expected,s,[]);h=2166136261;roles={s['owner_callback']:1,s['node_callback']:2,s['node_alternate']:3,s['func_1516972C']:4,s['func_1514EDF0']:5}
  for t,a in calls:
   for v in(roles[t],norm(a[0]),norm(a[1])if len(a)>1 else 0):h=((h^v)*16777619)&0xFFFFFFFF
  new.append('{'+','.join(str(v)+'u'for v in(c.count,c.owner_kind,c.kind&255,c.mutation,c.seed,memoryHash,h))+'}')
 code=code.replace(old,',\n'.join(new))+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native-chain.c';p.write_text(code);reports=[]
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-chain'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);(o/('native'+opt+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);assert q.returncode==0,(opt,q.returncode,q.stderr)
  reports.append(dict(profile=opt,cases=len(cases),UBSan=True,controls=[n for n,t in controls],all_eight_controls_effective=True,canaries=True,native_indices_minus_one_or_zero_through_four=True))
 return reports
def qualify(root,output,core):
 global r,o,source
 r,o,source=Path(root),Path(output),core
 g,ps=guest();print('guest',g,flush=True)
 report=dict(guest=g,faults=faults(ps),connected=connected(ps),callers=callers(ps),native=native(),installed=False,matching_credit=0)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
