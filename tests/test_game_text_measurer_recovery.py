"""Full original/candidate measurers with real helpers; not a byte-match claim."""
import hashlib
import itertools
import json
import math
import struct
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
    def __init__(self,memory,args):
        self.memory=memory.copy();self.args=args;self.calls=[]
    def integer(self,address):return signed(read(self.memory,address))
    def store(self,address,value):put(self.memory,address,value)
    def fp(self,address):return floating(read(self.memory,address))
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
            values[name]=read(self.memory,metrics.SYMBOLS[value]) if isinstance(value,str) else value
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
                        row=read(self.memory,screen.SYMBOLS['D_80085994'])+glyph*4
                        value=self.integer(width)+self.memory[row]+self.memory[row+2]-1
                        self.store(width,value)
                        row=read(self.memory,screen.SYMBOLS['D_80085994'])+glyph*4
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


class GameTextMeasurerRecoveryTests(unittest.TestCase):
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
        assert cls.baseline['elf']=='978d39eab009d4134e5c03d4bdd2d433010812544a5be599c823fdff1ce2aa14'
        assert cls.baseline['guards']=='3f12cf872b84100963934734de2e67f5f07073ce3112ccbd2e5c4cb8af84666e'
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


if __name__=='__main__':
    unittest.main()
