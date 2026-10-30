"""Private effect-motion qualification; bounded IEEE model, no hardware/FCSR claim."""
from pathlib import Path
from dataclasses import dataclass,replace
import hashlib,itertools,json,re,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=Path(__file__).resolve().parent
F='func_150B36AC';ENTRY=0x150B36AC;ROM=0xE0B5C;TABLE=0x80089934;RECORD=0x22000
FLOATS=(0,0x80000000,1,0x80000001,0x007FFFFF,0x00800000,0x80800000,0x3E800000,0xBE800000,0x3F800000,0xBF800000,0x40000000,0xC0000000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC00000,0xFFC12345)
@dataclass(frozen=True)
class Case:
 vertical:int=0x40000000
 threshold:int=0x3F800000
 scale:int=0x3F000000
 height:int=0x41200000
 offset:int=0x3F800000
 motion:tuple=(0x3FA00000,0xC0200000,0x40400000,0xC0880000,0x40B00000)
 flags:int=0xFFFFFFFF
 clamp:int=33
 phase:int=0
 home:int=-1
 seed:int=0xA5

def base(c):return RECORD if c.home<0 else STACK+c.phase+4-c.home
def arguments(c):return(base(c),0x12345678,0x87654321,0xDEADBEEF,c.offset,base(c)+0x114)
def fixture(c):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,2048)};p=base(c)
 for i in range(-32,0x1A0):m.setdefault(p+i,c.seed)
 for at,v in ((0x10,c.height),(0x14,c.scale),(0x48,c.vertical),(0x170,c.threshold),(0x60,c.flags),(0x110,c.offset)):
  put(m,p+at,v)
 for at,v in zip((0x44,0x4C,0x50,0x54,0x58),c.motion):put(m,p+at,v)
 put(m,p+0x64,c.clamp&65535,2);return m

def reference(initial,c,sp=None,args=None):
 m=dict(initial);args=arguments(c)if args is None else args;p=args[0];sp=STACK+c.phase if sp is None else sp
 # The ABI's outgoing cells exist before entry; incoming unused register homes
 # may alias the record and must be written before the first record read.
 for i,v in enumerate(args[1:4],1):put(m,sp+4*i,v)
 vertical=read(m,p+0x48);limit=read(m,p+0x170)
 position=bits(floating(read(m,p+0x10))+floating(read(m,sp+16)))
 put(m,p+0x3C,position)
 if floating(limit)<floating(vertical):
  flags=read(m,p+0x60);timer=((read(m,p+0x64,2)^32768)-32768)
  put(m,p+0x60,flags&0xFFFFFF90)
  for at in(0x44,0x48,0x4C):put(m,p+at,0)
  if timer>32:put(m,p+0x64,32,2)
 else:
  scale=read(m,p+0x14)
  values=[read(m,p+at)for at in(0x44,0x4C,0x50,0x54,0x58)]
  for at,v in zip((0x44,0x4C,0x50,0x54,0x58),values):put(m,p+at,bits(floating(v)*floating(scale)))
  put(m,p+0x48,bits(floating(vertical^0x80000000)*floating(scale)))
 return m

class Oracle(TimingOracle):
 def __init__(self,ws,m,c=Case(),entry=ENTRY,connected=None,args=None):
  self.trace=[];super().__init__(ws,m,phase=c.phase,entry=entry,arguments=arguments(c)if args is None else args,connected=connected)
 def execute(self,w):
  if w>>26==32:
   self.dispatched_word=w;self.own_instruction=True
   try:
    imm=w&65535;address=(self.r[w>>21&31]+(imm if imm<32768 else imm-65536))&0xFFFFFFFF
    value=self.get(address,1);self.r[w>>16&31]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
   finally:self.own_instruction=False
  elif w>>26==17 and w>>21&31==16 and w&63==7:
   self.dispatched_word=w;self.own_instruction=True
   try:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
   finally:self.own_instruction=False
  else:super().execute(w)
 def get(self,a,n):
  value=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,value))
  return value
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))
 def record_call(self,target):
  assert target==ENTRY,hex(target);self.calls.append((target,self.arguments(6)));self.events.append(('CALL',target,self.arguments(6)))
 def hook(self,target):raise AssertionError(('unbounded helper',hex(target)))

def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.root_accesses)
def linked(obj,label,entry=ENTRY):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,{});assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label='guest',at=ENTRY):return[linked(o/p,label+'-'+str(i),at)for i,p in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def compare(c,ims,at=ENTRY):
 initial=fixture(c);ms=[Oracle(ws,initial,c,at).run()for ws in ims]
 # Constructor populated outgoing stack arguments before execution.
 seeded=Oracle(ims[0],initial,c,at);want=reference(seeded.memory,c)
 for m in ms:
  assert m.memory==want,(c,'reference memory');assert m.r[2]==1 and not m.calls,c
 assert all(state(m)==state(ms[0])for m in ms[1:]),c
 return ms[0]
def cases():
 for i,(v,t,s)in enumerate(itertools.product(FLOATS,FLOATS,(0,0x80000000,1,0x3F000000,0xBF800000,0x40000000,0x7F800000,0x7FC00000))):
  yield Case(v,t,s,height=FLOATS[i%len(FLOATS)],offset=FLOATS[(i*7+3)%len(FLOATS)],motion=tuple(FLOATS[(i+3*j)%len(FLOATS)]for j in range(5)),clamp=(-32768,-1,0,31,32,33,32767)[i%7],phase=8*(i%2))
 for flag,timer,reset in itertools.product(range(256),(-32768,-1,0,31,32,33,32767),(False,True)):
  yield Case(threshold=0x3F800000 if reset else 0x40400000,flags=0xA5B60000|flag,clamp=timer,phase=8*(flag%2))
def guest_suite():
 ims=images();assert ims[0]==ims[1]==ims[2];count=0;visits=set()
 for c in cases():visits.update(compare(c,ims).visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))<=visits
 aliases=0
 for home in(0x10,0x14,0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x60,0x64,0x170):
  for phase,reset in itertools.product((0,8),(False,True)):
   compare(Case(home=home,phase=phase,threshold=0x3F800000 if reset else 0x40400000),ims);aliases+=1
 cuts=delays=0
 for c in(Case(),Case(clamp=32),Case(threshold=0x40400000),Case(vertical=0x7FC00000),Case(home=0x48)):
  full=compare(c,ims)
  for cut in range(full.root_accesses):
   ms=[]
   for ws in ims:
    m=Oracle(ws,fixture(c),c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('missing access cut',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for j,at in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  ims2=images('rebase-'+str(j),at);assert ims2[0]==ims2[1]==ims2[2]
  for v,t,s in itertools.product((0,0x80000000,1,0x3F800000,0x7FC00000),(0,0x3F000000,0x7F800000),(0xBF800000,0x40000000)):
   compare(Case(vertical=v,threshold=t,scale=s),ims2,at);rebased+=1
 return dict(cases=count,executions=count*3,covered_words=56,guest_only_home_alias_cases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,GNU_layouts=3,rebased_cases=rebased,full_state_trace_equal=True,NaNs_signed_zero_subnormals=True,hardware_FCSR_unmodeled=True,credit=0)

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
 def __getitem__(self,pc):
  if pc in self.owner.window_ends:raise WindowBoundary
  return super().__getitem__(pc)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ptr=struct.pack('>I',ENTRY);jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF))
 assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ptr]==[0x22E408]
 assert not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]
 table=rom[0x22E3F4:0x22E42C];assert len(table)==56 and struct.unpack_from('>I',table,20)[0]==ENTRY
 literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/'conker/asm/15F680.s').read_text())}
 current=(r/'conker/build/conker.us.elf').read_bytes();from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 parent=0x15133894;start=elf_slot_offset(current,parent,320);assert current[start:start+320]==rom[0x160D44:0x160E84]
 assert 'GLOBAL_ASM("asm/nonmatchings/generated_15F680/func_15133894.s")'in(r/'conker/src/game/generated_15F680.c').read_text()
 ims=images('caller');count=0;returns=set();delays=0
 for which,phase,selector,reset in itertools.product((0,1),(0,8),(0,5),(False,True)):
  # The second window begins after the parent's selector-nonzero gate.
  if which==1 and selector==0:continue
  c=Case(phase=phase,threshold=0x3F800000 if reset else 0x40400000);initial=fixture(c);p=base(c);sp=STACK+phase
  initial[p+0x73]=selector
  for i,v in enumerate(table):initial[TABLE+i]=v
  if which==0:
   entry,end=0x15132FDC,0x15133028;ends=(end,0x151332C8);stack_args=0x374
  else:entry,end=0x1513397C,0x151339C0;ends=(end,);stack_args=0x40
  incoming=(0x3F800000,0xC0000000,0x40A00000)
  for i,v in enumerate(incoming):put(initial,sp+stack_args+4*i,v)
  ws=[literal[pc]for pc in range(entry,end,4)];offset=entry-parent+0x160D44 if which else entry-0x15132DDC+0x16008C
  # Exact retail address-to-ROM mapping in this overlay is VA - 0x14FD2B50.
  offset=entry-0x14FD2B50;assert ws==list(struct.unpack_from('>%dI'%len(ws),rom,offset))
  ms=[]
  for body in ims:
   m=Oracle(ws,initial,c,entry=entry,connected={ENTRY+4*i:w for i,w in enumerate(body)},args=(p,));m.r[16]=p;m.window_ends=ends;m.code=WindowCode(dict(m.code),m)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('caller boundary absent')
   if which==0 and not selector:assert not m.calls
   else:
    expected_args=(p,*incoming,c.offset,p+0x114);assert m.calls==[(ENTRY,expected_args)]
    target_initial=dict(initial)
    for i,v in enumerate(expected_args[4:],4):put(target_initial,sp+4*i,v)
    want=reference(target_initial,c,sp,expected_args)
    assert bytes(m.memory[p+i]for i in range(0x180))==bytes(want[p+i]for i in range(0x180))
    assert m.r[2]==1
    if which==1:assert m.memory[sp+0x4F]==1
    returns.add(m.r[2]);delays+=which==0
   ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,original_windows=2,table_words=14,target_selector=5,indirect_calls=1,direct_calls=0,retained_parent_320_bytes_exact=True,first_current_parent_uncredited=True,earlier_helpers_bounded=True,fifth_float_delay_slot_witnesses=delays,signed_byte_return=sorted(returns),credit=0)

def controls():
 text=(o/'selected-semantic-input.c').read_text()
 changes={
 'wrong-limit':('record + 0x170','record + 0x174'),
 'equal-limit':(' < vertical',' <= vertical'),
 'reverse-test':(' < vertical',' > vertical'),
 'unsigned-clamp':('*(s16 *)(record + 0x64) >= 33','*(u16 *)(record + 0x64) >= 33'),
 'early-clamp':('>= 33','>= 32'),
 'wrong-clamp-value':('= 32;','= 31;'),
 'lose-preserved-bit':('& ~8u','& ~0x18u'),
 'miss-flag':('& ~0x40u','& ~0x80u'),
 'keep-vertical':('*(f32 *)(record + 0x48) = 0.0f;','*(f32 *)(record + 0x48) = vertical;'),
 'wrong-position':('record + 0x3C','record + 0x38'),
 'subtract-offset':('record + 0x10) + offset','record + 0x10) - offset'),
 'wrong-scale':('scale = *(f32 *)(record + 0x14)','scale = *(f32 *)(record + 0x10)'),
 'miss-last':('*(f32 *)(record + 0x58) *= scale;','*(f32 *)(record + 0x58) *= 1.0f;'),
 'positive-vertical':('= -vertical * scale','= vertical * scale'),
 'zero-result':('return 1;','return 0;'),
 }
 for name,(a,b)in changes.items():assert a in text,name
 return{n:text.replace(a,b)for n,(a,b)in changes.items()}

def compiled_controls():
 probes=[Case(),Case(clamp=-1),Case(clamp=32),Case(vertical=0x3F800000),Case(threshold=0x40400000),Case(flags=0x10),Case(vertical=0x80000000,threshold=0),Case(offset=0x40000000)]
 outcomes={}
 for name,text in controls().items():
  obj,diag=compile_owner(r,o,text,'control-'+name);assert not diag,diag;ws=linked(obj,'control-linked-'+name);witness=None
  for c in probes:
   try:compare(c,[ws])
   except(AssertionError,KeyError):witness=repr(c);break
  # Changing >=33 to >=32 and setting32 is semantically identical, but the
  # retail instruction/halfword store prefix is distinct at the boundary.
  if name=='early-clamp':
   assert witness is None;assert payload(obj,F)!=payload(o/'selected-final.o',F);outcomes[name]='shape-only equivalent control';continue
  assert witness is not None,('ineffective semantic control',name);outcomes[name]=witness
 return dict(IDO_controls=len(outcomes),semantic_defects_rejected=len(outcomes)-1,equivalent_shape_control=1,witnesses=outcomes)

def native_suite():
 # Final object bytes and return only. Intermediate C stores are not portable
 # observations. NaN payload propagation and hardware FCSR are not asserted.
 rows=[];corpus=list(cases())
 for c in corpus:
  m=fixture(c);sp=STACK+c.phase
  for i,v in enumerate(arguments(c)[4:],4):put(m,sp+4*i,v)
  want=reference(m,c)
  offsets=(0x10,0x14,0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x170,0x60)
  raw=[read(m,RECORD+x)for x in offsets];expected=[read(want,RECORD+x)for x in offsets]
  vals=raw+expected+[c.clamp&65535,read(want,RECORD+0x64,2),c.offset]
  rows.append('{'+','.join('0x%Xu'%v for v in vals)+'}')
 source=(o/'selected-semantic-input.c').read_text();variants={'selected':source,**controls()};names=[]
 for name,text in variants.items():
  if name=='early-clamp':continue
  names.append(name);source_name='candidate_'+name.replace('-','_');variants[name]=text.replace(F,source_name)
 harness='\n'.join(variants[n]for n in names)+r'''
typedef s32(*Callback)(u8*,s32,s32,s32,f32,void*);
static const u32 rows[][25]={ROWS};
static const u32 offsets[]={0x10,0x14,0x3C,0x44,0x48,0x4C,0x50,0x54,0x58,0x170,0x60};
typedef union {u8 b[0x200];u32 w[0x80];f32 f[0x80];s16 h[0x100];} Record;
static Record record;
static f32 real(u32 v){union{u32 w;f32 f;}x;x.w=v;return x.f;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
static int one(Callback fn,const u32 *row){u32 i,j;u8*p=record.b+32;u32 result;
 for(i=0;i<0x80;i++)record.w[i]=0xA5A5A5A5u;
 for(i=0;i<11;i++)*(u32*)(void*)(p+offsets[i])=row[i];
 *(s16*)(void*)(p+0x64)=(s16)row[22];
 result=fn(p,0x12345678,(s32)0x87654321u,(s32)0xDEADBEEFu,real(row[24]),p+0x114);
 if(result!=1)return 1;
 for(i=0;i<11;i++){u32 a=*(u32*)(void*)(p+offsets[i]);if(i<10?!same(a,row[11+i]):a!=row[11+i])return 2;}
 if(*(u16*)(void*)(p+0x64)!=row[23])return 3;
 for(i=0;i<0x200;i++){int writable=0;if(i>=32){j=i-32;writable=j>=0x64&&j<0x66;for(u32 k=0;k<11;k++)if(j>=offsets[k]&&j<offsets[k]+4)writable=1;}if(!writable&&record.b[i]!=0xA5)return 4;}
 return 0;}
static int run(void){u32 i,n;Callback functions[]={FUNCTIONS};
 for(n=0;n<sizeof(functions)/sizeof(functions[0]);n++){int rejected=0;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){int e=one(functions[n],rows[i]);if(n==0&&e)return e;if(e){rejected=1;break;}}if(n&& !rejected)return 60+n;}return 0;}
'''
 harness=harness.replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS',','.join('candidate_'+n.replace('-','_')for n in names))+START
 path=o/'native-effect-motion.c';path.write_text(harness);profiles=[]
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-effect-motion'+opt);p=subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(exe)],capture_output=True,text=True);exe.with_suffix('.diagnostics.txt').write_text(p.stdout+p.stderr);assert p.returncode==0,(opt,p.stdout,p.stderr)
  assert not p.stderr,p.stderr;p=subprocess.run([str(exe)],capture_output=True,timeout=60);assert p.returncode==0,(opt,p.returncode,p.stdout,p.stderr);profiles.append(opt)
 return dict(cases_per_profile=len(rows),profiles=profiles,trapping_UBSan=True,native_controls=len(names)-1,all_effective=True,full_record_and_canaries=True,NaN_payloads_not_asserted=True,intermediate_C_stores_not_observed=True)
