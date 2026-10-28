"""Spawn query: eleven-argument ABI, output lifetimes, real helper and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_spawn_result_query_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];INPUT,TABLE,ACTOR=0x20000,0x40000,0x50000
@dataclass(frozen=True)
class Case:
    gate:int=1
    context:int=7
    previous:int=128
    selected:int=255
    mode:int=0
    phase:int=0
    layout:int=0
    seed:int=0x12345678

def effective_locations(c,globals_=source.GLOBALS):
    g,context,old,index=globals_;sp=STACK+c.phase
    if c.layout==1:context=old-3
    elif c.layout==2:context=sp-4
    elif c.layout==3:g=sp
    elif c.layout==4:old=context+3;index=context+2
    return g,context,old,index

def locations(c,globals_=source.GLOBALS):return globals_

def fixture(c,globals_=source.GLOBALS):
    sp=STACK+c.phase;m={sp+i:(i*17+0xA5)&255 for i in range(-768,256)};m.update({INPUT+i:(i*13+0x59)&255 for i in range(16)})
    g,context,old,index=locations(c,globals_);m[g]=c.gate;put(m,context,c.context);m[old]=c.previous;m[index]=c.selected;put(m,sp-4,c.seed)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+256}
def sign_byte(x):return((x&255)^128)-128
def helper_args(sp,index):return(0,index,1,sp-12,sp-24,sp-29,sp-30,sp-28,sp-36,1,sp-4)
def provider(m,args,c,globals_):
    for p,v in zip((args[3],args[3]+2,args[3]+4),(0x8000,0x1234,0x7FFF)):put(m,p,v,2)
    for p,v in zip((args[4],args[4]+4,args[4]+8),(0x3F800000,0xC0200000,0)):put(m,p,v)
    put(m,args[5],0xA5,1);put(m,args[6],0x5A,1);put(m,args[7],0x12345678);put(m,args[8],0xFFFFFF80)
    if c.mode!=3:put(m,args[10],(0,1,0xFFFFFFFF,0,0x7FFFFFFF)[c.mode])
    if c.mode==4:
        g,context,old,index=locations(c,globals_);m[g]=0;put(m,context,0xCAFEBABE);m[old]=7;m[index]=8

def reference(initial,c,globals_=source.GLOBALS,input_=INPUT):
    m=dict(initial);sp=STACK+c.phase;put(m,sp,input_);g,context,old,index=locations(c,globals_);calls=[];observations=[]
    if not m[g]or read(m,context)in(24,34):return public(m),calls,observations,0
    put(m,context,sign_byte(m[old]));args=helper_args(sp,m[index]);calls.append((source.HELPER,args));observations.append((m[g],read(m,context),m[old],m[index]));provider(m,args,c,globals_)
    return public(m),calls,observations,(read(m,sp-4)+1)&0xFFFFFFFF

class SpawnOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,globals_=source.GLOBALS,helper=source.HELPER,connected=None,input_=INPUT):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(input_,),connected=connected);self.case,self.globals,self.helper,self.trace=c,globals_,helper,[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        args=self.arguments(1 if target==source.ENTRY else 11);assert target in(source.ENTRY,self.helper),hex(target)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.helper:
            g,context,old,index=locations(self.case,self.globals);self.observations.append((self.memory[g],read(self.memory,context),self.memory[old],self.memory[index]))
    def hook(self,target):
        assert target==self.helper;provider(self.memory,self.calls[-1][1],self.case,self.globals)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=99;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED
    return dict(exact_gate=b.replace('if (!D_800D18A8)','if (D_800D18A8 != 1)'),wrong_blocks=b.replace('== 0x22','== 0x23').replace('== 0x18','== 0x19'),unsigned_context=b.replace('(s32)(s8)D_800BE3DF','(s32)D_800BE3DF'),signed_index=b.replace('func_15084D70(0, D_800BE3E0,','func_15084D70(0, (s8)D_800BE3E0,'),keep_context=b.replace('    D_800BE9F4 = (u16 *)(s32)(s8)D_800BE3DF;',''),wrong_query_flag=b.replace('D_800BE3E0, 1, position','D_800BE3E0, 0, position'),raw_result=b.replace('return result + 1;','return result;'),wrong_result_output=b.replace('&signedTag, 1, &result','&result, 1, &signedTag'))

def native_harness():
    t=source.HEADERS+source.DECLARATIONS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(f32)==4&&sizeof(s32)==4)?1:-1];
u8 D_800D18A8,D_800BE3DF,D_800BE3E0;u16 *D_800BE9F4;
static u32 mode,calls,bad,observedContext,observedIndex;static s32 token=0x12345678;
s32 func_15084D70(s32 a,s32 index,s32 query,s16*p,f32*r,u8*x,u8*y,s32*flags,s32*tag,s32 one,s32*result){
 calls++;observedContext=(u32)D_800BE9F4;observedIndex=(u32)index;if(a||query!=1||one!=1)bad=1;
 p[0]=-32768;p[1]=0x1234;p[2]=32767;r[0]=1.0f;r[1]=-2.5f;r[2]=0.0f;*x=0xA5;*y=0x5A;*flags=0x12345678;*tag=-128;*result=(s32)mode-1;
 if(mode==2){D_800D18A8=0;D_800BE9F4=(u16*)0xCAFEBABE;D_800BE3DF=7;D_800BE3E0=8;}return 99;
}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+name)+'\n'
    t+=r'''
typedef s32(*Query)(s32*);
static int check(Query fn){const u32 ctx[]={0,7,24,34,0x80000018,0xFFFFFFFF};const u8 bytes[]={0,1,127,128,254,255};u32 gate,k,i,j,expected,call;
 for(gate=0;gate<256;gate++)for(k=0;k<6;k++)for(i=0;i<6;i++)for(j=0;j<6;j++)for(mode=0;mode<3;mode++){
  s32 result;D_800D18A8=(u8)gate;D_800BE9F4=(u16*)ctx[k];D_800BE3DF=bytes[i];D_800BE3E0=bytes[j];calls=bad=0;observedContext=observedIndex=0;
  call=gate&&ctx[k]!=24&&ctx[k]!=34;expected=call?(u32)(s32)(s8)bytes[i]:ctx[k];
  result=fn((i&1)?&token:0);
  if(result!=(call?(s32)mode:0)||calls!=call||bad||token!=0x12345678)return 1;
  if(call&&(observedContext!=expected||observedIndex!=bytes[j]))return 1;
  if(call&&mode==2){if(D_800D18A8||D_800BE9F4!=(u16*)0xCAFEBABE||D_800BE3DF!=7||D_800BE3E0!=8)return 1;}
  else if(D_800D18A8!=gate||(u32)D_800BE9F4!=expected||D_800BE3DF!=bytes[i]||D_800BE3E0!=bytes[j])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class SpawnResultQueryTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>47I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>47I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def linked_pair(self,entry,globals_,helper):
        key=(entry,globals_,helper)
        if not hasattr(self,'alias_links'):self.alias_links={}
        if key in self.alias_links:return self.alias_links[key]
        symbols=dict(zip(('D_800D18A8','D_800BE9F4','D_800BE3DF','D_800BE3E0'),globals_));symbols['func_15084D70']=helper;pair=[];number=len(self.alias_links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('alias-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.alias_links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,globals_=source.GLOBALS,helper=source.HELPER):
        if c.layout:globals_=effective_locations(c,globals_);images=self.linked_pair(entry,globals_,helper)
        initial=fixture(c,globals_);want,calls,obs,result=reference(initial,c,globals_);calls=[(helper,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=SpawnOracle(words,initial,c,entry,globals_,helper).run();self.assertEqual((public(m.memory),m.calls,m.observations,m.r[2]),(want,calls,obs,result),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_GLOBAL_ASM_actual_Make_ABI_and_census(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFA0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),16)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),15);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game_A9D90.c.o.compact'),16);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([4*i for i,w in enumerate(ws)if w==0x0C000000|(source.ENTRY>>2&0x3FFFFFF)],[0x35118]);self.assertFalse(any(w in(source.ENTRY,0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=47,frame=96,bindings=9,guards=0,neighbors=15,compact_functions=16,Make_commands=5,GLOBAL_ASM_neighbors=3,ABI='s32(s32* unusedSelection)',typed_helper_arguments=11,unchanged_shared_declarations=True,no_diagnostics=True)
    def test_02_gates_signed_context_output_homes_and_guest_aliases(self):
        count=0;visits=set()
        for gate,ctx,mode in itertools.product(range(256),(24,34,7),(0,3)):
            m=self.compare(Case(gate,ctx,mode=mode));visits.update(m.visits);count+=1
        for prev,index,phase in itertools.product(range(256),(0,128,255),(0,8)):
            self.compare(Case(previous=prev,selected=index,phase=phase));count+=1
        for layout,mode,seed,ctx in itertools.product(range(5),range(5),(0,0x7FFFFFFF,0xFFFFFFFF),(0,24,34,0x10000018,0x80000022,0xFFFFFFFF)):
            self.compare(Case(context=ctx,mode=mode,layout=layout,seed=seed));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+188,4))-{source.ENTRY+44});self.receipt['guest']=dict(cases=count,all_gate_and_signed_previous_bytes=True,unsigned_index_boundaries=True,fullword_context_comparisons=True,layouts=5,context_store_before_index_reload=True,eleven_physical_arguments_and_private_outputs=True,unwritten_result_home_and_wrapping_add_guest_only=True,unreachable_load_offset=44,reachable_words=46)
    def test_03_original_caller_return_store_and_complete_original_helper(self):
        start,stop=0x15007C64,0x15007C7C;body=list(struct.unpack_from('>6I',self.rom,start-0x15000000+0x2D4B0));count=0
        for gate,ctx,mode,phase in itertools.product((0,1,255),(7,24,34),(0,1,3),(0,8)):
            c=Case(gate,ctx,mode=mode,phase=phase);initial=fixture(c);initial[0x800E0B94]=2;pair=[];sp=STACK+phase
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=SpawnOracle(body,initial,c,entry=start,connected=connected);m.r[13]=0x89ABCDEF;m.code[stop]=0;m.code=StopCode(m.code,m,stop)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual(m.calls[0],(source.ENTRY,(sp+48,)));self.assertEqual(read(m.memory,sp+48),0x89ABCDEF);self.assertEqual(read(m.memory,sp+44),reference(initial,c,input_=sp+48)[3]);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        hwords=list(struct.unpack_from('>424I',self.rom,0xB2220));helper_cases=0;unwritten=0
        for index,link,tag in itertools.product((0,1,3),(0,255,1,127),(0,255,254)):
            c=Case(selected=index,seed=0x12345678);initial=fixture(c)
            for a,v in((0x800BE9F0,0),(0x800D212C,TABLE),(0x800D2128,4),(0x800CC5EC,ACTOR)):put(initial,a,v)
            initial[0x800BE616]=0;initial[ACTOR+0x11B]=0xA5;initial[0x800DDE38]=0
            for row in range(4):
                base=TABLE+24*row;initial.update({base+i:0 for i in range(24)});put(initial,base,0x12348000);put(initial,base+4,0x7FFF1234)
                for off,val in((8,0x3F800000),(12,0xC0200000),(16,0)):put(initial,base+off,val)
                initial[base+20]=0xA5;initial[base+21]=tag;initial[base+22]=link
            chosen=link if 0<link<4 else index;want=0x12345679 if link==0 else(2 if sign_byte(tag)<-1 else 1);pair=[]
            for target in(self.truth,self.words):
                connected={source.HELPER+4*i:w for i,w in enumerate(hwords)};m=SpawnOracle(target,initial,c,connected=connected).run();self.assertEqual(m.r[2],want);self.assertEqual(m.memory[ACTOR+0x11B],index);self.assertEqual(len(m.calls),1);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helper_cases+=1;unwritten+=link==0
        self.receipt['caller']=dict(original_window_words=6,cases=count,unused_pointer_input_canary_and_return_store=True,parent_stub_uncredited=True,complete_original_helper_words=424,helper_cases=helper_cases,unwritten_result_cases=unwritten,no_opaque_subcalls_in_qualified_helper_paths=True,helper_C_stub_remains_uncredited=True,no_full_parent_or_gameplay_claim=True)
    def test_04_native32_legacy_word_casts_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=165888,effective_controls=8,trapping_UBSan=True,valid_typed_outputs_and_unused_pointer=True,legacy_pointer_word_conversions_qualified_for_32bit_ABI=True,unwritten_outputs_overflow_and_guest_aliases_excluded=True)
    def test_05_fired_fault_prefixes_and_sparse_early_returns(self):
        cuts=0
        for c in(Case(),Case(gate=0),Case(context=24),Case(context=34),Case(mode=3),Case(mode=4),Case(layout=1),Case(layout=2),Case(layout=4)):
            globals_=effective_locations(c);initial=fixture(c,globals_);good=self.compare(c);images=self.linked_pair(source.ENTRY,globals_,source.HELPER)if c.layout else(self.truth,self.words)
            for cut in range(good.root_accesses):
                pair=[]
                for words in images:
                    m=SpawnOracle(words,initial,c,globals_=globals_);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for gate,ctx in((0,7),(1,24),(1,34)):
            c=Case(gate,ctx);m=fixture(c);keep=set(range(STACK-768,STACK+256))|{source.GLOBALS[0]}
            if gate:keep.update(range(source.GLOBALS[1],source.GLOBALS[1]+4))
            sparse={a:v for a,v in m.items()if a in keep}
            for words in(self.truth,self.words):x=SpawnOracle(words,sparse,c,input_=0xDEAD0000).run();self.assertEqual(x.r[2],0);self.assertFalse(x.calls)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_trace_PC_delay_equal=True,disabled_needs_no_context_or_inputs=True,blocked_context_needs_no_selected_bytes_or_helper=True,unused_pointer_never_dereferenced=True)
    def test_06_legacy_padder_raw_controls_and_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[44]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{156:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/'conker/retail_layout.us.txt',source.OWNER,rodata_symbol='jtbl_8009B884_game',word_patches_path=ROOT/'conker/retail_word_patches.us.csv'));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        links=cases=0
        for i,(entry,helper,globals_)in enumerate(((source.ENTRY,source.HELPER,source.GLOBALS),(0x17007FFC,0x17018000,(0x81008000,0x81010000,0x81017FFF,0x81018000)),(0x2500FFFC,0x25028000,(0x8120FFFC,0x81218000,0x81227FFF,0x81228000)))):
            symbols=dict(zip(('D_800D18A8','D_800BE9F4','D_800BE3DF','D_800BE3E0'),globals_));symbols['func_15084D70']=helper;asm,missing=emit_function(raw,dict(value=0,size=188),rs,source.FUNCTION,symbols);self.assertFalse(missing);p=self.fresh/('rebase-%d.s'%i);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True);images=[]
            for j,obj_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('link-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj_)],capture_output=True,check=True);images.append(list(struct.unpack_from('>47I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for c in(Case(),Case(gate=0),Case(context=24),Case(previous=255,mode=3),Case(layout=1),Case(layout=4)):self.compare(c,images,entry,globals_,helper);cases+=1
        self.receipt['rebases']=dict(GNU_links=links,layouts=3,guest_cases=cases,nine_bindings_and_signed_low_carries=True,raw_corruption_controls=3,unreachable_word_literal_checked=True,guards=0)
    def test_07_compiled_result_initializer_is_rejected(self):
        body=source.SELECTED.replace('s32 result;','s32 result = 0;');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-initialized-result');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mode=3,seed=0x55);m=SpawnOracle(words,fixture(c),c).run();self.assertNotEqual(m.r[2],reference(fixture(c),c)[3]);self.receipt['negative_initializer']=dict(compiled_initializer_mutant_rejected=True,original_unwritten_home_seed85_returns86=True,guest_only_indeterminate_home_contract=True)
    def test_08_strict_full_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+188];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,188);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+44,at+188,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),141);self.receipt['image']=dict(changed_bytes=141,code_bytes=140,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guard_manifest_and_shared_headers_unchanged=True)
