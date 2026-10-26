"""Direct packed command C: widths, lazy reads, real callbacks and literal image gates."""
import itertools,json,struct,subprocess,unittest
from pathlib import Path
from tools.experiments import game_packed_object_command_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
ENTRY=0x1509F284;P1=0x1509F660;P2=0x1509F77C;INPUT=0x30000;PACKET=0x800D2F60;TABLE=0x800884D4;COUNT=0x800D3840;EFFECT=0x31000

COMMANDS=(0,1,2,3,256,0x80000000,0xFFFFFFFF);VALUES=(0,1,0xFFF,0x1000,0x7FFF8000,0x80000000,0xFFFFFFFF,0x12345678)
def fixture(key=0,value=0):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
 for base,length in((INPUT-16,64),(PACKET-16,96),(TABLE,64),(COUNT-16,36),(EFFECT,16)):
  for i in range(length):m.setdefault(base+i,(i*13+0xA5)&255)
 for i,v in enumerate((key,0xDEADBEEF,value,value^0x80008000,(value+0x12345678)&0xFFFFFFFF,(value^0x87654321))):put(m,INPUT+4*i,v)
 put(m,TABLE+24,ENTRY);put(m,COUNT,0x12345678);return m
def public(m):return{a:v for a,v in m.items()if not STACK-0x400<=a<STACK+0x100}
def reference(memory,args,mode=0):
 m=dict(memory);unused,command,record=args;calls=[]
 if command in(0,1):calls=[(P1,(read(m,record+8)&4095,1-command))]
 elif command==2:calls=[(P2,((read(m,record)&0xFFFF0000)>>16,read(m,record+8)&4095,read(m,record+12),read(m,record+16),read(m,record+20)))]
 if calls and mode:put(m,EFFECT,mode^calls[0][0]);put(m,EFFECT+4,calls[0][1][-1])
 return m,int(command in(0,1,2)),calls
class Oracle(TimingOracle):
 def __init__(self,code,memory,args,phase=0,entry=ENTRY,connected=None,mode=0,script=False):
  self.trace=[];self.effect_mode=mode
  super().__init__(code,memory,phase=phase,entry=entry,arguments=args,connected=connected)
  if script:self.before[23]=self.before[31]
 def get(self,address,size):
  value=super().get(address,size)
  if self.own_instruction:self.trace.append(('R',address,size,value))
  return value
 def put(self,address,value,size):
  if self.recording and self.own_instruction:assert all(address+i in self.memory for i in range(size)),('unmapped store',address,size)
  super().put(address,value,size)
  if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
 def record_call(self,target):
  assert target in(ENTRY,P1,P2),hex(target)
  args=tuple(self.r[4:7])if target==ENTRY else tuple(self.r[4:6])if target==P1 else(*self.r[4:8],read(self.memory,self.r[29]+16))
  self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target in(P1,P2)
  args=self.calls[-1][1]
  if self.effect_mode:self.put(EFFECT,self.effect_mode^target,4);self.put(EFFECT+4,args[-1],4)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0x80000000|target

def compare(m,args,phase=0,mode=0):
 expected,result,calls=reference(m,args,mode);models=[Oracle(code,m,args,phase,mode=mode).run()for code in(truth,words)]
 for x in models:assert public(x.memory)==public(expected)and x.r[2]==result and x.calls==calls
 assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace
 return models
header=r'''typedef int s32;typedef unsigned int u32;typedef unsigned short u16;typedef short s16;typedef unsigned char u8;typedef float f32;
typedef struct{u32 fence0[4],record[6];f32 object[8];u32 fence1[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(u32)==4&&sizeof(s16)==2)?1:-1];
static State state,before;static u32 missing,lookup_count,lookup_id,toggle_count,toggle_kind,start_count,sink[10],bad;
static u8* func_1505EEF4(s32 index){lookup_count++;lookup_id=(u32)index;return missing?(u8*)0:(u8*)state.object;}
static void func_10010A3C(void *object){toggle_count++;toggle_kind=1;if(object!=(void*)state.object)bad=1;}
static void func_100109D0(void *object){toggle_count++;toggle_kind=0;if(object!=(void*)state.object)bad=1;}
static s32 func_1000F91C(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,s32 i,s32 j){start_count++;sink[0]=a;sink[1]=b;sink[2]=c;sink[3]=d;sink[4]=e;sink[5]=f;sink[6]=g;sink[7]=h;sink[8]=i;sink[9]=j;return (s32)0xFEDCBA98u;}
void func_1509F660(s32,s32);s32 func_1509F77C(u32,s32,s32,s32,s32);
'''
tail=r'''
static void prepare(u32 key,u32 value,u32 miss){u32 i;u8 *a=(u8*)&state,*b=(u8*)&before;
 for(i=0;i<sizeof(State);i++)a[i]=(u8)(i*13+0xA5);
 state.record[0]=key;state.record[1]=0xDEADBEEF;state.record[2]=value;state.record[3]=value^0x80008000u;state.record[4]=value+0x12345678u;state.record[5]=value^0x87654321u;
 state.object[5]=12.75f;state.object[6]=-3.5f;state.object[7]=0.0f;
 for(i=0;i<sizeof(State);i++)b[i]=a[i];missing=miss;lookup_count=lookup_id=toggle_count=toggle_kind=start_count=bad=0;
 for(i=0;i<10;i++)sink[i]=0xA5A5A5A5u;
}
static int unchanged(void){u32 i;u8*a=(u8*)&state,*b=(u8*)&before;for(i=0;i<sizeof(State);i++)if(a[i]!=b[i])return 0;return 1;}
static u32 signed16(u32 value){u32 low=value&65535u;return low<32768u?low:low|0xFFFF0000u;}
static int check_sink(u32 id,u32 value,u32 extra,u32 last){return sink[0]==id&&sink[1]==32767u&&sink[2]==signed16(value)&&sink[3]==0&&sink[4]==0&&sink[5]==12&&sink[6]==0xFFFFFFFDu&&sink[7]==0&&sink[8]==extra&&sink[9]==last;}
static int run(void){const u32 commands[]={0,1,2,3,256,0x80000000u,0xFFFFFFFFu};const u32 values[]={0,1,4095,4096,0x7FFF8000u,0x80000000u,0xFFFFFFFFu,0x12345678u};u32 c,k,v,miss,ret,command;
 for(c=0;c<7;c++)for(k=0;k<8;k++)for(v=0;v<8;v++)for(miss=0;miss<2;miss++){
  command=commands[c];prepare(values[k],values[v],command==2?0:miss);
  ret=func_1509F284((s32)0x87654321u,(s32)command,command<3?state.record:(u32*)0);
  if(ret!=(command<3)||!unchanged()||bad)return 23;
  if(command>=3){if(lookup_count||toggle_count||start_count)return 23;continue;}
  if(lookup_count!=1||lookup_id!=(state.record[2]&4095u))return 23;
  if(command<2){if(start_count||toggle_count!=(miss?0u:1u)||(!miss&&toggle_kind!=1-command))return 23;}
  else if(toggle_count||start_count!=1||!check_sink(state.record[0]>>16,state.record[3],state.record[4],state.record[5]))return 23;
 }
 for(k=0;k<8;k++)for(v=0;v<8;v++){
  prepare(0,0,0);ret=(u32)func_1509F77C(values[k],17,(s32)values[v],(s32)0x87654321u,-31);
  if(ret!=0xFEDCBA98u||lookup_count!=1||lookup_id!=17||start_count!=1||toggle_count||bad||!unchanged()||!check_sink(values[k]&65535u,values[v],0x87654321u,0xFFFFFFE1u))return 23;
 }return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
def native(label,wrapper,provider,opt):
 code=header+wrapper+'\n'+primary+'\n'+provider+tail;src=o/(label+opt+'.c');elf=src.with_suffix('.elf');src.write_text(code)
 p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector','-fno-builtin','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Werror=implicit-function-declaration','-Wl,-e,_start',str(src),'-o',str(elf)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(elf)],capture_output=True).returncode


class PackedObjectCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global words,truth,rom,text,selected,primary,fallback,o
        cls.out=ROOT/source.BUILD;cls.receipt={}
        cls.values=source.snapshot(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out)
        cls.obj,diagnostics=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+'\n'+source.SELECTED,'fresh-selected')
        if diagnostics:raise ValueError(diagnostics)
        raw,bindings=source.checked_payload(*source.payload(cls.obj))
        data,functions=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER)
        words=list(struct.unpack_from('>46I',data,functions[source.FUNCTION]['value']))
        rom=cls.values['conker/conker.us.bin'];truth=list(struct.unpack_from('>46I',rom,source.ROM))
        text=source.recovered_owner(cls.values[source.SOURCE].decode())
        def body(name):
            lo,hi=source.function_span(text,name);return text[lo:hi]
        selected,primary,fallback=(body(n)for n in(source.FUNCTION,'func_1509F660','func_1509F77C'))
        o=cls.out/'native32';o.mkdir(exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def test_01_direct_C_original_owner_actual_Make_and_installed_extent(self):
        self.assertEqual(words,truth)
        raw,bindings=source.checked_payload(*source.payload(self.obj))
        self.assertEqual(source.payload(self.out/'after-owner.o'),(raw,bindings))
        self.assertEqual(source.payload(self.out/'original-func_1509F284.o'),(raw,bindings))
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),16)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['words'],q['frame'],q['guards'],q['preserved_neighbors']),(46,40,0,16))
        self.assertEqual((self.out/'make-shadow/src/game/generated_CBDB0.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        self.assertEqual((self.out/'qualified-guards.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        if self.installed:source.audit(ROOT,self.out)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,ENTRY,184)
        m=fixture();self.assertNotEqual(Oracle(struct.unpack_from('>46I',old,at),m,(0,0,INPUT)).run().r[2],1)
        self.receipt.update(words=46,alignment_words=0,frame=40,guards=0,bindings=3,neighbors=16,provider_body_byte_identical=True,actual_Make_commands=3)
    def test_02_fullword_commands_packed_fields_lazy_reads_and_access_order(self):
        visits=set();count=0
        for command,key,value,phase,mode in itertools.product(COMMANDS,VALUES,VALUES,(0,8),(0,1,3)):
         m=fixture(key,value);models=compare(m,(0x87654321,command,INPUT if command<3 else 0),phase,mode);visits.update(models[0].visits);count+=1
        assert set(range(ENTRY,ENTRY+184,4))<=visits
        lazy=0
        for command in COMMANDS[3:]:
         m=fixture();m={a:v for a,v in m.items()if not INPUT-16<=a<INPUT+48};compare(m,(0,command,0));lazy+=1
        self.receipt.update(guest_cases=count,all46_words_visited=True,lazy_unknown_command_cases=lazy,exact_access_order=True)
    def test_03_native32_complete_wrapper_provider_narrowing_and_effective_controls(self):
        rows=[]
        for opt in('-O0','-O2','-O3'):
         code=native('selected',selected,fallback,opt);assert code==0,(opt,code);rows.append(dict(opt=opt,exit=code,wrapper_cases=896,direct_provider_narrowing_cases=64))
        controls={
         'toggle-mode':(selected.replace('record[2] & 0xFFF, 0','record[2] & 0xFFF, 1'),fallback),
         'identifier-mask':(selected.replace('record[2] & 0xFFF','record[2] & 0xFFFF'),fallback),
         'header-shift':(selected.replace('>> 16','>> 8'),fallback),
         'payload-signedness':(selected.replace('record[3], record[4], record[5]','record[3] & 0xFF, record[4], record[5]'),fallback),
         'payload-order':(selected.replace('record[3], record[4], record[5]','record[4], record[3], record[5]'),fallback),
         'last-argument':(selected.replace('record[3], record[4], record[5]','record[3], record[4], record[4]'),fallback),
         'handled-zero':(selected.replace('return 1;','return 0;'),fallback),
         'unknown-one':(selected.replace('    return 0;','    return 1;'),fallback),
         'provider-u16':(selected,fallback.replace('(u16) arg0','arg0')),
         'provider-s16':(selected,fallback.replace('(s16) arg2','arg2')),
        }
        for label,(wrapper,provider)in controls.items():
         assert(wrapper,provider)!=(selected,fallback),label;code=native(label,wrapper,provider,'-O2');assert code==23,(label,code)
        self.receipt.update(native_optimizations=rows,native_effective_controls=len(controls),trap_UBSan=True,provider_internal_narrowing_checked=True)
    def test_04_actual_variadic_and_script_callbacks_and_fired_fault_prefixes(self):
        # Real variadic callback caller, slot 6 of D_800884D4.
        caller=list(struct.unpack_from('>92I',rom,0xC9460));connected=dict(zip(range(ENTRY,ENTRY+184,4),words));callercount=0
        for n,index,command,phase in itertools.product((-1,0,1,2,3,4,5,7,8),(0,4095),COMMANDS,(0,8)):
         m=fixture(0x12345678,0xFEDCBA98);values=[0x81020304+i*0x01020304 for i in range(8)]
         for i,v in enumerate(values[1:]):put(m,STACK+phase+16+i*4,v)
         args=(n&0xFFFFFFFF,0xAB007000|index,command,values[0]);expected=dict(m);put(expected,PACKET,index);put(expected,PACKET+4,command)
         for i in range(max(0,n)):put(expected,PACKET+8+i*4,values[i])
         expected,result,calls=reference(expected,(index,command,PACKET),1);model=Oracle(caller,m,args,phase,0x1509BFB0,connected,mode=1).run()
         assert public(model.memory)==public(expected)and model.r[2]==result
         assert model.calls==[(ENTRY,(index,command,PACKET))]+calls;callercount+=1
        # Real script callback window, including zero-selector bypass and S7 link scratch.
        script=list(struct.unpack_from('>26I',rom,0xDB5DC));scriptcount=0
        for index,command,selector,phase in itertools.product((0,4095),COMMANDS,(0,7),(0,8)):
         m=fixture(0x12345678,0xFEDCBA98);put(m,INPUT,0x40000000|selector<<12|index);put(m,INPUT+4,command)
         expected,result,calls=reference(m,(0x40000000|index,command,INPUT),1)if selector else(m,0,[])
         model=Oracle(script,m,(INPUT,),phase,0x150AE12C,connected,mode=1,script=True).run()
         assert public(model.memory)==public(expected)and model.r[2]==result and model.r[23]==0xDEAD0000
         assert model.calls==([(ENTRY,(0x40000000|index,command,INPUT))]+calls if selector else[]);scriptcount+=1
        # Literal emitted access-prefix state, including provider-boundary clobbers.
        faultcount=0
        for command,phase in itertools.product((0,1,2,3),(0,8)):
         m=fixture(0xFEDCBA98,0x12345678);args=(0x12345678,command,INPUT);good=Oracle(truth,m,args,phase,mode=1).run()
         for cut in range(good.root_accesses):
          models=[Oracle(code,m,args,phase,mode=1)for code in(truth,words)]
          for model in models:
           model.root_fault=cut
           try:model.run()
           except faults.AccessBoundary:pass
           else:raise AssertionError('Access control did not fire')
          assert complete(models[0])==complete(models[1]);faultcount+=1
        pointer=struct.pack('>I',ENTRY);sites=[i for i in range(0,len(rom),4)if rom[i:i+4]==pointer];assert sites==[0x22CFAC]
        jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF));assert not any(rom[i:i+4]==jal for i in range(0,len(rom),4))
        self.receipt.update(complete_caller_words=92,caller_cases=callercount,script_window_words=26,script_cases=scriptcount,fired_fault_prefixes=faultcount,table_slot=6,actual_callback_registration_ROM=sites,full_script_parent_or_provider_runtime_claimed=False)
    def test_05_independent_GNU_links_and_JAL_PC_plus_4_region_carry(self):
        o=self.out/'GNU-rebases';o.mkdir(exist_ok=True);function=source.FUNCTION
        objects=(('original',self.out/'original-func_1509F284.o'),('C',self.obj));rows=[]
        layouts=((0x1700FFFC,0x17017FFC,0x17028000),(0x1FFFFFBC,0x20017FFC,0x20028000),(0x1FFFFFC0,0x20027FFC,0x20038000))
        for i,(entry,first,second)in enumerate(layouts):
         anchors=dict(func_1509F660=first,func_1509F77C=second);images=[]
         for label,obj in objects:
          text,functions,bindings=parse_object(obj);assembly,unknown=emit_function(text,functions[function],bindings,function,anchors);assert not unknown
          stem=o/('layout-'+str(i)+'-'+label);src=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf');src.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
          subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(src)],check=True,capture_output=True)
          subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',function,*['--defsym=%s=0x%X'%x for x in anchors.items()],'-o',str(elf),str(out)],check=True,capture_output=True)
          image=sections(elf)['.text'][1][:184];assert len(image)==184;words=struct.unpack('>46I',image)
          for offset,wanted in((64,first),(92,first),(148,second)):
           w=words[offset//4];assert w>>26==3 and ((((entry+offset+4)&0xF0000000)|((w&0x3FFFFFF)<<2))==wanted)
          images.append(image)
         assert images[0]==images[1];rows.append(dict(entry=hex(entry),anchors={k:hex(v)for k,v in anchors.items()},all46_words_equal=True,first_JAL_PC_plus_4_region_carry=entry==0x1FFFFFBC))
        self.receipt.update(independent_GNU_links=6,rebase_layouts=rows,all3_J26_bindings_checked=True)
    def test_06_strict_image_static_inputs_guards_and_effective_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out)
        before=values['conker/build/conker.us.elf'];truth_bytes=rom[source.ROM:source.ROM+184];predicted=source.predicted_image(before,truth_bytes)
        self.assertEqual((self.out/'first-linked.elf').read_bytes(),predicted)
        at=source.elf_slot_offset(before,ENTRY,184)
        for offset in(0,at-1,at,at+180,at+184,len(before)-1):
            bad=bytearray(predicted);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth_bytes)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth_bytes)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),values['conker/retail_word_patches.us.csv'])
        self.receipt.update(strict_image_corruptions_rejected=7,metadata_exclusions=0,frozen_and_current_inputs=len(values),entire_guard_manifest_unchanged=True)

if __name__=='__main__':unittest.main()
