"""Random approach motion: captured command, live fields and original 64-bit RNG."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_bounce_random_sound_oracle import BounceSoundOracle
from tools.tests.test_game_random_selector_outputs_match import next_seed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,RANDOM,STATE,TABLE,SCRIPT,SEED=0x1511AF30,0x150ADA20,0x30000,0x80088C90,0x70000,0x800885B0
COEFFICIENTS={'D_800A3188':0x3C23D70A,'D_800A318C':0x3B03126F,'D_800A3190':0x3C23D70A,'D_800A3194':0x3ECCCCCD}
COMMANDS=(0,1,0xFFFFFFFF,17,0xFFFFFFEF,32767,0x7FFFFFFF,0x80000000)
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
 mode:int=0

def symbols(i=0,alias=0):
 s=dict(func_150ADA20=(RANDOM,0x17148000,0x17248000)[i])
 for j,n in enumerate(COEFFICIENTS):s[n]=int(n[2:],16)if not i else(0x3417FFC,0x2427FFC)[i-1]+j*0x8004
 if alias==1:s['D_800A318C']=STATE+0x84
 elif alias==2:s['D_800A3190']=STATE+0x80
 elif alias==3:s['D_800A3194']=STATE+0x84
 return s

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}

def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({STATE+i:0xA5 for i in range(-16,192)})
 for name,value in COEFFICIENTS.items():put(m,s[name],value)
 command=COMMANDS[c.index%8];put(m,STATE+0x3C,command)
 target=fp(fp(bits(75.),bits(float(signed(command))),'mul'),read(m,s['D_800A3188']),'mul')
 current=fp(target,bits((0.,-0.,.5,-.5,1.,-1.,2.,-2.)[(c.index//8)%8]),'add')
 for at,v in((0,bits(99.)),(0x7C,current),(0x80,bits((0.,-0.,1.,-1.,.25,-.5,3.,-3.)[c.index%8])),(0x84,bits((0.,1.,-2.,3.,-.25,.5,-3.,2.)[(c.index//3)%8]))):put(m,STATE+at,v)
 put(m,SEED,((c.index*0x123456781234567+1)^0xFEDCBA9876543210)&((1<<64)-1),8)
 return m

def provider(c):return(0,1,499,500,999,1000,1499,1500,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678)[c.index%12]

def effect(m,c,s):
 if c.mode&1:
  put(m,STATE+0x3C,7);put(m,STATE+0x7C,bits(-12.5));put(m,STATE+0x80,bits(-3.25));put(m,STATE+0x84,bits(4.5))
 if c.mode&2:
  put(m,STATE,bits(-70.));put(m,s['D_800A318C'],bits(.25));put(m,s['D_800A3190'],bits(-.5));put(m,s['D_800A3194'],bits(.125))

def reference(initial,c,s,actual=False):
 m=dict(initial);calls=[];command=bits(float(signed(read(m,STATE+0x3C))));target=fp(fp(bits(75.),command,'mul'),read(m,s['D_800A3188']),'mul');current=read(m,STATE+0x7C)
 if floating(target)!=floating(current):
  delta=fp(target,current,'sub')
  if abs(floating(delta))<1.:value=target
  else:value=fp(current,bits(-1. if floating(delta)<0. else 1.),'add')
  put(m,STATE+0x7C,value);put(m,STATE+0x80,0)
 else:
  calls.append((s['func_150ADA20'],()))
  if actual:
   seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);answer=seed&0xFFFFFFFF
  else:answer=provider(c);effect(m,c,s)
  sample=answer%1000
  if sample<500:
   v=fp(fp(fp(fp(bits(float(sample)),bits(5.),'mul'),command,'mul'),read(m,s['D_800A318C']),'mul'),read(m,s['D_800A3190']),'mul');put(m,STATE+0x84,v)
  resting=read(m,STATE+0x80);delta=fp(read(m,STATE+0x84),resting,'sub');put(m,STATE+0x80,fp(resting,fp(delta,read(m,s['D_800A3194']),'mul'),'add'))
 put(m,STATE,fp(read(m,STATE+0x7C),read(m,STATE+0x80),'add'))
 return public(m),calls

class Oracle(BounceSoundOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},connected=connected,args=(STATE,));self.before_f=self.f[:]
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(1))
  else:assert t==self.s['func_150ADA20'],hex(t);a=()
  self.calls.append((t,a))
 def hook(self,t):
  assert t==self.s['func_150ADA20'];answer=provider(self.c);effect(self.memory,self.c,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=answer

def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>83I',sections(p.with_suffix('.elf'))['.text'][1][:332]))
def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17038000,0x1F00FFFC)[i];ps=[link(o/n,'approach-program-%d-%d-%d'%(i,alias,j),entry,s)for j,n in enumerate(('original-func_1511AF30.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o'))];raw=ps[-1][:]
 for at,a,b in source.NEW_GUARDS:assert ps[-1][at//4]==a;ps[-1][at//4]=b
 assert all(v==ps[0]for v in ps)
 return s,entry,ps+[raw]
def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p,code=None,initial=None):
 s,entry,ps=p;initial=fixture(c,s)if initial is None else initial;expected,calls=reference(initial,c,s,code is not None);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry,code).run();assert(public(m.memory),m.calls)==(expected,calls),(c,m.calls,calls,[(hex(a),m.memory.get(a),expected[a])for a in expected if m.memory.get(a)!=expected[a]][:12]);models.append(m);assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 assert all(state(v)==state(models[0])for v in models[:4])
 return models[0]
def guest():
 count=0;seen=set();p0=None
 for i in range(3):
  for alias in range(4):
   p=programs(i,alias)
   if not i and not alias:p0=p
   for index,phase,mode in itertools.product(range(256 if i==0 else 64),(0,8),(0,3)):
    m=compare(Case(index,alias,phase,mode),p);seen.update(m.visits);count+=1
 missing=set(range(ENTRY,ENTRY+332,4))-seen;assert missing=={ENTRY+0x70},[hex(v)for v in missing]
 return dict(cases=count,executions=count*5,rebases=3,all_82_reachable_words_executed=True,unreachable_duplicate_zero_word='0x70',strict_snap_and_random_gate_branches=True,global_alias_layouts=4,four_exact_programs_full_state_equal=True,unguarded_C_public_memory_and_preserved_ABI_equal=True),p0
def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(3,mode=3),Case(16,phase=8,mode=1),Case(32),Case(40)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing random approach fault prefix')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)
def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>18I',before,source.elf_slot_offset(before,RANDOM,72));assert words==struct.unpack_from('>18I',rom,0xDAED0);code=dict(zip(range(RANDOM,RANDOM+72,4),words));seen=set();count=helpers=0
 for name,value in COEFFICIENTS.items():assert struct.unpack_from('>I',before,source.elf_slot_offset(before,int(name[2:],16),4))[0]==value
 for alias in range(4):
  ps=programs(0,alias)
  for index,phase in itertools.product(range(128),(0,8)):
   c=Case(index,alias,phase);result=compare(c,ps,code);seen.update(result.visits);count+=1;helpers+=len(result.calls)
 assert all(RANDOM+j*4 in seen for j in range(18))
 return dict(cases=count,executions=count*5,original_RNG_words=18,all_18_RNG_words_executed=True,original_RNG_invocations=helpers,original_coefficients_pinned=True,independent_64_bit_seed_reference=True,original_seed_store_verified=True,full_FCSR_and_NaN_payloads_not_claimed=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
def callers(p):
 rom=(r/'conker/conker.us.bin').read_bytes();s,entry,ps=p;count=0;seen=set();windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),(0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8))
 for va,off,n,ends,return_pc in windows:
  body=struct.unpack_from('>%dI'%n,rom,off)
  for index,poison,loop in itertools.product((0,1,7,63,128,255),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
   c=Case(index,mode=3);initial=fixture(c,s);put(initial,STATE+0x38,ENTRY);put(initial,0x800D23C0,0x60000);put(initial,0x60002,0x1234,2);expected,calls=reference(initial,c,s)
   for words in ps:
    code=dict(zip(range(entry,entry+332,4),words));m=Oracle(body,initial,c,s,va,code);m.r[16]=STATE;m.r[17]=0x60000;m.r[18]=loop;m.r[23]=0;m.r[30]=0;m.before=m.r[:];m.return_pc=return_pc;m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing random approach callback boundary')
    assert public(m.memory)==expected and m.calls==[(ENTRY,(STATE,))]+calls and m.poison_hits==1 and m.r[2]==poison
    if va==windows[0][0]:assert m.r[30]==1 and m.r[17]==0x600A0
    else:assert m.r[4]==0x1234 and m.r[5]==0x60000 and m.r[6]==2
    seen.update(m.visits)
   count+=1
  assert all(va+j*4 in seen for j in range(n))
 return dict(cases=count,executions=count*5,original_window_words=[7,9],both_original_JALR_sites_executed=True,return_poisons=4,void_result_ignored=True,larger_dispatcher_not_fully_emulated=True)
def installer():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>22I',rom,0xCC06C);va=0x1509EBBC;c=Case();s=symbols();m=fixture(c,s);m.update({SCRIPT+i:0xA5 for i in range(32)})
 for j in range(3):put(m,TABLE+52*12+j*4,struct.unpack_from('>I',rom,0x22D9C0+j*4)[0])
 put(m,SCRIPT+8,52);expected=dict(m);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0);expected[STATE+0x92]=0;instance=Oracle(body,m,c,s,va);instance.r[16]=SCRIPT;instance.r[2]=STATE;instance.before=instance.r[:];instance.code=WindowCode(instance.code,instance);instance.code.ends=(0x1509ED5C,)
 try:instance.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing random approach installer boundary')
 assert public(instance.memory)==public(expected)and all(va+j*4 in instance.visits for j in range(22))
 return dict(original_words=22,table_row=52,callback_field='0x38',all_words_executed=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY]);assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22D9C0]),q;q.update(callback_table='D_80088C90',row=52,callback_field='0x38',ABI='void(u8 *state)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')
def native():
 selected=source.SELECTED
 cached=selected.replace('    f32 resting;','    f32 resting = *(f32 *)(state + 0x80);').replace('        resting = *(f32 *)(state + 0x80);\n','')
 controls=(('wrong-target-scale',selected.replace('75.0f','74.0f')),('wrong-snap-threshold',selected.replace('fabsf(delta) < 1.0f','fabsf(delta) < 0.5f')),('wrong-step-sign',selected.replace('delta < 0.0f ? -1 : 1','delta < 0.0f ? 1 : -1')),('missing-offset-clear',selected.replace('*(f32 *)(state + 0x80) = 0.0f','*(f32 *)(state + 0x80) = 1.0f')),('signed-random-remainder',selected.replace('(u32)func_150ADA20() % 1000U','func_150ADA20() % 1000')),('inclusive-random-gate',selected.replace('sample < 500','sample <= 500')),('lost-command-snapshot',selected.replace('* 5.0f * command','* 5.0f * (f32)*(s32 *)(state + 0x3C)')),('cached-resting-offset',cached))
 assert all(v!=selected for _,v in controls)
 def array(v):return'{'+','.join('0x%Xu'%x for x in v)+'}'
 def image(m):
  v=bytearray(m[STATE+j]for j in range(160))
  for at in(0,0x3C,0x7C,0x80,0x84):v[at:at+4]=v[at:at+4][::-1]
  return v
 rows=[]
 for index,mode in itertools.product(range(512),range(4)):
  c=Case(index,mode=mode);sy=symbols();m=fixture(c,sy);expected,calls=reference(m,c,sy)
  rows.append('{%d,%d,0x%Xu,%d,%s,%s}'%(index,mode,provider(c),len(calls),array(image(m)),array(image(expected))))
 code=source.HEADERS.replace('#pragma intrinsic (fabsf)\n','')+r'''
typedef struct{u32 index,mode,random,expectedCalls;u8 input[160],expected[160];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record record;static u8 *state;static Case *current;static u32 calls,error;
f32 D_800A3188,D_800A318C,D_800A3190,D_800A3194;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
f32 fabsf(f32 x){union{u32 u;f32 f;}v;v.f=x;v.u&=0x7FFFFFFFu;return v.f;}
s32 func_150ADA20(void){u32 mode=current->mode;if(calls++)error=1;
 if(mode&1){*(s32*)(state+0x3C)=7;*(f32*)(state+0x7C)=-12.5f;*(f32*)(state+0x80)=-3.25f;*(f32*)(state+0x84)=4.5f;}
 if(mode&2){*(f32*)state=-70.f;D_800A318C=.25f;D_800A3190=-.5f;D_800A3194=.125f;}
 return (s32)current->random;
}
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_1511AF30(','candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];calls=error=0;D_800A3188=D_800A3190=floating(0x3C23D70Au);D_800A318C=floating(0x3B03126Fu);D_800A3194=floating(0x3ECCCCCDu);
  for(k=0;k<192;k++)record.bytes[k]=0xA5;for(k=0;k<160;k++)state[k]=current->input[k];candidates[j](state);failed=error||calls!=current->expectedCalls;
  for(k=0;k<192;k++)if(record.bytes[k]!=(k>=16&&k<176?current->expected[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode);result.append(dict(profile=opt,cases=len(rows),UBSan=True,canaries=True,all_eight_controls_effective=True,controls=[n for n,_ in controls]))
 return result

def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core;fingerprint=source.sha(b''.join((o/n).read_bytes()for n in('qualified-padded.o','selected-final.o','first-linked.elf'))+Path(__file__).read_bytes()+source.SELECTED.encode());saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),connected=connected(p),callers=callers(p),installer=installer(),native=native());saved.write_text(json.dumps(q,indent=2)+'\n');return q
