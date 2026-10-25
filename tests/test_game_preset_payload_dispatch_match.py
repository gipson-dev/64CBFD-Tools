"""Preset dispatch: actual classifier, late argument homes and exact C emission."""
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_preset_payload_dispatch_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_table_range_loader import RangeOracle
from tools.tests.test_game_queued_segment_writer import SegmentQueueOracle,STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_indexed_state_save_match import external
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
CLASSIFIER,FACTORY,TABLE,OBJECT,OTHER=0x1518FDC4,0x1518F5D0,0x8008D630,0x30000,0x31000
KINDS={0:0,1:0,2:0,3:0,4:0,17:6,20:6,22:7,59:6,73:1,80:3,83:17,88:2,
90:4,95:4,112:16,116:4,117:4,122:4,128:5,135:13,136:8,144:8,150:18,
152:6,153:6,156:9,157:10,159:11,160:12,176:13,177:14,178:16,180:15}
CALLERS=((0x1502460C,2032,'50D80.s'),(0x150265CC,3451,'50D80.s'),
         (0x1509D180,384,'C9EC0.s'),(0x15194FF4,123,'1C1150.s'))
SITES=(0x15025564,0x15027FE8,0x1509D4AC,0x15195160,0x151951C8)

def put(m,a,v,n=4):
    for i,b in enumerate((v&((1<<(8*n))-1)).to_bytes(n,'big')):m[a+i]=b
def get(m,a,n=4):return int.from_bytes(bytes(m[a+i]for i in range(n)),'big')
def signed(v,n):return ((v&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
def normalized(args,pointer):
    return tuple(v&0xFFFFFFFF for v in(args[0],pointer,signed(args[2],16),
        signed(args[3],8),signed(args[4],8),signed(args[5],8),args[6]&255,args[7],args[8]&255,args[9]))

def fixture(data,kind=0,variant=0,phase=0):
    m={STACK+i:0xA5 for i in range(-0x600,0x200)};m.update(data)
    for a in(OBJECT,OTHER):m.update({a+i:(i*17+0x31)&255 for i in range(256)})
    put(m,OBJECT+4,kind,1)
    args=(OBJECT,0xA7000000|variant,0xABCD8001,0xAB000080,0xDE0000FF,
          0xCA00007F,0xBAD000FF,0x8000000C,0xDEF00080,0x80000001)
    return m,args

class Oracle(TriangleOracle):
    def __init__(self,words,memory,args,phase=0,actual=False,helper=(),preset=0,result=1,
                 mutation=0,returned=0x32000,entry=source.ENTRY,table=TABLE,
                 classifier=CLASSIFIER,factory=FACTORY,connected=None,fault=None):
        code=dict(connected or {})
        if actual:code.update({classifier+4*i:w for i,w in enumerate(helper)})
        TriangleOracle.__init__(self,words,memory,entry=entry,arguments=args,phase=phase,connected=code)
        self.hi=self.lo=0;self.root_entry=entry;self.classifier=classifier;self.factory=factory
        self.table=table;self.root_sp=self.r[29]-56;self.actual=actual;self.preset=preset
        self.result=result;self.mutation=mutation;self.returned=returned;self.own_accesses=0
        self.root_fault=fault;self.in_instruction=False;self.current_pc=None;self.delay_of=None
        self.dispatched_word=0;self.code=faults.TrackedCode(self.code,self)
    def execute(self,word):
        self.dispatched_word=word;self.in_instruction=True
        try:
            if word>>26==32:
                rs,rt,offset=word>>21&31,word>>16&31,signed(word&65535,16)
                self.r[rt]=signed(self.get((self.r[rs]+offset)&0xFFFFFFFF,1),8)&0xFFFFFFFF
                self.r[0]=0
                return
            return super().execute(word)
        finally:self.in_instruction=False
    def access(self):
        if self.in_instruction and self.current_pc is not None and self.root_entry<=self.current_pc<self.root_entry+180:
            if self.own_accesses==self.root_fault:raise faults.AccessBoundary
            self.own_accesses+=1
    def get(self,a,n):self.access();return super().get(a,n)
    def put(self,a,v,n):self.access();return RangeOracle.put(self,a,v,n)
    def record_call(self,target):
        assert target in(self.classifier,self.factory),hex(target)
        args=self.arguments(3 if target==self.classifier else 10)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target==self.classifier:
            self.put(self.r[5],self.preset,1)
            if self.mutation:
                for index,value in ((1,0xAB000003),(2,0x12348000),(3,0x123400FF),
                    (4,0x12340080),(5,0x123400FE),(6,0x12340081),(7,0x80001234),
                    (8,0xAB0000FF),(9,0x80004321)):
                    self.put(self.root_sp+56+4*index,value,4)
                if self.mutation==2:self.put(self.root_sp+56,OTHER,4)
                self.put(self.table+4*self.preset,0x40000,4)
            result=self.result
        else:result=self.returned
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&0xFFFFFFFF

def expected(args,memory,preset=0,result=1,mutation=0,actual=False,returned=0x32000,table=TABLE):
    values=list(args)
    if not args[0]:return 0,[]
    if actual:
        kind=get(memory,args[0]+4,1);preset=KINDS.get(kind);result=int(preset is not None and(args[1]&255)==0)
    if not result:return 0,[]
    pointer=get(memory,table+4*preset)
    if mutation:
        for i,v in((1,0xAB000003),(2,0x12348000),(3,0x123400FF),(4,0x12340080),
          (5,0x123400FE),(6,0x12340081),(7,0x80001234),(8,0xAB0000FF),(9,0x80004321)):values[i]=v
        if mutation==2:values[0]=OTHER
        pointer=0x40000
    return returned&0xFFFFFFFF,[normalized(values,pointer+80*(values[1]&255))]

def native(body):
    return '#include <ultra64.h>\n'+source.DECLARATIONS+body+r'''
typedef char preset_size_is_80[sizeof(Generated1BA1D0Preset)==80?1:-1];
static Generated1BA1D0Preset storage[19][256];
Generated1BA1D0Preset *D_8008D630[19];
static u8 object[256],returned[16];
static u32 expected[10],seen[10];
static s32 preset,gate,calls,error,allocation;
s32 func_1518FDC4(void *p,u8 *out,s32 variant){
 calls++;if(p!=object||variant!=(s32)expected[1])error=1;
 *out=(u8)preset;object[127]^=0x69;return gate;
}
void *func_1518F5D0(void *p,Generated1BA1D0Preset *v,s32 mode,s32 first,s32 second,
                  s32 third,s32 value,s32 extra,s32 channel,s32 context){
 u32 i;calls++;seen[0]=(u32)p;seen[1]=(u32)v;seen[2]=mode;seen[3]=first;
 seen[4]=second;seen[5]=third;seen[6]=value;seen[7]=extra;seen[8]=channel;seen[9]=context;
 for(i=0;i<10;i++)if(seen[i]!=(i==1?(u32)&storage[preset][expected[1]]:expected[i]))error=1;
 if(object[127]!=0x69)error=1;return allocation?returned:NULL;
}
int run(void){
 u32 v,p,phase,i;static const s16 modes[]={0,1,-1,-32768,32767};
 static const s32 words[]={0,12,-1,(-2147483647-1),2147483647};
 for(i=0;i<19;i++)D_8008D630[i]=storage[i];
 for(p=0;p<19;p++)for(v=0;v<256;v++)for(phase=0;phase<5;phase++){
  void *result;u32 state;expected[0]=(u32)object;expected[1]=v;expected[2]=(s32)modes[phase];
  expected[3]=(s32)(s8)v;expected[4]=(s32)(s8)(255-v);expected[5]=(s32)(s8)(v^128);
  expected[6]=(u8)(v*17);expected[7]=words[phase];expected[8]=(u8)(v^255);expected[9]=words[4-phase];
  preset=p;
  for(state=0;state<4;state++){
   gate=state>=2?(-2147483647-1):0;allocation=state==2;calls=error=0;object[127]=0;
   for(i=0;i<10;i++)seen[i]=0xA5A5A5A5;
   result=func_1518F51C(state?(void*)object:NULL,(u8)v,(s16)expected[2],(s8)expected[3],
       (s8)expected[4],(s8)expected[5],(u8)expected[6],expected[7],(u8)expected[8],expected[9]);
   if(error||calls!=(state==0?0:state==1?1:2)||result!=(state==2?(void*)returned:NULL))return 23;
  }
 }
 return 0;
}
'''+START

class Boundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.stop:raise Boundary
        return super().__getitem__(pc)

class PresetDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD;cls.values=source.snapshot(cls.output)
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.audit_inputs(ROOT,cls.output)if cls.installed else source.freeze(ROOT,cls.output)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>45I',cls.rom,source.ROM))
        linked,funcs=source.link_owner(ROOT,cls.output,cls.output/'qualified-after-owner.o',source.OWNER)
        cls.words=list(struct.unpack_from('>45I',linked,funcs[source.FUNCTION]['value']))
        cls.helper=list(struct.unpack_from('>158I',cls.rom,0x1BD274));cls.data={}
        for start,size in((TABLE,76),(0x800A7B7C,580)):
            off=0x2275E0+start-0x80082B20
            cls.data.update({start+i:b for i,b in enumerate(cls.rom[off:off+size])})
        cls.receipt={}
    @classmethod
    def tearDownClass(cls):(cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def pair(self,m,args,phase=0,**options):
        models=[Oracle(w,m,args,phase=phase,helper=self.helper,**options).run()for w in(self.truth,self.words)]
        self.assertEqual(complete(models[0]),complete(models[1]))
        result,calls=expected(args,m,**{k:v for k,v in options.items()if k in('preset','result','mutation','actual','returned','table')})
        self.assertEqual(models[0].r[2]&0xFFFFFFFF,result)
        factory=options.get('factory',FACTORY)
        self.assertEqual([a for t,a in models[0].calls if t==factory],calls)
        self.assertEqual(len([1 for t,a in models[0].calls if t==options.get('classifier',CLASSIFIER)]),int(bool(args[0])))
        return models[0]
    def test_01_direct_owner_Make_words_bindings_and_provider_boundary(self):
        self.assertEqual(self.words,self.truth);q=json.loads((self.output/'qualification.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['preserved_neighbors'],q['new_guards']),(45,56,4,60,0))
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],3)
        raw,bindings=source.payload(self.output/'qualified-after-owner.o');source.checked_payload(raw,bindings)
        for i in range(45):
            bad=bytearray(raw);bad[4*i]^=1
            with self.assertRaises(ValueError):source.checked_payload(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'unknown')]
            with self.assertRaises(ValueError):source.checked_payload(raw,bad)
        self.receipt.update(words=45,frame=56,bindings=4,neighbors=60,new_guards=0,word_controls=45,binding_controls=4)
    def test_02_guest_widths_live_homes_and_actual_classifier(self):
        count=0;seen=set();helpers=set()
        for kind,variant,phase in itertools.product(range(256),(0,1,127,128,254,255),(0,8)):
            m,args=fixture(self.data,kind,variant,phase);model=self.pair(m,args,phase,actual=True)
            seen|={x for x in model.visits if source.ENTRY<=x<source.ENTRY+180}
            helpers|={x for x in model.visits if CLASSIFIER<=x<CLASSIFIER+632};count+=1
        for variant,phase in itertools.product(range(256),(0,8)):
            m,args=fixture(self.data,0,variant,phase);self.pair(m,args,phase,actual=True);count+=1
        for preset,result,mutation,phase,returned in itertools.product(range(19),(0,1,0x80000000),(0,1,2),(0,8),(0,0x80000004)):
            m,args=fixture(self.data,0,255,phase);model=self.pair(m,args,phase,preset=preset,result=result,mutation=mutation,returned=returned)
            seen|={x for x in model.visits if source.ENTRY<=x<source.ENTRY+180};count+=1
        for phase in(0,8):
            m,args=fixture(self.data,phase=phase);args=(0,*args[1:]);model=self.pair(m,args,phase)
            seen|={x for x in model.visits if source.ENTRY<=x<source.ENTRY+180};count+=1
        self.assertEqual(len(seen),45)
        original=source.original(ROOT,self.output,'func_1518FDC4')
        linked,funcs=source.link_owner(ROOT,self.output,original,source.OWNER)
        self.assertEqual(linked[funcs['func_1518FDC4']['value']:][:632],self.rom[0x1BD274:0x1BD4EC])
        self.receipt.update(guest_phases=count,root_words_visited=len(seen),classifier_words_visited=len(helpers),
            original_classifier_and_both_tables=True,opaque_provider_cases_are_bounded=True,guest_home_aliases_not_native_C_claim=True)
    def test_03_native32_profiles_and_effective_controls(self):
        forms={'O0':source.SELECTED,'O2':source.SELECTED,'O3':source.SELECTED,
            'wrong_variant_stride':source.SELECTED.replace('[variant]','[0]'),
            'unsigned_mode':source.SELECTED.replace('s16 mode','u16 mode'),
            'unsigned_first':source.SELECTED.replace('s8 first','u8 first'),
            'truncated_extra':source.SELECTED.replace('s32 extraBytes','s16 extraBytes'),
            'null_return':source.SELECTED.replace('return func_1518F5D0(', 'func_1518F5D0(').replace('channel, context);','channel, context);\n    return NULL;'),
            'inverted_reject':source.SELECTED.replace('if (!func_1518FDC4','if (func_1518FDC4')}
        rows=[]
        for name,body in forms.items():
            path=self.output/('native-'+name+'.c');binary=path.with_suffix('');path.write_text(native(body))
            command=native_command('-'+name if name in('O0','O2','O3')else'-O2')
            command+=['-mstackrealign','-Wno-unused-variable',str(path),'-o',str(binary)]
            p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            result=subprocess.run([str(binary)],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0 if name in('O0','O2','O3')else 23,(name,result.stderr))
            rows.append(dict(name=name,exit=result.returncode))
        self.receipt.update(native_cases_per_profile=19*256*5*4,native_profiles=rows,
            actual_SDK_types=True,trap_UBSan=True,valid_extended_preset_backing=True)
    def test_04_five_actual_call_setup_and_return_windows(self):
        originals={}
        for entry,length,asm in CALLERS:
            name='func_%08X'%entry;obj=source.original(ROOT,self.output,name,'conker/asm/'+asm)
            linked,funcs=source.link_owner(ROOT,self.output,obj,source.OWNER);start=funcs[name]['value']
            wanted=self.rom[entry-0x15000000+0x2D4B0:][:4*length]
            self.assertEqual(linked[start:start+4*length],wanted)
            originals[entry]=dict(enumerate(struct.unpack('>%dI'%length,wanted)))
        count=0
        for site,kind,variant,phase in itertools.product(SITES,(0,180,255),(0,1),(0,8)):
            owner=next((entry for entry,length,_ in reversed(CALLERS)if entry<=site<entry+4*length),None)
            self.assertIsNotNone(owner)
            caller={owner+4*i:w for i,w in originals[owner].items()};m,args=fixture(self.data,kind,variant,phase)
            pair=[]
            for words in(self.truth,self.words):
                connected=dict(caller);connected.update({source.ENTRY+4*i:w for i,w in enumerate(words)})
                model=Oracle(words,m,args,phase,actual=True,helper=self.helper,connected=connected)
                model.entry=site-16;model.stop=site+8;model.code=WindowCode(dict(model.code),model)
                model.r[2]=12;model.r[3]=0xFFFFFF80
                for i in range(8,26):model.r[i]=(0x12340000+i)&0xFFFFFFFF
                model.r[24]=0xFFFFFFFF;model.r[25]=0xFF
                model.root_entry=source.ENTRY
                base_record=model.record_call
                def record(target,model=model,base_record=base_record):
                    if target==source.ENTRY:
                        a=model.arguments(10);model.calls.append((target,a));model.events.append(('CALL',target,a))
                    else:base_record(target)
                model.record_call=record
                with self.assertRaises(Boundary):model.run()
                self.assertEqual(model.r[29],STACK+phase);self.assertEqual(model.r[31],site+8)
                actual_args=next(a for t,a in model.calls if t==source.ENTRY)
                result,factory_args=expected(actual_args,m,actual=True)
                self.assertEqual([a for t,a in model.calls if t==FACTORY],factory_args)
                self.assertEqual(model.r[2]&0xFFFFFFFF,result)
                pair.append(model)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.receipt.update(original_call_sites=5,caller_window_phases=count,full_caller_entry_return_claimed=False,
            complete_original_caller_images_locked=True)
    def test_05_GNU_rebases_and_fired_root_fault_prefixes(self):
        links=0
        for i,table in enumerate((TABLE,0x80217FFC,0x80218004)):
            for j,entry in enumerate((source.ENTRY,0x15017FF0,0x15128010)):
                classifier,factory=0x15010400+i*0x100,0x15110200+j*0x100
                script=self.output/('rebase-%d-%d.ld'%(i,j));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                command=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=func_1518FDC4=0x%X'%classifier,'--defsym=func_1518F5D0=0x%X'%factory,
                    '--defsym=D_8008D630=0x%X'%table,'-o',str(elf),str(self.output/'qualified-selected.o')]
                subprocess.run(command,check=True,capture_output=True)
                address,code=sections(elf)['.text'];self.assertEqual(address,entry)
                words=list(struct.unpack_from('>45I',code));self.assertFalse(any(code[180:]))
                for phase in(0,8):
                    m,args=fixture(self.data,phase=phase)
                    for n in range(76):m[table+n]=m[TABLE+n]
                    model=Oracle(words,m,args,phase,preset=18,entry=entry,table=table,classifier=classifier,factory=factory).run()
                    result,calls=expected(args,m,preset=18,table=table)
                    self.assertEqual(model.r[2]&0xFFFFFFFF,result);self.assertEqual([a for t,a in model.calls if t==factory],calls)
                links+=1
        cuts=0
        for result,mutation,phase in itertools.product((0,1),(0,2),(0,8)):
            m,args=fixture(self.data,phase=phase);model=self.pair(m,args,phase,preset=18,result=result,mutation=mutation)
            for fault in range(model.own_accesses):
                pair=[Oracle(w,m,args,phase,preset=18,result=result,mutation=mutation,fault=fault)for w in(self.truth,self.words)]
                for item in pair:
                    with self.assertRaises(faults.AccessBoundary):item.run()
                    self.assertEqual(item.own_accesses,fault)
                self.assertEqual(complete(pair[0]),complete(pair[1]))
                self.assertEqual((pair[0].current_pc,pair[0].delay_of,pair[0].dispatched_word),
                                 (pair[1].current_pc,pair[1].delay_of,pair[1].dispatched_word));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebased_phases=links*2,fired_root_fault_prefixes=cuts)
    def test_06_strict_image_and_frozen_input_controls(self):
        before=self.values['conker/build/conker.us.elf'];actual=(self.output/'first-linked.elf').read_bytes()
        truth=self.rom[source.ROM:source.ROM+180];source.check_image(before,actual,truth)
        for at in(0,1,100,len(actual)//2,len(actual)-1):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertNotEqual(before,actual)
        for name in list(source.INPUTS)[:6]:
            path=self.output/('before-'+name.replace('/','_'));old=path.read_bytes()
            try:
                path.write_bytes(bytes([old[0]^1])+old[1:])
                with self.assertRaises(ValueError):source.snapshot(self.output)
            finally:path.write_bytes(old)
        source.audit_inputs(ROOT,self.output)if self.installed else source.freeze(ROOT,self.output)
        self.receipt.update(strict_image_controls=5,frozen_input_controls=6,metadata_exclusions=0)
