"""Record value restore: signed arithmetic, float truncation, aliases and closed allocation guards."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,os,re,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_record_value_restore_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,COMMAND=0x22000,0x30000
@dataclass(frozen=True)
class Case:
    baseline:int=100
    current:int=50
    flags:int=0
    packed:int=0x0003003C
    ticks:int=2
    factor:int=0x3D4CCCCD
    tick_alias:int=-1
    factor_alias:int=-1
    phase:int=0

def half(v):return((v&65535)^32768)-32768
def fixture(c,ticks=None,factor=None):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};m.update({RECORD+i:(i*13+0x59)&255 for i in range(-16,176)})
    for off,v,n in((0x7C,c.baseline,4),(0x12,c.current,2),(0x4F,c.flags,1),(0x3C,c.packed,4)):put(m,RECORD+off,v&((1<<(n*8))-1),n)
    t=RECORD+c.tick_alias if c.tick_alias>=0 else source.TICKS if ticks is None else ticks;f=RECORD+c.factor_alias if c.factor_alias>=0 else source.FACTOR if factor is None else factor
    put(m,t,c.ticks&0xFFFFFFFF);put(m,f,c.factor)
    return m,t,f

def trunc_word(v):
    return math.trunc(v)&0xFFFFFFFF if math.isfinite(v)and -2147483648.0<=v<2147483648.0 else 0x80000000

def reference(initial,ticks,factor):
    m=dict(initial);baseline=signed(read(m,RECORD+0x7C))
    if baseline==0:baseline=half(read(m,RECORD+0x12,2));put(m,RECORD+0x7C,baseline&0xFFFFFFFF)
    current=half(read(m,RECORD+0x12,2));difference=signed((baseline-current)&0xFFFFFFFF)
    if m[RECORD+0x4F]&4:
        packed=read(m,RECORD+0x3C)
        if difference<half(packed):put(m,RECORD+0x12,(current-half(packed>>16)*signed(read(m,ticks)))&65535,2)
    else:
        delta=floating(bits(float(difference)));weight=floating(read(m,factor));tick=floating(bits(float(signed(read(m,ticks)))));product=floating(bits(delta*weight));product=floating(bits(product*tick));value=floating(bits(floating(bits(float(current)))+product));put(m,RECORD+0x12,trunc_word(value)&65535,2)
    return m

class RestoreOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected);self.trace=[]
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            fs,fd=word>>11&31,word>>6&31;self.f[fd]=trunc_word(floating(self.f[fs]));return
        super().execute(word)
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target==source.ENTRY;args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):raise AssertionError(('unbounded provider',target))

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.window_end:raise WindowBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED
    return dict(wrong_flag=b.replace('record[0x4F] & 4','record[0x4F] & 8'),inclusive_threshold=b.replace('difference < (s16)packed','difference <= (s16)packed'),unsigned_threshold=b.replace('difference < (s16)packed','difference < (u16)packed'),wrong_rate_shift=b.replace('packed >> 16','packed >> 8'),unsigned_value=b.replace('*(s16 *)(record + 0x12);','*(u16 *)(record + 0x12);'),missing_baseline_store=b.replace('        *(s32 *)(record + 0x7C) = baseline;\n',''),overwrite_baseline=b.replace('if (baseline == 0)','if (1)'),wrong_ticks=b.replace('D_800BE9E4','1'),wrong_factor=b.replace('D_800A2F8C','0.1f'),regrouped=b.replace('(f32)current +\n            (f32)difference * D_800A2F8C * (f32)D_800BE9E4','((f32)current + (f32)difference * D_800A2F8C) * (f32)D_800BE9E4'),early_truncation=b.replace('(f32)difference * D_800A2F8C * (f32)D_800BE9E4','(f32)(s32)((f32)difference * D_800A2F8C * (f32)D_800BE9E4)'))

def native_harness():
    t=source.HEADERS+r'''
typedef struct{u8 pad0[0x12];s16 value;u8 pad14[0x28];s32 packed;u8 pad40[0xF];u8 flags;u8 pad50[0x2C];s32 baseline;}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(Record)==0x80&&__builtin_offsetof(Record,value)==0x12&&__builtin_offsetof(Record,packed)==0x3C&&__builtin_offsetof(Record,baseline)==0x7C)?1:-1];
static struct{u32 left[4];Record record;u32 right[4];}actual,expected;
static s32 clockValue,*clockPointer;static f32 factorValue;
#define D_800BE9E4 (*clockPointer)
#define D_800A2F8C factorValue
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){u32 n,mode,layout,i;u8*p=(u8*)&actual,*q=(u8*)&expected;s32 baseline,current,difference,tick,rate,threshold;u32 result;f32 delta,product,step,value;
 for(n=0;n<65537;n++)for(mode=0;mode<2;mode++)for(layout=0;layout<3;layout++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n*3+mode);
  actual.record.value=(s16)n;actual.record.flags=mode?4:0;
  actual.record.baseline=mode?(n&2?0:(n&4?(s32)0x80000001u:2147483647)):(n&2?0:(n&4?50000:-12345));
  actual.record.packed=mode?(s32)(((n*13u&65535u)<<16)|(n*7u&65535u)):3;
  clockValue=n&1?30:-17;factorValue=0.05f;clockPointer=layout==0?&clockValue:layout==1?&actual.record.baseline:&actual.record.packed;
  if(n==65536){actual.record.value=mode?10:1;actual.record.baseline=mode?15:-2;actual.record.packed=mode?0x00030005:3;clockValue=mode?1:3;clockPointer=&clockValue;}
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];baseline=expected.record.baseline;current=expected.record.value;
  if(baseline==0){baseline=current;expected.record.baseline=baseline;}
  difference=(s32)((u32)baseline-(u32)current);tick=n==65536?clockValue:layout==0?clockValue:layout==1?expected.record.baseline:expected.record.packed;
  if(mode){threshold=(s16)expected.record.packed;rate=(s16)((u32)expected.record.packed>>16);if(difference<threshold){result=(u32)current-(u32)rate*(u32)tick;expected.record.value=(s16)result;}}
  else{delta=(f32)difference;product=delta*0.05f;step=(f32)tick;product=product*step;value=(f32)current+product;if(!(value>=-2147483648.0f&&value<2147483648.0f))return 2;expected.record.value=(s16)(s32)value;}
  fn((u8*)&actual.record);for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class RecordValueRestoreTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,ticks=None,factor=None):
        initial,t,f=fixture(c,ticks,factor);want=reference(initial,t,f);pair=[]
        for words in images or(self.truth,self.words):
            m=RestoreOracle(words,initial,c,entry).run();self.assertEqual(m.memory,want,c);self.assertEqual(m.calls,[]);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def linked(self,entry,ticks,factor):
        if not hasattr(self,'links'):self.links={}
        key=(entry,ticks,factor)
        if key in self.links:return self.links[key]
        # Actual guarded object is independently assembled from the normalized payload.
        raw,rs=source.normalized_payload(*source.payload(self.out/'selected.o'));original=self.out/('original-'+source.FUNCTION+'.o');pair=[];number=len(self.links)
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        from tools.pad_generated_object import parse_object
        data,functions,bindings=parse_object(self.out/'selected.o');function=functions[source.FUNCTION];changed=bytearray(data);changed[function['value']:function['value']+function['size']]=raw
        asm,unknown=emit_function(bytes(changed),function,bindings,source.FUNCTION,{'D_800BE9E4':ticks,'D_800A2F8C':factor});self.assertFalse(unknown);p=self.fresh/('normalized-%d.s'%number);p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(p)],capture_output=True,check=True)
        for j,obj in enumerate((original,obj)):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x%X'%ticks,'--defsym=D_800A2F8C=0x%X'%factor,'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def test_01_complete_owner_actual_Make_and_closed_register_cycle(self):
        self.assertEqual(self.words,self.truth);raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));self.assertEqual(source.normalized_payload(raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o')))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),84)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),83);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_142560.c.o.compact'),84)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual((self.out/'proposed-owner.c').read_text().count('#pragma GLOBAL_ASM('),10);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(ws)if w==source.ENTRY],[0x22D798]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(struct.unpack_from('>3I',self.rom,0x22D798),(source.ENTRY,0,0))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=48,frame=0,bindings=6,guards=25,guard_role='one closed ten-GPR allocation cycle',neighbors=83,compact_functions=84,GLOBAL_ASM_routines=10,Make_commands=5,diagnostics=0,callback_slot=6,callback_entry_stride=12,no_direct_JAL_or_tail_J=True)
    def test_02_guest_modes_boundaries_rounding_lazy_aliases_and_raw_C(self):
        count=0;visits=set()
        for baseline,current,flags,packed,ticks in itertools.product((0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(-32768,-1,0,1,32767),(0,4,255),(0x80008000,0x7FFF7FFF,0x0003003C,0xFFFF0000),(0,1,30,0x80000000)):
            m=self.compare(Case(baseline,current,flags,packed,ticks));visits.update(m.visits);count+=1
        for flags in range(256):self.compare(Case(flags=flags,phase=(flags&1)*8));count+=1
        for offset,mode,which in itertools.product(range(0,128,4),(0,4),('tick','factor')):
            c=Case(baseline=0,flags=mode,ticks=2,factor=0x3D4CCCCD,tick_alias=offset if which=='tick'else-1,factor_alias=offset if which=='factor'else-1);images=self.linked(source.ENTRY,RECORD+offset if which=='tick'else source.TICKS,RECORD+offset if which=='factor'else source.FACTOR);self.compare(c,images);count+=1
        for pattern in(0,0x80000000,1,0x80000001,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345):self.compare(Case(factor=pattern));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4))-{source.ENTRY+108})
        # Also execute the actual unnormalized compiler output: public semantics must already agree.
        obj=self.fresh/'raw-selected.o';obj.write_bytes((self.out/'selected.o').read_bytes());data,functions=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=functions[source.FUNCTION];words=list(struct.unpack_from('>48I',data,f['value']))
        for c in(Case(),Case(baseline=0),Case(flags=4),Case(flags=4,packed=0xFFFF8000),Case(baseline=0x80000000,current=32767)):
            initial,t,factor=fixture(c);self.assertEqual(RestoreOracle(words,initial,c).run().memory,reference(initial,t,factor))
        self.receipt['guest']=dict(cases=count,visited_words=47,unreachable_difference_word_retained=True,signed_halfword_and_wrapped32_boundaries=True,all256_flag_bytes=True,all32_aligned_tick_and_factor_aliases=True,lazy_access_and_baseline_store_order=True,raw_compiled_C_semantics_checked=True,full_guarded_private_state_trace=True,indefinite_conversion_is_bounded_model_not_exception_hardware_acceptance=True)
    def test_03_original_registry_install_and_indirect_call_windows(self):
        install=list(struct.unpack_from('>22I',self.rom,0xCC06C));call=list(struct.unpack_from('>5I',self.rom,0x141390))
        for words,path,va in((install,'conker/asm/CBDB0.s',0x1509EBBC),(call,'conker/asm/13D350.s',0x15113EE0)):
            asm=self.values[path].decode();literal={int(a,16):int(w,16)for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',asm)};self.assertEqual(words,[literal[va+i*4]for i in range(len(words))])
        initial,_,_=fixture(Case());put(initial,COMMAND+8,6);entry=self.rom[0x22D798:0x22D7A4]
        for i,b in enumerate(entry):initial[source.TABLE+72+i]=b
        m=RestoreOracle(install,initial,entry=0x1509EBBC);m.r[2]=RECORD;m.r[16]=COMMAND;m.window_end=0x1509ED5C;m.code=WindowCode(dict(m.code),m)
        with self.assertRaises(WindowBoundary):m.run()
        self.assertEqual((read(m.memory,RECORD+0x38),read(m.memory,RECORD+0x78),m.memory[RECORD+0x92]),(source.ENTRY,0,0));count=0
        for c in(Case(),Case(baseline=0),Case(flags=4),Case(flags=4,current=-32768),Case(ticks=0x80000000)):
            initial,t,f=fixture(c);put(initial,RECORD+0x38,source.ENTRY);want=reference(initial,t,f);pair=[]
            for words in(self.truth,self.words):
                m=RestoreOracle(call,initial,c,entry=0x15113EE0,connected={source.ENTRY+i*4:w for i,w in enumerate(words)});m.r[16]=RECORD;m.r[30]=10;m.window_end=0x15113EF4;m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.memory,want);self.assertEqual(m.calls,[(source.ENTRY,(RECORD,))]);self.assertEqual(m.r[30],11);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for path,name in(('conker/src/game/generated_CBDB0.c','func_1509E900'),('conker/src/game/generated_13D350.c','func_15113E54')):self.assertIn('s32 '+name+'() {\n    return 0;\n}',self.values[path].decode())
        self.receipt['caller']=dict(original_install_words=22,original_indirect_words=5,connected_cases=count,slot6_and_record_plus38_callback=True,A0_record_void_result_contract=True,current_install_and_dispatcher_stubs_unchanged=True,no_complete_registry_or_dispatcher_acceptance=True)
    def test_04_native32_signed_values_aliases_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65537*2*3,effective_controls=len(controls()),trapping_UBSan=True,all_signed_halfwords=True,valid_typed_record_backing_and_full_storage_fences=True,disjoint_clock_or_signed32_baseline_packed_alias=True,float_to_signed32_domain_validated=True,no_native_float_integer_type_punning_or_nonfinite_cast_claim=True)
    def test_05_fired_fault_prefixes_and_lazy_unmapped_inputs(self):
        cuts=0
        for baseline,flags,threshold,phase in itertools.product((0,100),(0,4),(-32768,32767),(0,8)):
            c=Case(baseline=baseline,flags=flags,packed=0x00030000|(threshold&65535),phase=phase);initial,_,_=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=RestoreOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for c,missing in((Case(flags=4,packed=0x00038000),[source.TICKS,source.FACTOR]),(Case(flags=0),[RECORD+0x3C])):
            initial,t,f=fixture(c)
            for address in missing:
                for i in range(4):initial.pop(address+i,None)
            for words in(self.truth,self.words):RestoreOracle(words,initial,c).run()
        c=Case(baseline=0);m=self.compare(c);self.assertEqual([e[1]-RECORD for e in m.trace if e[0]=='W'],[0x7C,0x12]);self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,no_ticks_or_factor_on_rejected_integer_path=True,no_packed_read_on_float_path=True,baseline_before_output_store=True)
    def test_06_real_padder_guard_corruptions_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,52:[('R_MIPS_HI16','wrong')]})):
            with self.assertRaises(ValueError):source.normalized_payload(b,bindings)
        rows=[dict(x)for x in source.NEW_GUARDS];rows[0]['expected']='0x00000000'
        with patch.object(source,'NEW_GUARDS',rows):
            with self.assertRaises(ValueError):source.normalized_payload(raw,rs)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=self.out/'proposed-word-patches.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        import csv,io
        reader=csv.DictReader(io.StringIO((self.out/'proposed-word-patches.csv').read_text()));fields=reader.fieldnames;rows=list(reader);next(x for x in rows if x['function']==source.FUNCTION)['expected']='0x00000000';bad_csv=self.fresh/'bad.csv'
        with bad_csv.open('w',newline='')as stream:writer=csv.DictWriter(stream,fields);writer.writeheader();writer.writerows(rows)
        with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad_csv,filename=source.OWNER)
        cases=0
        for entry,t,f in((source.ENTRY,source.TICKS,source.FACTOR),(0x17007FFC,0x800B7FFC,0x800A8004),(0x2500FFFC,0x800C8004,0x8009FFFC)):
            images=self.linked(entry,t,f)
            for flags,baseline in itertools.product((0,4),(0,100,0x80000000)):
                self.compare(Case(flags=flags,baseline=baseline),images,entry,t,f);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,six_HI_LO_bindings_and_low_half_carry=True,GNU_original_and_actual_normalized_payload=True,effective_raw_guard_binding_controls=5,actual_padder_bad_expected_rejected=True,guards=25)
    def test_07_actually_compiled_inclusive_threshold_rejected_by_value(self):
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()['inclusive_threshold'],'negative-inclusive');self.assertFalse(diag);p=self.fresh/'negative.ld';elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x151152A8 : SUBALIGN(4) { *(.text) } }\n');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x800BE9E4','--defsym=D_800A2F8C=0x800A2F8C','-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];words=list(struct.unpack('>%dI'%(len(raw)//4),raw));c=Case(baseline=15,current=10,flags=4,packed=0x00030005,ticks=1);initial,t,f=fixture(c);m=RestoreOracle(words,initial,c).run();want=reference(initial,t,f);self.assertEqual((read(m.memory,RECORD+0x12,2),read(want,RECORD+0x12,2)),(7,10));self.receipt['compiled_control']=dict(actually_compiled_inclusive_threshold_rejected=True,value_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_named_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol,0x2BA844,before.index(b'D_800A2F8C\0D_8009078C\0func_151A8A78\0')):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),187);self.receipt['image']=dict(changed_bytes=187,code_bytes=141,size_bytes=1,closed_symbol_string_cycle_bytes=45,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=8,inherited_guard_rows_preserved=True,new_allocation_guard_rows=25,shared_headers_and_current_callers_unchanged=True)
