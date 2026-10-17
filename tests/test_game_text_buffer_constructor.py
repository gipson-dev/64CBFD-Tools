"""Full text-constructor words, memory, native ABI, helper and caller qualification."""
import hashlib
from functools import lru_cache
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_text_buffer_constructor as source
from tools.experiments import game_text_buffer_constructor_installation as install
from tools.tests import text_buffer_constructor_checkpoint as checkpoint
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import test_game_dual_buffer_fade as fade
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command

STACK=point.STACK
TEXT,RECORD,NEXT=0x30000,0x50000,0x39000
SPLIT,MAXIMUM,FACTORY,COPY,INITIALIZE=0x150CFD84,0x150CFDB8,0x15149130,0x10022EC0,0x150CFE3C
PROVIDERS=dict(func_150CFD84=SPLIT,func_150CFDB8=MAXIMUM,func_15149130=FACTORY,memcpy=COPY,func_150CFE3C=INITIALIZE)


def fixture(seed=0,alias=0):
    memory={STACK+i:(i*17+seed*31+0xA5)&255 for i in range(-0x600,0x140)}
    for base in (TEXT,RECORD,NEXT):memory.update({base+i:(i*13+seed*7+0x57)&255 for i in range(-16,0x900)})
    text=(TEXT,RECORD+0x20,RECORD+0x80)[alias]
    args=(0xABCDEF00|(seed&255),text,0xCAFE0000|((seed*199)&65535),
          (0,1,8,64)[seed%4],0xFFFFFF00|((seed*31)&255),
          0x12345600|((seed*71)&255),0xFEDCBA00|((seed*19)&255),seed^0x80001234)
    return memory,args


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x140}


class Oracle(fade.Oracle):
    def __init__(self,words,memory,args,first=3,longest=7,outcome=1,phase=0,mode=0,
                 entry=source.ENTRY,providers=None,connected=None):
        self.io=[];self.first,self.longest,self.outcome,self.effect_mode=first,longest,outcome,mode
        self.names={v:k for k,v in (providers or PROVIDERS).items()};self.copies=[];self.forwarded=[]
        self.names.update({0x150CFD20:'func_150CFD20',0x150CFD5C:'func_150CFD5C'})
        super().__init__(words,memory,args,phase=phase,entry=entry,connected=connected)
        self.incoming_sp=self.r[29]

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def call_args(self,count):
        return tuple(self.r[4:4+min(4,count)])+tuple(read(self.memory,self.r[29]+i*4) for i in range(4,count))

    def record_call(self,target):
        if target==source.ENTRY:
            self.forwarded.append(self.call_args(8));return
        name=self.names.get(target)
        counts=dict(func_150CFD84=2,func_150CFDB8=1,func_15149130=9,memcpy=3,func_150CFE3C=1,
                    func_150CFD20=1,func_150CFD5C=1)
        if name not in counts:raise AssertionError('Unexpected constructor provider '+hex(target))
        args=self.call_args(counts[name]);self.calls.append((name,args))
        if name=='memcpy':self.copies.append(bytes(self.memory[(args[1]+i)&0xffffffff] for i in range(args[2])))

    def hook(self,target):
        name=self.names[target];args=self.calls[-1][1];result=0
        if name=='func_150CFD84':
            put(self.memory,args[1],NEXT);result=self.first
            if self.effect_mode==1:put(self.memory,self.r[29]+108,NEXT)
        elif name=='func_150CFDB8':
            result=self.longest
            if self.effect_mode==2:put(self.memory,self.r[29]+116,17)
        elif name=='func_15149130':result=RECORD if self.outcome else 0
        elif name=='memcpy':
            dst,src,count=args
            for i in range(count):put(self.memory,(dst+i)&0xffffffff,read(self.memory,(src+i)&0xffffffff,1),1)
            result=dst
            if self.effect_mode==3 and count==40:put(self.memory,self.r[29]+116,0)
        elif name=='func_150CFE3C':put(self.memory,args[0]+0x28,read(self.memory,args[0]+0x28,1)^0x80,1)
        else:raise AssertionError(name)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result&0xffffffff


def expected(initial,args,first,longest,outcome,mode=0):
    memory=dict(initial);tag,text,duration,payload,kind,flags,view,owner=args
    calls=[('func_150CFD84',(text,)),('func_150CFDB8',((NEXT if mode==1 else text),))]
    allocation_payload=17 if mode==2 else payload
    calls.append(('func_15149130',((((duration&65535)^32768)-32768)&0xffffffff,
                 0xffffffff,0xffffffff,5,3,71,(allocation_payload+2*longest+42)&0xffffffff,view&255,owner)))
    if outcome:
        fields=((0,tag,1),(4,text,4),(8,1,1),(12,text,4),(16,NEXT,4),(20,first,1),(21,0,1),
                (24,0,4),(28,0,4),(32,0,4),(36,kind,1),(37,flags,1))
        for off,value,size in fields:put(memory,RECORD+40+off,value,size)
        base=RECORD+80;buffer=(base+(0 if mode==3 else allocation_payload))&0xffffffff
        other=(buffer+longest+1)&0xffffffff
        put(memory,RECORD+72,base);put(memory,RECORD+64,buffer);put(memory,RECORD+68,other)
        put(memory,buffer,0,1);put(memory,other,0,1)
        put(memory,RECORD+40,read(memory,RECORD+40,1)^0x80,1)
        calls.extend([('memcpy',(RECORD+40,40)),('func_150CFE3C',(RECORD,))])
    return memory,calls


def calls_without_private_addresses(calls):
    return [(name,(args[0],) if name=='func_150CFD84' else (args[0],args[2]) if name=='memcpy' else args)
            for name,args in calls]


class TextConstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>73I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-constructor',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_full_body_and_bounded_scratch_mapping(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards']),(73,104,12))
        self.assertEqual(self.images[1],self.truth);self.assertEqual(source.normalize(self.images[0]),self.truth)
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],24)
        raw,bindings=source.parts(self.obj)
        for i in range(73):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'func_150CFD20')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        for at in source.PATCHES:
            wrong=list(self.images[0]);wrong[at//4]^=1
            with self.assertRaises(ValueError):source.normalize(wrong)
        original=self.obj.read_bytes();header=ELF_HEADER.unpack_from(original)
        sections=[SECTION_HEADER.unpack_from(original,header[6]+i*header[11]) for i in range(header[12])]
        names=sections[header[13]];strings=original[names[4]:names[4]+names[5]]
        text=next(s for s in sections if read_c_string(strings,s[0])=='.text')
        _,fs,_=source.parse_object(self.obj)
        for at in source.PATCHES:
            wrong=bytearray(original);wrong[text[4]+fs[source.FUNCTION]['value']+at+3]^=1
            path=self.out/('wrong-expected-%X.o'%at);path.write_bytes(wrong)
            with self.assertRaises((ValueError,AssertionError)):
                source.padded_object(self.root,self.out,path,'wrong-%X'%at,self.out/'candidate-guards.csv')
        self.receipt('emission',**self.row,raw_word_controls=73,binding_controls=5,scratch_controls=12,actual_padder_controls=12)

    def test_02_all_descriptor_fields_full_words_aliases_and_null(self):
        count=0;seen=set();holes={1,2,3,9,10,11,22,23,38,39}
        for seed,first,longest,outcome,phase,mode,alias in itertools.product(range(4),(0,1,255,511),
                (0,7,511,0xffffffff),range(2),(0,8),range(4),range(3)):
            memory,args=fixture(seed,alias)
            want,calls=expected(memory,args,first,longest,outcome,mode)
            machines=[Oracle(words,memory,args,first,longest,outcome,phase,mode).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual(m.r[2],RECORD if outcome else 0)
                self.assertEqual(calls_without_private_addresses(m.calls),calls)
                # Host C does not specify padding values; literal guest copies must retain them.
                actual=public(m.memory);expected_public=public(want)
                if outcome:
                    for off in holes:expected_public[RECORD+40+off]=machines[0].copies[0][off]
                self.assertEqual(actual,expected_public)
                self.assertEqual(m.memory,machines[0].memory);self.assertEqual(m.io,machines[0].io)
            self.assertEqual(point.state(machines[2]),point.state(machines[0]))
            seen.update(machines[0].visits);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+292,4)),seen)
        self.receipt('guest',three_way_cases=count,all_73_words_executed=True,aliases=3,phases=2,
            padding_bytes_compared=10,adversarial_home_mutation_modes=3,not_real_helper_mutations=True)

    def test_03_literal_fault_prefixes_not_observer_reads(self):
        count=0
        for outcome,mode,phase in itertools.product(range(2),range(4),(0,8)):
            memory,args=fixture(3)
            good=Oracle(self.truth,memory,args,outcome=outcome,mode=mode,phase=phase).run()
            for at in range(good.all_accesses):
                machines=[Oracle(words,memory,args,outcome=outcome,mode=mode,phase=phase) for words in (self.truth,self.images[1])]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                self.assertEqual(point.state(machines[0]),point.state(machines[1]));self.assertEqual(machines[0].io,machines[1].io)
                count+=1
        self.receipt('faults',two_way_target_prefixes=count,helper_faults_not_inferred=True,call_observers_use_direct_snapshot_reads=True)

    def test_04_native_separate_eight_argument_caller(self):
        driver=NATIVE
        path=self.out/'native-driver.c';path.write_text('#include <ultra64.h>\n'+source.TYPE+driver)
        head='#include <ultra64.h>\nvoid *memcpy(void *, const void *, unsigned int);\ns32 func_150CFD84(u8 *,u8 **);\ns32 func_150CFDB8(u8 *);\nvoid func_150CFE3C(u8 *);\n'+source.TYPE
        controls={'size':source.SELECTED.replace('* 2 + 0x2A','* 2 + 0x28'),
                  'stride':source.SELECTED.replace('(u32)state->buffers[0] + lineBytes','(u32)state->buffers[0] + lineBytes - 1'),
                  'terminator':source.SELECTED.replace('*state->buffers[1] = 0','state->buffers[1][1] = 0')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                c=self.out/('native-'+label+'.c');c.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(c.relative_to(self.root)),
                    str(path.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=2048,profiles=['O2','O0'],UBSan=True,effective_controls=6,
            separate_eight_argument_typed_caller=True,padding_values_not_inferred=True)

    def test_05_independent_original_raw_padded_rebases(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            providers={name:(address if index==0 else 0x18008000+index*0x100000+slot*0x8000)
                       for slot,(name,address) in enumerate(PROVIDERS.items())}
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,providers)
                self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                command=['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION]
                command+=['--defsym=%s=0x%X'%(name,at) for name,at in providers.items()]
                subprocess.run(command+['-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>73I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[2]);self.assertEqual(source.normalize(images[1]),images[0])
            for seed,outcome,mode in itertools.product(range(4),range(2),range(4)):
                memory,args=fixture(seed)
                machines=[Oracle(words,memory,args,outcome=outcome,mode=mode,entry=entry,providers=providers).run() for words in images]
                for m in machines:self.assertEqual(m.memory,machines[0].memory);self.assertEqual(m.calls,machines[0].calls)
                self.assertEqual(point.state(machines[2]),point.state(machines[0]));count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=5)

    def test_06_complete_actual_helpers_and_allocator_boundary(self):
        connected={}
        for entry,size in ((0x150CFD20,60),(0x150CFD5C,40),(SPLIT,52),(MAXIMUM,132),(INITIALIZE,92)):
            rom=entry-0x15000000+0x2D4B0
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%(size//4),self.rom,rom))})
        connected.update({COPY+i*4:w for i,w in enumerate(struct.unpack_from('>11I',self.rom,0x22EC0))})
        count=0
        for text,outcome,phase,payload in itertools.product((b'\0',b'ABC\0',b'AB\xBDLONGER\0',b'\xBDX\xBD\0',b'A'*127+b'\0'),range(2),(0,8),(0,8)):
            memory,args=fixture(1);args=list(args);args[3]=payload
            for i,v in enumerate(text):put(memory,TEXT+i,v,1)
            machines=[Oracle(words,memory,tuple(args),outcome=outcome,phase=phase,connected=connected).run() for words in (self.truth,*self.images)]
            for m in machines:self.assertEqual(m.memory,machines[0].memory);self.assertEqual(m.calls,machines[0].calls)
            self.assertEqual(point.state(machines[2]),point.state(machines[0]));count+=1
        self.receipt('connected',three_way_cases=count,actual_helper_words=94,actual_memcpy_words=11,
            scripted_allocator=True,full_factory_and_gameplay_not_inferred=True)

    def test_07_effective_compiled_guest_controls(self):
        controls={'size':source.SELECTED.replace('* 2 + 0x2A','* 2 + 0x28'),
                  'stride':source.SELECTED.replace('(u32)state->buffers[0] + lineBytes','(u32)state->buffers[0] + lineBytes - 1'),
                  'wide-terminator':source.SELECTED.replace('*state->buffers[1] = 0','*(u32 *)state->buffers[1] = 0')}
        memory,args=fixture(3);good=Oracle(self.truth,memory,args).run()
        before=(self.out/'before-tile_owner').read_text()
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label)
            self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            data,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            wrong=Oracle(words,memory,args).run()
            self.assertNotEqual((public(wrong.memory),wrong.calls),(public(good.memory),good.calls),label)
        self.receipt('semantic-controls',compiled_IDO_effective_controls=list(controls))

    def test_08_three_complete_actual_callers(self):
        count=0
        for caller,end,kind in ((0x150D0134,0x150D01A0,0),(0x150D02B4,0x150D032C,1),(0x150D04C4,0x150D0534,2)):
            rom=caller-0x15000000+0x2D4B0
            caller_words=list(struct.unpack_from('>%dI'%((end-caller)//4),self.rom,rom))
            for seed,outcome,phase in itertools.product(range(4),range(2),(0,8)):
                memory,eight=fixture(seed)
                args=(eight[0],eight[1],eight[2],eight[6],eight[7])
                machines=[Oracle(caller_words,memory,args,outcome=outcome,phase=phase,entry=caller,
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)}).run() for words in (self.truth,*self.images)]
                want=(eight[0]&255,eight[1],((((eight[2]&65535)^32768)-32768)&0xffffffff),8,kind,0,eight[6]&255,eight[7])
                for m in machines:
                    self.assertEqual(m.forwarded,[want]);self.assertEqual(m.memory,machines[0].memory)
                    self.assertEqual(m.calls,machines[0].calls)
                self.assertEqual(point.state(machines[2]),point.state(machines[0]));count+=1
        self.receipt('callers',complete_original_callers=3,caller_words=[27,30,28],three_way_cases=count)

    def test_09_all_protected_live_and_frozen_input_controls(self):
        source.freeze(self.root,self.out);real=hashlib.sha256;cache={}
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        if (self.root/install.BUILD/'after-elf').exists():
            for key in checkpoint.ALL_AFTER:
                for stage in ('before','after'):
                    p=self.root/install.BUILD/(stage+'-'+key);cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Changed dual-buffer live'),(self.out/('before-'+key),'Changed dual-buffer frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',altered),patch.object(Path,'exists',lambda p:p in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_10_complete_first_image_and_reversible_checkpoint(self):
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_complete_image_qualified=True);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed text-constructor checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        self.receipt('installation',installed=True,first_complete_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,game_data=report)

    def test_11_exact_fixture_cache_adapters_without_changing_image_prediction(self):
        out=self.root/install.BUILD;expected=install.compatibility_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-compatibility-prediction.json').read_text()),checkpoint.EXTRA_AFTER)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        if not (out/'after-elf').exists():return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.EXTRA_AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed text-constructor checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        self.receipt('compatibility',checkpoint_controls=count,original_image_pin_unchanged=True,
            original_live_and_frozen_corruption_targets_unchanged=True)


NATIVE=r'''
void *func_150CFF10(u8,u8 *,s16,s32,s8,u8,u8,s32);
static u32 storage[512],input[256],number,first,longest,payload,mode,outcome,error,stage;
static u8 tag,flags,view,kind;static s16 duration;static s32 owner;
s32 func_150CFD84(u8 *p,u8 **next){if(stage++!=0||p!=(u8 *)input)error=22;*next=(u8 *)input+first;return (s32)first;}
s32 func_150CFDB8(u8 *p){if(stage++!=1||p!=(u8 *)input)error=22;return (s32)longest;}
void *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,u32 n,u8 v,s32 o){
if(stage++!=2||a!=duration||b!=-1||c!=-1||d!=5||e!=3||f!=71||n!=payload+longest*2+42||v!=view||o!=owner)error=22;
return outcome?storage:0;}
void *memcpy(void *dst,const void *src,unsigned int n){u32 i;TextDescriptorFC5F0 *p=(TextDescriptorFC5F0 *)src;
if(stage++!=3||dst!=(u8 *)storage+40||n!=40||p->tag!=tag||p->active!=1||p->index||p->length!=(u8)first||
p->source!=(u8 *)input||p->start!=(u8 *)input||p->next!=(u8 *)input+first||p->buffers[0]||p->buffers[1]||p->payload||
(u8)p->kind!=kind||p->flags!=flags)error=22;
for(i=0;i<n;i++)((u8 *)dst)[i]=((const u8 *)src)[i];return dst;}
void func_150CFE3C(u8 *r){TextDescriptorFC5F0 *p=(TextDescriptorFC5F0 *)(r+40);u8 *a=r+80+payload,*b=(u8 *)((u32)a+longest+1);
if(stage++!=4||r!=(u8 *)storage||p->payload!=r+80||p->buffers[0]!=a||p->buffers[1]!=b||*a||*b||b[1]!=0xA5)error=22;
r[40]^=128;}
static int run(void){u32 seed=0x12345678,i,j;u32 lengths[]={0,1,127,255,256,511,0xffffffffu};
if(sizeof(TextDescriptorFC5F0)!=40||__builtin_offsetof(TextDescriptorFC5F0,kind)!=36)return 20;
for(i=0;i<2048;i++){seed=seed*1664525u+1013904223u;number=i;first=lengths[(seed>>5)%6];longest=lengths[(seed>>11)%7];
payload=(seed&3)*8;outcome=(seed>>3)&1;mode=0;tag=(u8)seed;kind=(u8)(seed>>8);flags=(u8)(seed>>16);view=(u8)(seed>>24);
duration=(s16)seed;owner=(s32)(seed^0x80001234u);error=0;stage=0;
for(j=0;j<sizeof(storage);j++)((u8 *)storage)[j]=0xA5;
if(func_150CFF10(tag,(u8 *)input,duration,(s32)payload,(s8)kind,flags,view,owner)!=(outcome?(void *)storage:0)||
error||stage!=(outcome?5u:3u)||(outcome&&((u8 *)storage)[40]!=(u8)(tag^128)))return 22;}
return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
