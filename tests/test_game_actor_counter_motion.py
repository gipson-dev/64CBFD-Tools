"""Literal actor update, float32/access order, native ABI and full-image gates."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_counter_motion as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.check_game_data_layout import audit_layout

STACK,ACTOR=point.STACK,0x20000
CALLER,FREE,TABLE,TICK=0x1513CFE4,0x1516972C,0x80089CB8,0x800BE9E4
SYMBOLS=dict(D_8009FDD4=0x8009FDD4,D_8009FDD8=0x8009FDD8,D_8009FDDC=0x8009FDDC,D_800BE9A4=0x800BE9A4)
CONSTANTS=(0x3E99999A,0x3FACCCCD,0x3F99999A,0x3F800000)
PATTERNS=((1.,-2.5,3.75,.5),(0.,-0.,0.,-0.),(-0.,0.,-0.,0.),(128.,-64.,32.,-16.),
    (0x7FC12345,1.,-2.,.5),(1.,0x7F800000,0xFF800000,2.),(.00001,-.00002,.00003,.00004))


def word(value):return value if isinstance(value,int) else point.bits(value)


def fixture(counter=0,pattern=0,clock=0x3F800000,phase=0,alias=0,symbols=None):
    s=symbols or SYMBOLS
    actor=ACTOR if alias==0 else list(s.values())[(alias-1)%4]-(0x110,0x2C,0x30,0x38,0x1C)[(alias-1)//4]
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x180)}
    for base,size in ((actor-16,0x150),*((at-16,36) for at in s.values())):
        for i in range(size):memory.setdefault(base+i,(i*13+0x57)&255)
    for (name,at),value in zip(s.items(),CONSTANTS):put(memory,at,clock if name=='D_800BE9A4' else value)
    for offset,value in zip((0x2C,0x30,0x38,0x110),PATTERNS[pattern]):put(memory,actor+offset,word(value))
    put(memory,actor+0x1C,counter,2)
    return memory,(actor,)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x180}


def reference(initial,args,symbols=None):
    s=symbols or SYMBOLS;memory=dict(initial);actor=args[0]
    if point.half(read(memory,actor+0x1C,2))<80:
        delta=point.mul(read(memory,s['D_8009FDD4']),read(memory,s['D_800BE9A4']))
        put(memory,actor+0x110,point.add(read(memory,actor+0x110),delta))
        put(memory,actor+0x38,point.sub(read(memory,actor+0x38),read(memory,actor+0x110)))
    if point.half(read(memory,actor+0x1C,2))>=115:
        factor=read(memory,s['D_8009FDD8'])
        put(memory,actor+0x2C,point.mul(read(memory,actor+0x2C),factor))
        put(memory,actor+0x30,point.mul(read(memory,actor+0x30),factor))
    elif point.half(read(memory,actor+0x1C,2))<65:
        put(memory,actor+0x30,point.add(read(memory,actor+0x30),read(memory,s['D_8009FDDC'])))
    return public(memory)


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.io=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if word>>26==32:
            super().execute(word|0x10000000)
            rt=(word>>16)&31
            if rt:self.r[rt]=((self.r[rt]^128)-128)&0xffffffff
            self.dispatched_word=word
        else:super().execute(word)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        if target not in (source.ENTRY,FREE):raise AssertionError('Unexpected actor-motion provider '+hex(target))
        self.calls.append((target,(self.r[4],)))

    def hook(self,target):
        if target!=FREE:raise AssertionError('Actor update must be connected')
        put(self.memory,self.r[4]+0x10,0)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


class ActorCounterMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>39I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-counter-motion',
            (cls.out/'before-motion_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_direct_words_bindings_and_identity_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(39,0,0,7))
        self.assertEqual(self.images,[self.truth,self.truth]);raw,bindings=source.parts(self.obj)
        for i in range(39):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'D_8009FDD0')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,word_controls=39,binding_controls=8)

    def test_02_signed_thresholds_float32_and_complete_private_state(self):
        count=0;seen=set();counters=sorted(set(range(256))|{-32768,-32767,-257,-128,-1,256,32766,32767})
        for counter,pattern,clock,phase in itertools.product(counters,range(len(PATTERNS)),
                (point.bits(0.),point.bits(1.),point.bits(-1.),point.bits(4.)),(0,8)):
            memory,args=fixture(counter,pattern,clock,phase);want=reference(memory,args)
            machines=[Oracle(words,memory,args,phase).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.r[2]),(want,1))
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
            seen.update(machines[0].visits);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        self.receipt('guest',three_way_cases=count,all_39_words_executed=True,full_private_and_target_access_order=True,
            float32_model_not_hardware_or_FCSR=True,NaN_payload_hardware_parity_not_claimed=True)

    def test_03_global_aliases_preserve_reload_and_cached_scale_order(self):
        count=0
        for alias,counter,pattern,phase in itertools.product(range(1,21),(-1,64,65,79,80,114,115,32767),(0,1,3,4),(0,8)):
            memory,args=fixture(counter,pattern,phase=phase,alias=alias);want=reference(memory,args)
            machines=[Oracle(words,memory,args,phase).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual(public(m.memory),want);self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
            count+=1
        self.receipt('aliases',three_way_guest_cases=count,placements=20,guest_only_alias_addresses=True,
            clock_constants_counter_and_output_overlaps=True)

    def test_04_literal_access_fault_prefixes_without_observer_reads(self):
        count=0
        for counter,pattern,phase,alias in itertools.product((-1,64,65,79,80,114,115,32767),(0,4),(0,8),(0,2,6,10,14,18)):
            memory,args=fixture(counter,pattern,phase=phase,alias=alias)
            good=Oracle(self.truth,memory,args,phase).run()
            for at in range(good.all_accesses):
                machines=[Oracle(words,memory,args,phase) for words in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
                count+=1
        self.receipt('faults',three_way_access_prefixes=count,no_observer_memory_reads=True,
            portable_C_fault_or_hardware_exception_parity_not_claimed=True)

    def test_05_nine_independent_links_all_eight_sites_and_signed_low_carries(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=SYMBOLS if index==0 else dict(zip(SYMBOLS,(0x80347FFC+index*0x100000,
                0x80518010+index*0x100000,0x8072FFF8+index*0x100000,0x80938000+index*0x100000)))
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>39I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images,[images[0]]*3)
            for counter,alias,phase in itertools.product((-32768,64,65,79,80,114,115,32767),(0,2,6,10,14,18),(0,8)):
                memory,args=fixture(counter,3,phase=phase,alias=alias,symbols=symbols);want=reference(memory,args,symbols)
                machines=[Oracle(words,memory,args,phase,entry).run() for words in images]
                for m in machines:self.assertEqual(public(m.memory),want);self.assertEqual(point.state(m),point.state(machines[0]))
                count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=8,signed_low_carries=True)

    def test_06_native_separate_typed_caller_and_exhaustive_halfwords(self):
        head='#include <ultra64.h>\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'unsigned-counter':source.SELECTED.replace('*(s16 *)','*(u16 *)'),
            'threshold':source.SELECTED.replace(' < 80',' < 79'),
            'motion-sign':source.SELECTED.replace('(actor + 0x38) -=','(actor + 0x38) +=')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=65536,all_signed_halfwords=True,profiles=['O2','O0'],UBSan=True,
            separately_typed_caller=True,effective_controls=6,valid_nonaliased_objects_only=True,
            native_NaNs_compare_category_not_payload=True)

    def test_07_effective_IDO_threshold_and_cached_factor_controls(self):
        controls={'threshold':source.SELECTED.replace(' < 80',' < 79'),
            'reload-factor':source.SELECTED.replace('*(f32 *)(actor + 0x30) *= factor;','*(f32 *)(actor + 0x30) *= D_8009FDD8;')}
        before=(self.out/'before-motion_owner').read_text();count=0
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label);self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            data,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            memory,args=fixture(79 if label=='threshold' else 115,3,alias=0 if label=='threshold' else 6)
            good=Oracle(self.truth,memory,args).run();wrong=Oracle(words,memory,args).run()
            self.assertNotEqual(public(wrong.memory),public(good.memory),label);count+=1
        self.receipt('semantic-controls',effective_IDO_controls=count,real_alias_exercises_cached_global=True)

    def test_08_actual_dispatcher_slot_three_and_countdown_paths(self):
        caller_words=list(struct.unpack_from('>195I',self.rom,0x16A494));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22E784)[0],source.ENTRY)
        for counter,active,callback,timer,tick,phase in itertools.product((-1,0,64,65,79,80,114,115,32767),range(2),(0,3),range(2),(0,1,3),(0,8)):
            memory,args=fixture(counter,3,phase=phase);actor=args[0]
            for offset,value,size in ((0x10,active,4),(0x58,timer,4),(0x70,callback,1),(0x71,0,1),(0x72,0,1),(0x24,0,4)):
                put(memory,actor+offset,value,size)
            put(memory,TICK,tick);put(memory,TABLE+12,source.ENTRY)
            want=dict(memory);calls=[]
            if active:
                stop=False
                if timer:
                    put(want,actor+0x1C,point.half(read(want,actor+0x1C,2))-tick,2)
                    stop=point.half(read(want,actor+0x1C,2))<0
                if callback:calls.append((source.ENTRY,(actor,)));want=reference(want,args)
                if stop:put(want,actor+0x10,0);calls.append((FREE,(actor,)))
            machines=[Oracle(caller_words,memory,args,phase,CALLER,
                {source.ENTRY+i*4:w for i,w in enumerate(words)}).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.calls),(public(want),calls));self.assertEqual(point.state(m),point.state(machines[0]))
            count+=1
        self.receipt('caller',complete_caller_words=195,three_way_cases=count,table_slot=3,
            bounded_no_animation_no_secondary_callback_paths=True,scripted_free_boundary=True,
            full_dispatcher_path_or_heap_gameplay_coverage_not_claimed=True)

    def test_09_every_protected_live_and_frozen_input(self):
        source.freeze(self.root,self.out);original=Path.read_bytes;real=hashlib.sha256;cache={};count=0
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        for key,path in source.PATHS.items():
            for target,kind in ((self.root/path,'live'),(self.out/('before-'+key),'frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else cache[path] if path in cache else original(path)
                with patch.object(Path,'read_bytes',altered),patch.object(Path,'exists',lambda p:p in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,'Changed counter-motion '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_10_entire_first_image_symbols_data_and_fail_closed_checkpoint(self):
        from tools.experiments import game_actor_counter_motion_installation as install
        from tools.tests import actor_counter_motion_checkpoint as checkpoint
        from tools.tests import test_game_actor_burst_packet_match as serialization
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        baseline=(out/'before-elf').read_bytes();metadata_controls=0
        for group,_,_ in install.SERIALIZATION:
            for name in group:
                row=next(r for r in symbol_rows(baseline) if r[1]==name)
                for address in (row[0]+7,row[3]):
                    wrong=bytearray(baseline);wrong[address]^=1
                    with patch.object(serialization,'SERIALIZATION',install.SERIALIZATION):
                        with self.assertRaises(AssertionError):serialization.apply_burst_symbol_serialization(wrong)
                    metadata_controls+=1
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True,metadata_controls=metadata_controls);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            self.assertEqual((self.root/source.PATHS[key]).read_bytes(),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed actor counter-motion checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        from tools.match_progress import load_elf_functions
        old_functions,_,old_addresses=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new_functions,_,new_addresses=load_elf_functions(str(self.root/source.PATHS['elf']),'mips-linux-gnu-objdump')
        self.assertEqual(old_addresses,new_addresses);self.assertEqual(set(old_functions),set(new_functions))
        self.assertEqual([n for n in old_functions if old_functions[n]!=new_functions[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        for key,path in source.PATHS.items():
            if key not in expected:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,metadata_controls=metadata_controls,game_data=report,
            compared_function_bodies=len(old_functions),only_target_changed=True,all_function_addresses_unchanged=True,
            symbol_definitions_unchanged_except_target_extent=True,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
s32 func_150B9560(u8 *);
f32 D_8009FDD4=0.30000001192092895508f,D_8009FDD8=1.3500000238418579102f,D_8009FDDC=1.2000000476837158203f,D_800BE9A4;
typedef struct {u8 pad00[28];s16 counter;u8 pad1E[14];f32 x,y;u8 pad34[4];f32 z;u8 pad3C[212];f32 step;} Record;
static Record record;
static f32 from(u32 value){union {u32 word;f32 number;} x;x.word=value;return x.number;}
static int same(f32 a,f32 b){union {u32 word;f32 number;} x,y;x.number=a;y.number=b;
if((x.word&0x7fffffff)>0x7f800000u&&(y.word&0x7fffffff)>0x7f800000u)return 1;return x.word==y.word;}
static int run(void){u32 i;u32 choices[]={0,0x80000000u,0x3f800000u,0xc0200000u,0x43000000u,0x7fc12345u,0x7f800000u,0xff800000u};
if(sizeof(void*)!=4||__builtin_offsetof(Record,x)!=44||__builtin_offsetof(Record,z)!=56||__builtin_offsetof(Record,step)!=272)return 20;
for(i=0;i<65536;i++){f32 x,y,z,step,delta,factor;record.counter=(s16)i;
x=from(choices[i%8]);y=from(choices[(i+2)%8]);z=from(choices[(i+4)%8]);step=from(choices[(i+6)%8]);D_800BE9A4=from(choices[(i+1)%5]);
if(i==79){x=1;y=2;z=3;step=1;D_800BE9A4=1;}
record.x=x;record.y=y;record.z=z;record.step=step;
if(record.counter<=79){delta=D_8009FDD4*D_800BE9A4;step=step+delta;z=z-step;}
if(record.counter>114){factor=D_8009FDD8;x=x*factor;y=y*factor;}else if(record.counter<=64)y=y+D_8009FDDC;
if(func_150B9560((u8 *)&record)!=1||!same(record.x,x)||!same(record.y,y)||!same(record.z,z)||!same(record.step,step))return 22;}
return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
