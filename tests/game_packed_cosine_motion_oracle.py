"""Packed cosine motion: byte snapshots, live phases/ticks and original cosine."""
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
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.tests.test_game_cosine_match import reference as cosine_reference
from tools.tests.test_game_trig_match import COS_GLOBALS
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=source=None
ENTRY,COS,STATE,TABLE,SCRIPT=0x151163C0,0x15047C00,0x30000,0x80088C90,0x70000
PHASES=(0,1,65535,0x7FFFFFFF,0x80000000,0xFFFFFFFF,0x12345678,0xFFFF0001)
half=lambda n:((n&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 index:int=0
 alias:int=0
 phase:int=0
 mode:int=0
def symbols(i=0,alias=0):
 s=dict(cosf=(COS,0x17148000,0x17248000)[i],D_800A2FB0=(0x800A2FB0,0x3417FFC,0x2428000)[i],D_800A2FB4=(0x800A2FB4,0x3428000,0x2437FFC)[i],D_800BE9E4=(0x800BE9E4,0x3437FFC,0x2448000)[i])
 if alias==1:s['D_800BE9E4']=STATE+0x7C
 elif alias==2:s['D_800A2FB4']=STATE+0x18
 elif alias==3:s['D_800BE9E4']=STATE
 return s
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def packed(c):return(c.index&255)|(((c.index*17+1)&255)<<8)|(((c.index*37+255)&255)<<16)|(((c.index*63+128)&255)<<24)
def fixture(c,s):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};m.update({STATE+i:0xA5 for i in range(-16,192)})
 put(m,s['D_800BE9E4'],(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF)[(c.index//2)%5]);put(m,s['D_800A2FB0'],0x38C90FDB);put(m,s['D_800A2FB4'],0x38C90FDB)
 for at,v in((0,bits((-1000.,-0.,0.,0.25,360.)[c.index%5])),(0x18,bits(0.75)),(0x3C,packed(c)),(0x7C,PHASES[c.index%8]),(0x80,PHASES[(c.index*3+1)%8])):put(m,STATE+at,v)
 put(m,STATE+0x12,(-32768,-1,0,32767)[c.index%4]&65535,2)
 return m
def provider(c,ordinal):return(0,0x80000000,bits(1.),bits(-1.),bits(0.5),bits(-0.25),0x3EAAAAAB,1)[(c.index+ordinal*3)%8]
def effect(m,c,s,ordinal):
 if not ordinal and c.mode&1:
  put(m,STATE+0x3C,0xAA558001);put(m,STATE+0x12,0xFFEF,2);put(m,STATE,bits(-10.));put(m,STATE+0x7C,0xFFFFFFFE);put(m,STATE+0x80,0x12345678);put(m,s['D_800A2FB4'],bits(0.5));put(m,s['D_800BE9E4'],0xFFFFFFF1)
 if ordinal==1 and c.mode&2:
  put(m,STATE+0x7C,0x7FFFFFFE);put(m,STATE+0x80,0x80000002);put(m,STATE+0x12,0x8000,2);put(m,STATE,bits(-70.));put(m,s['D_800BE9E4'],3);put(m,s['D_800A2FB0'],bits(-0.125))
def reference(initial,c,s,actual=False):
 m=dict(initial);word=read(m,STATE+0x3C);amplitude=bits(float(word&255));angleAmplitude=fp(bits(float(word>>8&255)),bits(1.40625),'mul');first,second=word>>16&255,word>>24&255;oldY=half(read(m,STATE+0x12,2));oldAngle=read(m,STATE);calls=[]
 arg=fp(bits(float(signed(read(m,STATE+0x7C)))),read(m,s['D_800A2FB0']),'mul');calls.append((s['cosf'],(arg,)));answer=cosine_reference(arg)if actual else provider(c,0)
 if not actual:effect(m,c,s,0)
 put(m,STATE+0x18,fp(answer,amplitude,'mul'))
 arg=fp(bits(float(signed(read(m,STATE+0x80)))),read(m,s['D_800A2FB4']),'mul');calls.append((s['cosf'],(arg,)));answer=cosine_reference(arg)if actual else provider(c,1)
 if not actual:effect(m,c,s,1)
 angle=fp(answer,angleAmplitude,'mul');phase1,phase2=read(m,STATE+0x7C),read(m,STATE+0x80);put(m,STATE,angle)
 put(m,STATE+0x7C,(phase1+first*read(m,s['D_800BE9E4']))&0xFFFFFFFF)
 put(m,STATE+0x80,(phase2+second*read(m,s['D_800BE9E4']))&0xFFFFFFFF)
 put(m,STATE+0x5C,(half(read(m,STATE+0x12,2))-oldY)&65535,2);put(m,STATE+0x60,fp(angle,oldAngle,'sub'))
 return public(m),calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s,entry,connected=None):
  self.c,self.s=c,s;self.ordinal=0;super().__init__(words,memory,c,entry=entry,s={},arguments=(STATE,),connected=connected);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(7,13):self.f[w>>6&31]=(self.f[w>>11&31]^0x80000000)if w&63==7 else trunc(self.f[w>>11&31])
  else:super().execute(w)
 def record_call(self,t):
  if t==ENTRY:a=tuple(self.arguments(1))
  else:assert t==self.s['cosf'],hex(t);a=(self.f[12],)
  self.calls.append((t,a))
 def hook(self,t):
  assert t==self.s['cosf'];answer=provider(self.c,self.ordinal);effect(self.memory,self.c,self.s,self.ordinal);self.ordinal+=1
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for k in(1,2,3,*range(4,16),24,25):self.r[k]=0xA5000000+k
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.f[0]=answer
def link(obj,label,entry,s):
 text,fs,relocs=parse_object(obj);assembly,unknown=emit_function(text,fs[source.FUNCTION],relocs,source.FUNCTION,s);assert not unknown,unknown
 p=o/label;p.with_suffix('.s').write_text(assembly);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>83I',sections(p.with_suffix('.elf'))['.text'][1][:332]))
def programs(i,alias=0):
 s=symbols(i,alias);entry=(ENTRY,0x17038000,0x1F00FFFC)[i];ps=[link(o/n,'packed-program-%d-%d-%d'%(i,alias,j),entry,s)for j,n in enumerate(('original-func_151163C0.o','qualified-padded.o','make-shadow/src/game/generated_142560.c.o','selected-final.o'))];raw=ps[-1][:]
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
 missing=set(range(ENTRY,ENTRY+332,4))-seen;assert missing=={ENTRY+0x4C,ENTRY+0x50,ENTRY+0x54},[hex(v)for v in missing]
 return dict(cases=count,executions=count*5,rebases=3,all_80_reachable_words_executed=True,unreachable_unsigned_byte_correction_words=['0x4C','0x50','0x54'],all_256_values_in_each_packed_byte=True,global_alias_layouts=4,four_exact_programs_full_state_equal=True,unguarded_C_public_memory_and_preserved_ABI_equal=True),p0
def faults(p):
 s,entry,ps=p;count=0
 for c in(Case(),Case(7,mode=3),Case(128,phase=8,mode=1),Case(255,mode=2)):
  initial=fixture(c,s);full=compare(c,p)
  for cut in range(full.all_accesses):
   states=[]
   for words in ps[:4]:
    m=Oracle(words,initial,c,s,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Missing packed motion fault prefix')
    states.append(state(m))
   assert all(v==states[0]for v in states);count+=1
 return dict(prefixes=count,executions=count*4,exact_programs_full_state_equal=True,unguarded_C_fault_order_not_claimed=True)
def connected(p):
 before=(o/'before-conker_build_conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>88I',before,source.elf_slot_offset(before,COS,352));assert words==struct.unpack_from('>88I',rom,0x750B0);code=dict(zip(range(COS,COS+352,4),words));constants={a:struct.unpack_from('>I',before,source.elf_slot_offset(before,a,4))[0]for a in COS_GLOBALS};assert constants==COS_GLOBALS;count=0;seen=set()
 for alias in range(4):
  ps=programs(0,alias)
  for index,phase in itertools.product(range(128),(0,8)):
   c=Case(index,alias,phase);m=fixture(c,ps[0])
   for a,v in constants.items():put(m,a,v)
   result=compare(c,ps,code,m);seen.update(result.visits);count+=1
 return dict(cases=count,executions=count*5,original_cosine_slot_words=88,original_cosine_body_words=85,helper_body_words_executed=sum(COS+j*4 in seen for j in range(85)),original_constants_pinned=True,independent_finite_cosine_reference=True,full_FCSR_and_NaN_payloads_not_claimed=True)
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
    else:raise AssertionError('Missing packed callback boundary')
    assert public(m.memory)==expected and m.calls==[(ENTRY,(STATE,))]+calls and m.poison_hits==1 and m.r[2]==poison
    if va==windows[0][0]:assert m.r[30]==1 and m.r[17]==0x600A0
    else:assert m.r[4]==0x1234 and m.r[5]==0x60000 and m.r[6]==2
    seen.update(m.visits)
   count+=1
  assert all(va+j*4 in seen for j in range(n))
 return dict(cases=count,executions=count*5,original_window_words=[7,9],both_original_JALR_sites_executed=True,return_poisons=4,void_result_ignored=True,larger_dispatcher_not_fully_emulated=True)
def installer():
 rom=(r/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>22I',rom,0xCC06C);va=0x1509EBBC;c=Case();s=symbols();m=fixture(c,s);m.update({SCRIPT+i:0xA5 for i in range(32)})
 for j in range(3):put(m,TABLE+59*12+j*4,struct.unpack_from('>I',rom,0x22DA14+j*4)[0])
 put(m,SCRIPT+8,59);expected=dict(m);put(expected,STATE+0x38,ENTRY);put(expected,STATE+0x78,0);expected[STATE+0x92]=0;instance=Oracle(body,m,c,s,va);instance.r[16]=SCRIPT;instance.r[2]=STATE;instance.before=instance.r[:];instance.code=WindowCode(instance.code,instance);instance.code.ends=(0x1509ED5C,)
 try:instance.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing packed installer boundary')
 assert public(instance.memory)==public(expected)and all(va+j*4 in instance.visits for j in range(22))
 return dict(original_words=22,table_row=59,callback_field='0x38',all_words_executed=True)
def census():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>%dI'%(len(rom)//4),rom);q=dict(aligned_ROM_JALs=[4*i for i,w in enumerate(words)if w>>26==3 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_Js=[4*i for i,w in enumerate(words)if w>>26==2 and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)],aligned_ROM_pointer_literals=[4*i for i,w in enumerate(words)if w==ENTRY]);assert q==dict(aligned_ROM_JALs=[],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[0x22DA14]),q;q.update(callback_table='D_80088C90',row=59,callback_field='0x38',ABI='void(u8 *state)');(o/'caller-census.json').write_text(json.dumps(q,indent=2)+'\n')
def native():
 selected=source.SELECTED;controls=(('wrong-first-byte',selected.replace('0x3C)) & 0xFF','0x3C)) & 0x7F',1)),('signed-angle-byte',selected.replace('(f32)(u32)','(f32)(s8)')),('wrong-angle-scale',selected.replace('1.40625f','1.0f')),('wrong-second-phase',selected.replace('(f32)*(s32 *)(state + 0x80)','(f32)*(s32 *)(state + 0x7C)')),('cached-entry-ticks',selected.replace('(u32)D_800BE9E4','(u32)savedTicks').replace('    f32 angle;','    f32 angle;\n    s32 savedTicks = D_800BE9E4;')),('wrong-first-step',selected.replace('>> 16','>> 8')),('lost-y-snapshot',selected.replace('- previousY;','- *(s16 *)(state + 0x12);').replace('    s16 previousY = *(s16 *)(state + 0x12);\n','')),('lost-angle-snapshot',selected.replace('- previousAngle;','- *(f32 *)state;').replace('    f32 previousAngle = *(f32 *)state;\n','')))
 assert all(v!=selected for _,v in controls)
 def array(v):return'{'+','.join('0x%Xu'%x for x in v)+'}'
 def image(m):
  v=bytearray(m[STATE+j]for j in range(160))
  for at,n in((0,4),(0x12,2),(0x18,4),(0x3C,4),(0x5C,2),(0x60,4),(0x7C,4),(0x80,4)):v[at:at+n]=v[at:at+n][::-1]
  return v
 rows=[]
 for index,mode in itertools.product(range(512),range(4)):
  c=Case(index,mode=mode);s=symbols();m=fixture(c,s);expected,calls=reference(m,c,s);rows.append('{%d,%d,0x%Xu,%s,%s,%s,%s}'%(index,mode,read(m,s['D_800BE9E4']),array([a[1][0]for a in calls]),array([provider(c,0),provider(c,1)]),array(image(m)),array(image(expected))))
 code=source.HEADERS+r'''
typedef struct{u32 index,mode,ticks,args[2],returns[2];u8 input[160],expected[160];}Case;
static Case cases[]={'''+',\n'.join(rows)+r'''};
typedef union{u32 align[48];u8 bytes[192];}Record;
static Record record;static u8 *state;static Case *current;static u32 calls,error;
s32 D_800BE9E4;f32 D_800A2FB0,D_800A2FB4;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
f32 cosf(f32 x){u32 ordinal=calls++,mode=current->mode;if(ordinal>=2){error=1;return 0;}if(bits(x)!=current->args[ordinal])error=1;
 if(ordinal==0&&(mode&1)){*(u32*)(state+0x3C)=0xAA558001u;*(s16*)(state+0x12)=-17;*(f32*)state=-10.0f;*(u32*)(state+0x7C)=0xFFFFFFFEu;*(u32*)(state+0x80)=0x12345678u;D_800A2FB4=0.5f;D_800BE9E4=(s32)0xFFFFFFF1u;}
 if(ordinal==1&&(mode&2)){*(u32*)(state+0x7C)=0x7FFFFFFEu;*(u32*)(state+0x80)=0x80000002u;*(s16*)(state+0x12)=-32768;*(f32*)state=-70.0f;D_800BE9E4=3;D_800A2FB0=-0.125f;}
 return floating(current->returns[ordinal]);
}
'''
 for j,(_,body)in enumerate((('valid',selected),)+controls):code+=body.replace('func_151163C0(','candidate_%d('%j)+'\n'
 code+='static void (*candidates[])(u8*)={'+','.join('candidate_%d'%j for j in range(9))+'};\n'
 code+=r'''
static int run(void){u32 n,j,k,killed=0,failed;state=record.bytes+16;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<9;j++){
  current=&cases[n];calls=error=0;D_800BE9E4=(s32)current->ticks;D_800A2FB0=D_800A2FB4=floating(0x38C90FDBu);
  for(k=0;k<192;k++)record.bytes[k]=0xA5;for(k=0;k<160;k++)state[k]=current->input[k];candidates[j](state);failed=error||calls!=2;
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
