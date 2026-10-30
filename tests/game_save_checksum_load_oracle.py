"""Save checksum reader with original transfer/default helpers and bounded I/O."""
from pathlib import Path
from dataclasses import dataclass,replace
import csv,hashlib,io,itertools,json,re,struct,subprocess,sys
from tools.tests import game_save_checksum_submit_oracle as prior
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-save-checksum-load-1500727C-match';F='func_1500727C';ENTRY=0x1500727C;ROM=0x3472C
HELPER,RESET,POLL,READ=0x151DD3A0,0x15007168,0x151DCFD8,0x151DD140
OTHER=0x300000;put,read,STACK=prior.put,prior.read,prior.STACK
SYMS=dict(D_800BE2F0=0x800BE2F0,D_800BE2F2=0x800BE2F2,D_800BE2F3=0x800BE2F3,D_800BE2F4=0x800BE2F4,D_800BE358=0x800BE358,D_800BE900=0x800BE900,D_80082BBC=0x80082BBC,jtbl_80095A00_game=0x80095A00,func_151DD3A0=HELPER,func_15007168=RESET,func_151DCFD8=POLL,func_151DD140=READ)
OFFSETS=(0x9C,0xAC,0xAC,0xF4,0xF4,0xCC,0xF4,0xBC,0xE8,0xE8)
@dataclass(frozen=True)
class Case:
 first:int=17
 second:int=91
 pattern:int=2
 match:bool=True
 fail:int=-1
 write_failure:bool=False
 effect:int=0
 status:int=0xFFFFFFFF
 busy:int=0
 phase:int=0
 record_alias:int=0
 seed:int=0
 lane:int=-1
 byte:int=1

def checksum(data):return(204+4*data[2]+8*data[3]+sum((1,2,4,8)[i%4]*data[i]for i in range(4,104)))&65535
def patterns(c):
 old=[(i*13+c.seed+0xA5)&255 for i in range(112)]
 new=[(0,255,i*7+c.seed,1<<(i&7),(i*37+c.seed)^0x80)[c.pattern%5]&255 for i in range(112)];new[2:4]=[c.first,c.second]
 if c.lane>=0:new[c.lane]=c.byte
 n=112 if c.fail<0 else 8*(c.fail+int(c.write_failure));blended=new[:n]+old[n:];h=checksum(blended)^(0 if c.match else 1)
 old[0:2]=list(struct.pack('>H',h if n==0 else h^0x5555));new[0:2]=list(struct.pack('>H',h if n else h^0x5555))
 return old,new
def reset_memory(m,c,s):
 a=s['D_800BE2F0'];dest=read(m,s['D_80082BBC'])
 for i in range(104):m[a+i]=0
 fifth={0:3,1:5,2:5,5:20,7:20,8:3,9:3}
 for i in range(10):
  p=dest+10*i
  for at,v in ((1,3),(2,0 if i==5 else 10),(3,2),(4,1),(9,0)):m[p+at]=v
  if i in fifth:m[p+5]=fifth[i]
def after_read(m,c,s):
 a=s['D_800BE2F0']
 if c.effect&1:put(m,a,0xF00D,2)
 if c.effect&2:m[a+2]^=0x80
 if c.effect&4:m[a+103]^=0x55
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed)&255 for i in range(-1024,256)}
 for base,n in ((s['D_800BE2F0']-8,128),(s['D_800BE900'],32),(OTHER,112),(s['jtbl_80095A00_game'],40)):
  for i in range(n):m[base+i]=(i*13+c.seed)&255
 old,_=patterns(c)
 for i,v in enumerate(old):m[s['D_800BE2F0']+i]=v
 put(m,s['D_80082BBC'],OTHER if c.record_alias else s['D_800BE2F4'])
 for i,offset in enumerate(OFFSETS):put(m,s['jtbl_80095A00_game']+4*i,s['func_15007168']+offset)
 return m
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+256}
def block(m,s):return bytes(m[s['D_800BE2F0']+i]for i in range(112))
def reference(initial,c,s=SYMS):
 m=dict(initial);a=s['D_800BE2F0'];calls=[];observations=[];_,image=patterns(c)
 def call(t,args):calls.append((t,args));observations.append((t,block(m,s)))
 call(s['func_151DD3A0'],(s['D_800BE900'],68,a,112))
 for _ in range(c.busy+1):call(s['func_151DCFD8'],(1,))
 count=14 if c.fail<0 else c.fail+1
 for k in range(count):
  call(s['func_151DD140'],(s['D_800BE900'],68+k,a+8*k))
  if k!=c.fail or c.write_failure:
   for i in range(8):m[a+8*k+i]=image[8*k+i]
  if k==count-1:after_read(m,c,s)
 if checksum(block(m,s))!=read(m,a,2):call(s['func_15007168'],());reset_memory(m,c,s)
 return m,calls,observations
def object_from_asm(function,path,label):
 text=(r/path).read_text();part=text[text.index('glabel '+function):text.index('endlabel '+function)+len('endlabel '+function)].replace('glabel '+function,'.globl '+function+'\n.type '+function+',@function\n'+function+':').replace('endlabel '+function,'.size '+function+',.-'+function)
 p=o/(label+'.s');p.write_text('.include "asm_processor_prelude.inc"\n.text\n'+part+'\n');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True);return p.with_suffix('.o')
def linked(obj,label,function=F,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def codes(label='guest',entry=ENTRY,s=SYMS):
 ps=[linked(o/n,label+'-'+str(i),entry=entry,s=s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];assert ps[0]==ps[2]
 transfer=linked(object_from_asm('func_151DD3A0','conker/asm/20A850.s','original-transfer'),label+'-transfer','func_151DD3A0',s['func_151DD3A0'],s)
 defaults=linked(object_from_asm('func_15007168','conker/asm/nonmatchings/game_33990/func_15007168.s','original-defaults'),label+'-defaults','func_15007168',s['func_15007168'],s)
 assert(len(transfer),len(defaults))==(45,69);connected={}
 for base,words in ((s['func_151DD3A0'],transfer),(s['func_15007168'],defaults)):connected.update(zip(range(base,base+len(words)*4,4),words))
 a,data=sections(r/'conker/build/conker.us.elf')['.game_data'];assert struct.unpack_from('>10I',data,0x80095A00-a)==tuple(RESET+i for i in OFFSETS)
 return ps,connected
class Oracle(prior.Oracle):
 def __init__(self,words,memory,c=Case(),s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,s,entry,connected);self.remaining=c.busy;self.chunk=0;self.image=patterns(c)[1]
 def record_call(self,t):
  counts={self.s['func_151DD3A0']:4,self.s['func_15007168']:0,self.s['func_151DCFD8']:1,self.s['func_151DD140']:3,ENTRY:0};assert t in counts,('Unbounded call',hex(t))
  a=tuple(self.arguments(counts[t]));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append((t,block(self.memory,self.s)))
 def hook(self,t):
  assert t in (self.s['func_151DCFD8'],self.s['func_151DD140']);args=self.calls[-1][1]
  if t==self.s['func_151DCFD8']:result=1 if self.remaining else 0;self.remaining=max(0,self.remaining-1)
  else:
   k=self.chunk;self.chunk+=1
   if k!=self.c.fail or self.c.write_failure:
    for i in range(8):self.memory[args[2]+i]=self.image[8*k+i]
   if k==(13 if self.c.fail<0 else self.c.fail):after_read(self.memory,self.c,self.s)
   result=self.c.status if k==self.c.fail else 0
  for i in range(4):self.put(self.r[29]+4*i,0xB6000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=result&0xFFFFFFFF
def state(m):return prior.state(m)
def check(m,initial,c,s=SYMS):
 want,calls,obs=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),c
 assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28] and m.r[30]==m.before[30] and m.f[20:]==m.saved_f
def cases():
 for n in range(256):
  yield Case(first=n,second=255-n,pattern=n%5,seed=n,match=True)
  yield Case(first=255-n,second=n,pattern=(n+1)%5,seed=n,match=False,phase=8)
 for pattern,match,fail,write,eff,busy,phase,alias in itertools.product((0,1,4),(False,True),(-1,0,7,13),(False,True),(0,7),(0,2),(0,8),(0,1)):
  yield Case(pattern=pattern,match=match,fail=fail,write_failure=write,effect=eff,busy=busy,phase=phase,record_alias=alias)
 for lane,byte,match in itertools.product(range(4,104),(1,255),(False,True)):yield Case(first=0,second=0,pattern=0,lane=lane,byte=byte,match=match)
 for fail,status,match in itertools.product((0,1,13),(1,0x80000000,0xFFFFFFFF),(False,True)):yield Case(fail=fail,status=status,match=match,write_failure=True,busy=3)
def guest_suite():
 ps,helpers=codes();count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for ws in ps:m=Oracle(ws,initial,c,connected=helpers).run();check(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c;visited.update(ms[0].visits);count+=1
 assert set(range(ENTRY,ENTRY+228,4))<=visited and set(helpers)<=visited,[hex(x)for x in set(helpers)-visited]
 cuts=delays=0
 for c in (Case(),Case(match=False,fail=7,effect=7,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c,connected=helpers).run()
  for cut in range(full.root_accesses):
   ms=[]
   for ws in ps:
    m=Oracle(ws,initial,c,connected=helpers);m.root_fault=cut
    try:m.run()
    except prior.faults.AccessBoundary:pass
    else:raise AssertionError(('Missing root prefix',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]) and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of)==(ms[2].current_pc,ms[2].delay_of)
   cuts+=1;delays+=ms[0].delay_of is not None
 rebases=0
 for j,(entry,a)in enumerate(((0x17007FFC,0x90017FFC),(0x2500FFFC,0x9001FFFC),(0x15008000,0x90028000))):
  s=dict(SYMS,D_800BE2F0=a,D_800BE2F2=a+2,D_800BE2F3=a+3,D_800BE2F4=a+4,D_800BE358=a+104,D_800BE900=0x90100000+j*0x100,D_80082BBC=0x90110000+j*0x100,jtbl_80095A00_game=0x90120000+j*0x100,func_151DD3A0=entry+0x10000,func_15007168=entry+0x20000,func_151DCFD8=entry+0x30000,func_151DD140=entry+0x40000);rps,rh=codes('rebase-'+str(j),entry,s)
  for match,fail,alias in itertools.product((False,True),(-1,0,13),(0,1)):
   c=Case(match=match,fail=fail,record_alias=alias,busy=2);initial=fixture(c,s);ms=[]
   for ws in rps:m=Oracle(ws,initial,c,s,entry,rh).run();check(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebases+=1
 return dict(cases=count,executions=count*3,body_words=57,frame=24,guards=10,bindings=14,original_transfer_words=45,original_defaults_words=69,all_target_and_helper_words_exercised=True,root_access_cuts=cuts,delay_cuts=delays,rebase_cases=rebases,rebase_layouts=3,partial_read_failure_positions=[0,1,7,13],busy_polls=[0,2,3],reset_destination_layouts=2,complete_cross_image_RAM_registers_and_trace=True,independent_public_RAM_protocol_and_observations=True,hardware_IO_claimed=False,private_only=True,matching_credit=0)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ws=struct.unpack_from('>4I',rom,0x49B64);assert ws==(0x0C000000|((ENTRY>>2)&0x3FFFFFF),0,0x1000000B,0)
 literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',(r/'conker/asm/48FD0.s').read_text())};assert list(ws)==[literal[0x1501C6B4+4*i]for i in range(4)]
 assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==struct.pack('>I',ws[0])]==[0x49B64]
 assert not any(rom[i:i+4]==struct.pack('>I',ENTRY)for i in range(0,len(rom)-3,4))
 ps,h=codes('caller');count=0
 for c in itertools.islice(cases(),0,None,23):
  initial=fixture(c);want,calls,obs=reference(initial,c);ms=[]
  for program in ps:
   connected=dict(h);connected.update(zip(range(ENTRY,ENTRY+228,4),program));connected[0x1501C6EC]=0;m=Oracle(ws,initial,c,entry=0x1501C6B4,connected=connected);m.code=WindowCode(dict(m.code),m);m.code.ends=(0x1501C6EC,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller exit')
   assert public(m.memory)==public(want) and m.calls==[(ENTRY,()),*calls] and m.observations==[(ENTRY,block(initial,SYMS)),*obs];ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,parent='func_1501C57C',parent_source='conker/src/game/generated_48FD0.c',window_entry='0x1501C6B4',window_ROM='0x49B64',window_words=4,window_exit='0x1501C6EC',arguments=0,return_ignored=True,full_parent_claimed=False)
def controls(source):
 call='    func_151DD3A0(&D_800BE900, 0x44, D_800BE2F0.bytes, 0x70);'
 return dict(wrong_first_weight=source.replace('(checksum << 2)','(checksum << 1)'),wrong_second_weight=source.replace('D_800BE2F3 << 3','D_800BE2F3 << 2'),signed_seed=source.replace('checksum = D_800BE2F2;','checksum = (s8)D_800BE2F2;'),wrong_constant=source.replace('+ 0xCC','+ 0xCD'),wrong_shift=source.replace('(index & 3)','(index & 7)'),short_loop=source.replace('index < 104','index < 100'),long_loop=source.replace('index < 104','index < 112'),wrong_test=source.replace('checksum != D_800BE2F0.checksum','checksum == D_800BE2F0.checksum'),missing_defaults=source.replace('        func_15007168();','        (void)0;'),wrong_command=source.replace('0x44, D_800BE2F0.bytes','0x45, D_800BE2F0.bytes'),wrong_length=source.replace('D_800BE2F0.bytes, 0x70','D_800BE2F0.bytes, 0x68'),early_checksum=source.replace(call,'').replace('    if (checksum !=',call+'\n    if (checksum !='),error_bypasses_checksum=source.replace(call,'    if (func_151DD3A0(&D_800BE900, 0x44, D_800BE2F0.bytes, 0x70) != 0) return;'))
def compiled_controls():
 selected=(o/'selected-semantic-input.c').read_text();rows={};_,helpers=codes('control')
 corpus=list(itertools.islice(cases(),0,None,17))
 for name,text in controls(selected).items():
  assert text!=selected;obj,diag=compile_owner(r,o,text,'negative-'+name);assert not diag;ws=linked(obj,'negative-linked-'+name)
  for k,c in enumerate(corpus):
   initial=fixture(c);m=Oracle(ws,initial,c,connected=helpers).run();want,calls,obs=reference(initial,c)
   if(public(m.memory),m.calls,m.observations)!=(public(want),calls,obs):rows[name]=k;break
  else:raise AssertionError(('Ineffective semantic control',name))
 return dict(count=len(rows),effective_IDO_controls=rows,compiler_or_oracle_errors_accepted=False)

def native_source(selected):
 head,body=selected.split('/* Read the save block',1);body='/* Read the save block'+body
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(SaveBlock33990)==112&&sizeof(OSMesgQueue)==24,"SDK layouts");
static struct {u32 left[4];SaveBlock33990 block;u32 right[4];}actual,expected;
static SaveBlock33990 input;
static OSMesgQueue queue;
static u8 records[116],expectedRecords[116];
static u32 effectMode,readCalls,resetCalls,error,failed,writeFailed,aliasMode;
static u8 beforeBlock[112];
#define D_800BE2F0 actual.block
#define D_800BE2F2 actual.block.bytes[2]
#define D_800BE2F3 actual.block.bytes[3]
#define D_800BE900 queue
static void mutation(SaveBlock33990*b){if(effectMode&1)b->checksum=0xF00D;if(effectMode&2)b->bytes[2]^=0x80;if(effectMode&4)b->bytes[103]^=0x55;}
static u32 total(const SaveBlock33990*b){static const u32 weights[4]={1,2,4,8};u32 i,v=204+4u*b->bytes[2]+8u*b->bytes[3];for(i=4;i<104;i++)v+=weights[i%4]*b->bytes[i];return v&65535u;}
static void defaults(SaveBlock33990*b,u8*p){u32 i;static const s32 value[10]={3,5,5,-1,-1,20,-1,20,3,3};for(i=0;i<104;i++)b->bytes[i]=0;for(i=0;i<10;i++){p[10*i+1]=3;p[10*i+2]=i==5?0:10;p[10*i+3]=2;p[10*i+4]=1;p[10*i+9]=0;if(value[i]>=0)p[10*i+5]=(u8)value[i];}}
__attribute__((noinline)) s32 func_151DD3A0(OSMesgQueue*q,u8 command,u8*dest,s32 length){u32 i,n=(u32)length<112u?(u32)length:112u;readCalls++;if(q!=&queue||command!=68||dest!=actual.block.bytes||length!=112)error=1;for(i=0;i<112;i++)if(actual.block.bytes[i]!=beforeBlock[i])error=2;if(failed<14){u32 limit=8*(failed+writeFailed);if(limit<n)n=limit;}for(i=0;i<n;i++)actual.block.bytes[i]=input.bytes[i];mutation(&actual.block);return failed<14?(s32)0x80000000u:0;}
s32 func_15007168(void){resetCalls++;defaults(&actual.block,aliasMode?records+8:actual.block.bytes+4);return 10;}
'''
 for name,b in dict(selected=body,**controls(body)).items():text+=b.replace('void '+F,'static void '+name)+'\n'
 text+=r'''
typedef void(*Update)(void);
static int check(Update update){u32 n,k,i,copied,h,wantReset;u8*p=(u8*)&actual,*e=(u8*)&expected;
static const u32 effects[8]={0,0,1,2,4,7,0,7};
for(n=0;n<65536;n++)for(k=0;k<8;k++){
 effectMode=effects[k];failed=k<2?14:k<4?0:k<6?7:13;writeFailed=(k>>1)&1;aliasMode=(k>>2)&1;
 for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n+k*17);
 for(i=0;i<116;i++)records[i]=expectedRecords[i]=(u8)(i*19+n+k);
 for(i=0;i<112;i++){u32 value=n%5==0?0:n%5==1?255:n%5==2?i*7+n:n%5==3?1u<<(i&7):(i*37+n)^0x80;input.bytes[i]=(u8)value;}
 input.bytes[2]=(u8)n;input.bytes[3]=(u8)(n>>8);
 copied=failed==14?112:8*(failed+writeFailed);
 for(i=0;i<sizeof(actual);i++)e[i]=p[i];for(i=0;i<copied;i++)expected.block.bytes[i]=input.bytes[i];h=total(&expected.block)^(k&1);
 actual.block.checksum=(u16)(copied?h^0x5555:h);input.checksum=(u16)(copied?h:h^0x5555);
 for(i=0;i<112;i++)beforeBlock[i]=actual.block.bytes[i];
 for(i=0;i<sizeof(actual);i++)e[i]=p[i];for(i=0;i<copied;i++)expected.block.bytes[i]=input.bytes[i];mutation(&expected.block);
 wantReset=total(&expected.block)!=expected.block.checksum;if(wantReset)defaults(&expected.block,aliasMode?expectedRecords+8:expected.block.bytes+4);
 readCalls=resetCalls=error=0;update();if(error||readCalls!=1||resetCalls!=wantReset)return 0;
 for(i=0;i<sizeof(actual);i++)if(p[i]!=e[i])return 0;for(i=0;i<116;i++)if(records[i]!=expectedRecords[i])return 0;
}
return 1;}
static int run(void){if(!check(selected))return 1;
'''
 for i,name in enumerate(controls(body),2):text+='if(check('+name+'))return '+str(i)+';\n'
 return text+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def native_suite():
 selected=(o/'selected-semantic-input.c').read_text();p=o/'native.c';p.write_text(native_source(selected));profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=o/('native-'+opt[1:]);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,UBSan=True,cases=524288)
 return dict(cases_per_profile=524288,all65536_seed_pairs_through_full_read=True,negative_controls=13,profiles=profiles,helper_status_ignored_correctly=True,partial_read_and_helper_mutations=True,full_block_canaries_and_separate_records_checked=True,hardware_IO_claimed=False)

def guard_suite():
 import tools.pad_generated_object as pad
 sys.modules.setdefault('pad_generated_object',pad)
 from tools.pad_c_object import emit_padded_assembly
 rows=json.loads((o/'new-guard-rows.json').read_text());before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();assert len(rows)==10
 columns=next(csv.reader(io.StringIO(before.decode())));count=0
 for i in range(10):
  for field in ('expected','expected_relocations'):
   bad=[dict(v)for v in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else'R_MIPS_26:foreign';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=columns,lineterminator='\n').writerows(bad);p=o/('bad-guards-%d-%s.csv'%(i,field));p.write_bytes(before+stream.getvalue().encode())
   try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_33990',word_patches_path=p)
   except ValueError:pass
   else:raise AssertionError('Ineffective padder control')
   count+=1
 def dag(words):
  regs=[('reg',i)for i in range(32)];regs[0]=('const',0)
  def operation(op,a,b):
   if op=='or' and b==('const',0):return a
   if op=='or' and a==('const',0):return b
   return(op,*sorted((a,b),key=repr))if op in('or','add')else(op,a,b)
  for w in words:
   op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
   if op==15:regs[rt]=('const',(w&65535)<<16)
   elif op==9:regs[rt]=operation('add',regs[rs],('const',((w&65535)^32768)-32768))
   elif op==12:regs[rt]=operation('and',regs[rs],('const',w&65535))
   elif op==0 and fn in(33,37):regs[rd]=operation('add'if fn==33 else'or',regs[rs],regs[rt])
   else:raise AssertionError(('Non-register guard operation',hex(w)))
   regs[0]=('const',0)
  return regs
 for j,(entry,a)in enumerate(((ENTRY,SYMS['D_800BE2F0']),(0x17007FFC,0x90017FFC),(0x2500FFFC,0x9001FFFC),(0x15008000,0x90028000))):
  s=dict(SYMS,D_800BE2F0=a,D_800BE2F2=a+2,D_800BE2F3=a+3,D_800BE2F4=a+4,func_151DD3A0=entry+0x10000,func_15007168=entry+0x20000);a_words=linked(o/('original-'+F+'.o'),'guard-original-'+str(j),entry=entry,s=s);b_words=linked(o/'selected-final.o','guard-raw-'+str(j),entry=entry,s=s)
  for start,end in ((72,84),(100,108),(128,144)):
   left,right=a_words[start//4:end//4],b_words[start//4:end//4];assert sorted(left)==sorted(right)and dag(left)==dag(right),(j,start)
  a,b=a_words[49],b_words[49];assert a>>26==b>>26==20 and a&65535==b&65535 and(a>>21&31,a>>16&31)==(b>>16&31,b>>21&31)
 return dict(guards=10,actual_padder_rejections=count,closed_windows=[[72,84],[100,108],[128,144]],GNU_alias_layouts=4,all32_register_DAGs_equal=True,operation_multisets_equal=True,commutative_equality_branch_word=49,memory_or_control_in_register_windows=0,insertions=0,omissions=0,inherited_prefix_preserved=True)
