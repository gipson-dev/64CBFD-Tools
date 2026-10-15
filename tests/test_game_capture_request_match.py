"""Guarded full private-state, relocation and closed instruction-mapping checks."""
import copy
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_capture_request_match as match
from tools.experiments import game_capture_request_slot as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_capture_request_slot as model


class GuardSourceTests(unittest.TestCase):
    def test_bijective_schedule_exact_guard_count_and_relocation_only_sites(self):
        mapping={at:match.SCHEDULE.get(at,at) for at in range(0,156,4)}
        self.assertEqual(set(mapping),set(mapping.values()))
        self.assertEqual(len(match.POINTER_WORDS),16)
        rows=list(csv.reader(io.StringIO(match.guard_rows())))
        self.assertEqual(len(rows),22)
        self.assertEqual([int(row[2],0) for row in rows if row[3]==row[4]],[12,16])
        self.assertTrue(all(row[-3:]==['','','false'] for row in rows))
        with self.assertRaises(ValueError):
            match.guard_manifest(b'bad')
        with self.assertRaises(ValueError):
            match.guard_manifest(('x,'+source.FUNCTION+',x\n').encode())

    def test_register_swap_has_closed_operand_domains(self):
        self.assertEqual(match.swap_pointer_registers(0x3C020000),0x3C030000)
        self.assertEqual(match.swap_pointer_registers(0xE4440008),0xE4640008)
        self.assertEqual(match.swap_pointer_registers(0x00405825),0x00605825)
        with self.assertRaises(ValueError):
            match.swap_pointer_registers(0x03E00008)
        with self.assertRaises(ValueError):
            match.swap_pointer_registers(0x00001025)


class CaptureRequestMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/match.BUILD
        cls.obj,cls.padded,cls.words,cls.record=match.qualify(cls.root,cls.out)
        cls.retail=list(struct.unpack_from('>40I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM))
        cls.data,cls.functions,cls.relocations=parse_object(cls.obj)
        cls.f=cls.functions[source.FUNCTION]
        cls.raw=cls.data[cls.f['value']:cls.f['value']+cls.f['size']]
        cls.relative={at-cls.f['value']:v for at,v in cls.relocations.items()
            if cls.f['value']<=at<cls.f['value']+cls.f['size']}

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_closed_mapping_real_guards_and_full_slot(self):
        self.assertEqual(self.words,self.retail)
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),match.RAW_SHA256)
        self.assertEqual((self.record['raw_differences'],self.record['linked_differences'],self.record['guards']),(22,0,22))
        words,relocations=match.normalized_instructions(self.raw,self.relative)
        padded,functions,rel=parse_object(self.padded)
        f=functions[source.FUNCTION]
        self.assertEqual(padded[f['value']:f['value']+156],struct.pack('>39I',*words))
        self.assertEqual({at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+156},relocations)
        for name in self.functions.keys()-{source.FUNCTION}:
            original=self.functions[name]
            other=functions[name]
            self.assertEqual(padded[other['value']:other['value']+other['size']],
                self.data[original['value']:original['value']+original['size']])

    def test_02_all_completed_guest_private_states_and_reachable_words(self):
        cases=0
        coverage=set()
        for states,callback,vector,mode in itertools.product(model.STATES,model.CALLBACKS,model.VECTORS,range(4)):
            for phase in (0,8):
                memory,payload,value=model.fixture(states,callback,vector,mode,phase)
                expected,result=model.reference(memory,states,callback,vector,payload,value,phase)
                pair=[model.RequestOracle(words,memory,vector,payload,phase).run() for words in (self.retail,self.words)]
                self.assertEqual(model.state(pair[0]),model.state(pair[1]))
                self.assertEqual((pair[1].memory,pair[1].r[2],pair[1].calls),(expected,result,[]))
                coverage.update(pair[1].visits)
                cases+=1
        self.assertEqual(len(coverage),38)
        self.receipt('guest',paired_SP_cases=cases,all_modeled_private_state_exact=True,
            all_38_reachable_words=True,raw_C_private_mismatch_not_erased=True,not_hardware_or_FCSR=True)

    def test_03_all_paired_fired_prefixes_now_match(self):
        total=0
        for states,mode in itertools.product(((0,1,255),(1,0,128),(1,255,0),(1,128,255)),range(4)):
            memory,payload,_=model.fixture(states,-1,model.VECTORS[3],mode)
            count=model.RequestOracle(self.retail,memory,model.VECTORS[3],payload).run().accesses
            for cut in range(count):
                pair=[]
                for words in (self.retail,self.words):
                    instance=model.RequestOracle(words,memory,model.VECTORS[3],payload,fault=cut)
                    with self.assertRaises(model.machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses,cut)
                    pair.append(instance)
                self.assertEqual(model.state(pair[0]),model.state(pair[1]))
                total+=1
        self.assertEqual(total,322)
        self.receipt('prefixes',paired_fired_prefixes=total,all_modeled_private_states_exact=True,
            not_hardware_exception_acceptance=True)

    def test_04_original_assembly_three_rebases_signed_low_and_execution(self):
        original=(self.root/source.BUILD/'before-request_original').read_text()
        block=original.split('glabel '+source.FUNCTION,1)[1].split('endlabel '+source.FUNCTION,1)[0]
        path=self.out/'original.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+
            'glabel '+source.FUNCTION+block+'endlabel '+source.FUNCTION+'\n.word 0\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path)],capture_output=True,check=True)
        # The normalized standalone input preserves relocations, not fixed linked addresses.
        _,pf,pr=parse_object(self.padded)
        f=pf[source.FUNCTION]
        assembly,unresolved=emit_function(parse_object(self.padded)[0],f,pr,source.FUNCTION,
            {'D_800DD348':source.BASE,'D_800DD3FC':source.END})
        self.assertEqual(unresolved,[])
        generated=self.out/'rebase-selected.s'
        generated.write_text(assembly+'\n.word 0\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(generated.with_suffix('.o')),str(generated)],capture_output=True,check=True)
        count=0
        for index,(entry,base) in enumerate(((source.ENTRY,source.BASE),(source.ENTRY+0x5000,0x800D7FF0),
                (source.ENTRY-0x7000,0x800DFFF0))):
            outputs=[]
            for label,obj in (('original',path.with_suffix('.o')),('selected',generated.with_suffix('.o'))):
                script=self.out/('rebase-%d.ld'%index)
                elf=self.out/('%s-rebase-%d.elf'%(label,index))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800DD348=0x%X'%base,'--defsym=D_800DD3FC=0x%X'%(base+180),
                    '-o',str(elf),str(obj)],capture_output=True,check=True)
                outputs.append(sections(elf)['.text'][1][:160])
            self.assertEqual(outputs[0],outputs[1])
            words=list(struct.unpack('>40I',outputs[1]))
            with patch.multiple(source,ENTRY=entry,BASE=base,END=base+180):
                for states,mode in itertools.product(model.STATES,range(4)):
                    memory,payload,value=model.fixture(states,-1,model.VECTORS[3],mode)
                    expected,result=model.reference(memory,states,-1,model.VECTORS[3],payload,value)
                    instance=model.RequestOracle(words,memory,model.VECTORS[3],payload).run()
                    self.assertEqual((instance.memory,instance.r[2]),(expected,result))
                    count+=1
        self.receipt('rebases',original_assembly_pairs=3,independent_text_base_and_signed_low=True,
            guest_cases=count,retail_end_stays_three_records_past_base=True)

    def test_05_every_raw_word_relocation_and_each_guard_is_effective(self):
        for index in range(39):
            bad=bytearray(self.raw)
            bad[index*4]^=1
            with self.assertRaises(ValueError):
                match.normalized_instructions(bytes(bad),self.relative)
        for offset in self.relative:
            bad=copy.deepcopy(self.relative)
            bad[offset]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):
                match.normalized_instructions(self.raw,bad)
        for index in range(len(match.GUARDS)):
            guards=list(match.GUARDS)
            offset,expected,replacement=guards[index]
            guards[index]=(offset,expected^1,replacement)
            with patch.object(match,'GUARDS',tuple(guards)):
                manifest=match.guard_manifest((self.root/source.BUILD/'before-guards').read_bytes())
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                match.pad(self.root,self.out,self.obj,'bad-guard-%d'%index,manifest)
        self.receipt('controls',all_raw_word_flips_rejected=39,raw_relocation_controls=4,
            all_expected_guard_word_controls=22,unknown_codegen_fails_closed=True)


if __name__=='__main__':
    unittest.main()
