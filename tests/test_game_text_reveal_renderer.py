"""Direct reveal words, ordered float/copy semantics, native ABI and private data."""
import hashlib
from functools import lru_cache
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_text_reveal_renderer as source
from tools.experiments import game_text_buffer_constructor as constructor
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.check_game_data_layout import audit_layout

STACK=point.STACK
RECORD,PAYLOAD,ALT,LINE,OTHER=0x20000,0x30000,0x30100,0x60000,0x60100
COPY,COLOR,TEXT,SUBMIT=0x10022EC0,0x1504332C,0x15042D94,0x15042ECC
SYMBOLS=dict(D_800A0880=0x800A0880,D_800A0888=0x800A0888,D_800BE9A4=0x800BE9A4,
    memcpy=COPY,func_1504332C=COLOR,func_15042D94=TEXT)


def fixture(fraction=0,count=0,length=7,flags=0,clock=1,index=0,symbols=None,alias=0):
    s=symbols or SYMBOLS
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base,size in ((RECORD-16,0x480),(PAYLOAD-16,0x180),(LINE-16,0x280),(0x800CBD50,64)):
        memory.update({base+i:(i*13+0x57)&255 for i in range(size)})
    for name,size in (('D_800A0880',5),('D_800A0888',4),('D_800BE9A4',4)):
        for i in range(size):memory[s[name]+i]=0
    for i,v in enumerate(b'C:> \0'):put(memory,s['D_800A0880']+i,v,1)
    put(memory,s['D_800A0888'],0x3EDFBE77);put(memory,s['D_800BE9A4'],point.bits(float(clock)))
    payload=(PAYLOAD,RECORD+0x28,RECORD+0x34)[alias]
    put(memory,RECORD+0x48,payload);put(memory,payload,fraction);put(memory,payload+4,count,2)
    put(memory,RECORD+0x30,flags,1);put(memory,RECORD+0x3C,length,1);put(memory,RECORD+0x3D,index,1)
    for i in range(256):put(memory,RECORD+0x40+i*4,LINE if i%2==0 else OTHER)
    put(memory,RECORD+0x48,payload)
    return memory,(RECORD,)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x180}


def effects(memory,ordinal,mode,payload):
    if ordinal==1:
        if mode==1:
            put(memory,RECORD+0x3D,read(memory,RECORD+0x3D,1)^1,1);put(memory,payload+4,3,2)
        elif mode==3:put(memory,RECORD+0x48,ALT)
    if ordinal==2 and mode==2:put(memory,payload+4,2,2)


def reference(initial,mode=0,symbols=None):
    s=symbols or SYMBOLS;memory=dict(initial);payload=read(memory,RECORD+0x48)
    if read(memory,RECORD+0x30,1)&1:put(memory,payload+4,0,2);put(memory,payload,0)
    if point.floating(read(memory,payload))<float(read(memory,RECORD+0x3C,1)):
        put(memory,payload,point.add(read(memory,payload),point.mul(read(memory,s['D_800A0888']),read(memory,s['D_800BE9A4']))))
        while 1.0<point.floating(read(memory,payload)):
            count=point.half(read(memory,payload+4,2)+1)
            put(memory,payload+4,min(count,read(memory,RECORD+0x3C,1)),2)
            put(memory,payload,point.sub(read(memory,payload),point.bits(1.0)))
    effects(memory,1,mode,payload)
    count=point.half(read(memory,payload+4,2));assert 0<=count<=73
    buffer=read(memory,RECORD+0x40+read(memory,RECORD+0x3D,1)*4)
    message=bytearray(bytes(memory[s['D_800A0880']+i] for i in range(4)))
    message.extend(memory[buffer+i] for i in range(count))
    effects(memory,2,mode,payload)
    count=point.half(read(memory,payload+4,2))
    # The scripted second-copy mutation shortens the displayed prefix.
    message=message[:count+4]+b' \xBB\0'
    return public(memory),bytes(message).split(b'\0',1)[0]+b'\0'


class PrefixBoundary(Exception):pass


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,mode=0,phase=0,symbols=None,entry=source.ENTRY,connected=None,tick_limit=None):
        self.s=symbols or SYMBOLS;self.io=[];self.payloads=[];self.messages=[];self.ordinal=0
        record=args[1] if entry==0x150D0034 else args[0]
        self.payload=read(memory,record+0x48);self.reveal_mode=mode;self.ticks=0;self.tick_limit=tick_limit
        super().__init__(words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if self.tick_limit is not None and self.ticks==self.tick_limit:raise PrefixBoundary
        self.ticks+=1
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
        if self.own_instruction and self.recording:self.io.append(('W',address,size,value&((1<<(8*size))-1)))

    def record_call(self,target):
        if target==SUBMIT:
            pointer=self.r[5]
            self.payloads.append(tuple(read(self.memory,pointer+i*4) for i in range(16)));return
        if target==source.ENTRY:self.calls.append((target,(self.r[4],)));return
        count=3 if target==self.s['memcpy'] else 4
        if target not in (self.s['memcpy'],self.s['func_1504332C'],self.s['func_15042D94']):raise AssertionError(hex(target))
        args=tuple(self.r[4:4+count]);self.calls.append((target,args))
        if target==self.s['func_15042D94']:
            pointer=args[3];message=[]
            for i in range(80):
                message.append(read(self.memory,pointer+i,1))
                if message[-1]==0:break
            self.messages.append(bytes(message))

    def hook(self,target):
        if target==SUBMIT:return
        result=0
        if target==self.s['memcpy']:
            dst,src,count=self.calls[-1][1]
            if count>80:raise PrefixBoundary
            for i in range(count):put(self.memory,dst+i,read(self.memory,src+i,1),1)
            self.ordinal+=1;effects(self.memory,self.ordinal,self.reveal_mode,self.payload);result=dst
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result


class TextRevealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>102I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-reveal',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_direct_complete_emission_and_effective_identity_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['new_guards'],self.row['unchanged_raw_padded_neighbors']),(102,128,0,24))
        self.assertEqual(self.images,[self.truth,self.truth]);raw,bindings=source.parts(self.obj)
        for i in range(102):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'D_800A0890')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,word_controls=102,binding_controls=10)

    def test_02_ordered_float_count_copy_and_public_reference(self):
        count=0;seen=set()
        fractions=(0,0x80000000,point.bits(.5),point.bits(1),point.bits(1.0000001192092896),point.bits(2.75),0x7FC12345,0x7F800000,0xFF800000)
        for fraction,chars,length,flags,clock,index,phase in itertools.product(fractions,(0,1,7),(0,1,7,73,128,255),(0,1,2),(0,1,4,-1),range(2),(0,8)):
            memory,args=fixture(fraction,chars,length,flags,clock,index)
            want,message=reference(memory)
            machines=[Oracle(words,memory,args,phase=phase).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.messages,m.r[2]),(want,[message],1))
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
            seen.update(machines[0].visits);count+=1
        unreachable={source.ENTRY+i*4 for i in (25,26,27)}
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-unreachable)
        self.receipt('guest',three_way_cases=count,reachable_retail_words=99,unsigned_fallback_unreachable_after_LBU=3,
            float32_reference_not_FCSR_or_hardware=True,all_private_state_compared=True)

    def test_03_aliases_reloads_full_byte_index_and_scripted_copy_mutations(self):
        count=0
        for alias,mode,index,phase in itertools.product(range(3),range(4),(0,1,127,255),(0,8)):
            memory,args=fixture(point.bits(.5),7,73,index=index,alias=alias)
            want,message=reference(memory,mode)
            machines=[Oracle(words,memory,args,mode,phase).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual((public(m.memory),m.messages),(want,[message]))
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
            count+=1
        for phase,chars in itertools.product((0,8),(0,72,73)):
            memory,args=fixture(point.bits(255),chars,255)
            want,message=reference(memory)
            for words in (self.truth,*self.images):
                m=Oracle(words,memory,args,phase=phase).run();self.assertEqual((public(m.memory),m.messages),(want,[message]))
            count+=1
        self.receipt('aliases',three_way_cases=count,payload_placements=3,scripted_copy_modes=3,
            full_byte_indices=[0,1,127,255],maximum_defined_visible_characters=73)

    def test_04_literal_access_faults_and_bounded_malformed_prefixes(self):
        count=0
        for flags,fraction,mode,phase in itertools.product((0,1),(0,point.bits(2.75)),range(4),(0,8)):
            memory,args=fixture(fraction,7,73,flags)
            good=Oracle(self.truth,memory,args,mode,phase).run()
            for at in range(good.all_accesses):
                machines=[Oracle(words,memory,args,mode,phase) for words in (self.truth,self.images[1])]
                for m in machines:
                    m.access_fault=at
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(point.state(machines[0]),point.state(machines[1]));self.assertEqual(machines[0].io,machines[1].io);count+=1
        prefixes=0
        for chars,fraction,clock in ((0xffff,point.bits(255),1),(32767,point.bits(2),1),(0,0,float('inf'))):
            memory,args=fixture(fraction,chars,255,clock=clock)
            machines=[Oracle(words,memory,args,tick_limit=90) for words in (self.truth,*self.images)]
            for m in machines:
                with self.assertRaises(PrefixBoundary):m.run()
            for m in machines[1:]:self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.io,machines[0].io)
            prefixes+=1
        self.receipt('faults',literal_target_access_prefixes=count,malformed_tick_or_copy_prefixes=prefixes,
            observer_reads_not_fault_accesses=True,malformed_completion_or_portable_C_faults_not_inferred=True)

    def test_05_independent_original_raw_padded_rebases(self):
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=dict(SYMBOLS)
            if index:
                symbols.update(D_800A0880=0x80347FFC+index*0x100000,D_800A0888=0x80518010+index*0x100000,
                    D_800BE9A4=0x8072FFF8+index*0x100000,memcpy=0x18010000+index*0x100000,
                    func_1504332C=0x18028000+index*0x100000,func_15042D94=0x18037FFC+index*0x100000)
            images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.out/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>102I',source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images,[images[0]]*3)
            for fraction,mode,phase in itertools.product((0,point.bits(2.75),0x7FC12345),range(4),(0,8)):
                memory,args=fixture(fraction,7,73,symbols=symbols);want,message=reference(memory,mode,symbols)
                machines=[Oracle(words,memory,args,mode,phase,symbols,entry).run() for words in images]
                for m in machines:
                    self.assertEqual((public(m.memory),m.messages),(want,[message]));self.assertEqual(point.state(m),point.state(machines[0]))
                count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,all_ten_bindings=True,signed_low_carries=True)

    def test_06_actual_memcpy_color_variadic_wrapper_and_dispatcher(self):
        connected={}
        for entry,rom,words in ((COPY,0x22EC0,11),(COLOR,0x707DC,22),(TEXT,0x70244,42)):
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%words,self.rom,rom))})
        count=0
        for flags,chars,phase in itertools.product((0,1),(0,7,73),(0,8)):
            memory,args=fixture(point.bits(255),chars,255,flags)
            machines=[Oracle(words,memory,args,phase=phase,connected=connected).run() for words in (self.truth,*self.images)]
            self.assertEqual(len(machines[0].payloads),1)
            for m in machines:
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.payloads,machines[0].payloads)
            count+=1
        caller=0x150D0034;caller_words=list(struct.unpack_from('>35I',self.rom,0xFD4E4))
        for phase,flags in itertools.product((0,8),(0,1,255)):
            memory,args=fixture(0,7,73,flags);put(memory,RECORD+0x4C,1,1);put(memory,RECORD+0x38,0x76543210)
            put(memory,0x800888A0+4,source.ENTRY)
            caller_args=(0x76543210,RECORD,0x87654321)
            machines=[Oracle(caller_words,memory,caller_args,phase=phase,entry=caller,
                connected=connected|{source.ENTRY+i*4:w for i,w in enumerate(words)}).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.payloads,machines[0].payloads)
                self.assertEqual(read(m.memory,RECORD+0x30,1),flags&254)
                self.assertEqual(m.r[2],caller_args[0])
            count+=1
        overlaps=0
        for phase,offset in itertools.product((0,8),(-4,0,1,4,8,12)):
            memory,args=fixture(point.bits(255),7,255)
            put(memory,RECORD+0x40,STACK-phase-128+40+offset)
            machines=[Oracle(words,memory,args,phase=phase,connected=connected).run() for words in (self.truth,*self.images)]
            for m in machines:
                self.assertEqual(point.state(m),point.state(machines[0]));self.assertEqual(m.payloads,machines[0].payloads)
            overlaps+=1
        self.receipt('connected',three_way_cases=count,actual_memcpy_words=11,actual_color_words=22,
            actual_text_wrapper_words=42,copied_payload_words=16,actual_dispatcher_words=35,
            guest_only_actual_copy_overlap_cases=overlaps,portable_C_overlap_not_inferred=True,
            real_text_consumer_and_presentation_not_executed=True)

    def test_07_native_typed_caller_float_boundaries_and_effective_controls(self):
        head='#include <ultra64.h>\nextern f32 D_800BE9A4;\nvoid *memcpy(void *,const void *,unsigned int);\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text('#include <ultra64.h>\n'+source.TYPE+constructor.TYPE+NATIVE)
        controls={'cursor':source.SELECTED.replace('= 0xBB','= 0xBA'),
            'threshold':source.SELECTED.replace('if (1.0f < payload->fraction)','if (1.0f <= payload->fraction)'),
            'reset':source.SELECTED.replace('payload->characters = 0;','payload->characters = 1;')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=2048,profiles=['O2','O0'],UBSan=True,separate_typed_caller=True,
            effective_controls=6,malformed_or_hardware_float_behavior_not_inferred=True)

    def test_08_compiled_guest_semantic_controls(self):
        before=(self.out/'before-tile_owner').read_text();memory,args=fixture(point.bits(1),7,73,clock=0)
        good=Oracle(self.truth,memory,args).run();count=0
        for label,body in (('cursor',source.SELECTED.replace('= 0xBB','= 0xBA')),
                ('threshold',source.SELECTED.replace('if (1.0f < payload->fraction)','if (1.0f <= payload->fraction)'))):
            obj,diag=source.compile_owner(self.root,self.out,source.recovered_owner(before,body),'control-'+label);self.assertFalse(diag)
            with self.assertRaises(ValueError):source.checked_parts(*source.parts(obj))
            data,fs=source.build.link_owner(self.root,self.out,obj,source.OWNER);f=fs[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            wrong=Oracle(words,memory,args).run()
            self.assertNotEqual((public(wrong.memory),wrong.messages),(public(good.memory),good.messages));count+=1
        self.receipt('semantic-controls',effective_IDO_controls=count)

    def test_09_protected_live_and_frozen_inputs(self):
        source.freeze(self.root,self.out);original=Path.read_bytes;original_exists=Path.exists;real=hashlib.sha256;count=0;cache={}
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        for key,path in source.PATHS.items():
            for target,kind in ((self.root/path,'live'),(self.out/('before-'+key),'frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def altered(path):return wrong if path==target else cache[path] if path in cache else original(path)
                with patch.object(Path,'read_bytes',altered),patch.object(Path,'exists',lambda p:p in cache or original_exists(p)),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,'Changed reveal '+kind+' input'):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),effective_controls=count)

    def test_10_first_complete_image_and_fail_closed_checkpoint(self):
        from tools.experiments import game_text_reveal_installation as install
        from tools.tests import text_reveal_checkpoint as checkpoint
        out=self.root/install.BUILD;expected=install.expected_inputs(self.root,out)
        self.assertEqual(json.loads((out/'initial-prediction.json').read_text()),checkpoint.AFTER)
        self.assertEqual((out/'prelink-prediction.elf').read_bytes(),expected['elf'])
        from tools.tests import test_game_actor_burst_packet_match as serialization
        from tools.tests.test_game_one_shot_timer_match import symbol_rows
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
                    with self.assertRaisesRegex(AssertionError,'Changed text reveal checkpoint fixture'):
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
        self.assertEqual([name for name in old_functions if old_functions[name]!=new_functions[name]],[source.FUNCTION])
        old_symbols=[(n,(f[1],source.SIZE if n==source.FUNCTION else f[2],*f[3:])) for _,n,f,_ in symbol_rows(baseline)]
        new_symbols=[(n,f[1:]) for _,n,f,_ in symbol_rows(expected['elf'])]
        self.assertEqual(sorted(old_symbols),sorted(new_symbols))
        for key in source.PATHS:
            if key not in expected:self.assertEqual((self.root/source.PATHS[key]).read_bytes(),(out/('before-'+key)).read_bytes())
        self.receipt('installation',installed=True,entire_first_image_exact=True,metadata_exclusions=0,
            checkpoint_controls=count,metadata_controls=metadata_controls,game_data=report,all_other_protected_inputs_unchanged=True,
            compared_function_bodies=len(old_functions),target_only_changed=True,all_function_addresses_unchanged=True,
            all_symbol_definitions_unchanged_except_target_extent=True)


NATIVE=r'''
f32 D_800BE9A4,D_800A0888=0.43700000643730163574f;
TextRevealHeaderFC5F0 D_800A0880={{'C',':','>',' ',0}};
s32 func_150D032C(u8 *);
static struct {u8 prefix[40];TextDescriptorFC5F0 state;} record;
static TextRevealPayloadFC5F0 payload;
static u8 line[80],other[80],expected[80];
static u32 stage,error,expectedCount;static f32 expectedFraction;
void *memcpy(void *dst,const void *src,unsigned int n){u32 i;
if(stage==0&&(n!=4||((const u8 *)src)[0]!='C'||((const u8 *)src)[3]!=' '))error=22;
if(stage==1&&(n!=expectedCount||src!=record.state.buffers[record.state.index]))error=22;
stage++;for(i=0;i<n;i++)((u8 *)dst)[i]=((const u8 *)src)[i];return dst;}
void func_1504332C(u8 a,u8 b,u8 c,u8 d){if(stage++!=2||a||b!=255||c||d!=150)error=22;}
void func_15042D94(s32 x,s32 y,u8 flags,s32 address,...){u32 i;u8 *p=(u8 *)address;
if(stage++!=3||x!=15||y!=190||flags!=128)error=22;
for(i=0;i<expectedCount+7;i++)if(p[i]!=expected[i])error=22;}
static int run(void){u32 i,j,seed=0x12345678;f32 choices[]={0.0f,-0.0f,0.5f,1.0f,1.0000001192092895508f,2.75f,255.0f};
if(sizeof(payload)!=8||sizeof(TextRevealHeaderFC5F0)!=5||sizeof(record.state)!=40)return 20;
for(i=0;i<2048;i++){f32 value,delta;u32 count,length,flags;
seed=seed*1664525u+1013904223u;flags=(seed>>15)&3;length=(u32[]){0,1,7,73,128,255}[i%6];
count=i%8;value=choices[i%7];D_800BE9A4=(f32)((s32)(i%6)-1);
if(i==0){flags=0;length=73;count=7;value=1.0f;D_800BE9A4=0.0f;}
payload.fraction=value;payload.characters=(s16)count;
record.state.active=(u8)flags;record.state.payload=(u8 *)&payload;record.state.length=(u8)length;
record.state.index=(u8)(seed&1);record.state.buffers[0]=line;record.state.buffers[1]=other;
if(flags&1){count=0;value=0.0f;}
if(value<(f32)length){delta=D_800A0888*D_800BE9A4;value=value+delta;
while(value>1.0f){count++;if(count>length)count=length;value=value-1.0f;}}
expectedCount=count;expectedFraction=value;expected[0]='C';expected[1]=':';expected[2]='>';expected[3]=' ';
for(j=0;j<80;j++){line[j]=(u8)(j%26+'A');other[j]=(u8)(j%26+'a');}
for(j=0;j<count;j++)expected[j+4]=record.state.buffers[record.state.index][j];
expected[count+4]=' ';expected[count+5]=187;expected[count+6]=0;stage=error=0;
if(func_150D032C((u8 *)&record)!=1||error||stage!=4||payload.characters!=(s16)count||payload.fraction!=expectedFraction)return 22;}
return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
