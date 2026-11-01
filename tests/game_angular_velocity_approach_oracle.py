"""Angular approach semantics, closed guards, original dispatch and native controls."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_view_fov_transfer import fp
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,STATE,TABLE,SCRIPT=0x15116D7C,0x30000,0x80088C90,0x70000
ANGLES=(-1080.,-360.,-1.,-0.,0.,0.25,359.,360.,720.,1080.,1e20,-1e20)
VELOCITIES=(-64.,-1.,-0.,0.,0.25,1.,64.,128.)
SCALES=(0,1,-1,256,-256,65536,-65536,2147483647,-2147483648)
TICKS=(0,1,-1,30,-30,2147483647,-2147483648)
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
def symbols(i=0):return dict(D_800BE9E4=(0x800BE9E4,0x3407FFC,0x2428000)[i])
def base(c,s):return (STATE,s['D_800BE9E4'],s['D_800BE9E4']-0x60)[c.alias]
def public(m):return{a:b for a,b in m.items() if not STACK-512<=a<STACK+512}
def fixture(c,s):
 b=base(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)}
 m.update({b+i:0xA5 for i in range(-16,192)});put(m,s['D_800BE9E4'],TICKS[(c.index//7)%len(TICKS)]&0xFFFFFFFF)
 put(m,b+0x3C,SCALES[c.index%len(SCALES)]&0xFFFFFFFF)
 for j in range(3):
  put(m,b+4*j,bits(ANGLES[(c.index+j*3)%len(ANGLES)]));put(m,b+0x60+4*j,bits(VELOCITIES[(c.index//3+j)%len(VELOCITIES)]));put(m,b+0x7C+4*j,bits(VELOCITIES[(c.index//5+j*3)%len(VELOCITIES)]))
 return m
def reference(initial,c,s):
 m=dict(initial);b=base(c,s);step=fp(bits(float(signed(read(m,b+0x3C)))),bits(0.00390625),'mul');ticks=bits(float(signed(read(m,s['D_800BE9E4']))))
 for j in range(3):
  v,t,a=b+0x60+4*j,b+0x7C+4*j,b+4*j;speed,desired=read(m,v),read(m,t)
  if floating(speed)!=floating(desired):
   if floating(speed)>floating(desired):
    speed=fp(speed,step,'sub');put(m,v,speed)
    if floating(speed)<floating(read(m,t)):put(m,v,read(m,t))
   else:
    speed=fp(speed,step,'add');put(m,v,speed)
    if floating(speed)>floating(read(m,t)):put(m,v,read(m,t))
  angle=fp(read(m,a),fp(read(m,v),ticks,'mul'),'add');put(m,a,angle)
  if floating(angle)<0:put(m,a,fp(angle,bits(360.),'add'))
  elif floating(angle)>=360.:put(m,a,fp(angle,bits(360.),'sub'))
 return public(m)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;super().__init__(words,memory,c,entry=entry,s={},arguments=(base(c,s),),connected=connected);self.before_f=self.f[:]
 def record_call(self,t):assert t==ENTRY;self.calls.append((t,tuple(self.arguments(1))))
 def hook(self,t):raise AssertionError(('Unexpected angular helper',hex(t)))
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>74I',sections(p.with_suffix('.elf'))['.text'][1][:296]))
def programs(i):
 s=symbols(i);entry=(ENTRY,0x17038000,0x1F00FFFC)[i]
 ps=[link(o/n,'angular-program-%d-%d'%(i,j),entry,s)for j,n in enumerate(('original-func_15116D7C.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o'))]
 raw=ps[-1][:]
 for at,a,b in source.NEW_GUARDS:assert ps[-1][at//4]==a;ps[-1][at//4]=b
 assert all(v==ps[0]for v in ps)
 return s,entry,ps+[raw]
def state(m):return(m.memory,m.r,m.f,m.trace,m.calls,m.hi,m.lo,m.condition,m.current_pc,m.delay_of,m.all_accesses)
def compare(c,p):
 s,entry,ps=p;initial=fixture(c,s);expected=reference(initial,c,s);models=[]
 for words in ps:
  m=Oracle(words,initial,c,s,entry).run();assert public(m.memory)==expected,(c,[(hex(a),m.memory.get(a),expected[a])for a in expected if m.memory.get(a)!=expected[a]][:12]);models.append(m)
  assert all(m.r[k]==m.before[k]for k in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 assert all(state(v)==state(models[0])for v in models[:4])
 return models[0]
def guest():
 count=0;seen=set();p0=None
 for i in range(3):
  p=programs(i)
  if not i:p0=p
  for index,alias,phase in itertools.product(range(512 if i==0 else 128),range(3),(0,8)):
   m=compare(Case(index,alias,phase),p);seen.update(m.visits);count+=1
 missing={ENTRY+4*j for j in range(74)}-seen
 assert missing=={ENTRY+0xA0,ENTRY+0x100},[hex(v)for v in missing]
 return dict(cases=count,executions=count*5,rebases=3,all_72_reachable_words_executed=True,two_unreachable_branch_likely_duplicates=['0xA0','0x100'],three_exact_objects_and_guarded_isolated_C_full_state_equal=True,unguarded_C_public_memory_and_saved_registers_equal=True,global_alias_layouts=3,integer_extremes_and_signed_zero=True),p0
def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(1),Case(37),Case(93,1,8),Case(211,2)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing angular access fault')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)
class PoisonCode(WindowCode):
 def __getitem__(self,pc):
  if pc==self.owner.return_pc:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
  return super().__getitem__(pc)
def callers(p):
 rom=(r/'conker/conker.us.bin').read_bytes();s,entry,ps=p;seen=set();count=0
 windows=((0x15113EE0,0x141390,7,(0x15113EB4,0x15113EFC),0x15113EF0),(0x15113FB8,0x141468,9,(0x15113FDC,),0x15113FC8))
 for va,off,n,ends,return_pc in windows:
  body=struct.unpack_from('>%dI'%n,rom,off)
  for index,poison,loop in itertools.product((0,1,7,37,93,211,255,511),(0,1,0x80000000,0xFFFFFFFF),(0,1)):
   c=Case(index);initial=fixture(c,s);put(initial,STATE+0x38,ENTRY);put(initial,0x800D23C0,0x60000);put(initial,0x60002,0x1234,2);expected=reference(initial,c,s)
   for words in ps:
    connected=dict(zip(range(entry,entry+296,4),words));m=Oracle(body,initial,c,s,va,connected);m.r[16]=STATE;m.r[17]=0x60000;m.r[18]=loop;m.r[23]=0;m.r[30]=0;m.before=m.r[:];m.return_pc=return_pc;m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    assert public(m.memory)==expected and m.calls==[(ENTRY,(STATE,))]and m.poison_hits==1,(hex(va),c,m.calls)
    assert m.r[2]==poison
    if va==windows[0][0]:assert m.r[30]==1 and m.r[17]==0x600A0
    else:assert m.r[4]==0x1234 and m.r[5]==0x60000 and m.r[6]==2
    seen.update(m.visits)
   count+=1
  assert all(va+4*j in seen for j in range(n))
 return dict(cases=count,executions=count*5,original_window_words=[7,9],both_original_JALR_sites_executed=True,return_poisons=4,void_result_ignored=True,larger_dispatcher_not_fully_emulated=True)
def installer():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>22I',rom,0xCC06C);entry=0x1509EBBC;c=Case();s=symbols();m=fixture(c,s);m.update({SCRIPT+i:0xA5 for i in range(32)})
 for j in range(3):put(m,TABLE+0x384+j*4,struct.unpack_from('>I',rom,0x22DAD4+j*4)[0])
 put(m,SCRIPT+8,75);expected=dict(m);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0);expected[STATE+0x92]=0
 instance=Oracle(body,m,c,s,entry);instance.r[16]=SCRIPT;instance.r[2]=STATE;instance.before=instance.r[:];instance.code=WindowCode(instance.code,instance);instance.code.ends=(0x1509ED5C,)
 try:instance.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing installer boundary')
 assert public(instance.memory)==public(expected)
 assert all(entry+4*j in instance.visits for j in range(22))
 return dict(original_words=22,table_row=75,callback_field='0x38',record_pointer_callback_installed=True,all_words_executed=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom)
 q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY])
 assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22DAD4]),q
 q.update(callback_table='D_80088C90',row=75,callback_field='0x38',ABI='void(u8 *state)',original_JALR_sites=['0x15113EE8','0x15113FC0']);(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n');return q
def native():
 selected=source.SELECTED
 controls=(('unsigned-step',selected.replace('(s32 *)(state + 0x3C)','(u32 *)(state + 0x3C)')),
 ('step-times-ticks',selected.replace('    s32 offset = 0;','    s32 offset = 0;').replace('    do {','    maxStep *= ticks;\n    do {')),
 ('wrong-approach-factor',selected.replace('0.00390625f','0.0078125f')),
 ('missing-down-clamp',selected.replace('if (*velocity < *desired)','if (0)')),
 ('missing-up-clamp',selected.replace('if (*velocity > *desired) {\n                    *velocity =','if (0) {\n                    *velocity =')),
 ('wrong-axis-count',selected.replace('offset != 12','offset != 8')),
 ('wrong-wrap-equality',selected.replace('*angle >= 360.0f','*angle > 360.0f')),
 ('wrong-angle-direction',selected.replace('*angle += *velocity * ticks','*angle -= *velocity * ticks')))
 assert all(v!=selected for _,v in controls)
 def array(a):return '{'+','.join('0x%Xu'%v for v in a)+'}'
 def image(m):
  b=bytearray(m[STATE+j]for j in range(160))
  for at in(0,4,8,0x3C,0x60,0x64,0x68,0x7C,0x80,0x84):b[at:at+4]=b[at:at+4][::-1]
  return b
 rows=[]
 for index in range(2048):
  c=Case(index);m=fixture(c,symbols());expected=reference(m,c,symbols());rows.append('{0x%Xu,%s,%s}'%(read(m,symbols()['D_800BE9E4']),array(image(m)),array(image(expected))))
 code=source.HEADERS+r'''
typedef struct{u32 ticks;u8 input[160],expected[160];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record record;static u8 *state;
s32 D_800BE9E4;
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_15116D7C(', 'candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  D_800BE9E4=(s32)cases[n].ticks;for(k=0;k<192;k++)record.bytes[k]=0xA5;
  for(k=0;k<160;k++)state[k]=cases[n].input[k];candidates[j](state);failed=0;
  for(k=0;k<192;k++)if(record.bytes[k]!=(k>=16&&k<176?cases[n].expected[k-16]:0xA5))failed=1;
  if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }
 return killed==255u?0:3;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 result=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode)
  result.append(dict(profile=opt,cases=len(rows),UBSan=True,canaries=True,controls=[n for n,_ in controls],all_eight_controls_effective=True))
 return result
def qualify(root,output,core):
 global r,o,source
 r,o,source=root,output,core
 fingerprint=source.sha(b''.join((o/n).read_bytes()for n in('qualified-padded.o','selected-final.o','first-linked.elf'))+Path(__file__).read_bytes()+source.SELECTED.encode())
 saved=o/'runtime-qualification.json'
 if saved.exists():
  q=json.loads(saved.read_text())
  if q.get('fingerprint')==fingerprint:return q
 census();g,p=guest();q=dict(fingerprint=fingerprint,guest=g,faults=faults(p),callers=callers(p),installer=installer(),native=native())
 saved.write_text(json.dumps(q,indent=2)+'\n');return q
