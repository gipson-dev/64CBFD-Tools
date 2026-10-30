"""Resource bitmap: 67 variadic queries, eight cleared bytes and preserved ninth-byte bits."""
from pathlib import Path
from dataclasses import dataclass,replace
from collections import Counter
import csv,io,itertools,json,struct,subprocess
from tools.experiments import game_resource_bitmap_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
BITMAP,SELECTOR,ZERO,QUERY,LOOKUP,BASE=0x800BE580,0x800BEAAB,0x100226F0,0x1502B020,0x1502AC88,0xAB1950
SYMS=dict(D_800BE580=BITMAP,D_800BEAAB=SELECTOR,bzero=ZERO,func_1502B020=QUERY)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 seed:int=0
 selector:int=0
 pattern:int=0
 mutation:int=0
 missing:int=-1
 phase:int=0
 alias:int=0

def symbols(c,s=SYMS):return dict(s,D_800BEAAB=s['D_800BE580']+c.alias)if c.alias else dict(s)

def fixture(c,s=SYMS):
 s=symbols(c,s);m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,1024)};b=s['D_800BE580'];sel=s['D_800BEAAB'];m.update({b+i:(i*29+c.seed)&255 for i in range(-16,32)});put(m,sel,c.selector,1);put(m,STACK+c.phase-12,0xF0000000|c.seed);return m

def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+1024}

def size_for(c,index,selector):
 values=(0,1,0x100,0x10000,0x1000000,0xFFFFFFF,0,0x100000)
 if c.missing in(0,1):return 0
 return(0,1,values[(index+c.seed)&7],int(index==66),int(index==64),values[(index+selector+c.seed)&7])[c.pattern]

def effects(m,c,index,s):
 b,sel=s['D_800BE580'],s['D_800BEAAB']
 if c.mutation&1 and index%13==0:put(m,sel,(read(m,sel,1)+73)&255,1)
 if c.mutation&2 and index%11==0:put(m,b+(index>>3),0xA0|((index+c.seed)&31),1)

def reference(initial,c,s=SYMS):
 s=symbols(c,s);m=dict(initial);b,sel=s['D_800BE580'],s['D_800BEAAB'];calls=[(s['bzero'],(b,8))];queries=[]
 for i in range(8):put(m,b+i,0,1)
 for index in range(67):
  selector=read(m,sel,1);size=size_for(c,index,selector);queries.append((3,0x1A,selector,index));calls.append((s['func_1502B020'],(STACK+c.phase-16,3,0x1A,selector,index)));effects(m,c,index,s)
  if size:put(m,b+(index>>3),read(m,b+(index>>3),1)|(1<<(index&7)),1)
 return m,calls,queries

def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:220]))

def helpers(connected):
 if not connected:return{}
 rom=(r/'conker/conker.us.bin').read_bytes();code=dict(zip(range(ZERO,ZERO+160,4),struct.unpack_from('>40I',rom,0x226F0)));code.update(zip(range(QUERY,QUERY+240,4),struct.unpack_from('>60I',rom,0x584D0)));return code

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),s=SYMS,entry=ENTRY,connected=False,code=None):
  self.c=c;self.syms=symbols(c,s);self.cut=None;self.accesses=0;self.trace=[];self.queries=[];self.lookup_stage=0;self.query_args=None;self.connected_provider=connected;self.lookup_packets=[]
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(),connected=helpers(connected)if code is None else code);self.before=self.r[:];self.saved_f=self.f[20:]
 def access(self):
  if self.own_instruction:
   if self.accesses==self.cut:raise faults.AccessBoundary
   self.accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  counts={self.syms['bzero']:2,self.syms['func_1502B020']:5,LOOKUP:3,ENTRY:0,0x151EEFF0:0,0x150061B0:0}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_1502B020']:
   self.query_args=a;self.lookup_stage=0;self.queries.append(a[1:])
   assert a[1:3]==(3,0x1A)and a[4]<67,('query-protocol',a)
   assert a[0]==STACK+self.c.phase-16,('size-pointer',a[0])
  if t==LOOKUP:self.lookup_packets.append(a)
 def hook(self,t):
  a=self.calls[-1][1];c=self.c;s=self.syms;value=0x76543210
  if t==s['bzero']:
   assert a==(s['D_800BE580'],8),('zero-protocol',a)
   for i in range(a[1]):put(self.memory,a[0]+i,0,1)
  elif t==s['func_1502B020']:
   p,depth,tag,selector,index=a;put(self.memory,p,size_for(c,index,selector));effects(self.memory,c,index,s);value=0 if size_for(c,index,selector)else 0xDEAD0000
  elif t==LOOKUP:
   index=self.query_args[4];selector=self.query_args[3];stage=self.lookup_stage;self.lookup_stage+=1
   assert a[1]==(0x1A,selector,index)[stage],('component',stage,a)
   descriptor=0 if c.missing==stage else size_for(c,index,selector)if stage==2 else 1
   put(self.memory,a[2],0xF0000000|descriptor)
   if c.missing==stage:put(self.memory,a[2],0)
   if c.missing==stage or stage==2:effects(self.memory,c,index,s)
   value=4*(stage+1)
  elif t in(0x151EEFF0,0x150061B0):pass
  else:raise AssertionError(hex(t))
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=value

def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.queries,m.lookup_packets)

def check(m,initial,c,s=SYMS):
 want,calls,queries=reference(initial,c,s);assert public(m.memory)==public(want),(c,'bitmap');assert m.queries==queries,(c,'queries')
 actual=[x for x in m.calls if x[0]!=LOOKUP];assert actual==calls,(c,actual,calls)
 assert m.r[16:24]==m.before[16:24]and m.r[29]==m.before[29]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f

def cases():
 for n in range(256):yield Case(seed=n,selector=n,pattern=n%6,mutation=n%4,phase=(n%2)*8)
 for pattern,mutation,missing,alias,phase in itertools.product(range(6),range(4),(-1,0,1),(0,4,8),(0,8)):
  yield Case(seed=0xE7,selector=0x81,pattern=pattern,mutation=mutation,missing=missing,alias=alias,phase=phase)

def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();zero_visits=set();query_visits=set();count=0
 # Alias layouts receive independent GNU links for their exact symbol bindings.
 aliases={a:[linked(p,'alias-%d-%d'%(a,i),s=symbols(Case(alias=a)))for i,p in enumerate(objects)]for a in(4,8)}
 for i,c in enumerate(cases()):
  connected=i%7==0;initial=fixture(c);programs=aliases.get(c.alias,ws);ms=[Oracle(w,initial,c,connected=connected).run()for w in programs]
  for m in ms:check(m,initial,c)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits&set(range(ENTRY,ENTRY+220,4)));zero_visits.update(ms[0].visits&set(range(ZERO,ZERO+160,4)));query_visits.update(ms[0].visits&set(range(QUERY,QUERY+240,4)));count+=1
 assert len(visits)==55
 cuts=delays=0
 for c in(Case(pattern=0),Case(pattern=1,mutation=3,phase=8)):
  initial=fixture(c);full=Oracle(ws[0],initial,c).run();selected=sorted(set(list(range(35))+list(range(35,full.accesses,17))+list(range(max(0,full.accesses-20),full.accesses))))
  for cut in selected:
   ms=[Oracle(w,initial,c)for w in ws]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective access cut')
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for j,(entry,bitmap,selector)in enumerate(((0x17007FFC,0x90017FFC,0x90028000),(0x2500FFFC,0xA001FFFC,0xA0027FFC),(0x15008000,0x90028000,0x9002FFFC))):
  s=dict(D_800BE580=bitmap,D_800BEAAB=selector,bzero=entry+0x10000,func_1502B020=entry+0x20000);bs=[linked(p,'rebase-%d-%d'%(j,i),entry=entry,s=s)for i,p in enumerate(objects)]
  for c in(Case(pattern=0),Case(pattern=1),Case(pattern=5,mutation=3,phase=8)):
   initial=fixture(c,s);ms=[Oracle(w,initial,c,s=s,entry=entry).run()for w in bs]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 return dict(cases=count,executions=count*3,body_words=55,slot_words=58,alignment_words=3,all_body_words_visited=True,queries_per_execution=67,selector_bytes=256,ninth_byte_preserved_and_ORed=True,selector_bitmap_aliases=[4,8],first_mask_home_unobservable=True,original_bzero_words=40,bzero_words_visited=len(zero_visits),original_query_words=60,query_words_visited=len(query_visits),catalog_lookup_bounded=True,access_prefix_cases=cuts,access_cut_scope='all first35 and last20 plus every17th intervening instruction access in two complete executions',branch_delay_cuts=delays,rebased_cases=rebased,complete_RAM_registers_trace_and_fault_context=True,portable_private_alias_or_hardware_claimed=False)

def guard_suite():
 rows=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(before.decode())));count=0;assert len(rows)==2
 for i in range(2):
  for field in('expected','expected_relocations'):
   bad=[dict(v)for v in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else'R_MIPS_26:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(bad);p=o/('bad-guard-%d-%s.csv'%(i,field));p.write_bytes(before+stream.getvalue().encode())
   try:source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,source.OWNER,p)
   except ValueError:pass
   else:raise AssertionError('Ineffective actual padder control')
   count+=1
 def dag(words):
  g=[('reg',i)for i in range(32)];g[0]=('const',0)
  for w in words:
   op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63;imm=((w&65535)^32768)-32768
   if op==9:g[rt]=('add',g[rs],('const',imm))
   elif op==0 and fn==37:g[rd]=g[rs]if g[rt]==('const',0)else('or',g[rs],g[rt])
   else:raise AssertionError(hex(w))
  return g
 for i,(entry,addr)in enumerate(((ENTRY,SELECTOR),(0x17007FFC,0x90017FFC),(0x2500FFFC,0xA001FFFC),(0x15008000,0x90028000))):
  s=dict(SYMS,D_800BEAAB=addr,bzero=entry+0x10000,func_1502B020=entry+0x20000);a=linked(o/('original-'+F+'.o'),'guard-original-'+str(i),s,entry);b=linked(o/'selected-final.o','guard-raw-'+str(i),s,entry);assert Counter(a[16:18])==Counter(b[16:18])and dag(a[16:18])==dag(b[16:18]);assert a[:16]==b[:16]and a[18:]==b[18:]
 return dict(guards=2,actual_padder_rejections=count,closed_windows=[[64,72]],GNU_alias_layouts=4,all32_GPR_DAGs_equal=True,instruction_multisets_equal=True,memory_or_control_in_window=0,only_selector_LO16_moves=True,insertions=0,omissions=0,inherited_prefix_preserved=True)

def controls(body):
 edits={
 'clear-nine':('bzero(D_800BE580, 8);','bzero(D_800BE580, 9);'),
 'clear-seven':('bzero(D_800BE580, 8);','bzero(D_800BE580, 7);'),
 'first-byte':('byteIndex = -1;','byteIndex = 0;'),
 'mask-reset':('mask = 1;','mask = 2;'),
 'byte-boundary':('(index & 7) == 0','(index & 3) == 0'),
 'mask-shift':('mask <<= 1;','mask <<= 2;'),
 'query-depth':('(&size, 3, 0x1A,','(&size, 2, 0x1A,'),
 'query-tag':('(&size, 3, 0x1A,','(&size, 3, 0x1B,'),
 'selector':('0x1A, D_800BEAAB, index','0x1A, 0, index'),
 'index-argument':('D_800BEAAB, index);','D_800BEAAB, index + 1);'),
 'return-not-size':('func_1502B020(&size,','size = func_1502B020(&size,'),
 'replace-byte':('D_800BE580[byteIndex] |= mask;','D_800BE580[byteIndex] = mask;'),
 'size-zero':('size != 0','size == 0'),
 'size-byte':('size != 0','(u8)size != 0'),
 'limit64':('index != 67','index != 64')}
 result={}
 for n,(a,b)in edits.items():assert body.count(a)==1,(n,a);result[n]=body.replace(a,b,1)
 return result

def compiled_controls():
 effective={};corpus=[Case(seed=n,selector=n,pattern=p,mutation=mut)for n,p,mut in itertools.product((0,1,128,255),range(6),(0,3))]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);source.check_owner_diagnostics(diag);text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,SYMS);assert not unknown;p=o/('IDO-control-'+name);p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%ENTRY+'\n'.join('%s = 0x%X;'%(n,v)for n,v in SYMS.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);words=list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
  for c in corpus:
   initial=fixture(c);m=Oracle(words,initial,c)
   try:m.run()
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]in('zero-protocol','query-protocol','size-pointer'),(name,e)
    effective[name]='explicit helper protocol disagreement';break
   try:check(m,initial,c)
   except AssertionError:effective[name]='independent bitmap/query disagreement';break
  else:raise AssertionError('Ineffective IDO control: '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_errors_counted=False)

def native_harness(body):
 from tools.tests.test_game_projected_packet_draw import native_command
 text=(r/'conker/src/game_57FA0.c').read_text();a,b=source.function_span(text,'func_1502B020');provider=text[a:b].replace('u32 func_1502B020(','static u32 retainedQuery(')
 sdk=(r/'conker/include/libc/stdarg.h').read_text()
 return source.HEADERS+'\n'+sdk+'\nextern u8 D_AB1950[];\ns32 func_1502AC88(u32,s32,u32*);\n'+provider+'\n#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wmaybe-uninitialized"\n'+body+'\n#pragma GCC diagnostic pop\n'+r'''
u8 D_800BE580[48],D_800BEAAB,D_AB1950[16];
static u8 expected[48],expectedSelector;static u32 seed,pattern,mutationMode;static s32 missing;static int zeroCalls,queryCalls,lookupStage,error;static u32 queryIndex,querySelector,expectedBase;
static u32 wanted(u32 index,u32 select){static const u32 values[]={0,1,0x100,0x10000,0x1000000,0xFFFFFFF,0,0x100000};if(missing==0||missing==1)return 0;
 switch(pattern){case0:return0;case1:return1;case2:return values[(index+seed)&7];case3:return index==66;case4:return index==64;default:return values[(index+select+seed)&7];}}
static void effect(u8*bitmap,u8*select,u32 index){if((mutationMode&1)&&index%13==0)*select=(u8)(*select+73);if((mutationMode&2)&&index%11==0)bitmap[index>>3]=(u8)(0xA0|((index+seed)&31));}
void bzero(void*destination,int count){int i;zeroCalls++;if(destination!=D_800BE580||count!=8)error=1;for(i=0;i<count&&i<48;i++)((u8*)destination)[i]=0;}
s32 func_1502AC88(u32 base,s32 component,u32*descriptor){u32 stage=(u32)lookupStage++;u32 expectedComponent=stage==0?0x1A:stage==1?querySelector:queryIndex;
 if(stage>2||component!=(s32)expectedComponent||base!=expectedBase)error=2;
 *descriptor=missing==(s32)stage?0:0xF0000000u|(stage==2?wanted(queryIndex,querySelector):1);expectedBase+=4*(stage+1);return(s32)(4*(stage+1));}
__attribute__((noinline)) u32 func_1502B020(u32*size,u32 depth,...){va_list ap;u32 tag,select,index,result;
 va_start(ap,depth);tag=(u32)va_arg(ap,s32);select=(u32)va_arg(ap,s32);index=(u32)va_arg(ap,s32);va_end(ap);
 if(depth!=3||tag!=0x1A||select!=D_800BEAAB||index!=(u32)queryCalls||index>=67)error=3;queryCalls++;
 queryIndex=index;querySelector=select;lookupStage=0;expectedBase=(u32)D_AB1950;result=retainedQuery(size,depth,(s32)tag,(s32)select,(s32)index);
 if(lookupStage!=(missing<0?3:missing+1)||*size!=wanted(index,select)||(result==0)!=(*size==0))error=4;
 effect(D_800BE580,&D_800BEAAB,index);return *size?0:0xDEAD0000u;
}
static int run(void){u32 n,p,m,fail,i,index,size;for(n=0;n<256;n++)for(p=0;p<6;p++)for(m=0;m<4;m++)for(fail=0;fail<3;fail++){
 seed=n;pattern=p;mutationMode=m;missing=(s32)fail-1;for(i=0;i<48;i++)D_800BE580[i]=expected[i]=(u8)(i*29+n);D_800BEAAB=expectedSelector=(u8)n;
 for(i=0;i<8;i++)expected[i]=0;for(index=0;index<67;index++){size=wanted(index,expectedSelector);effect(expected,&expectedSelector,index);if(size)expected[index>>3]|=(u8)(1u<<(index&7));}
 zeroCalls=queryCalls=error=0;func_15016588();if(error)return error;if(zeroCalls!=1||queryCalls!=67||D_800BEAAB!=expectedSelector)return 5;for(i=0;i<48;i++)if(D_800BE580[i]!=expected[i])return 6;
 }return0;}
'''.replace('case0','case 0').replace('case1','case 1').replace('case2','case 2').replace('case3','case 3').replace('case4','case 4').replace('return0','return 0').replace('return1','return 1')

def native_suite():
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 profiles={};effective={}
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED)+START);exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,cases=18432,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body)+START);exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,7)and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);effective[name]=q.returncode
 return dict(cases_per_profile=18432,profiles=profiles,SDK32_layout=True,first_iteration_initializes_mask_before_use=True,GCC_false_positive_maybe_uninitialized_suppressed_only_for_target=True,real_variadic_query_C=True,catalog_lookup_bounded=True,return_value_decoupled_from_outsize=True,all256_selectors_and_initial_ninth_bytes=True,clear_eight_query67_write_ninth_verified=True,all48_bitmap_and_canary_bytes_checked=True,negative_controls=len(effective),effective_native_controls=effective,portable_private_stack_alias_or_hardware_claimed=False)

def caller_suite():
 from tools.match_progress import load_elf_functions
 rom=(r/'conker/conker.us.bin').read_bytes();jal=(0x0C000000|(ENTRY>>2&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')];assert len(calls)==1 and not pointers
 at=calls[0];entry=0x15000000+at-0x2D4B0;words=list(struct.unpack_from('>4I',rom,at));assert words[2]==0x0C000000|(0x151EEFF0>>2&0x3FFFFFF);end=entry+16
 fs,_,_=load_elf_functions(str(o/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');original=list(struct.unpack_from('>124I',rom,0x34CE0));assert fs['func_15007830']==original
 programs=[linked(p,'caller-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];count=0;visits=set()
 for c in(Case(seed=n,selector=n,pattern=p,mutation=mut,phase=phase)for n,p,mut,phase in itertools.product((0,255),range(6),range(4),(0,8))):
  initial=fixture(c);want,expected,queries=reference(initial,c);expected=[(ENTRY,()),*expected,(0x151EEFF0,())];ms=[]
  for body in programs:
   code=helpers(False);code.update(zip(range(ENTRY,ENTRY+220,4),body));m=Oracle(words,initial,c,entry=entry,code=code);m.code=WindowCode(m.code,m);m.code.ends={end}
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   assert public(m.memory)==public(want)and m.calls==expected and m.queries==queries,c;assert m.r[16:24]==m.before[16:24]and m.r[29]==m.before[29];ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits&set(range(entry,end,4)));count+=1
 return dict(cases=count,original_windows=1,window_words=4,parent='func_15007830',call_ROM=hex(at),entry=hex(entry),exit=hex(end),caller_words_visited=len(visits),arguments=0,return_ignored=True,current_linked_C_parent_all124_words_equal_retail=True,full_parent_execution_or_hardware_claimed=False,aligned_literal_pointers=0)

def consumer_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();entry=0x15080738;helper=0x15080718;words=list(struct.unpack_from('>19I',rom,0xADBE8));code=dict(zip(range(helper,helper+32,4),struct.unpack_from('>8I',rom,0xADBC8)));count=0;visits=set()
 class Consumer(TimingOracle):
  def record_call(self,t):assert t==helper;self.calls.append((t,tuple(self.arguments(3))))
  def hook(self,t):raise AssertionError(('Unexpected consumer helper',hex(t)))
 for seed,pattern in itertools.product((0,255),range(6)):
  c=Case(seed=seed,selector=seed,pattern=pattern);memory,_,_=reference(fixture(c),c)
  for index in range(67):
   m=Consumer(words,memory,entry=entry,arguments=(index,),connected=code).run();expected=int(bool(read(memory,BITMAP+(index>>3),1)&(1<<(index&7))));assert m.r[2]==expected,(c,index);visits.update(m.visits);count+=1
 return dict(cases=count,original_consumer_words=19,original_index_helper_words=8,consumer_words_visited=len(visits&set(range(entry,entry+76,4))),index_helper_words_visited=len(visits&set(code)),all67_indices=True,byte8_low_bits_observed=True,no_additional_matching_credit=True)
