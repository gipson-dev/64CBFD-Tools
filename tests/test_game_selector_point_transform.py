"""Selector width, preserved table ownership, real math and private caller ABI."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_selector_point_transform as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_point_transform_match as math_helper
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string

STACK,ACTOR,OUTPUT,BANK=point.STACK,0x20000,0x24000,0x50000
HELPER,CALLER,DRAW=0x15143134,0x150F2390,0x151C329C
STATUS,DIAGNOSTIC,FLAG=math_helper.STATUS,math_helper.DIAGNOSTIC,math_helper.FLAG
SYMBOLS={source.TABLE_SYMBOL:source.TABLE,'D_800A1920':source.VECTOR,'func_15143134':HELPER}


def fixture(selector=3,flag=0,pattern=0,alias=0,entry=source.ENTRY,symbols=None):
    s=symbols or SYMBOLS
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base,size in ((ACTOR-16,0x240),(OUTPUT-16,64),(STATUS-4,36),(FLAG-4,12),(s['D_800A1920']-4,20),(s[source.TABLE_SYMBOL]-4,44)):
        for i in range(size):memory.setdefault(base+i,(i*13+0x57)&255)
    for i,value in enumerate((0,0xC2340000,0)):put(memory,s['D_800A1920']+i*4,value)
    for i,at in enumerate(source.TABLE_OFFSETS):put(memory,s[source.TABLE_SYMBOL]+i*4,entry+at)
    put(memory,ACTOR+0x1D4,BANK);put(memory,FLAG,flag,1)
    for index in (0x29,0x2D,0x31,0x35,0x39,0x3D):
        values=[0.]*16
        for i in (0,5,10,15):values[i]=.5 if pattern==0 else 1.25
        if pattern==2:values[1],values[4],values[9]=-.25,.75,.125
        values[12:15]=[index*.25,-4.5,5.75+pattern]
        payload=struct.pack('>16I',*[point.bits(v) for v in values])
        if flag:
            integers=[int(v*65536)&0xffffffff for v in values]
            payload=struct.pack('>32H',*[v>>16 for v in integers],*[v&65535 for v in integers])
        for i,b in enumerate(payload):memory[BANK+index*64+i]=b
    out=(OUTPUT,ACTOR+0x1D4,s['D_800A1920'],s[source.TABLE_SYMBOL],BANK+0x29*64)[alias]
    for i in range(12):memory.setdefault(out+i,0xA5)
    return memory,(out,ACTOR,selector&0xffffffff)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x180}


def scripted(matrix,values):
    return tuple(((matrix*17)^(value+i*0x1020304))&0xffffffff for i,value in enumerate(values))


def reference(initial,args,symbols=None):
    s=symbols or SYMBOLS;memory=dict(initial);out,actor,selector=args
    selector&=255
    if not 3<=selector<=8:return memory,[],0
    matrix=(read(memory,actor+0x1D4)+(0x29+(selector-3)*4)*64)&0xffffffff
    values=tuple(read(memory,s['D_800A1920']+i*4) for i in range(3))
    for i,value in enumerate(scripted(matrix,values)):put(memory,out+i*4,value)
    return memory,[(s['func_15143134'],(s['D_800A1920'],out,matrix))],1


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None,symbols=None):
        self.io=[];self.targets=symbols or SYMBOLS
        super().__init__(words,memory,args,[],phase&8,entry,connected)
        # Phase controls alignment; nested frames need their actual entry SP.
        self.r[29]=self.before[29]=STACK+phase

    def args(self,count):
        return tuple(self.r[4+i] if i<4 else read(self.memory,self.r[29]+i*4) for i in range(count))

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        counts={self.targets['func_15143134']:3,source.ENTRY:3,DRAW:3,
            math_helper.CONVERT:2,math_helper.TRANSFORM:7,math_helper.TRANSLATE:3}
        if target not in counts:raise AssertionError('Unexpected selector-point provider '+hex(target))
        args=self.args(counts[target])
        if target==DRAW:self.calls.append((target,args,tuple(read(self.memory,args[0]+i*4) for i in range(3))))
        else:self.calls.append((target,args))
        self.observations.append((target,tuple(self.r[16:24]),read(self.memory,STATUS)))

    def hook(self,target):
        if target==self.targets['func_15143134']:
            template,out,matrix=self.args(3)
            values=tuple(read(self.memory,template+i*4) for i in range(3))
            for i,value in enumerate(scripted(matrix,values)):put(self.memory,out+i*4,value)
        elif target!=DRAW:raise AssertionError('Real math helpers must be connected')
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


def state(m):return point.state(m),m.condition,m.io


def section_row(path,name):
    data=path.read_bytes();h=ELF_HEADER.unpack_from(data)
    rows=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
    names=rows[h[13]];strings=data[names[4]:names[4]+names[5]]
    return next(r for r in rows if read_c_string(strings,r[0])==name)


class SelectorPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-selector-point',
            (cls.out/'before-phase_original').read_text(),source.FUNCTION)
        cls.helper=list(struct.unpack_from('>98I',cls.rom,0x1705E4));cls.connected={}
        for address,offset,count in ((HELPER,0x1705E4,98),(math_helper.CONVERT,0x21D368,46),(math_helper.TRANSFORM,0xD4E10,40)):
            cls.connected.update({address+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%count,cls.rom,offset))})

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,images=None,entry=source.ENTRY,symbols=None):
        want,calls,result=reference(memory,args,symbols)
        machines=[Oracle(w,memory,args,phase,entry,symbols=symbols).run() for w in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(want),calls,result));self.assertEqual(state(m),state(machines[0]))
        return machines[0]

    def test_01_complete_words_bindings_and_exact_pool_ownership(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(43,24,0,8))
        self.assertEqual(self.images,[self.truth,self.truth]);raw,bindings=source.parts(self.obj)
        for i in range(43):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'changed')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        row=section_row(self.obj,'.rodata');count=0
        for i in range(8):
            data=bytearray(self.obj.read_bytes());data[row[4]+i*4+3]^=4
            path=self.out/('pool-control-%d.o'%i);path.write_bytes(data)
            with self.assertRaises(ValueError):source.checked_pool(path)
            count+=1
        row=section_row(self.obj,'.rel.rodata')
        data=bytearray(self.obj.read_bytes());data[row[4]+7]^=1
        wrong=self.out/'pool-relocation-control.o';wrong.write_bytes(data)
        with self.assertRaises(ValueError):source.checked_pool(wrong)
        self.receipt('emission',**self.row,word_controls=43,binding_controls=5,pool_controls=count+1,
            compiler_pool_is_not_duplicated_runtime_data=True)

    def test_02_all_byte_selectors_high_bits_lazy_invalid_inputs_and_aliases(self):
        count=0;seen=set()
        for low,high,phase in itertools.product(range(256),(0,0x10000,0x80000000,0xffffff00),(0,8)):
            memory,args=fixture(high|low)
            if not 3<=low<=8:args=(0,0,args[2])
            m=self.compare(memory,args,phase);seen.update(m.visits)
            self.assertEqual(read(m.memory,STACK+phase+4),args[1])
            self.assertEqual(read(m.memory,STACK+phase+8),args[2]);count+=1
        aliases=0
        for selector,alias,phase in itertools.product(range(3,9),range(1,5),(0,8)):
            memory,args=fixture(selector,alias=alias);self.compare(memory,args,phase);aliases+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4)))
        self.receipt('guest',three_way_cases=count,alias_cases=aliases,all_43_words=True,all_byte_values=True,
            full_width_selector_home_preserved=True,invalid_selector_null_actor_output_lazy=True,
            full_private_state_and_access_order=True,extended_aliases_guest_only=True)

    def test_03_actual_point_wrapper_matrix_conversion_and_transform(self):
        count=0
        for selector,flag,pattern,phase in itertools.product(range(3,9),(0,1,255),range(3),(0,8)):
            memory,args=fixture(selector,flag,pattern);out,actor,_=args
            matrix=read(memory,actor+0x1D4)+(0x29+(selector-3)*4)*64
            expected=math_helper.PointOracle(self.helper,memory,(source.VECTOR,out,matrix),(phase-24)&8)
            expected.r[29]=expected.before[29]=STACK+phase-24
            expected.run()
            calls=[(HELPER,(source.VECTOR,out,matrix)),*((r[0],r[1]) for r in expected.calls)]
            machines=[Oracle(w,memory,args,phase,connected=self.connected).run() for w in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.calls,m.r[2]),(public(expected.memory),calls,1));self.assertEqual(state(m),state(machines[0]))
            count+=1
        self.receipt('connected',three_way_cases=count,point_wrapper_words=98,SDK_conversion_slot_words=46,
            matrix_transform_words=40,original_helpers=True,existing_independent_SDK_reference=True,
            finite_exact_fixed_domain=True,FCSR_and_hardware_not_claimed=True)

    def test_04_real_access_fault_prefixes(self):
        count=0
        for selector,flag,phase,connected in itertools.product((0,3,8),(0,1),(0,8),(None,self.connected)):
            memory,args=fixture(selector,flag)
            good=Oracle(self.truth,memory,args,phase,connected=connected).run()
            for at in range(good.all_accesses):
                machines=[Oracle(w,memory,args,phase,connected=connected) for w in (self.truth,*self.images)]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,at)
                for m in machines[1:]:self.assertEqual(state(m),state(machines[0]))
                count+=1
        self.receipt('faults',three_way_prefixes=count,actual_helper_chain=True,no_observer_accesses=True,
            portable_C_fault_or_hardware_exception_parity_not_claimed=True)

    def test_05_nine_independent_links_and_table_jump_targets(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=SYMBOLS if index==0 else {source.TABLE_SYMBOL:0x80347FFC+index*0x100000,
                'D_800A1920':0x80518000+index*0x100000,'func_15143134':0x15187FFC+index*0x10000}
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj)
                rs={at:[(kind,source.TABLE_SYMBOL if name=='.rodata' else name) for kind,name in rows] for at,rows in rs.items()}
                text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertEqual(unknown,[])
                stem=self.out/('rebase-%d-%s'%(index,label));asm=stem.with_suffix('.s');asm.write_text(text)
                compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images,[images[0]]*3)
            for selector,phase,alias in itertools.product((0,3,4,5,6,7,8,9,0x10003,0xffffff08),(0,8),(0,2)):
                memory,args=fixture(selector,alias=alias,entry=entry,symbols=symbols)
                self.compare(memory,args,phase,images,entry,symbols);count+=1
        memory,args=fixture(3);put(memory,source.TABLE,source.ENTRY+0x44)
        wrong=Oracle(self.truth,memory,args).run()
        good_mem,good_args=fixture(3);good=Oracle(self.truth,good_mem,good_args).run()
        self.assertNotEqual(wrong.calls,good.calls)
        self.receipt('rebases',independent_links=9,three_way_cases=count,bindings=5,
            table_and_template_independent_signed_low_carries=True,effective_runtime_table_target_control=True)

    def test_06_native32_typed_selector_and_effective_controls(self):
        head='#include <ultra64.h>\n#include "structs.h"\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'record':source.SELECTED.replace('index = 0x3D','index = 0x3C'),
            'stride':source.SELECTED.replace('(index << 6)','(index << 5)')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,
            separately_typed_caller=True,effective_controls=4,scripted_helper_not_retail_math=True,
            valid_complete_nonaliased_objects=True,float_array_pointer_roundtrip=True)

    def test_07_compiled_width_record_and_unwanted_initialization_controls(self):
        before=(self.out/'before-fixed_owner').read_text();count=0
        controls={'width':source.SELECTED.replace('u8 selector)','u32 selector)'),
            'record':source.SELECTED.replace('index = 0x3D','index = 0x3C'),
            'clear':source.SELECTED.replace('    switch (selector) {',
                '    output->unk0 = 0.0f;\n    output->unk4 = 0.0f;\n    output->unk8 = 0.0f;\n\n    switch (selector) {')}
        for label,body in controls.items():
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label);self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            raw=source.raw_object(self.root,self.out,obj,'control-'+label)
            data,fs=source.build.link_owner(self.root,self.out,raw,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            memory,args=fixture(0x10003 if label=='width' else 8 if label=='record' else 2)
            phase=0
            if label=='clear':args=(STACK-12,args[1],args[2]);phase=-0x28
            good=Oracle(self.truth,memory,args,phase).run();wrong=Oracle(words,memory,args,phase).run()
            if label=='clear':
                self.assertNotEqual([read(good.memory,args[0]+i*4) for i in range(3)],
                    [read(wrong.memory,args[0]+i*4) for i in range(3)])
            else:self.assertNotEqual((good.calls,good.r[2]),(wrong.calls,wrong.r[2]))
            count+=1
        self.receipt('controls',effective_IDO_controls=count,high_bits_exercise_byte_truncation=True,
            unsupported_selector_preserves_real_private_output=True)

    def test_08_actual_caller_keeps_unsupported_selector_stack_payload(self):
        caller=list(struct.unpack_from('>20I',self.rom,0x11F840));count=stale=0
        for selector,present,phase in itertools.product((0,2,3,4,5,6,7,8,9,255,0x10003,0xffffff08),(0,1),(0,8)):
            memory,args=fixture(selector);actor=args[1]
            if not present:put(memory,actor+0x1D4,0)
            want=dict(memory);calls=[];out=STACK+phase-12
            if present:
                want,math_calls,_=reference(want,(out,actor,selector&255))
                calls=[(source.ENTRY,(out,actor,selector&255)),*math_calls,
                    (DRAW,(out,255,0),tuple(read(want,out+i*4) for i in range(3)))]
                if not 3<=selector&255<=8:
                    self.assertEqual([read(want,out+i*4) for i in range(3)],[read(memory,out+i*4) for i in range(3)]);stale+=1
            machines=[Oracle(caller,memory,(actor,selector,0x87654321),phase,CALLER,
                {source.ENTRY+i*4:w for i,w in enumerate(words)}).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.calls),(public(want),calls));self.assertEqual(state(m),state(machines[0]))
            count+=1
        self.receipt('caller',complete_caller_words=20,three_way_cases=count,unsupported_stale_point_cases=stale,
            exact_private_draw_payload=True,draw_is_scripted_boundary=True,portable_uninitialized_C_or_gameplay_not_claimed=True)

    def test_09_every_live_and_frozen_input(self):
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
                    with self.assertRaisesRegex(ValueError,'Changed selector-point '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),effective_controls=count)

    def test_10_entire_first_image_table_data_and_checkpoint(self):
        from tools.experiments import game_selector_point_transform_installation as install
        from tools.tests import selector_point_checkpoint as checkpoint
        from tools.tests import test_game_actor_burst_packet_match as serialization
        from tools.match_progress import load_elf_functions
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out);baseline=(out/'before-elf').read_bytes()
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf']);metadata=0
        for group,_,_ in install.SERIALIZATION:
            for name in group:
                row=next(r for r in symbol_rows(baseline) if r[1]==name)
                for at in (row[0]+7,row[3]):
                    wrong=bytearray(baseline);wrong[at]^=1
                    with patch.object(serialization,'SERIALIZATION',install.SERIALIZATION):
                        with self.assertRaises(AssertionError):serialization.apply_burst_symbol_serialization(wrong)
                    metadata+=1
        if not (out/'after-elf').exists():
            self.receipt('installation',installed=False,first_image_qualified=True,metadata_controls=metadata);return
        original=Path.read_bytes;count=0
        for key,data in expected.items():
            from tools.tests import halfword_point_checkpoint as latest
            self.assertEqual(latest.previous_input((self.root/source.PATHS[key]).read_bytes(),source.PATHS[key],self.root),data)
            self.assertEqual(hashlib.sha256(data).hexdigest(),checkpoint.AFTER[key])
            self.assertEqual(checkpoint.previous_input(data,source.PATHS[key],self.root),(out/('before-'+key)).read_bytes())
            for stage in ('before','after'):
                target=out/(stage+'-'+key);wrong=bytearray(target.read_bytes());wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else original(path)
                with patch.object(Path,'read_bytes',altered):
                    with self.assertRaisesRegex(AssertionError,'Changed selector-point checkpoint fixture'):
                        checkpoint.previous_input(data,source.PATHS[key],self.root)
                count+=1
            wrong=bytearray(data);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
            self.assertEqual(checkpoint.previous_input(wrong,source.PATHS[key],self.root),wrong);count+=1
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        old,_,oa=load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
        new,_,na=load_elf_functions(str(out/'after-elf'),'mips-linux-gnu-objdump')
        self.assertEqual(oa,na);self.assertEqual(set(old),set(new))
        self.assertEqual([n for n in old if old[n]!=new[n]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        self.assertEqual(sorted(old_symbols),sorted((n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])))
        owned={source.PATHS[k] for k in expected}
        for key,path in source.PATHS.items():
            if path not in owned:self.assertEqual((self.root/path).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,metadata_controls=metadata,game_data=report,compared_function_bodies=len(old),
            only_target_changed=True,all_function_addresses_unchanged=True,
            symbol_definitions_unchanged_except_target_extent=True,all_other_protected_inputs_unchanged=True)


NATIVE=r'''
s32 func_150F22D0(struct17 *,u8 *,u8);
f32 D_800A1920[3]={0.f,-45.f,0.f};
typedef struct {u8 pad[468];u8 *bank;} Actor;
static Actor actor;
static u8 bank[4096];
static f32 output[3];
static int calls;
static f32 *lastPoint,*lastOutput;
static u8 *lastMatrix;
void func_15143134(f32 *point,f32 *out,u8 *matrix){calls++;lastPoint=point;lastOutput=out;lastMatrix=matrix;
out[0]=(f32)((matrix-bank)/64);out[1]=point[1];out[2]=.5f;}
static int run(void){int i,result,valid,index;
if(sizeof(void*)!=4||sizeof(struct17)!=12||__builtin_offsetof(Actor,bank)!=468)return 20;
actor.bank=bank;
for(i=0;i<256;i++){calls=0;output[0]=99.f;output[1]=98.f;output[2]=97.f;valid=i>=3&&i<=8;index=0x29+(i-3)*4;
result=func_150F22D0((struct17 *)output,valid?(u8 *)&actor:(u8 *)0,(u8)i);
if(result!=valid||calls!=valid)return 22;
if(valid){if(lastPoint!=D_800A1920||lastOutput!=output||lastMatrix!=bank+index*64||output[0]!=(f32)index||output[1]!=-45.f||output[2]!=.5f)return 22;}
else if(output[0]!=99.f||output[1]!=98.f||output[2]!=97.f)return 22;
if(!valid&&func_150F22D0((struct17 *)0,(u8 *)0,(u8)i)!=0)return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
