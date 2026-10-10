"""Qualify closed selector layout, full private traces and linked-only installation."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_segment_selector_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_segment_selector_recovery as recovery
from tools.tests import test_game_object_color_mode_match as color
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, ACTORS, OUTPUT, PAIR = recovery.STACK,recovery.ACTORS,recovery.OUTPUT,recovery.PAIR
LINKS=recovery.LINKS


class FullFaultOracle(recovery.SegmentOracle):
    def gate(self,address):
        if self.fault==self.accesses: raise recovery.AccessFault(self.accesses)
        self.accesses+=1


class GameActorSegmentSelectorMatchTests(unittest.TestCase):
    run_host=recovery.GameActorSegmentSelectorRecoveryTests.run_host
    write_rows=classmethod(color.GameObjectColorModeMatchTests.write_rows.__func__)
    assemble=classmethod(color.GameObjectColorModeMatchTests.assemble.__func__)
    test_02_byte_gates_mutations_and_order=recovery.GameActorSegmentSelectorRecoveryTests.test_02_all_bytes_nulls_and_mutating_callbacks
    test_03_output_and_pair_aliases=recovery.GameActorSegmentSelectorRecoveryTests.test_03_output_aliases_and_pair_aliases
    test_04_actual_banked_override_and_animation_reader=recovery.GameActorSegmentSelectorRecoveryTests.test_04_real_banked_override_and_animation_reader
    test_09_actual_native32_SDK_C=recovery.GameActorSegmentSelectorRecoveryTests.test_07_actual_native32_with_SDK_macro
    test_10_fresh_effective_compiled_negatives=recovery.GameActorSegmentSelectorRecoveryTests.test_08_fresh_effective_complete_negative_controls

    def receipt(self,name,**values):
        if name in ('guest','aliases','callees'):
            values['executions']=values['cases']*3
        if name=='guest':
            values.pop('complete_private_frame_not_yet_exact',None)
            values['raw_private_layout_differs']=True
            values['fitted_complete_private_memory_and_order_exact']=True
        recovery.GameActorSegmentSelectorRecoveryTests.receipt(self,name,**values)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-segment-selector-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream)
            cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>146I',cls.rom,screen.ROM))
        assembly=(cls.root/'conker/asm/58F80.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot_asm=cls.out/'slot.s'
        cls.slot_asm.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.write_rows(cls.out/'isolated.csv',screen.guard_rows(cls.out/'selected.o'))
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot_asm,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80'))
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+screen.FUNCTION+',@function\n'+
            screen.FUNCTION+':\n'+assembly+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.linked=cls.link('fitted',LINKS[0])
        cls.link('original',LINKS[0])
        cls.objects,cls.diagnostics=[],[]
        before=(cls.out/'before-source').read_text()
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings=compile_owner(cls.root,cls.out,body,name)
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/(name+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.objects.append(obj)
            cls.diagnostics.append(warnings)
        cls.rows=screen.guard_rows(cls.objects[1])
        cls.guards=cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.old_rows+cls.rows)
        elf=(cls.root/cls.paths['elf']).read_bytes()
        cls.helpers={}
        for entry,rom,size in ((recovery.OVERRIDE,0xABDB8,96),(recovery.ANIMATION_HELPER,0xB1E50,44)):
            words=list(struct.unpack_from('>%dI'%(size//4),elf,elf_slot_offset(elf,entry,size)))
            assert words==list(struct.unpack_from('>%dI'%(size//4),cls.rom,rom))
            cls.helpers.update({entry+i*4:w for i,w in enumerate(words)})
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        fixture='#include <PR/mbi.h>\n#include <PR/gbi.h>\n#define NULL ((void *)0)\n'+screen.recovery.TYPES+'''
static u8 D_800CC2D0[26*0x32C];
static u8 modes[256][24], *D_800D1C90[256], pair[2];
static ActorSegmentRow58F80 rows[256], otherRows[256], *D_800C5338[256];
static Gfx output[8];
static s32 wantedSlot, calls, mutation, failFirst, error;
u8 *func_1507E908(u8 *actor,s32 selector) {
    if(actor!=D_800CC2D0+wantedSlot*0x32C || selector!=1) error=1;
    calls++;
    if(mutation) { actor[4]=8; actor[0x6C]=0; D_800C5338[8]=otherRows; }
    return failFirst && calls==1 ? NULL : pair;
}
'''+screen.SELECTED+'\n'
        cls.fixture=subprocess.run(['cc','-m32','-E','-P','-D_LANGUAGE_C','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',
            '-I',str(cls.root/'conker/include/2.0L'),'-xc','-'],input=fixture,
            capture_output=True,text=True,check=True).stdout

    @classmethod
    def link(cls,name,symbols):
        script=cls.out/('link-%s-%X.ld'%(name,symbols[0]))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%symbols[0])
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%(key,value) for key,value in zip(screen.recovery.SYMBOLS,symbols[1:])],
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        count=parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))

    def compare(self,memory,slot=0,output=OUTPUT,returns=(PAIR,PAIR),actions=None,
            symbols=LINKS[0],phase=0,words=None,real=False):
        expected,events,calls,result=recovery.reference(memory,slot,output,returns,actions,symbols,real)
        helper=self.linked
        if screen.recovery.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            elf=(self.root/self.paths['elf']).read_bytes()
            helper=list(struct.unpack_from('>146I',elf,elf_slot_offset(elf,screen.ENTRY,584)))
            self.assertEqual(helper,self.linked)
        models=[]
        for body in (words or self.words,self.retail,helper):
            model=recovery.SegmentOracle(body,memory,slot,output,returns,actions,symbols,phase,
                connected=self.helpers if real else None).run()
            self.assertEqual(recovery.public_memory(model.memory),recovery.public_memory(expected))
            self.assertEqual(recovery.public(model.events),events)
            self.assertEqual((model.calls,model.r[2]),(calls,result))
            models.append(model)
        self.assertEqual((models[1].memory,models[1].events,models[1].calls),
            (models[2].memory,models[2].events,models[2].calls))
        return models

    def test_01_closed_shape_every_word_and_relocation(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes']), (144,136,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.linked,self.retail)
        self.assertEqual(sum(bool(r['insert_after']) for r in self.rows),3)
        self.assertEqual([r['offset'] for r in self.rows if r['omit']=='true'],['0xC8'])
        for index in range(144):
            stale=list(screen.RAW)
            stale[index]^=0x10000
            with self.assertRaisesRegex(ValueError,'stale complete'): screen.recipe(stale)
        self.receipt('shape',raw_words=144,matched_words=146,frame=136,guards=144,
            changed_rows=sum(r['expected']!=r['replacement'] for r in self.rows),
            inserted_producers=3,omitted_NOPS=1,tail_padding=0,recipe_never_reads_ROM=True,
            full_raw_word_rejections=144)

    def test_05_complete_private_aliases_holes_and_fault_prefixes(self):
        cases=faults=0
        inputs=[]
        for phase,first,second,pair_offset in itertools.product((0,8),(0,9,10),(0,9),
                (0x18,0x68,0x6C,0x80)):
            pair=STACK+phase-0x88+pair_offset
            inputs.append((recovery.fixture(first,second),phase,(pair,pair),False))
        inputs += [(recovery.fixture(first,second),phase,(PAIR,PAIR),real)
            for phase,first,second,real in itertools.product((0,8),(0,9,10),(0,9,10),(False,True))]
        for memory,phase,returns,real in inputs:
            hole=STACK+phase-0x88+0x10
            for byte in range(4): del memory[hole+byte]
            models=[FullFaultOracle(body,memory,returns=returns,phase=phase,
                connected=self.helpers if real else None).run() for body in (self.retail,self.linked)]
            self.assertEqual((models[0].memory,models[0].events,models[0].calls,models[0].r[2]),
                (models[1].memory,models[1].events,models[1].calls,models[1].r[2]))
            events=models[0].events
            cases+=1
            for index,event in enumerate(events):
                if event[0]=='CALL': continue
                ordinal=sum(e[0]!='CALL' for e in events[:index])
                expected=memory.copy()
                for prior in events[:index]:
                    if prior[0]=='W': recovery.put(expected,prior[1],prior[3],prior[2])
                for body in (self.retail,self.linked):
                    model=FullFaultOracle(body,memory,returns=returns,phase=phase,
                        connected=self.helpers if real else None)
                    model.fault=ordinal
                    with self.assertRaises(recovery.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args,(ordinal,))
                    self.assertEqual(model.events,events[:index])
                    self.assertEqual(model.memory,expected)
                faults+=1
        self.receipt('private',cases=cases,full_fault_prefixes=faults,fault_executions=faults*2,
            gates_verified=True,complete_private_memory_and_order_exact=True,reserved_holes_untouched=True)

    def test_06_independent_links_with_private_memory(self):
        cases=0
        for symbols in LINKS:
            bodies=[self.link(name,symbols) for name in ('original','fitted','selected')]
            for first,second,phase in itertools.product((0,1,9,10),(0,2,10),(0,8)):
                memory=recovery.fixture(first,second,symbols=symbols)
                expected,events,calls,result=recovery.reference(memory,symbols=symbols)
                models=[recovery.SegmentOracle(body,memory,symbols=symbols,phase=phase).run() for body in bodies]
                for model in models:
                    self.assertEqual(recovery.public_memory(model.memory),recovery.public_memory(expected))
                    self.assertEqual(recovery.public(model.events),events)
                    self.assertEqual((model.calls,model.r[2]),(calls,result))
                self.assertEqual((models[0].memory,models[0].events),(models[1].memory,models[1].events))
                cases+=1
        self.receipt('rebases',links=12,symbol_sets=4,cases=cases,full_private_memory_and_traces=True)

    def test_07_copied_owner_and_only_target_padded_bytes(self):
        self.assertEqual(self.diagnostics,[[],[]])
        old,of,orels=parse_object(self.objects[0])
        new,nf,nrels=parse_object(self.objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative=lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name in of:
            if name==screen.FUNCTION: continue
            a,b=of[name],nf[name]
            self.assertEqual((a['size'],old[a['value']:a['value']+a['size']],relative(orels,a)),
                (b['size'],new[b['value']:b['value']+b['size']],relative(nrels,b)),name)
        self.assertEqual(normalized_pools(self.objects[0]),normalized_pools(self.objects[1]))
        bodies=[]
        for index,obj in enumerate(self.objects):
            name='padded-owner-%d'%index
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if index==0 else self.guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            bodies.append(parse_object(self.out/(name+'.o')))
        start=bodies[1][1][screen.FUNCTION]['value']
        self.assertEqual(bodies[1][1][screen.FUNCTION]['size'],584)
        self.assertEqual(bodies[0][0][:start],bodies[1][0][:start])
        self.assertEqual(bodies[0][0][start+584:],bodies[1][0][start+584:])
        self.receipt('owner',neighbors=len(nf)-1,pools_and_relative_relocations_unchanged=True,
            actual_padded_owner_only_target_584_bytes_changes=True,zero_diagnostics=True)

    def test_08_actual_padder_stale_words_and_relocations(self):
        data=(self.out/'selected.o').read_bytes()
        header=ELF_HEADER.unpack_from(data)
        headers=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11]) for i in range(header[12])]
        ns=headers[header[13]]
        names=data[ns[4]:ns[4]+ns[5]]
        text=next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(144):
            changed=bytearray(data)
            struct.pack_into('>I',changed,text[4]+index*4,screen.RAW[index]^0x10000)
            path=self.out/'stale.o'
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows=[dict(row) for row in screen.guard_rows(self.out/'selected.o')]
            rows[offset//4]['expected_relocations']='-'
            path=self.out/'stale-relocations.csv'
            self.write_rows(path,rows)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,filename='generated_58F80')
        self.receipt('stale',actual_word_rejections=144,relocation_rejections=7)

    def test_11_whole_linked_installation_audit(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.recovery.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes()
        expected=bytearray(before)
        struct.pack_into('>146I',expected,elf_slot_offset(before,screen.ENTRY,584),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),584)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_584_bytes_and_symbol_extent_changed=True,
            old_guards_exact_byte_prefix=True,conversion_rows_unchanged=True,protected_data=audit)

    def test_12_literal_retail_call_site_cursor_forwarding(self):
        downstream=0x1502F9FC
        # The nine retail words are a boundary test, not a complete banked caller.
        literal=list(struct.unpack_from('>9I',self.rom,0x5A300))
        self.assertEqual(literal[:5],[0x0D40BC07,0x02002025,0x00402025,0x0D40BE7F,0x02402825])
        wrapper=[0x27BDFFE0,0xAFBF0014,0xAFB00018,0xAFB2001C,0x00808025,0x00A09025,
            *literal,0x8FBF0014,0x8FB00018,0x8FB2001C,0x03E00008,0x27BD0020]
        helper=self.linked
        if screen.recovery.ORIGINAL not in (self.root/screen.SOURCE).read_text():
            elf=(self.root/self.paths['elf']).read_bytes()
            helper=list(struct.unpack_from('>146I',elf,elf_slot_offset(elf,screen.ENTRY,584)))
            self.assertEqual(helper,self.linked)
        class Boundary(recovery.SegmentOracle):
            def record_call(model,target):
                count=1 if target==recovery.ANIMATION_HELPER else 2
                args=model.arguments(count)
                model.calls.append((target,*args))
                model.events.append(('CALL',target,args))
            def hook(model,target):
                assert target==downstream
                result=model.r[4]+16
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
                model.r[2]=result
        cases=0
        for slot,first,second,enabled,phase in itertools.product((0,25),(0,9,10),(0,1),
                (False,True),(0,8)):
            memory=recovery.fixture(first,second,slot=slot,output=enabled)
            connected=dict(self.helpers)
            connected.update({screen.ENTRY+i*4:w for i,w in enumerate(helper)})
            model=Boundary(wrapper,memory,slot=slot,entry=0x15204000,phase=phase,connected=connected).run()
            expected=OUTPUT+(32 if enabled else 0)
            self.assertEqual(model.calls[0],(screen.ENTRY,OUTPUT,slot))
            self.assertEqual(model.calls[-1],(downstream,expected,slot))
            self.assertEqual(model.r[2],expected+16)
            self.assertEqual(recovery.read(model.memory,expected+16),0xDB06000C)
            self.assertEqual(recovery.read(model.memory,expected+20),model.before[19])
            cases+=1
        self.receipt('caller',cases=cases,literal_retail_words=9,caller='func_1502CCFC',
            synthetic_ABI_wrapper=True,full_caller_not_claimed=True,downstream_callback_bounded=True,
            actual_installed_or_fitted_helper=True,cursor_and_slot_forwarding_verified=True)


if __name__=='__main__':
    unittest.main()
