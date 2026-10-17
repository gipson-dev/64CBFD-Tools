"""Complete uninstalled recovery, real byte copy and explicit matching limits."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_overlay_fade_packet as source
from tools.tests import game_overlay_fade_oracle as model
from tools.tests import game_overlay_fade_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout


class OverlayFadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row = source.candidate(cls.root,cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>54I',cls.rom,source.ROM))
        cls.copy = model.memcpy_words(cls.rom)
        context = type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original = assembly.ViewListSetupTests.original.__func__(context,'original-fade',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)

    def receipt(self, name, **data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_candidate_is_uninstalled_unmatched_and_preserves27_neighbors(self):
        self.assertEqual((self.row['words'],self.row['retail_words'],self.row['frame'],self.row['ordinal_differences']),(53,54,64,45))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],27)
        self.assertEqual(self.images[0],self.images[1])
        self.assertNotEqual(self.images[0],self.truth)
        self.assertFalse(self.row['installed']); self.assertFalse(self.row['matching_credit']); self.assertFalse(self.row['byte_exact'])
        source.checked_parts(*source.parts(self.obj),source.projection.sections(self.obj)['.rodata'][1])
        before = (self.out/'before-color_owner').read_bytes()
        self.assertEqual((self.root/source.PATHS['color_owner']).read_bytes(),before)
        self.assertEqual(before.decode().count(source.PRAGMA),1)
        image = (self.out/'before-elf').read_bytes()
        at = elf_slot_offset(image,source.ENTRY,216)
        self.assertEqual(image[at:at+216],self.rom[source.ROM:source.ROM+216])

    def test_02_full_guest_reference_inherited_padding_provider_boundary_and_actual_memcpy(self):
        count = 0; seen = [set(),set()]; padding = set()
        for memory,args,phase,outcome,mode in model.cases():
            expected,calls = model.reference(memory,args,phase,outcome,mode)
            states = []
            for i,words in enumerate((self.truth,self.images[0])):
                m = model.FadeOracle(words,memory,args,self.copy,phase,outcome,mode).run()
                self.assertEqual(m.memory,expected,(args,phase,outcome,mode,i))
                self.assertEqual(m.calls,calls)
                if model.half(args[4])>0:
                    self.assertEqual(m.packets,[model.payload(args,memory[model.STACK+phase-7])])
                    if outcome:
                        pad = 0x5A if mode == 1 else memory[model.STACK+phase-7]
                        self.assertEqual(m.copies,[model.payload(args,pad)])
                        padding.add(pad)
                        self.assertTrue(set(range(source.MEMCPY,source.MEMCPY+44,4))<=m.visits)
                else:
                    self.assertFalse(m.packets); self.assertFalse(m.copies)
                seen[i].update(m.visits)
                states.append(m.memory)
            self.assertEqual(*states)
            count += 1
        missing = [[i*4 for i in range(n) if source.ENTRY+i*4 not in seen[k]] for k,n in enumerate((54,53))]
        self.assertEqual(missing,[[140,156,160,164],[96,112,116,120]])
        self.assertIn(0x5A,padding); self.assertGreater(len(padding),1)
        self.receipt('guest',paired_cases=count,retail_missing_offsets=missing[0],candidate_missing_offsets=missing[1],
            actual_memcpy_words=11,all8_guest_bytes_and_full_memory=True,inherited_and_live_padding_observed=True,
            allocator_is_scripted_nine_word_boundary=True,no_private_register_or_fault_equivalence_claim=True)

    def test_03_native32_typed_caller_fields_controls_and_padding_acceptance_limit(self):
        caller,driver = self.out/'native-caller.c',self.out/'native-driver.c'
        caller.write_text(native.CALLER); driver.write_text(native.DRIVER)
        forms = [('o2','-O2',source.SELECTED,0),('o0','-O0',source.SELECTED,0),('zero-padding','-O2',native.ZERO_PADDING,0)]
        forms += [(n,'-O2',b,22) for n,b in native.controls(source.SELECTED).items()]
        exits = {}
        for name,opt,body,wanted in forms:
            unit = self.out/('native-'+name+'.c'); exe = unit.with_suffix('.elf')
            unit.write_text(native.HEADER+body+'\n')
            built = subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran = subprocess.run([str(exe)],capture_output=True,text=True,timeout=120)
            exits[name] = ran.returncode
            self.assertEqual(ran.returncode,wanted,(name,ran.stderr))
        _,zero = source.measure(self.root,self.out,'zero-padding')
        args = (204,204,255,255,15,2,255,0x8765ABCD); memory = model.fixture(args)
        original = model.FadeOracle(self.truth,memory,args,self.copy).run()
        changed = model.FadeOracle(zero,memory,args,self.copy).run()
        self.assertNotEqual(original.memory,changed.memory)
        self.assertEqual(changed.memory[model.EVENT+0x28+5],0)
        self.assertNotEqual(original.memory[model.EVENT+0x28+5],0)
        self.receipt('native',cases_each=384,exits=exits,UBSan=True,separate_full_body_and_typed_caller=True,
            seven_semantic_bytes_and_all_external_canaries=True,padding_byte5_excluded_only=True,
            zero_padding_passes_native_but_changes_guest_bytes=True,not_an_installation_certificate=True)

    def test_04_duration_reload_and_trap_schedule_hypothesis_are_separate(self):
        _,last = source.measure(self.root,self.out,'fade-last')
        def loads(words):
            return [i*4 for i,w in enumerate(words) if w>>26==33 and w>>21&31==29 and w&65535==0x52]
        def order(words):
            trap = next(i for i,w in enumerate(words) if w>>26==0 and w&63==13)
            store = max(i for i,w in enumerate(words) if w>>26==40 and w>>21&31==29 and 0x34<=w&65535<=0x38)
            return trap,store
        self.assertEqual(loads(self.truth),[24,48,104])
        self.assertEqual(loads(self.images[0]),[24])
        self.assertEqual(loads(last),[24])
        self.assertEqual(len(last),53)
        self.assertGreater(*order(self.truth)); self.assertLess(*order(self.images[0])); self.assertGreater(*order(last))
        rows = []
        for phase in (0,8):
            args = (204,204,255,255,15,2,255,0x8765ABCD); memory = model.fixture(args,phase)
            completed = [model.FadeOracle(w,memory,args,self.copy,phase).run() for w in (self.truth,self.images[0])]
            self.assertEqual(completed[0].all_accesses-completed[1].all_accesses,2)
            self.assertNotEqual(completed[0].io,completed[1].io)
            faults_fired = 0
            for words,m in zip((self.truth,self.images[0]),completed):
                for fault in range(m.all_accesses):
                    stopped = model.FadeOracle(words,memory,args,self.copy,phase)
                    stopped.access_fault = fault
                    with self.assertRaises(faults.AccessBoundary):
                        stopped.run()
                    self.assertEqual(stopped.all_accesses,fault)
                    faults_fired += 1
            rows.append(dict(phase=phase,original_accesses=completed[0].all_accesses,candidate_accesses=completed[1].all_accesses,
                positively_fired_faults=faults_fired))
        self.receipt('private-gap',incoming_duration_LH_counts=[3,1,1],fade_last_still53=True,rows=rows,
            trap_placement_alone_does_not_restore_reload=True,not_fault_equivalence=True)

    def test_05_all53_word_bindings_pool_and172_input_corruptions_fail_closed(self):
        raw,bindings = source.parts(self.obj); pool = source.projection.sections(self.obj)['.rodata'][1]
        for i in range(53):
            bad = bytearray(raw); bad[i*4] ^= 1
            with self.assertRaises(ValueError):
                source.checked_parts(bytes(bad),bindings,pool)
        for i in range(len(pool)):
            bad = bytearray(pool); bad[i] ^= 1
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bindings,bytes(bad))
        for at in (*bindings,-4):
            bad = dict(bindings); bad[at] = [('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):
                source.checked_parts(raw,bad,pool)
        read = Path.read_bytes
        self.assertEqual(len(source.PATHS),172)
        for relative in source.PATHS.values():
            target = self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):
                    source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        layout = audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        self.receipt('inputs',protected_entries=172,distinct_paths=len(set(source.PATHS.values())),raw_word_controls=53,
            binding_controls=3,pool_controls=16,all_production_unchanged=True,protected_layout=layout)

    def test_06_independent_original_and_C_links_relocate_both_actual_calls(self):
        raw,bindings = source.parts(self.obj)
        count = 0
        for index,(entry,provider,copy) in enumerate(((0x15507FFC,0x17127FFC,0x18218004),
                (0x16218004,0x18227FFC,0x15528004),(0x18FFF000,0x15508004,0x17117FFC))):
            anchors = dict(func_15149130=provider,memcpy=copy)
            text,unresolved = emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path = self.out/('rebase-C-%d.s'%index); path.write_text(text)
            obj = path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            bodies = []
            for name,target,length in (('original',self.original,216),('C',obj,212)):
                script = self.out/('rebase-%d-%s.ld'%(index,name))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],capture_output=True,check=True)
                data = source.projection.sections(elf)['.text'][1][:length]
                bodies.append(list(struct.unpack('>%dI'%(length//4),data)))
            self.assertNotEqual(*bodies)
            for memory,args,phase,outcome,mode in model.cases():
                expected,calls = model.reference(memory,args,phase,outcome,mode)
                calls = [(provider if target==source.PROVIDER else copy,args) for target,args in calls]
                for words in bodies:
                    m = model.FadeOracle(words,memory,args,self.copy,phase,outcome,mode,
                        entry=entry,provider=provider,memcpy=copy).run()
                    self.assertEqual((m.memory,m.calls),(expected,calls))
                count += 1
        self.receipt('rebases',independent_original_C_links=6,paired_cases=count,both_actual_call_targets=True,
            actual_eleven_word_copy_relocated=True,byte_exact=False,not_private_schedule_equivalence=True)

    def test_07_all_four_original_call_sites_two_full_callers_and_two_bounded_windows(self):
        class Join(Exception):
            pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc == self.join:
                    raise Join
                return super().__getitem__(pc)
        count = 0; sites = []
        for entry,rom,size,frame in ((0x150B6754,0xE3C04,140,0x30),
                (0x150D66A4,0x103B54,140,0x30),(0x15194EF4,0x1C23A4,52,0),
                (0x151DC87C,0x209D2C,48,0)):
            packet = list(struct.unpack_from('>%dI'%(size//4),self.rom,rom))
            sites.append(dict(entry=hex(entry),words=size//4,full_caller=bool(frame)))
            for variant,outcome,mode,phase in itertools.product(range(4),(0,1,2),(0,1,2),(0,8)):
                random = ((0,0),(55,10),(0xFFFFFFFF,0x80000000),(0x8765ABCD,0x12345678))[variant]
                owner,channel,context = 0x12340081,0xABCD0002,0x8765ABCD
                initial = (owner,context,0,0,0,0,0,0)
                registers = {}
                if entry == 0x150B6754:
                    forwarded = (204,204,255,200+random[0]%56,15+random[1]%11,0,owner&255,context)
                elif entry == 0x150D66A4:
                    initial = (channel,owner,context,0,0,0,0,0)
                    forwarded = (255,255,255,200+random[0]%56,25+random[1]%6,channel&255,owner&255,context)
                elif entry == 0x15194EF4:
                    registers = {8:0x30000,25:35+variant}
                    forwarded = (255,255,255,255,35+variant,channel&255,255,1)
                else:
                    registers = {8:(0,1,49,50)[variant],10:variant,14:owner&255,13:context}
                    forwarded = (255,255,255,150+registers[8],8+variant,0,owner&255,context)
                memory = model.fixture(initial,phase)
                if entry == 0x15194EF4:
                    model.put(memory,0x30318,0x32000)
                    model.put(memory,0x3223D,channel&255,1)
                states = []
                for words in (self.truth,self.images[0]):
                    connected = dict(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
                    if not frame:
                        connected[entry+size] = 0
                    m = model.FadeOracle(packet,memory,initial,self.copy,phase,outcome,mode,
                        entry=entry,connected=connected,random=random)
                    for register,value in registers.items():
                        m.r[register] = value
                    if frame:
                        m.run()
                        for register in (*range(16,24),28,29,30,31):
                            self.assertEqual(m.r[register],m.before[register])
                        self.assertEqual(m.random_index,2)
                    else:
                        m.code = Code(m.code,m); m.code.join = entry+size
                        with self.assertRaises(Join):
                            m.run()
                        self.assertEqual(m.r[29],model.STACK+phase)
                    self.assertEqual(m.forwarded,[forwarded])
                    self.assertEqual(m.packets,[model.payload(forwarded,memory[model.STACK+phase-frame-7])])
                    provider_calls = [args for target,args in m.calls if target == source.PROVIDER]
                    self.assertEqual(provider_calls,[model.provider_arguments(forwarded)])
                    if outcome:
                        padding = 0x5A if mode == 1 else memory[model.STACK+phase-frame-7]
                        self.assertEqual(m.copies,[model.payload(forwarded,padding)])
                    else:
                        self.assertFalse(m.copies)
                    states.append((m.memory,m.calls))
                self.assertEqual(*states)
                count += 1
        self.receipt('callers',original_sites=sites,paired_cases=count,actual_target_and_copy=True,
            argument_capture_after_call_delay_slots=True,full_allocator=False,two_larger_parents_not_executed=True,
            no_private_register_or_fault_equivalence_claim=True)


if __name__ == '__main__':
    unittest.main()
