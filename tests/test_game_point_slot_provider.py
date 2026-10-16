"""Qualify the slot builder, its recovered caller and closed scratch-role guards."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_point_slot_provider as source
from tools.tests import test_game_packed_point_transform as caller
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections


def fixture(value, pointer, alias):
    output = (caller.OUTPUT, caller.SOURCE, caller.SOURCE-4, caller.SOURCE+4)[alias]
    memory = {caller.STACK+i:(i*17+13)&255 for i in range(-64,64)}
    memory.update({output+i:0xA5 for i in range(-16,80)})
    memory.update({caller.SOURCE+i:0xB6 for i in range(8)})
    caller.put(memory, caller.SOURCE+1, value, 1)
    caller.put(memory, caller.SOURCE+4, pointer)
    expected = dict(memory)
    first, end = value&15, (value>>4)+1
    for i in range(16):
        caller.put(expected, output+i*4, (pointer+(i-first)*16)&0xFFFFFFFF if first <= i < end else 0)
    return memory, (caller.SOURCE,output), expected


def state(model):
    return model.r, model.f, model.memory, model.events, model.calls, model.lo, model.condition, model.accesses


class PointSlotProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj, cls.padded, cls.raw, cls.truth, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        data, placed = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.normalized = list(struct.unpack_from('>71I',data,placed[source.FUNCTION]['value']))
        cls.wrapper = list(struct.unpack_from('>55I',data,placed['func_150948C0']['value']))
        if cls.normalized != cls.truth or cls.wrapper != list(struct.unpack_from('>55I',cls.rom,0xC1D70)):
            raise AssertionError('Changed emitted provider or caller words')

    def receipt(self, name, **row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_all_ranges_pointer_carries_aliases_and_all_instruction_coverage(self):
        count, visits = 0, set()
        for value, pointer, alias, phase in itertools.product(range(256),(0,0x20000,0xFFFFFFF0),range(4),(0,8)):
            memory,args,expected = fixture(value,pointer,alias)
            models = [caller.PackedOracle(words,memory,phase=phase,entry=source.ENTRY,arguments=args).run()
                for words in (self.truth,self.raw,self.normalized)]
            for model in models:
                self.assertEqual(model.memory,expected,(value,pointer,alias,phase))
                self.assertEqual(model.events,models[0].events)
                self.assertEqual((model.accesses,model.calls),(18,[]))
            self.assertEqual(state(models[0]),state(models[2]))
            visits.update(models[1].visits)
            count += 1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+284,4)))
        self.receipt('guest',cases=count,range_bytes=256,private_stack_writes=0,memory_accesses_per_case=18,
            raw_public_memory_and_access_trace=True,normalized_complete_state=True,covered_words=len(visits),
            raw_caller_saved_register_identity_not_claimed=True)

    def test_02_every_access_fault_prefix_all_range_bytes(self):
        count = 0
        for value, cut in itertools.product(range(256),range(18)):
            memory,args,_ = fixture(value,0xFFFFFFF0,value%4)
            models = [caller.PackedOracle(words,memory,entry=source.ENTRY,arguments=args,fault=cut)
                for words in (self.truth,self.raw,self.normalized)]
            for model in models:
                with self.assertRaises(AccessFault):
                    model.run()
                self.assertEqual(model.accesses,cut)
                self.assertEqual((model.memory,model.events),(models[0].memory,models[0].events))
            self.assertEqual(state(models[0]),state(models[2]))
            count += 1
        self.receipt('fault-prefixes',cases=count,hardware_fault_or_portable_C_fault_semantics_not_claimed=True)

    def test_03_actual_recovered_transform_provider_and_retail_matrix(self):
        wrapper = self.wrapper
        matrix = {caller.TRANSFORM+i*4:w for i,w in enumerate(struct.unpack_from('>40I',self.rom,0xD4E10))}
        count = 0
        for value,phase,alias in itertools.product(range(256),(0,8),range(4)):
            memory,args = caller.fixture(value,value%5,alias)
            expected,calls = caller.reference(memory,args)
            models = []
            for provider in (self.truth,self.raw,self.normalized):
                connected = dict(matrix)
                connected.update({source.ENTRY+i*4:w for i,w in enumerate(provider)})
                models.append(caller.PackedOracle(wrapper,memory,entry=0x150948C0,
                    arguments=args,phase=phase,connected=connected).run())
            for model in models:
                self.assertEqual(caller.public(model.memory),expected)
                self.assertEqual(model.memory,models[0].memory)
                self.assertEqual((model.events,model.calls),(models[0].events,models[0].calls))
                self.assertEqual(model.calls[1:],calls)
            self.assertEqual(state(models[0]),state(models[2]))
            count += 1
        self.receipt('connected',cases=count,real_wrapper_words=55,real_provider_words=71,real_matrix_words=40,
            no_opaque_helper_hooks=True,full_gameplay_or_hardware_FCSR_parity_not_claimed=True)

    def test_04_native32_actual_provider_and_caller_O2_O0_UBSan_effective_controls(self):
        harness = caller.native_harness().replace('s32 func_1509499C();',
            'void func_1509499C(PackedPointSource948C0 *, s16 **);')
        lo,hi = source.build.function_span(harness,source.FUNCTION)
        harness = harness[:lo]+harness[hi:]
        harness_path = self.out/'native-harness.c'
        harness_path.write_text(harness)
        wrapper = self.out/'native-wrapper.c'
        wrapper.write_text('#include <ultra64.h>\n'+source.previous.DECLARATIONS+source.previous.SELECTED)
        controls = {
            'wrong-first':source.SELECTED.replace('& 0xF','& 0x7'),
            'exclusive-end':source.SELECTED.replace('(source->slotRange >> 4) + 1','(source->slotRange >> 4)'),
            'wrong-stride':source.SELECTED.replace('point += 8;','point += 4;'),
            'uncleared-prefix':source.SELECTED.replace('slots[index] = NULL;',
                'slots[index] = (s16 *)source->points;',1),
        }
        exits = {}
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (label,'-O2',body,False) for label,body in controls.items()]:
            if not valid:
                self.assertNotEqual(body,source.SELECTED)
            selected = self.out/'native-provider.c'
            selected.write_text('#include <ultra64.h>\n'+source.previous.DECLARATIONS+body)
            exe = self.out/('native-'+label)
            result = subprocess.run([*caller.native_command(opt,valid),str(selected),str(wrapper),str(harness_path),
                '-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result = subprocess.run([str(exe)],capture_output=True,timeout=30)
            self.assertIn(result.returncode,(0,) if valid else (21,22,23),(label,result.stderr))
            exits[label] = result.returncode
        self.receipt('native',cases_per_selected=2560,separate_units_actual_provider_and_caller=True,
            native32_O2_O0_UBSan=True,exits=exits)

    def test_05_eighteen_neighbors_complete_guard_history_and_object_controls(self):
        obj,diagnostics = source.build.compile_owner(self.root,self.out,
            (self.out/'before-packet_owner').read_text(),'neighbor-before')
        self.assertFalse(diagnostics)
        before,after = parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(before[1]),set(after[1]))
        for name,f in before[1].items():
            if name == source.FUNCTION:
                continue
            g = after[1][name]
            self.assertEqual(before[0][f['value']:f['value']+f['size']],after[0][g['value']:g['value']+g['size']],name)
            bindings = lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value'] <= a < f['value']+f['size']}
            self.assertEqual(bindings(before,f),bindings(after,g),name)
        self.assertEqual(len(before[1])-1,18)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],len(source.GUARDS)),(71,0,33,33))
        source.closed_instruction_roles(self.raw,self.truth)
        for i in range(71):
            bad = self.raw.copy()
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                source.closed_instruction_roles(bad,self.truth)
        text,functions,rel = after
        f = functions[source.FUNCTION]
        for i in range(71):
            bad = bytearray(text)
            bad[f['value']+i*4] ^= 1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source,'parse_object',return_value=(text,functions,{f['value']:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        old = (self.out/'before-guards').read_bytes()
        guards = source.proposed_guards(old)
        self.assertTrue(guards.startswith(old))
        import csv
        import io
        rows = list(csv.DictReader(io.StringIO(guards.decode())))[-33:]
        self.assertEqual(len(rows),33)
        for row,(offset,(expected,replacement)) in zip(rows,source.GUARDS.items()):
            self.assertEqual((int(row['offset'],0),int(row['expected'],0),int(row['replacement'],0)),
                (offset,expected,replacement))
            self.assertEqual((row['expected_relocations'],row['replacement_relocations'],row['omit']),('-','-','false'))
        with self.assertRaises(ValueError):
            source.proposed_guards(guards)

    def test_06_frozen_inputs_and_measured_source_screen_receipts(self):
        rb = Path.read_bytes
        for key in source.PATHS:
            path = self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p == path else rb(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)
        count = 0
        before = (self.out/'before-packet_owner').read_text()
        for label,body in source.forms():
            receipt = self.out/(label+'.json')
            if not receipt.exists():
                continue
            row = json.loads(receipt.read_text())
            self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(before,body))
            text,functions,rel = parse_object(self.out/(label+'.o'))
            f = functions[source.FUNCTION]
            self.assertEqual(hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            self.assertFalse({a:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']})
            data = sections(self.out/(label+'.elf'))['.text'][1]
            words = struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            differences = sum(a != b for a,b in zip(words,self.truth))+abs(len(words)-71)
            self.assertEqual((len(words),differences,row['diagnostics']),(row['words'],row['differences'],''))
            self.assertGreaterEqual(differences,33)
            count += 1
        self.assertGreaterEqual(count,100)
        self.receipt('screens',measured_source_forms=count,selected_differences=33,unguarded_match_not_claimed=True)

    def test_07_complete_first_prediction_and_slot_controls(self):
        row = source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_serialization_bytes'],row['metadata_exclusions']),(220,0,0))
        slot = (self.out/'predicted-slot.bin').read_bytes()
        for i in range(71):
            bad = bytearray(slot)
            bad[i*4] ^= 1
            with self.assertRaises(ValueError):
                source.slot_expected_image((self.out/'before-elf').read_bytes(),bytes(bad))


if __name__ == '__main__':
    unittest.main()
