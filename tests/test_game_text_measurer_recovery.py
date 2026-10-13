"""Full original/candidate measurers with real helpers; not a byte-match claim."""
import csv
import hashlib
import io
import itertools
import json
import math
import struct
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_text_measurer_candidates as screen
from tools.experiments import game_character_normalizer_candidates as lookup
from tools.experiments import game_extended_character_metrics_candidates as metrics
from tools.tests import test_game_actor_attachment_update_match as guest
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_extended_character_metrics_match import CASES,DEFAULT,BITS,CONSTANTS
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_text_measurer_native32 as native
from tools.tests import test_game_actor_renderer_install_match as installed
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools

STACK,TEXT,FONT,OUTPUT=guest.STACK,0x22000,0x24000,0x26000


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-512<=a<STACK+512}


def fixture(text,table,alias=0,scales=(1.0,1.0)):
    memory={STACK+i:0xA5 for i in range(-512,512)}
    for address,size in ((TEXT,256),(FONT,1024),(OUTPUT-16,64),(lookup.TABLE,96),(metrics.TABLE,76),
            (screen.SYMBOLS['D_80085994'],4),(screen.SYMBOLS['D_800380A0'],8)):
        memory.update({address+i:(i*13+53)&255 for i in range(size)})
    for i,v in enumerate(table):memory[lookup.TABLE+i]=v
    for i,v in enumerate(text):memory[TEXT+i]=v
    for i in range(len(text),256):memory[TEXT+i]=0
    for glyph in range(256):
        for byte,v in enumerate((3+glyph%11,2+glyph%9,4+glyph%7,5+glyph%13)):
            memory[FONT+glyph*4+byte]=v
    for i,target in enumerate([metrics.ENTRY+next((off for codes,off,ops in CASES if code in codes),0x188)
            for code in range(0xA8,0xBB)]):put(memory,metrics.TABLE+i*4,target)
    for name,value in zip(CONSTANTS,BITS):put(memory,metrics.SYMBOLS[name],value)
    put(memory,screen.SYMBOLS['D_80085994'],FONT)
    for address,value in zip((screen.SYMBOLS['D_800380A0'],screen.SYMBOLS['D_800380A4']),scales):
        put(memory,address,bits(value))
    outputs=[OUTPUT+i*4 for i in range(3)]
    if alias==1:outputs=[OUTPUT]*3
    elif alias==2:outputs[1]=outputs[0]
    elif alias==3:outputs[2]=outputs[0]
    elif alias==4:outputs[2]=outputs[1]
    elif alias==5:outputs[0]=FONT+10*4
    elif alias==6:outputs[0]=metrics.SYMBOLS['D_80098B00']
    elif alias==7:outputs[0]=screen.SYMBOLS['D_800380A0']
    elif alias==8:outputs[1]=screen.SYMBOLS['D_800380A4']
    elif alias==9:outputs[0]=TEXT+4
    return memory,(TEXT,*outputs)


class Reference:
    def __init__(self,memory,args,byteorder='big'):
        self.memory=memory.copy();self.args=args;self.calls=[];self.byteorder=byteorder
    def word(self,address):
        return int.from_bytes(bytes(self.memory[address+i] for i in range(4)),self.byteorder)
    def integer(self,address):return signed(self.word(address))
    def store(self,address,value):
        for i,v in enumerate((value&0xFFFFFFFF).to_bytes(4,self.byteorder)):self.memory[address+i]=v
    def fp(self,address):return floating(self.word(address))
    def normalize(self,code):
        self.calls.append((lookup.ENTRY,code))
        if code==32:return 96
        normalized=code-32 if 97<=code<123 else code
        for index in range(95):
            if self.memory[lookup.TABLE+index]==normalized:return index
        return code
    def glyph_metrics(self,code):
        self.calls.append((metrics.ENTRY,code))
        values=dict(w=0,h=0,s=0,m=0,f=bits(1.0))
        operations=next((ops for codes,off,ops in CASES if code in codes),DEFAULT)
        for name,value in operations:
            values[name]=self.word(metrics.SYMBOLS[value]) if isinstance(value,str) else value
        return signed(values['w']),signed(values['h']),floating(values['s']),floating(values['f'])
    @staticmethod
    def rounded(value):return floating(bits(value))
    @staticmethod
    def trunc(value):
        assert math.isfinite(value) and -2147483648<=value<2147483648,('outside qualified conversion domain',value)
        return math.trunc(value)
    def run(self):
        cursor,width,height,baseline=self.args
        if not cursor:return self
        for address in (width,height,baseline):self.store(address,0)
        maximum,line_height=0,0
        if self.memory[cursor]==0:self.store(height,self.integer(height)+12)
        if self.memory[cursor]!=0:
            for _ in range(512):
                code=self.memory[cursor]
                if code==0xBC:cursor+=2
                else:
                    glyph=self.normalize(code)&255;use_font=False
                    if glyph==96:
                        self.store(width,self.integer(width)+4);line_height=max(line_height,12)
                    elif glyph<161 or glyph>=168:
                        if glyph>=168:
                            w,h,offset,factor=self.glyph_metrics(glyph)
                            value=self.rounded(self.rounded(float(self.integer(width)))+
                                self.rounded(self.rounded(float(w))*factor))
                            self.store(width,self.trunc(value))
                            extent=self.trunc(self.rounded(float(self.trunc(self.rounded(self.rounded(float(h))*factor)))-offset))+1
                            line_height=max(line_height,extent)
                            if self.rounded(float(self.integer(baseline)))<offset:self.store(baseline,self.trunc(offset))
                        elif self.memory[cursor]==10:
                            maximum=max(maximum,self.integer(width));self.store(width,0)
                            line_height=max(line_height,12)
                            self.store(height,self.integer(height)+line_height);line_height=0
                        else:use_font=True
                    cursor+=1
                    if use_font:
                        row=self.word(screen.SYMBOLS['D_80085994'])+glyph*4
                        value=self.integer(width)+self.memory[row]+self.memory[row+2]-1
                        self.store(width,value)
                        row=self.word(screen.SYMBOLS['D_80085994'])+glyph*4
                        line_height=max(line_height,self.memory[row+3]+self.memory[row+1])
                if self.memory[cursor]==0:break
            else:raise AssertionError('reference text bound exceeded')
        if self.integer(width)<maximum:self.store(width,maximum)
        self.store(height,self.integer(height)+line_height)
        for address,scale in ((width,screen.SYMBOLS['D_800380A0']),(height,screen.SYMBOLS['D_800380A4']),
                (baseline,screen.SYMBOLS['D_800380A0'])):
            self.store(address,self.trunc(self.rounded(self.rounded(float(self.integer(address)))*self.fp(scale))))
        return self


class MeasurerOracle(guest.AttachmentOracle):
    def __init__(self,words,memory,args,connected,phase=0):
        super().__init__(words,memory,arguments=args,connected=connected,entry=screen.ENTRY,phase=phase)
    def record_call(self,target):
        assert target in (lookup.ENTRY,metrics.ENTRY)
        args=self.arguments(1 if target==lookup.ENTRY else 6)
        if target==metrics.ENTRY:
            assert all(STACK-256<=a<STACK for a in args[1:])
            assert len(set(args[1:]))==5 and all(a%4==0 for a in args[1:])
        self.calls.append((target,args[0]))
        self.events.append(('CALL',target,args))
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            value=floating(self.f[word>>11&31]);assert math.isfinite(value) and -2147483648<=value<2147483648
            self.f[word>>6&31]=math.trunc(value)&0xFFFFFFFF
        else:super().execute(word)


class InstructionFaultMeasurer(MeasurerOracle):
    def execute(self,word):
        self.dispatched_word=word
        super().execute(word)


class GameTextMeasurerRecoveryTests(unittest.TestCase):
    maxDiff=None
    run_native=installed.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-text-measurer-recovery-test';cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',makefile='conker/Makefile',assembly='conker/asm/6E770.s',
            table_data='conker/asm/data/2275E0.data.s',pool='conker/asm/data/23D570.rodata.s',layout='conker/retail_layout.us.txt')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            assert screen.ORIGINAL in (cls.root/screen.SOURCE).read_text()
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes();(cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads(manifest.read_text())
        assert cls.baseline['source']=='802b4d27659c80620c2ca509df4c3da84d136c5c92b758d7a6390c4428d2273d'
        assert cls.baseline['elf']=='c25a2f5ee0e9c056d10f79f83b8d1060a94948740a386e347103f5033b6d06c2'
        assert cls.baseline['guards']=='420eb4c5458868e6b19f5a7eb45f04b38ef96532216f283689eec7e0c5e8d796'
        cls.before=(cls.out/'before-elf').read_bytes();cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>219I',cls.rom,screen.ROM))
        cls.table=cls.rom[lookup.TABLE_ROM:lookup.TABLE_ROM+96]
        assert cls.table==cls.before[elf_slot_offset(cls.before,lookup.TABLE,96):][:96]
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.connected={}
        for entry,rom,words in ((lookup.ENTRY,lookup.ROM,65),(metrics.ENTRY,metrics.ROM,115)):
            body=list(struct.unpack_from('>%dI'%words,cls.rom,rom))
            assert body==list(struct.unpack_from('>%dI'%words,cls.before,elf_slot_offset(cls.before,entry,words*4)))
            cls.connected.update({entry+i*4:w for i,w in enumerate(body)})

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,text,alias=0,phase=0,scales=(1.0,1.0),null=False,factor=None):
        memory,args=fixture(text,self.table,alias,scales)
        if factor is not None:put(memory,metrics.SYMBOLS['D_80098B00'],bits(factor))
        if null:args=(0,*args[1:])
        expected=Reference(memory,args).run()
        models=[MeasurerOracle(body,memory,args,self.connected,phase).run() for body in (self.retail,self.raw)]
        for model in models:
            self.assertEqual(public(model.memory),public(expected.memory))
            self.assertEqual(model.calls,expected.calls)
        return models

    def test_01_complete_measurers_actual_helpers_and_all_byte_paths(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],self.meta['pool_bytes']),(216,128,211,0))
        self.assertNotEqual(self.raw,self.retail)
        cases=0;reached=set()
        for byte,phase in itertools.product(range(256),(0,8)):
            text=bytes((byte,0,0,0)) if byte!=0xBC else bytes((byte,7,65,0))
            models=self.compare(text,phase=phase);reached.update(models[0].visits);cases+=1
        for text,phase in itertools.product((b'',b'A',b'hello',b'  ',b'\n',b'A\nB',b'AB\n',b'\n\n',
                bytes((0xBC,1,0)),bytes((0xBC,0,65,0)),bytes((0xAA,0xBA,0xAE,65,32,10,0xFF,0))), (0,8)):
            self.compare(text+b'\0\0',phase=phase);cases+=1
        self.compare(b'A\0',null=True);cases+=1
        self.receipt('full-chain',cases=cases,original219_and_complete_candidate216=True,
            actual_normalizer65_metrics115_no_hooks=True,all_bytes_empty_null_newlines_and_control_skip=True,
            public_memory_and_call_sequence_exact=True,retail_body_words_reached=len(reached&set(range(screen.ENTRY,screen.ENTRY+876,4))),
            candidate_not_byte_exact=True,private_order_GPR_FPR_hardware_and_gameplay_not_claimed=True)

    def test_02_public_output_table_constant_text_aliases_and_final_scales(self):
        cases=0
        for text,alias,phase,scales in itertools.product((b'A\0',b'\nA\0',b'A\nB\0',b' AB\0',
                bytes((0xAA,0xBA,0xAE,0)),bytes((0xA8,0xAA,65,0))),range(10),(0,8),((1.0,1.0),(0.75,1.25))):
            self.compare(text,alias,phase,scales);cases+=1
        self.receipt('aliases',cases=cases,outputs_each_other_font_record_live_factor_scales_and_text=True,
            final_width_height_baseline_write_order_and_live_scales=True,finite_in_range_FP_domain_only=True,
            not_native_or_private_home_alias_claim=True)

    def font_pointer_fixture(self):
        memory,args=fixture(bytes((0xA8,65,0)),self.table)
        memory.update({i:0 for i in range(1024)})
        for address,value in ((72,6),(73,2),(74,4),(75,1),(82,13),(84,17)):memory[address]=value
        args=(args[0],screen.SYMBOLS['D_80085994'],args[2],args[3])
        return memory,args

    def test_03_live_font_pointer_reload_and_nested_float_truncation(self):
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        self.assertEqual(read(expected.memory,args[1]),41);self.assertEqual(read(expected.memory,args[2]),30)
        for body in (self.retail,self.raw):
            model=MeasurerOracle(body,memory,args,self.connected).run()
            self.assertEqual(public(model.memory),public(expected.memory));self.assertEqual(model.calls,expected.calls)
        self.compare(bytes((0xAA,0)),factor=1.0/18.0)
        self.receipt('live-pointer-float',font_pointer_alias_reloads32_then41=True,height30_not15=True,
            nested_truncation_crossing_zero=True,synthetic_low_addresses_guest_only=True)

    def test_04_fresh_effective_complete_candidate_controls(self):
        font='''                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +
                            D_80085994[glyph * 4 + 2] - 1);
                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];'''
        mutations=(
            ('empty-height',screen.SELECTED.replace('(u32)*height + 12','(u32)*height + 13'),b'\0',0,(1.0,1.0),None),
            ('skip-one',screen.SELECTED.replace('cursor += 2','cursor += 1'),bytes((0xBC,66,65,0)),0,(1.0,1.0),None),
            ('space-width',screen.SELECTED.replace('(u32)*width + 4','(u32)*width + 5'),b' \0',0,(1.0,1.0),None),
            ('no-newline-clear',screen.SELECTED.replace('                                *width = 0;','                                *width = *width;'),b'A\nB\0',0,(1.0,1.0),None),
            ('wrong-height-scale',screen.SELECTED.replace('(f32)*height * D_800380A4','(f32)*height * D_800380A0'),b'A\0',0,(0.75,1.25),None),
            ('early-font-height',screen.SELECTED.replace(font,'''                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];
                        *width = (s32)((u32)*width + D_80085994[glyph * 4] + D_80085994[glyph * 4 + 2] - 1);'''),b'A\0',5,(1.0,1.0),None),
            ('one-truncation',screen.SELECTED.replace('(f32)(s32)((f32)glyphHeight * factor)','((f32)glyphHeight * factor)'),bytes((0xAA,0)),0,(1.0,1.0),1.0/18.0),
        )
        for name,body,text,alias,scales,factor in mutations:
            self.assertNotEqual(body,screen.SELECTED,name)
            _,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            memory,args=fixture(text,self.table,alias,scales)
            if factor is not None:put(memory,metrics.SYMBOLS['D_80098B00'],bits(factor))
            expected=Reference(memory,args).run();model=MeasurerOracle(words,memory,args,self.connected).run()
            self.assertNotEqual(public(model.memory),public(expected.memory),name)
        cached=screen.SELECTED.replace('    s32 extent;', '    s32 extent;\n    u8 *cached;').replace(
            '                    if (useFont) {', '                    if (useFont) {\n                        cached = D_80085994;').replace(
            'extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1]',
            'extent = cached[glyph * 4 + 3] + cached[glyph * 4 + 1]')
        _,words=screen.compile_candidate(self.root,self.out,'negative-cached-font-pointer',cached)
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        self.assertNotEqual(public(MeasurerOracle(words,memory,args,self.connected).run().memory),public(expected.memory))
        self.receipt('controls',eight_fresh_compiled_complete_body_controls=True,all_public_mismatches_effective=True,
            actual_helpers_not_hooks=True,zero_crossing_float_and_live_pointer_controls=True)

    def test_05_production_and_protected_data_unchanged(self):
        for name,path in self.paths.items():
            before=(self.out/('before-'+name)).read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(),self.baseline[name])
            self.assertEqual((self.root/path).read_bytes(),before,name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker');self.assertTrue(data['exact'],data)
        self.receipt('production',source_placeholder_retained=True,entire_ELF_guards_progress_makefile_and_all9_inputs_exact=True,
            no_installation_or_matching_credit=True,protected_data=data)

    def test_06_effective_immutable_production_controls(self):
        rb=Path.read_bytes
        source=self.root/self.paths['source'];body=source.read_bytes()
        with patch.object(Path,'read_bytes',lambda p:body+b'\n' if p==source else rb(p)):
            with self.assertRaises(AssertionError):self.test_05_production_and_protected_data_unchanged()
        elf=self.root/self.paths['elf'];data=elf.read_bytes()
        for address,size in ((screen.ENTRY,876),(lookup.ENTRY,260),(metrics.ENTRY,460),(lookup.TABLE,96)):
            offset=elf_slot_offset(data,address,size);bad=bytearray(data);bad[offset+4]^=1
            with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==elf else rb(p)):
                with self.assertRaises(AssertionError):self.test_05_production_and_protected_data_unchanged()
        guards=self.root/self.paths['guards'];data=guards.read_bytes()
        with patch.object(Path,'read_bytes',lambda p:data+b'\n' if p==guards else rb(p)):
            with self.assertRaises(AssertionError):self.test_05_production_and_protected_data_unchanged()
        self.receipt('integrity-controls',source1_ELF4_including_helpers_table_guard1=True,all_effective=True)

    def test_07_closer_layout_candidate_retains_complete_semantics(self):
        body=dict(screen.candidates())['initial-index-late']
        meta,words=screen.compile_candidate(self.root,self.out,'closer-layout',body)
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences']),(217,128,185))
        cases=0
        for text,alias,phase in itertools.product((b'\0',b'A\0',b'A\nB\0',b' AB\0',
                bytes((0xBC,0,65,0)),bytes((0xA8,0xAA,0xBA,0xAE,65,0))),range(10),(0,8)):
            memory,args=fixture(text,self.table,alias,(0.75,1.25));expected=Reference(memory,args).run()
            for code in (self.retail,words):
                model=MeasurerOracle(code,memory,args,self.connected,phase).run()
                self.assertEqual(public(model.memory),public(expected.memory));self.assertEqual(model.calls,expected.calls)
            cases+=1
        for byte in range(256):
            text=bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0))
            memory,args=fixture(text,self.table);expected=Reference(memory,args).run()
            for code in (self.retail,words):
                model=MeasurerOracle(code,memory,args,self.connected).run()
                self.assertEqual(public(model.memory),public(expected.memory));self.assertEqual(model.calls,expected.calls)
            cases+=1
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        self.assertEqual(public(MeasurerOracle(words,memory,args,self.connected).run().memory),public(expected.memory));cases+=1
        memory,args=fixture(bytes((0xAA,0)),self.table);put(memory,metrics.SYMBOLS['D_80098B00'],bits(1.0/18.0))
        expected=Reference(memory,args).run()
        self.assertEqual(public(MeasurerOracle(words,memory,args,self.connected).run().memory),public(expected.memory));cases+=1
        self.receipt('closer-layout',cases=cases,body_words=217,frame128=True,differences185=True,
            complete_public_memory_and_calls_with_actual_helpers=True,not_installed_or_byte_exact=True)

    def native_cases(self):
        cases=[]
        words=[screen.SYMBOLS['D_80085994'],screen.SYMBOLS['D_800380A0'],
            screen.SYMBOLS['D_800380A4'],*[metrics.SYMBOLS[name] for name in CONSTANTS]]
        def add(text,alias=0,scales=(1.0,1.0),null=False,factor=None):
            memory,args=fixture(text,self.table,alias,scales)
            for address in words:
                value=read(memory,address)
                for i,v in enumerate(value.to_bytes(4,'little')):memory[address+i]=v
            if factor is not None:
                for i,v in enumerate(bits(factor).to_bytes(4,'little')):
                    memory[metrics.SYMBOLS['D_80098B00']+i]=v
            if null:args=(0,*args[1:])
            expected=Reference(memory,args,'little').run()
            cases.append((memory,args,expected.memory))
        for byte,scales in itertools.product(range(256),((1.0,1.0),(0.75,1.25))):
            add(bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0)),scales=scales)
        for text,alias,scales in itertools.product((b'\0',b'A\0',b'hello\0',b'  \0',b'\n\0',b'A\nB\0',
                b'AB\n\0',b'\n\n\0',bytes((0xBC,0,65,0)),bytes((0xA8,0xAA,0xBA,0xAE,65,0))),
                range(10),((1.0,1.0),(0.75,1.25))):
            add(text,alias,scales)
        for alias,scales in itertools.product(range(10),((1.0,1.0),(0.75,1.25))):
            add(b'A\0',alias,scales,null=True)
        add(bytes((0xAA,0)),factor=1.0/18.0)
        return cases

    def native_source(self,body,cases):
        regions=((TEXT,256,'nativeText'),(FONT,1024,'nativeFont'),(OUTPUT-16,64,'nativeOutputs'))
        parameters=[screen.SYMBOLS['D_800380A0'],screen.SYMBOLS['D_800380A4'],
            *[metrics.SYMBOLS[name] for name in CONSTANTS]]
        return native.source(body,self.table,cases,regions,parameters)

    def test_08_native32_complete_bodies_helpers_and_portable_aliases(self):
        cases=self.native_cases()
        self.assertEqual(len(cases),733)
        for name,body in (('clear',screen.SELECTED),('closer',dict(screen.candidates())['initial-index-late'])):
            source=self.native_source(body,cases)
            for profile in ('-O2','-O0'):
                self.assertEqual(self.run_native('native-'+name+'-'+profile[1:],source,profile),(0,''))
        self.receipt('native',profiles=['O2','O0'],cases_per_body_profile=len(cases),bodies=['clear216','closer217'],
            native_int_pointer_float_bytes4=True,complete_recovered_helpers_no_hooks=True,
            all_bytes_empty_null_newlines_control_skip_and_nested_truncation=True,
            host_endian_public_output_font_factor_scale_text_aliases=True,all_buffers_canaries=True,
            synthetic_low_font_pointer_alias_private_homes_FCSR_hardware_gameplay_not_claimed=True)

    def test_09_native32_effective_fresh_compiled_controls(self):
        font='''                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +
                            D_80085994[glyph * 4 + 2] - 1);
                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];'''
        controls=(('empty-height','(u32)*height + 12','(u32)*height + 13'),
            ('skip-one','cursor += 2','cursor += 1'),('space-width','(u32)*width + 4','(u32)*width + 5'),
            ('no-newline-clear','                                *width = 0;','                                *width = *width;'),
            ('wrong-height-scale','(f32)*height * D_800380A4','(f32)*height * D_800380A0'),
            ('one-truncation','(f32)(s32)((f32)glyphHeight * factor)','((f32)glyphHeight * factor)'),
            ('early-font-height',font,'''                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];
                        *width = (s32)((u32)*width + D_80085994[glyph * 4] + D_80085994[glyph * 4 + 2] - 1);'''))
        cases=self.native_cases();failures={}
        for name,old,new in controls:
            self.assertEqual(screen.SELECTED.count(old),1,name)
            body=screen.SELECTED.replace(old,new)
            code,detail=self.run_native('native-negative-'+name,self.native_source(body,cases))
            self.assertIn(code,range(1,5),name);self.assertEqual(len(detail),3,name)
            self.assertEqual(detail[0],code,name);failures[name]=detail
        canaries={}
        source=self.native_source(screen.SELECTED,cases)
        for name,statement,expected_code in (('text','textStorage[0]=0;',6),
                ('font','fontStorage[0]=0;',7),('outputs','outputsStorage[0]=0;',8),
                ('lookup','normalizerStorage[0]=0;',9)):
            marker='        D_80085994=nativeFont;'
            self.assertEqual(source.count(marker),1)
            corrupted=source.replace(marker,'        '+statement+'\n'+marker)
            code,detail=self.run_native('native-canary-negative-'+name,corrupted)
            self.assertEqual((code,detail),(expected_code,[expected_code,0,0]),name)
            canaries[name]=detail
        self.receipt('native-controls',seven_fresh_compiled_controls=True,all_effective_public_mismatches=True,
            failure_receipts=failures,four_effective_compiled_buffer_table_canary_controls=canaries,
            guest_only_low_pointer_cached_font_control_not_portable=True)

    def shape_candidate(self):
        return dict(screen.candidates())['remat-metrics-state-after']

    def captured_lifetime_candidate(self):
        return dict(screen.candidates())['capture-declaration-after-record']

    def test_10_original_saves_metric_homes_and_public_semantics(self):
        body=self.shape_candidate()
        meta,words=screen.compile_candidate(self.root,self.out,'lifetime-fit',body)
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences'],meta['pool_bytes']),(218,128,168,0))
        self.assertEqual(words[:13],self.retail[:13])
        self.assertEqual(words[14:28],self.retail[14:28])
        cases=0
        with patch.object(self,'raw',words):
            for byte,phase in itertools.product(range(256),(0,8)):
                text=bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0))
                models=self.compare(text,phase=phase)
                self.assertEqual([e for e in models[0].events if e[0]=='CALL'],
                    [e for e in models[1].events if e[0]=='CALL'])
                cases+=1
            for text,alias,phase,scales in itertools.product((b'\0',b'A\0',b'A\nB\0',b' AB\0',
                    bytes((0xBC,0,65,0)),bytes((0xA8,0xAA,0xBA,0xAE,65,0))),range(10),(0,8),
                    ((1.0,1.0),(0.75,1.25))):
                models=self.compare(text,alias,phase,scales)
                self.assertEqual([e for e in models[0].events if e[0]=='CALL'],
                    [e for e in models[1].events if e[0]=='CALL'])
                cases+=1
            self.compare(b'A\0',null=True);cases+=1
            self.compare(bytes((0xAA,0)),factor=1.0/18.0);cases+=1
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        self.assertEqual(public(MeasurerOracle(words,memory,args,self.connected).run().memory),public(expected.memory));cases+=1
        source=self.native_source(body,self.native_cases())
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-lifetime-'+profile[1:],source,profile),(0,''))
        self.receipt('lifetime-fit',body_words=218,frame=128,differences=168,pool_bytes=0,guest_cases=cases,
            saves_S0_to_S6_RA_exact_and_opening_index_reads_exact=True,
            original_five_private_metrics_output_homes_and_full_call_arguments_exact=True,
            complete_original_candidate_actual_helpers_and_public_memory_exact=True,
            native_cases_per_profile=733,native_profiles=['O2','O0'],owner_profile_unchanged=True,
            one_body_word_short_and_flag_spill_reload_schedule_unmatched=True,
            private_fault_order_GPR_FPR_hardware_and_installation_not_claimed=True)

    def test_11_copied_owner_seven_neighbors_pools_and_both_padders(self):
        self.check_copied_owner(self.shape_candidate(),'lifetime')
        self.check_copied_owner(self.captured_lifetime_candidate(),'captured-lifetime')

    def check_copied_owner(self,body,tag):
        source=(self.out/'before-source').read_text()
        self.assertEqual(source.count(screen.ORIGINAL),1)
        updated=source.replace(screen.ORIGINAL,body).replace('#include <ultra64.h>\n',
            '#include <ultra64.h>\n'+screen.DECLARATIONS,1)
        owners=[];run=subprocess.run
        def compact(command,*a,**k):
            if str(command[0]).endswith('/cc'):command=list(command)+['-Wo,-loopunroll,0']
            return run(command,*a,**k)
        for stage,text in (('before',source),('candidate',updated)):
            with patch('subprocess.run',side_effect=compact):
                obj,warnings=compile_owner(self.root,self.out,text,tag+'-owner-'+stage)
            self.assertEqual(warnings,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(tag+'-owner-'+stage+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            owners.append(obj)
        def fingerprint(obj,name):
            text,functions,relocs=parse_object(obj);f=functions[name];a,b=f['value'],f['value']+f['size']
            return f['size'],text[a:b],{o-a:r for o,r in relocs.items() if a<=o<b}
        names=set(parse_object(owners[0])[1])
        self.assertEqual(names,set(parse_object(owners[1])[1]));self.assertEqual(len(names-{screen.FUNCTION}),7)
        for name in names-{screen.FUNCTION}:
            self.assertEqual(fingerprint(owners[0],name),fingerprint(owners[1],name),name)
        self.assertEqual(normalized_pools(owners[0]),normalized_pools(owners[1]))
        screen.compile_candidate(self.root,self.out,tag+'-owner-isolated',body)
        self.assertEqual(fingerprint(owners[1],screen.FUNCTION),fingerprint(self.out/(tag+'-owner-isolated.o'),screen.FUNCTION))
        routes=[]
        for route in ('pad_c_object.py','pad_generated_object.py'):
            parsed=[]
            for stage,obj in zip(('before','candidate'),owners):
                asm=self.out/(tag+'-'+route+'-'+stage+'.s')
                args=[str(obj),str(self.out/'before-layout'),'generated_6E770',str(asm)] if route=='pad_c_object.py' else [
                    str(obj),str(self.out/'before-assembly'),str(asm),'--filename','generated_6E770']
                subprocess.run(['python3',str(self.root/'tools'/route),*args,'--word-patches',str(self.out/'before-guards'),
                    '--rodata-symbol',metrics.ANCHOR],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(asm.with_suffix('.o')),str(asm)],
                    check=True,capture_output=True)
                parsed.append(parse_object(asm.with_suffix('.o')))
                self.assertNotIn('.rodata',sections(asm.with_suffix('.o')))
            start=parsed[1][1][screen.FUNCTION]['value'];expected=bytearray(parsed[0][0])
            self.assertEqual(parsed[1][1][screen.FUNCTION]['size'],872)
            self.assertEqual(parsed[1][0][start+872:start+876],bytes(4))
            self.assertEqual(parsed[1][1][lookup.FUNCTION]['value'],start+876)
            expected[start:start+876]=parsed[1][0][start:start+876]
            self.assertEqual(bytes(expected),parsed[1][0])
            self.assertEqual({o:r for o,r in parsed[0][2].items() if not start<=o<start+876},
                {o:r for o,r in parsed[1][2].items() if not start<=o<start+876})
            for name in names-{screen.FUNCTION}:
                self.assertEqual(parsed[0][1][name],parsed[1][1][name])
            routes.append(parsed[1])
        self.assertEqual(routes[0],routes[1])
        self.receipt(tag+'-owner',neighbors7=True,all_other_bodies_extents_relocations_and_pools_exact=True,
            whole_padded_text_and_relocations_outside_target_exact=True,raw_target_matches_isolated=True,
            target_slot876_body872_zero_tail4_not_retail_match=True,
            actual_no_unroll_profile_asm_processor_both_padders_existing_metrics_binding=True,
            old_guards_unchanged_no_target_guards_added=True,not_installed_or_byte_exact=True)

    def test_12_private_flag_home_witness_rejects_current_candidate_as_match(self):
        _,words=screen.compile_candidate(self.root,self.out,'lifetime-private-witness',self.shape_candidate())
        witnesses=[]
        for text,phase in itertools.product((b'A\0',bytes((0xA8,0))),(0,8)):
            memory,args=fixture(text,self.table)
            args=(args[0],STACK+phase-128+0x68,args[2],args[3])
            models=[MeasurerOracle(code,memory,args,self.connected,phase).run() for code in (self.retail,words)]
            outputs=[tuple(signed(read(m.memory,a)) for a in args[1:]) for m in models]
            self.assertNotEqual(outputs[0],outputs[1])
            self.assertEqual(outputs,[(19,18,0),(20,18,0)] if text[0]==65 else [(32,15,3),(41,25,3)])
            witnesses.append(dict(byte=text[0],phase=phase,width_address=args[1],retail=outputs[0],candidate=outputs[1]))
        self.receipt('lifetime-private-witness',four_actual_instruction_chain_discriminants=witnesses,
            current_struct_flag_home_always_stored_and_late_read_is_not_retail_spill=True,
            candidate_rejected_for_full_private_equivalence=True,not_installed_or_byte_exact=True,
            synthetic_guest_stack_alias_not_native_portable_pointer_claim=True)

    def test_13_call_only_flag_capture_public_and_bounded_private_qualification(self):
        body=self.captured_lifetime_candidate()
        meta,words=screen.compile_candidate(self.root,self.out,'captured-lifetime',body)
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences'],meta['pool_bytes']),(218,128,174,0))
        cases=0
        with patch.object(self,'raw',words):
            for byte,phase in itertools.product(range(256),(0,8)):
                text=bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0))
                models=self.compare(text,phase=phase)
                self.assertEqual([e for e in models[0].events if e[0]=='CALL'],
                    [e for e in models[1].events if e[0]=='CALL']);cases+=1
            for text,alias,phase,scales in itertools.product((b'\0',b'A\0',b'A\nB\0',b' AB\0',
                    bytes((0xBC,0,65,0)),bytes((0xA8,0xAA,0xBA,0xAE,65,0))),range(10),(0,8),
                    ((1.0,1.0),(0.75,1.25))):
                models=self.compare(text,alias,phase,scales)
                self.assertEqual([e for e in models[0].events if e[0]=='CALL'],
                    [e for e in models[1].events if e[0]=='CALL']);cases+=1
            self.compare(b'A\0',null=True);cases+=1
            self.compare(bytes((0xAA,0)),factor=1.0/18.0);cases+=1
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        self.assertEqual(public(MeasurerOracle(words,memory,args,self.connected).run().memory),public(expected.memory));cases+=1
        private=[]
        for text,phase in itertools.product((b'A\0',bytes((0xA8,0)),bytes((65,0xA8,0))),(0,8)):
            memory,args=fixture(text,self.table);args=(args[0],STACK+phase-128+0x68,args[2],args[3])
            models=[MeasurerOracle(code,memory,args,self.connected,phase).run() for code in (self.retail,words)]
            outputs=[tuple(signed(read(m.memory,a)) for a in args[1:]) for m in models]
            self.assertEqual(outputs[0],outputs[1]);private.append(dict(text=list(text),phase=phase,outputs=outputs[0]))
        source=self.native_source(body,self.native_cases())
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-captured-lifetime-'+profile[1:],source,profile),(0,''))
        restore='                            useFont = metrics.useFont;\n'
        width='                            *width = (s32)((f32)*width + (f32)metrics.width * metrics.factor);'
        self.assertEqual(body.count(restore),1);self.assertEqual(body.count(width),1)
        late=body.replace(restore,'').replace(width,width+'\n'+restore.rstrip())
        _,bad=screen.compile_candidate(self.root,self.out,'captured-negative-late-flag-read',late)
        memory,args=fixture(bytes((0xA8,0)),self.table);args=(args[0],STACK-128+0x68,args[2],args[3])
        models=[MeasurerOracle(code,memory,args,self.connected).run() for code in (self.retail,bad)]
        outputs=[tuple(signed(read(m.memory,a)) for a in args[1:]) for m in models]
        self.assertNotEqual(outputs[0],outputs[1])
        self.receipt('captured-lifetime',body_words=218,frame=128,differences=174,guest_cases=cases,
            actual_helpers_complete_public_memory_calls_and_five_homes_exact=True,
            native_cases_per_profile=733,native_profiles=['O2','O0'],bounded_private_flag_home_cases6=private,
            fresh_late_flag_reload_private_negative_effective=outputs,
            call_only_capture_then_reload_before_width_store_restored=True,
            saved_register_set_S0_to_S7_instead_of_retail_S0_to_S6_still_unmatched=True,
            full_private_equivalence_fault_order_hardware_and_installation_not_claimed=True)

    def test_14_independently_linked_original_candidate_helpers_and_real_pools(self):
        asm=(self.out/'before-assembly').read_text()
        def block(name,section):
            body=asm.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]
            return '.section '+section+',"ax"\n.set noat\n.set noreorder\n.globl '+name+'\n.type '+name+',@function\n'+\
                name+':\n'+body+'\n.size '+name+',.-'+name+'\n'
        def assemble(name,source):
            path=self.out/(name+'.s');obj=path.with_suffix('.o')
            path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+source)
            result=subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout+result.stderr),(0,''))
            return obj
        original=assemble('chain-original',block(screen.FUNCTION,'.text.measurer'))
        helpers=block(metrics.FUNCTION,'.text.metrics')+block(lookup.FUNCTION,'.text.lookup')+'.space 12,0\n'
        offsets=[w-metrics.ENTRY for w in struct.unpack_from('>19I',self.rom,metrics.TABLE_ROM)]
        helpers+='\n.section .rodata.metrics,"a"\n.globl jtbl_80098AB0\njtbl_80098AB0:\n'+\
            '\n'.join('.word '+metrics.FUNCTION+'+0x%X'%o for o in offsets)+'\n'
        for name,value in zip(CONSTANTS,BITS):
            helpers+='.globl '+name+'\n'+name+':\n.word 0x%08X\n'%value
        helpers+='\n.section .data.lookup,"aw"\n'
        for i,value in enumerate(self.table):
            if i<4:helpers+='.globl D_800859%02X\nD_800859%02X:\n'%(0x30+i,0x30+i)
            helpers+='.byte %d\n'%value
        helpers+='\n.section .data.font,"aw"\n.globl D_80085994\nD_80085994:\n.word 0x%X\n'%FONT
        helpers+='\n.section .data.scales,"aw"\n.globl D_800380A0\nD_800380A0:\n.word 0x3F800000\n'+\
            '.globl D_800380A4\nD_800380A4:\n.word 0x3F800000\n'
        helper_obj=assemble('chain-original-helpers-data',helpers)
        screen.compile_candidate(self.root,self.out,'chain-candidate',self.captured_lifetime_candidate())
        slot=self.out/'chain-slot.s'
        body=asm.split('glabel '+screen.FUNCTION+'\n',1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        slot.write_text('glabel '+screen.FUNCTION+'\n'+body+'endlabel '+screen.FUNCTION+'\n')
        padded=emit_padded_assembly(self.out/'chain-candidate.o',slot,filename='generated_6E770')
        self.assertEqual(padded.count('.section .text, "ax"'),1)
        candidate=assemble('chain-padded-candidate',padded.replace('.section .text, "ax"','.section .text.measurer,"ax"',1))
        links=((screen.ENTRY,lookup.TABLE,metrics.TABLE,screen.SYMBOLS['D_80085994'],screen.SYMBOLS['D_800380A0']),
            (0x15287FFC,0x80107FFE,0x80327FFC,0x80407FFC,0x80507FFC),
            (0x15318004,0x80218004,0x80318004,0x80418004,0x80518004))
        records=[];cases=0
        for number,(entry,table,pool,font,scales) in enumerate(links):
            delta=entry-screen.ENTRY;normalizer=lookup.ENTRY+delta;metric=metrics.ENTRY+delta
            images=[]
            for stage,obj in (('original',original),('candidate',candidate)):
                script=self.out/('chain-'+stage+'-'+str(number)+'.ld');elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .metrics 0x%X : SUBALIGN(4) { *(.text.metrics) } '%metric+
                    '.text 0x%X : SUBALIGN(4) { *(.text.measurer) } .lookup 0x%X : SUBALIGN(4) { *(.text.lookup) } '%(entry,normalizer)+
                    '.lookup_data 0x%X : SUBALIGN(1) { *(.data.lookup) } '%table+
                    '.metrics_data 0x%X : SUBALIGN(4) { *(.rodata.metrics) } '%pool+
                    '.font 0x%X : SUBALIGN(4) { *(.data.font) } .scales 0x%X : SUBALIGN(4) { *(.data.scales) } }\n'%(font,scales))
                result=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    '-o',str(elf),str(obj),str(helper_obj)],capture_output=True,text=True)
                self.assertEqual((result.returncode,result.stdout+result.stderr),(0,''))
                images.append(elf.read_bytes())
            def region(data,address,size):
                offset=elf_slot_offset(data,address,size);return data[offset:offset+size]
            for address,size in ((normalizer,272),(metric,460),(table,96),(pool,96),(font,4),(scales,8)):
                self.assertEqual(region(images[0],address,size),region(images[1],address,size))
            self.assertEqual(region(images[0],table,96),self.table)
            expected_pool=struct.pack('>19I',*[metric+o for o in offsets])+struct.pack('>5I',*BITS)
            self.assertEqual(region(images[0],pool,96),expected_pool)
            forms=[list(struct.unpack('>219I',region(data,entry,876))) for data in images]
            if number==0:
                self.assertEqual(forms[0],self.retail)
                self.assertEqual(region(images[0],normalizer,272),self.rom[lookup.ROM:lookup.ROM+272])
                self.assertEqual(region(images[0],metric,460),self.rom[metrics.ROM:metrics.ROM+460])
            connected={}
            for address,size in ((normalizer,260),(metric,460)):
                words=struct.unpack('>%dI'%(size//4),region(images[0],address,size))
                connected.update({address+i*4:w for i,w in enumerate(words)})
            symbols=dict(screen.SYMBOLS,D_80085994=font,D_800380A0=scales,D_800380A4=scales+4,
                func_15042C40=normalizer,func_150415E0=metric)
            floats={name:pool+76+i*4 for i,name in enumerate(CONSTANTS)}
            with patch.object(screen,'ENTRY',entry),patch.dict(screen.SYMBOLS,symbols),\
                    patch.object(lookup,'ENTRY',normalizer),patch.object(lookup,'TABLE',table),\
                    patch.object(metrics,'ENTRY',metric),patch.object(metrics,'TABLE',pool),patch.dict(metrics.SYMBOLS,floats):
                for byte,phase in itertools.product(range(256),(0,8)):
                    text=bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0))
                    memory,args=fixture(text,self.table,scales=(0.75,1.25));expected=Reference(memory,args).run()
                    for words in forms:
                        model=MeasurerOracle(words,memory,args,connected,phase).run()
                        self.assertEqual(public(model.memory),public(expected.memory));self.assertEqual(model.calls,expected.calls)
                    cases+=1
                for text,phase in itertools.product((b'A\0',bytes((0xA8,0)),bytes((65,0xA8,0))),(0,8)):
                    memory,args=fixture(text,self.table);args=(args[0],STACK+phase-128+0x68,args[2],args[3])
                    models=[MeasurerOracle(words,memory,args,connected,phase).run() for words in forms]
                    self.assertEqual(tuple(read(models[0].memory,a) for a in args[1:]),
                        tuple(read(models[1].memory,a) for a in args[1:]));cases+=1
            records.append(dict(entry=entry,normalizer=normalizer,metrics=metric,table=table,pool=pool,font=font,scales=scales))
        self.receipt('independent-links',links=records,cases=cases,default_original219_and_helpers_full_slots_byte_exact=True,
            independent_original_candidate_assembly_linking_actual_helpers_real_tables_and_floats=True,
            lookup_scalar4_byte_labels_and_scale_pairs_cross_HI_LO_carries=True,
            public_memory_calls_and_bounded_private_flag_aliases_exact=True,
            not_full_private_fault_hardware_or_word_match_claim=True)

    def test_15_fired_frame_fault_rejects_extra_saved_register_lifetime(self):
        _,words=screen.compile_candidate(self.root,self.out,'captured-frame-fault',self.captured_lifetime_candidate())
        records=[]
        for phase,fault in itertools.product((0,8),(0,1)):
            memory,args=fixture(b'A\0',self.table)
            models=[MeasurerOracle(code,memory,args,self.connected,phase) for code in (self.retail,words)]
            for model in models:
                model.fault=fault
                with self.assertRaises(guest.AccessFault):model.run()
                self.assertEqual(model.accesses,fault)
            state=lambda m:(m.memory,m.events,m.r,m.f)
            if fault==0:self.assertEqual(state(models[0]),state(models[1]))
            else:
                self.assertNotEqual(state(models[0]),state(models[1]))
                address=STACK+phase-128+0x38
                self.assertEqual(read(models[0].memory,address),models[0].before[22])
                self.assertEqual(read(models[1].memory,address),models[1].before[23])
                self.assertNotEqual(read(models[0].memory,address),read(models[1].memory,address))
            records.append(dict(phase=phase,fault=fault,equal=fault==0))
        self.receipt('frame-fault-rejection',four_fired_fault_pairs=records,
            first_completed_frame_store_retail_S6_candidate_S7_discriminant=True,
            current_candidate_rejected_for_full_partial_state_equivalence=True,
            not_complete_fault_sweep_or_native_hardware_fault_claim=True)


    def test_16_ugen_trace_preserves_code_and_rejects_invalid_receipts(self):
        body=self.captured_lifetime_candidate()
        record=screen.trace_ugen(self.root,self.out,'ugen-diagnostic',body)
        self.assertTrue(record['code_unchanged'])
        self.assertGreater(record['bytes'],0)
        self.assertEqual((record['baseline']['body_words'],record['baseline']['frame'],
            record['baseline']['differences']),(218,0x80,174))
        run=subprocess.run
        for name,status,log in (('failed',1,'failed'),('empty',0,''),('missing',0,'trace')):
            def controlled(command,*args,**kwargs):
                if '-Wc,-d' in command:return subprocess.CompletedProcess(command,status,log,'')
                return run(command,*args,**kwargs)
            with self.subTest(name=name),patch.object(screen.subprocess,'run',side_effect=controlled):
                with self.assertRaisesRegex(ValueError,'failed, empty or missing'):
                    screen.trace_ugen(self.root,self.out,'ugen-'+name,body)
            receipt=json.loads((self.out/('ugen-'+name+'-trace.json')).read_text())
            self.assertFalse(receipt['code_unchanged'])
        parse=screen.compiler.parse_object
        def changed(path):
            text,functions,relocations=parse(path)
            if str(path).endswith('-trace.o'):text=bytes((text[0]^1,))+text[1:]
            return text,functions,relocations
        with patch.object(screen.compiler,'parse_object',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed code, relocations or pools'):
                screen.trace_ugen(self.root,self.out,'ugen-changed',body)
        self.assertFalse(json.loads((self.out/'ugen-changed-trace.json').read_text())['code_unchanged'])


    def qualify_seven_save_dispatch(self,name,differences,original_frame=False):
        body=dict(screen.candidates())[name]
        entry=screen.ENTRY+0x200000
        with patch.object(screen,'ENTRY',entry):
            meta,words=screen.compile_candidate(self.root,self.out,name+'-seven-saves',body)
        self.assertEqual((meta['body_words'],meta['frame'],meta['differences'],meta['pool_bytes']),
            (222,0x80,differences,0))
        self.assertLess(entry+len(words)*4,0x16000000)
        self.assertFalse(set(range(entry,entry+len(words)*4,4))&self.connected.keys())
        saves=[(w>>16&31,w&65535) for w in words[:13] if w>>26==43 and w>>21&31==29]
        self.assertEqual(set(saves),{(r,0x20+(r-16)*4) for r in range(16,23)}|{(31,0x3C)})
        self.assertEqual(saves[0],(22,0x38) if original_frame else (21,0x34))
        if original_frame:self.assertEqual(words[:13],self.retail[:13])
        asm=(self.out/'before-assembly').read_text()
        slot=self.out/(name+'-retail-slot.s')
        block=asm.split('glabel '+screen.FUNCTION+'\n',1)[1].split('endlabel '+screen.FUNCTION,1)[0]
        slot.write_text('glabel '+screen.FUNCTION+'\n'+block+'endlabel '+screen.FUNCTION+'\n')
        obj=self.out/(name+'-seven-saves.o')
        with self.assertRaisesRegex(ValueError,'span is only 0x36C'):
            emit_padded_assembly(obj,slot,filename='generated_6E770')
        row=next(row for row in csv.DictReader(io.StringIO((self.out/'before-layout').read_text()))
            if row['function']==screen.FUNCTION)
        self.assertEqual(int(row['end'],0)-int(row['address'],0),876)
        layout=self.out/(name+'-single-function-layout.csv')
        with layout.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
        padded=self.out/(name+'-legacy-overflow.s')
        result=subprocess.run(['python3',str(self.root/'tools/pad_c_object.py'),str(obj),str(layout),
            row['filename'],str(padded)],capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout+result.stderr),(0,''))
        result=subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),
            str(padded)],capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout+result.stderr),(0,''))
        raw,functions,relocs=parse_object(padded.with_suffix('.o'))
        self.assertEqual(raw[:4],bytes.fromhex('08000000'))
        self.assertEqual(relocs[0],[('R_MIPS_26','__retail_overflow_'+screen.FUNCTION)])
        self.assertEqual(functions[screen.FUNCTION]['size'],876)
        self.assertIn('.game_overflow',sections(padded.with_suffix('.o')))
        self.assertNotEqual(raw[:876],struct.pack('>219I',*self.retail))
        def models(memory,args,phase=0):
            original=MeasurerOracle(self.retail,memory,args,self.connected,phase)
            with patch.object(screen,'ENTRY',entry):
                candidate=MeasurerOracle(words,memory,args,self.connected,phase)
            return original,candidate
        cases=0
        def compare(text,alias=0,phase=0,scales=(1.0,1.0),null=False,factor=None):
            nonlocal cases
            memory,args=fixture(text,self.table,alias,scales)
            if null:args=(0,*args[1:])
            if factor is not None:put(memory,metrics.SYMBOLS['D_80098B00'],bits(factor))
            expected=Reference(memory,args).run()
            for model in models(memory,args,phase):
                model.run()
                self.assertEqual(public(model.memory),public(expected.memory))
                self.assertEqual(model.calls,expected.calls)
            cases+=1
        for byte,phase in itertools.product(range(256),(0,8)):
            compare(bytes((byte,0,0)) if byte!=0xBC else bytes((byte,7,65,0)),phase=phase)
        for text,alias,phase,scales in itertools.product((b'\0',b'A\0',b'A\nB\0',b' AB\0',
                bytes((0xBC,0,65,0)),bytes((0xA8,0xAA,0xBA,0xAE,65,0))),range(10),(0,8),
                ((1.0,1.0),(0.75,1.25))):compare(text,alias,phase,scales)
        compare(b'A\0',null=True)
        compare(bytes((0xAA,0)),factor=1.0/18.0)
        memory,args=self.font_pointer_fixture();expected=Reference(memory,args).run()
        for model in models(memory,args):
            model.run();self.assertEqual(public(model.memory),public(expected.memory))
            self.assertEqual(model.calls,expected.calls)
        cases+=1;self.assertEqual(cases,755)
        private=[]
        for text,phase in itertools.product((b'A\0',bytes((0xA8,0)),bytes((65,0xA8,0))),(0,8)):
            memory,args=fixture(text,self.table);args=(args[0],STACK+phase-128+0x68,args[2],args[3])
            pair=models(memory,args,phase)
            for model in pair:model.run()
            outputs=[tuple(signed(read(model.memory,a)) for a in args[1:]) for model in pair]
            self.assertEqual(outputs[0],outputs[1]);private.append(dict(text=list(text),phase=phase,outputs=outputs[0]))
        source=self.native_source(body,self.native_cases())
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+name+'-'+profile[1:],source,profile),(0,''))
        faults=[]
        for phase,fault in itertools.product((0,8),range(14) if original_frame else (0,1)):
            memory,args=fixture(b'A\0',self.table);pair=models(memory,args,phase)
            for model in pair:
                model.fault=fault
                with self.assertRaises(guest.AccessFault):model.run()
                self.assertEqual(model.accesses,fault)
            state=lambda m:(m.memory,m.events,m.r,m.f)
            if original_frame or fault==0:self.assertEqual(state(pair[0]),state(pair[1]))
            else:
                self.assertNotEqual(state(pair[0]),state(pair[1]))
                self.assertEqual(pair[0].events[0],('W',STACK+phase-128+0x38,4,pair[0].before[22]))
                self.assertEqual(pair[1].events[0],('W',STACK+phase-128+0x34,4,pair[1].before[21]))
            faults.append(dict(phase=phase,fault=fault,equal=original_frame or fault==0))
        self.receipt(name+'-seven-saves',entry=entry,body_words=222,frame=128,differences=differences,
            saves=saves,guest_cases=cases,actual_retail_helpers_at_original_addresses=True,
            private_flag_home_cases=private,native_cases_per_profile=733,native_profiles=['O2','O0'],
            fired_fault_pairs=faults,original_first13_words_and_28_early_fault_pairs_exact=original_frame,
            first_completed_store_retail_S6_SP38_candidate_S5_SP34=not original_frame,
            seven_saved_register_count_does_not_prove_original_lifetimes_or_store_order=True,
            strict_padder_rejects_888_into_876=True,
            legacy_padder_emits_in_slot_jump_and_separate_game_overflow_not_retail_match=True,
            slot_overflow12_not_installed_or_matched=True)


    def test_17_call_local_flag_seven_saves_semantics_and_frame_rejection(self):
        self.qualify_seven_save_dispatch('capture-local-dispatch',148)

    def test_18_late_flags_restore_original_frame_and_early_partial_states(self):
        for name,differences in (('flag-branches-captured',146),('capture-flat-late-flag',178)):
            with self.subTest(name=name):self.qualify_seven_save_dispatch(name,differences,True)


    def test_19_all_instruction_access_cuts_reject_current_flag_lifetime(self):
        entry=screen.ENTRY+0x200000
        body=dict(screen.candidates())['flag-branches-captured']
        with patch.object(screen,'ENTRY',entry):
            meta,words=screen.compile_candidate(self.root,self.out,'complete-fault-seed',body)
        asm=(self.out/'before-assembly').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        source=self.out/'fault-original.s';obj=source.with_suffix('.o')
        source.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+
            '.section .text.measurer,"ax"\n.set noreorder\n.set noat\n.globl '+screen.FUNCTION+'\n'+
            '.type '+screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+asm+
            '\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(source)],check=True,capture_output=True)
        script=self.out/'fault-original.ld';elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text.measurer) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in screen.SYMBOLS.items()],'-o',str(elf),str(obj)],
            check=True,capture_output=True)
        original=list(struct.unpack('>219I',sections(elf)['.text'][1]))
        self.assertEqual(original,self.retail)
        def models(memory,args,phase):
            with patch.object(screen,'ENTRY',entry):
                return [InstructionFaultMeasurer(code,memory,args,self.connected,phase) for code in (original,words)]
        state=lambda m:(m.memory,m.events,m.r,m.f,m.condition)
        records=[];pairs=0
        for text,phase in itertools.product((b'A\0',b' \0',b'\n\0',bytes((0xA8,0))),(0,8)):
            memory,args=fixture(text,self.table);normal=models(memory,args,phase)
            expected=Reference(memory,args).run()
            for model in normal:
                model.run()
                self.assertEqual(public(model.memory),public(expected.memory));self.assertEqual(model.calls,expected.calls)
                self.assertEqual(model.accesses,sum(e[0] in ('R','W') for e in model.events))
            counts=[model.accesses for model in normal];self.assertEqual(counts[0],counts[1])
            first=None;equal=0
            for fault in range(counts[0]):
                pair=models(memory,args,phase)
                for model in pair:
                    model.fault=fault
                    with self.assertRaises(guest.AccessFault):model.run()
                    self.assertEqual(model.accesses,fault)
                    self.assertIn(model.dispatched_word>>26,(32,33,35,36,37,40,41,43,49,57))
                same=state(pair[0])==state(pair[1]);equal+=same;pairs+=1
                if not same and first is None:
                    self.assertGreaterEqual(fault,14)
                    self.assertEqual(pair[0].r[31],pair[1].r[31])
                    self.assertEqual(pair[0].r[8],0);self.assertNotEqual(pair[1].r[8],0)
                    first=dict(fault=fault,words=['0x%08X'%model.dispatched_word for model in pair],
                        changed_gprs=[i for i in range(32) if pair[0].r[i]!=pair[1].r[i]],
                        t0=[model.r[8] for model in pair],memory_equal=pair[0].memory==pair[1].memory,
                        events_equal=pair[0].events==pair[1].events)
            self.assertIsNotNone(first)
            for model in models(memory,args,phase):
                model.fault=counts[0];model.run();self.assertEqual(model.accesses,counts[0])
            records.append(dict(text=list(text),phase=phase,instruction_accesses=counts[0],
                equal_cut_states=equal,first_difference=first))
        self.receipt('complete-instruction-fault-rejection',entry=entry,cases=records,fired_pairs=pairs,
            both_original_and_candidate_independently_linked_same_code_base=True,
            original219_still_byte_exact_no_instruction_projection=True,
            call_argument_observation_is_not_a_guest_memory_access=True,
            first_divergence_not_a_rebase_only_return_address_difference=True,
            all_instruction_access_ordinals_for_four_named_calls_two_phases_exercised=True,
            current_source_flag_lifetime_rejected_not_complete_match_qualification=True,
            not_all_inputs_private_aliases_FCSR_or_hardware_fault_claim=True)


    def test_20_call_observations_do_not_fire_instruction_access_faults(self):
        memory,args=fixture(bytes((0xA8,0)),self.table)
        model=InstructionFaultMeasurer(self.retail,memory,args,self.connected)
        model.fault=0
        snapshot=(model.memory.copy(),model.events.copy(),model.r.copy(),model.f.copy(),model.condition)
        observed=model.arguments(6)
        self.assertEqual(observed,tuple(model.r[4:8])+(read(model.memory,model.r[29]+16),
            read(model.memory,model.r[29]+20)))
        self.assertEqual((model.memory,model.events,model.r,model.f,model.condition),snapshot)
        self.assertEqual(model.accesses,0)
        contaminated=InstructionFaultMeasurer(self.retail,memory,args,self.connected);contaminated.fault=0
        with patch.object(contaminated,'peek',side_effect=contaminated.get):
            with self.assertRaises(guest.AccessFault):contaminated.arguments(6)
        self.assertEqual(contaminated.accesses,0)
        self.assertFalse(hasattr(contaminated,'dispatched_word'))
        with self.assertRaises(guest.AccessFault):model.run()
        self.assertEqual(model.accesses,0);self.assertEqual(model.dispatched_word,self.retail[1])


if __name__=='__main__':
    unittest.main()
