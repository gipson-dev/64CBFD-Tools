"""Signed ring submission: ABI-visible raw equivalence and literal installed traces.

The bounded lower draw service validates its ten-word packet; rendering hardware
and the complete parent dispatcher are deliberately outside this model.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import csv,io,itertools,json,struct,subprocess
from tools.experiments import game_ring_render_submit_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
FIRST,DESCRIBE,DRAW,RENDER=0x15094F70,0x15095060,0x150950D4,0x15142FBC
CURSOR,TABLE=0x30020,0x80400000
SYMS=dict(D_800DCE40=0x800DCE40,D_800DD220=0x800DD220,D_800DD224=0x800DD224,
 D_800DD228=0x800DD228,D_800903F4=0x800903F4,D_800DD230=0x800DD230,
 D_800D2C9C=0x800D2C9C,D_800A4AC8=0x800A4AC8,func_15094F70=FIRST,func_15142FBC=RENDER)
DESCRIPTOR,CACHE1,CACHE2=0x800D2C90,0x800DD218,0x800DD21C
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 old:int=0
 pattern:int=0
 mutation:int=0
 cache:int=0
 indirect:int=0
 phase:int=0
 packed:int=0xFEDC1234

def args(c):return(CURSOR,4,u32(c.packed),u32(signed(c.packed)>>16))
def home(c):return STACK+c.phase
def mode_values(c):
 return ((0,1,0xFFFFFFFF,0x87654321)[c.pattern%4],(0,0xFF00FF00,0x80000000,0x12345678)[c.pattern%4],(0,0x00FF00FF,0x7FFFFFFF,0x87654321)[c.pattern%4])
def mode_after(c):return(0x12345678,0x87650000,0xABCD)if c.mutation&1 else mode_values(c)
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,n in((CURSOR-16,160),(TABLE-512,1024),(s['D_800DD220']-16,80),(DESCRIPTOR-16,48),(s['D_800A4AC8']-16,64),(s['D_800903F4']-16,48)):
  m.update({base+i:0xA5 for i in range(n)})
 for i in range(-128,128):put(m,TABLE+i*4,u32(i*0x1020304+0x12345678))
 for name,n in(('D_800DD220',4),('D_800DD224',4),('D_800DD228',4),('D_800DCE40',2)):
  for i in range(-4,n+4):m[s[name]+i]=0xA5
 put(m,s['D_800DCE40'],c.old&65535,2)
 flags,a,b=mode_values(c);put(m,s['D_800D2C9C'],flags);put(m,s['D_800A4AC8']+24,a);put(m,s['D_800A4AC8']+28,b)
 values=mode_after(c);want=(values[0]|0x82CA0,values[1]|values[2]);put(m,CACHE1,want[0]if c.cache==0 else want[0]^1);put(m,CACHE2,want[1]if c.cache!=2 else want[1]^1)
 src=s['D_800903F4'];put(m,src,TABLE if c.indirect else 0x123456);put(m,src+4,0x91,1);put(m,src+6,0x1234,2);put(m,src+8,0xFEDC,2);put(m,src+10,0x80,1);put(m,src+11,0xFF,1)
 return m
def public(m):return{p:v for p,v in m.items()if not STACK-1024<=p<STACK+512}
def mutate(m,c,s):
 if c.mutation&1:
  flags,a,b=mode_after(c);put(m,s['D_800D2C9C'],flags);put(m,s['D_800A4AC8']+24,a);put(m,s['D_800A4AC8']+28,b)
 if c.mutation&2:
  put(m,s['D_800DCE40'],0xBEEF,2);put(m,s['D_800DD220'],0x87654321);put(m,s['D_800DD224'],0xFFFFFFFF);put(m,s['D_800DD228'],0)
def reference(c,s=SYMS,connected=False,cursor=CURSOR):
 m=fixture(c,s);old=half(c.old);n=half(old+128);put(m,s['D_800DCE40'],0 if n>=1280 else n&65535,2)
 put(m,s['D_800DD220'],u32(old));put(m,s['D_800DD224'],1);put(m,s['D_800DD228'],s['D_800903F4'])
 if connected:
  src=s['D_800903F4'];v=read(m,src);put(m,DESCRIPTOR,read(m,TABLE+(old>>8)*4)if c.indirect else v)
  for dst,off,n in((4,6,2),(6,8,2),(8,10,1),(9,11,1),(10,4,1)):put(m,DESCRIPTOR+dst,int.from_bytes(bytes(m[src+off+i]for i in range(n)),'big'),n)
  put(m,s['D_800DD230']+16,DESCRIPTOR)
 mutate(m,c,s);put(m,cursor,0xBA000003);put(m,cursor+4,u32(old));cursor+=8
 flags,a,b=mode_after(c);mode1,mode2=flags|0x82CA0,a|b
 if mode1!=read(m,CACHE1)or mode2!=read(m,CACHE2):
  put(m,cursor,0xE7000000);put(m,cursor+4,0);cursor+=8;put(m,cursor,0xEF000000|((mode1|15)&0xFFFFFF));put(m,cursor+4,mode2);cursor+=8;put(m,CACHE1,mode1);put(m,CACHE2,mode2)
 return m,cursor
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def helpers():
 rom=(r/'conker/conker.us.bin').read_bytes();result={}
 for va,at,n in((FIRST,0xC2420,30),(DESCRIBE,0xC2510,29),(RENDER,0x17046C,34)):
  result.update(zip(range(va,va+n*4,4),struct.unpack_from('>%dI'%n,rom,at)))
 return result
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.packet_states=[];self.window_stop=None
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=args(c),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:]
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
 def execute(self,w):
  if self.current_pc==self.window_stop:raise WindowBoundary
  super().execute(w)
 def record_call(self,t):
  counts={self.syms['func_15094F70']:9,self.syms['func_15142FBC']:4,DESCRIBE:3,DRAW:10,ENTRY:4}
  assert t in counts,hex(t);a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['func_15094F70']:
   assert a==(self.root_cursor,self.syms['D_800903F4'],u32(half(self.c.old)),self.syms['D_800DD230'],0,0,0,1,3),('first-packet',a)
   self.packet_states.append((read(self.memory,self.syms['D_800DD220']),read(self.memory,self.syms['D_800DD224']),read(self.memory,self.syms['D_800DD228'])))
  if t==self.syms['func_15142FBC']:
   flags,b,d=mode_after(self.c);assert a==(self.root_cursor+8,flags|0x82CA0,b|d,home(self.c)-1),('mode-packet',a);assert self.memory[a[3]]==1,('sync',self.memory[a[3]])
 def hook(self,t):
  a=self.calls[-1][1];s=self.syms
  if t==DRAW:
   assert a==(self.root_cursor,DESCRIPTOR,0,0,0,0,1,256,256,3),('draw-packet',a)
   value=read(self.memory,DESCRIPTOR);expected=read(self.memory,TABLE+(half(self.c.old)>>8)*4)if self.c.indirect else 0x123456
   assert value==expected and read(self.memory,s['D_800DD230']+16)==DESCRIPTOR,('descriptor',value,expected)
  if t in(self.syms['func_15094F70'],DRAW):
   mutate(self.memory,self.c,s);put(self.memory,self.root_cursor,0xBA000003);put(self.memory,self.root_cursor+4,u32(half(self.c.old)));value=self.root_cursor+8
  elif t==s['func_15142FBC']:
   cursor,mode1,mode2,sync=a
   if mode1!=read(self.memory,CACHE1)or mode2!=read(self.memory,CACHE2):
    if self.memory[sync]==1:put(self.memory,cursor,0xE7000000);put(self.memory,cursor+4,0);cursor+=8;put(self.memory,sync,0,1)
    put(self.memory,cursor,0xEF000000|((mode1|15)&0xFFFFFF));put(self.memory,cursor+4,mode2);cursor+=8;put(self.memory,CACHE1,mode1);put(self.memory,CACHE2,mode2)
   value=cursor
  else:raise AssertionError(('unexpected-bounded-service',hex(t)))
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=value
 root_cursor=CURSOR
class WindowBoundary(Exception):pass
def abi(m):return(m.r[2],m.r[16:24],m.r[28:31],m.f[20:],public(m.memory),m.calls,m.packet_states)
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.packet_states)
def check(m,c,s=SYMS,connected=False):
 want,cursor=reference(c,s,connected);assert public(m.memory)==public(want),('public',c,[(hex(p),v,want.get(p))for p,v in public(m.memory).items()if v!=want.get(p)][:12]);assert m.r[2]==cursor,('return',c,m.r[2],cursor)
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f
def corpus():
 olds=(-32768,-32641,-129,-128,-1,0,1,1151,1152,1279,1280,32639,32640,32767)
 for i,(old,pattern,mutation,cache,indirect,phase)in enumerate(itertools.product(olds,range(4),range(4),range(3),(0,1),(0,8))):
  yield Case(old,pattern,mutation,cache,indirect,phase,(0,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[i%4])
def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();hv=set();n=0
 for i,c in enumerate(corpus()):
  conn=helpers()if i%7==0 else None;ms=[Oracle(w,fixture(c),c,connected=conn).run()for w in ws]
  for m in ms:check(m,c,connected=bool(conn))
  assert abi(ms[0])==abi(ms[1])==abi(ms[2]),c;assert state(ms[0])==state(ms[2]),c
  visits.update(ms[0].visits&set(range(ENTRY,ENTRY+224,4)));hv.update(ms[0].visits&set(helpers())if conn else set());n+=1
 assert len(visits)==56
 cuts=delays=0
 for c in(Case(),Case(1152,mutation=3,cache=1,phase=8),Case(32767,cache=2,indirect=1)):
  ref=Oracle(ws[0],fixture(c),c).run()
  for cut in range(ref.accesses):
   ms=[Oracle(w,fixture(c),c)for w in(ws[0],ws[2])]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective fault control')
   assert state(ms[0])==state(ms[1]),(c,cut);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for j,entry in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  s={k:(entry+0x20000+i*0x10000 if k.startswith('func_')else 0x81000000+i*0x10000+0x7FFC+(i%2)*4)for i,k in enumerate(SYMS)}
  bw=[linked(p,'rebase-%d-%d'%(j,i),entry,s)for i,p in enumerate(objects)]
  for c in(Case(),Case(1152,mutation=3,cache=1),Case(32767,cache=2,phase=8)):
   ms=[Oracle(w,fixture(c,s),c,entry,s).run()for w in bw]
   for m in ms:check(m,c,s)
   assert abi(ms[0])==abi(ms[1])==abi(ms[2]);assert state(ms[0])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),original_helper_words=93,helper_words_visited=len(hv),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,raw_ABI_public_state_equal=True,retail_normalized_complete_state_trace_fault_prefix_equal=True,raw_all_registers_or_private_trace_equal_claimed=False,bounded_lower_draw=True)
def guard_suite():
 rows=source.NEW_GUARDS;before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();columns=next(csv.reader(io.StringIO(before.decode())));count=0
 for i in range(5):
  for field in('expected','expected_relocations'):
   bad=[dict(v)for v in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else'R_MIPS_26:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(bad);p=o/('bad-guard-%d-%s.csv'%(i,field));p.write_bytes(before+stream.getvalue().encode())
   try:source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,source.OWNER,word_patches_path=p)
   except ValueError:pass
   else:raise AssertionError('Ineffective actual padder control')
   count+=1
 raw,_=source.checked_payload(*source.payload(o/'selected-final.o'));truth,_=source.payload(o/('original-'+F+'.o'));a=struct.unpack('>56I',raw);b=struct.unpack('>56I',truth)
 assert [i for i,(x,y)in enumerate(zip(a,b))if x!=y]==[43,44,46,47,51]and a[:43]==b[:43]and a[50]==b[50]
 def dag(words):
  g=[('g',i)for i in range(32)];g[0]=('const',0);g[3]=('table',0);g[29]=('sp',0);reads=[]
  def OR(a,b):return tuple(sorted(set((a[1:]if a[0]=='or'else(a,))+(b[1:]if b[0]=='or'else(b,))),key=repr))
  def combine(a,b):return('or',*OR(a,b))
  for w in words:
   op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31;imm=((w&65535)^32768)-32768
   if op==35:assert g[rs]==('table',0);g[rt]=('load',imm);reads.append(imm)
   elif op==15:g[rt]=('const',(w&65535)<<16)
   elif op==13:g[rt]=combine(g[rs],('const',w&65535))
   elif op==9:g[rt]=(g[rs][0],g[rs][1]+imm)
   elif op==0 and w&63==37:g[rd]=g[rs]if rt==0 else combine(g[rs],g[rt])
   elif op==3:g[31]=('return-pc',ENTRY+208)
   else:raise AssertionError(hex(w))
  live=tuple(g[i]for i in(4,5,6,7,16,17,18,19,20,21,22,23,28,29,30,31))
  return live,sorted(reads)
 assert dag(a[43:52])==dag(b[43:52]);assert dag(a[43:52])[1]==[24,28]
 bad=list(a[43:52]);bad[-1]^=1<<16;assert dag(bad)!=dag(b[43:52])
 return dict(guards=5,actual_padder_rejections=count,closed_window=[172,208],call_and_delay_included=True,unchanged_call_binding_at=200,ABI_live_GPR_DAG_equal=True,all_FPRs_untouched=True,independent_table_offsets=[24,28],private_temp_registers_dead_at_ABI=True,all32_GPRs_equal_claimed=False,semantic_DAG_controls=1,insertions=0,omissions=0)
def controls(body):
 edits={'advance':('+= 0x80','+= 0x40'),'threshold-equality':('>= 0x500','> 0x500'),'unsigned-wrap':('D_800DCE40 >= 0x500','(u16)D_800DCE40 >= 0x500'),'capture-after-advance':('D_800DD220 = D_800DCE40;','D_800DD220 = (s16)(D_800DCE40 + 0x80);'),'sync-zero':('sync = 1;','sync = 0;'),'source-pointer':('D_800DD228 = D_800903F4;','D_800DD228 = D_800903F4 + 4;'),'draw-mode':('D_800DD224 = 1;','D_800DD224 = 2;'),'selector':('D_800DD224, 3);','D_800DD224, 2);'),'flags':('0x80000 | 0x2CA0','0x80000 | 0x2C80'),'table-op':('D_800A4AC8[7] | D_800A4AC8[6]','D_800A4AC8[7] & D_800A4AC8[6]'),'table-index':('D_800A4AC8[6]','D_800A4AC8[5]'),'ignored-first-return':('commands = (Gfx *)func_15094F70','(void)func_15094F70')}
 result={}
 for name,(a,b)in edits.items():assert body.count(a)==1,(name,a);result[name]=body.replace(a,b,1)
 return result
def compiled_controls():
 effective={};cases=[Case(old,pattern,mutation,cache)for old,pattern,mutation,cache in itertools.product((-32768,-1,0,1152,32767),range(4),(0,3),(0,1))]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag,diag;w=linked(obj,'IDO-linked-'+name)
  for c in cases:
   try:m=Oracle(w,fixture(c),c).run();check(m,c)
   except AssertionError as e:
    if e.args and isinstance(e.args[0],tuple):assert e.args[0][0]in('first-packet','mode-packet','sync','public','return'),(name,e)
    effective[name]='packet/state disagreement';break
  else:raise AssertionError('Ineffective IDO semantic control '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_failures_counted=False)
def native_harness(body):
 text=(r/'conker/src/game/generated_C1D70.c').read_text();providers=[]
 for name in('func_15094F70','func_15095060'):
  a,b=source.function_span(text,name);providers.append(text[a:b].replace('s32 func_15094F70(','static s32 actualFirst('))
 text=(r/'conker/src/game_16EE20.c').read_text().replace('Gfx *func_15142FBC(', 'void *func_15142FBC(');a,b=source.function_span(text,'func_15142FBC');renderer=text[a:b].replace('void *func_15142FBC(','static Gfx *actualRender(')
 return source.HEADERS+r'''
typedef struct {u32 unk0;u16 unk4,unk6;u8 unk8,unk9,unkA,padB;} structC1D70Descriptor;
typedef char SourceSize[sizeof(structC1D70Source)==12?1:-1];
typedef char DescriptorSize[sizeof(structC1D70Descriptor)==12?1:-1];
typedef char GfxSize[sizeof(Gfx)==8?1:-1];
s16 D_800DCE40;s32 D_800DD220,D_800DD224;u8 *D_800DD228;
u8 D_800DD230[32] __attribute__((aligned(8))),D_800903F4[16] __attribute__((aligned(8)));
u32 D_800D2C9C,D_800A4AC8[8],D_800DD218,D_800DD21C;
structC1D70Descriptor D_800D2C90;
void func_15095060(structC1D70Source *,s32,u8 *);
s32 func_150950D4(s32,structC1D70Descriptor *,s32,s32,s32,s32,s32,s32,s32,s32);
static Gfx output[12],expectedOutput[12];static u32 tables[256];
static u32 pattern,mutation,cache,indirect,oldBits;static s32 oldValue;static int error,firstCalls,drawCalls,renderCalls;
static const u32 flags[4]={0,1,0xFFFFFFFFu,0x87654321u};
static const u32 low[4]={0,0xFF00FF00u,0x80000000u,0x12345678u};
static const u32 high[4]={0,0x00FF00FFu,0x7FFFFFFFu,0x87654321u};
static void afterDraw(void){if(mutation&1){D_800D2C9C=0x12345678;D_800A4AC8[6]=0x87650000;D_800A4AC8[7]=0xABCD;}
 if(mutation&2){D_800DCE40=(s16)0xBEEF;D_800DD220=(s32)0x87654321u;D_800DD224=-1;D_800DD228=NULL;}}
'''+'\n'.join(providers)+'\n'+renderer+'\n'+body+r'''
__attribute__((noinline)) s32 func_150950D4(s32 cursor,structC1D70Descriptor *d,s32 a,s32 b,s32 c,s32 e,s32 f,s32 g,s32 h,s32 i){
 Gfx *p=(Gfx*)cursor;u32 wanted=indirect?tables[128+(oldValue>>8)]:0x123456;drawCalls++;
 if(p!=output+1||d!=&D_800D2C90||a||b||c||e||f!=1||g!=256||h!=256||i!=3){error=2;return cursor;}
 if(d->unk0!=wanted||d->unk4!=0x1234||d->unk6!=0xFEDC||d->unk8!=0x80||d->unk9!=0xFF||d->unkA!=0x91||d->padB!=0xA5||*(structC1D70Descriptor**)(D_800DD230+16)!=d){error=3;return cursor;}
 afterDraw();p->words.w0=0xBA000003;p->words.w1=(u32)oldValue;return(s32)(p+1);
}
__attribute__((noinline)) s32 func_15094F70(s32 cursor,structC1D70Source *src,s32 offset,u8 *scratch,s32 a,s32 b,s32 c,s32 mode,s32 selector){
 s32 n=(s16)(oldValue+128);firstCalls++;
 if(cursor!=(s32)(output+1)||src!=(structC1D70Source*)D_800903F4||offset!=oldValue||scratch!=D_800DD230||a||b||c||mode!=1||selector!=3){error=1;return cursor;}
 if(D_800DCE40!=(n>=1280?0:n)||D_800DD220!=oldValue||D_800DD224!=1||D_800DD228!=D_800903F4){error=4;return cursor;}
 return actualFirst(cursor,src,offset,scratch,a,b,c,mode,selector);
}
__attribute__((noinline)) Gfx *func_15142FBC(Gfx *p,u32 mode1,u32 mode2,u8 *sync){
 u32 a=mutation&1?0x12345678:flags[pattern],b=mutation&1?0x87650000:low[pattern],c=mutation&1?0xABCD:high[pattern];Gfx *result;renderCalls++;
 if(p!=output+2||mode1!=(a|0x82CA0)||mode2!=(b|c)||*sync!=1){error=5;return p;}
 result=actualRender(p,mode1,mode2,sync);if(*sync!=(cache?0:1))error=6;return result;
}
static int run(void){u32 n,i,j,m1,m2;int nHalf;Gfx *ret,*end;structC1D70Source *src=(structC1D70Source*)D_800903F4;u8 *d=(u8*)&D_800D2C90;
 for(i=0;i<256;i++)tables[i]=(i-128)*0x1020304u+0x12345678u;
 for(n=0;n<65536;n++)for(mutation=0;mutation<4;mutation++)for(cache=0;cache<3;cache++)for(indirect=0;indirect<2;indirect++){
 oldBits=n;oldValue=(s16)n;pattern=n&3;D_800DCE40=(s16)n;D_800DD220=0x13579;D_800DD224=0x12345;D_800DD228=NULL;
 for(i=0;i<32;i++)D_800DD230[i]=0xA5;for(i=0;i<16;i++)D_800903F4[i]=0xA5;for(i=0;i<12;i++)d[i]=0xA5;
 src->unk0=indirect?(u32)(tables+128):0x123456;src->unk4=0x91;src->unk6=0x1234;src->unk8=0xFEDC;src->unkA=0x80;src->unkB=0xFF;
 for(i=0;i<8;i++)D_800A4AC8[i]=0xA5A5A5A5;D_800D2C9C=flags[pattern];D_800A4AC8[6]=low[pattern];D_800A4AC8[7]=high[pattern];
 m1=(mutation&1?0x12345678:flags[pattern])|0x82CA0;m2=mutation&1?0x8765ABCD:(low[pattern]|high[pattern]);D_800DD218=m1^(cache==1);D_800DD21C=m2^(cache==2);
 for(i=0;i<12;i++){output[i].words.w0=expectedOutput[i].words.w0=0xA5A50000u+i;output[i].words.w1=expectedOutput[i].words.w1=0x5A5A0000u+i;}
 expectedOutput[1].words.w0=0xBA000003;expectedOutput[1].words.w1=(u32)oldValue;end=output+2;
 if(cache){expectedOutput[2].words.w0=0xE7000000;expectedOutput[2].words.w1=0;expectedOutput[3].words.w0=0xEF000000|((m1|15)&0xFFFFFF);expectedOutput[3].words.w1=m2;end=output+4;}
 firstCalls=drawCalls=renderCalls=error=0;ret=func_151668B8(output+1,4,(s32)(n*0x1020304u),(s32)0x87654321u);
 if(error)return error;if(ret!=end||firstCalls!=1||drawCalls!=1||renderCalls!=1)return 7;
 for(i=0;i<12;i++)if(output[i].words.w0!=expectedOutput[i].words.w0||output[i].words.w1!=expectedOutput[i].words.w1)return 8;
 nHalf=(s16)(oldValue+128);if(D_800DCE40!=(mutation&2?(s16)0xBEEF:nHalf>=1280?0:nHalf)||D_800DD220!=(mutation&2?(s32)0x87654321u:oldValue)||D_800DD224!=(mutation&2?-1:1)||D_800DD228!=(mutation&2?NULL:D_800903F4)||D_800DD218!=m1||D_800DD21C!=m2)return 9;
 for(i=0;i<32;i++){j=i>=16&&i<20?((u8*)&(structC1D70Descriptor*){&D_800D2C90})[i-16]:0xA5;if(D_800DD230[i]!=j)return 10;}
 }
 return 0;}
'''+START
def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wl,-Ttext-segment=0x20000000',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=1572864,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in range(1,11),(name,code);effective[name]=code
 return dict(cases_per_profile=1572864,profiles=profiles,SDK32_layout=True,all65536_signed_halfword_starts=True,real_first_wrapper_C=True,real_descriptor_updater_C=True,real_renderer_C=True,bounded_lower_draw=True,negative_controls=len(effective),effective_native_controls=effective,output_and_scratch_canaries=True,portable_private_stack_alias_claimed=False)
def caller_suite():
 rom=source.snapshot(o)['conker/conker.us.bin'];entry=0x1516774C;stop=0x151677A8;at=0x194BFC;descriptor=0x8008B578;record=rom[0x230038:0x23006C]
 assert len(record)==52 and int.from_bytes(record[20:24],'big')==ENTRY
 pointer=ENTRY.to_bytes(4,'big');jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big')
 pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer];calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];assert pointers==[0x23004C]and not calls
 window=list(struct.unpack_from('>23I',rom,at));assert len(window)==23 and window[0]==0x8E8B0010 and window[-1]==0x26730008
 ws=[linked(p,'caller-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];n=0;visits=set()
 for old,packed,cache,mutation,has_callback,has_display,phase in itertools.product((-32768,0,1152,32767),(0,0x7FFFFFFF,0x80000000,0xFFFF0001),range(3),(0,3),(0,1),(0,1),(0,8)):
  c=Case(old,packed&3,mutation,cache,1,phase,packed);mem=fixture(c);mem.update({descriptor+i:v for i,v in enumerate(record)});display=int.from_bytes(record[16:20],'big')if has_display else 0
  put(mem,descriptor+16,display);put(mem,descriptor+20,ENTRY if has_callback else 0);put(mem,home(c)+0x8C,4);put(mem,home(c)+0x9C,packed);cursor=CURSOR+8*has_display
  ms=[]
  for w in ws:
   conn=helpers();conn.update(zip(range(ENTRY,ENTRY+224,4),w));m=Oracle(window+[0],mem,c,entry=entry,connected=conn);m.r[19]=CURSOR;m.r[20]=descriptor;m.r[7]=packed;m.root_cursor=cursor;m.window_stop=stop
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Caller boundary not reached')
   ms.append(m);root_calls=[a for t,a in m.calls if t==ENTRY]
   assert root_calls==([(cursor,4,u32(packed),u32(signed(packed)>>16))]if has_callback else[]),('caller-marshal',root_calls)
   if has_callback:
    want,end=reference(c,connected=True,cursor=cursor);expected=public(want)
   else:expected=public(fixture(c));end=cursor
   expected.update({descriptor+i:v for i,v in enumerate(record)});put(expected,descriptor+16,display);put(expected,descriptor+20,ENTRY if has_callback else 0)
   if has_display:put(expected,CURSOR,0xDE000000);put(expected,CURSOR+4,display)
   put(expected,end,0xD9FDFFFF);put(expected,end+4,0)
   assert public(m.memory)==expected,('caller-public',c,has_callback,has_display,[(hex(p),v,expected.get(p))for p,v in public(m.memory).items()if v!=expected.get(p)][:8]);assert m.r[19]==end+8
   assert m.r[29]==home(c)and m.r[20]==descriptor
  assert abi(ms[0])==abi(ms[1])==abi(ms[2]);assert state(ms[0])==state(ms[2]);visits.update(ms[0].visits&set(range(entry,stop,4)));n+=1
 assert len(visits)==23
 return dict(cases=n,original_indirect_window_words=23,words_visited=len(visits),descriptor_index=4,descriptor_stride=52,callback_offset=20,aligned_ROM_literal_pointers=['0x23004C'],aligned_ROM_JALs=0,all_four_arguments_checked=True,signed_high_half=True,returned_cursor_consumed=True,null_callback_and_display_paths=True,full_parent_or_hardware_claimed=False)
