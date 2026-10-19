"""Qualify complete neighbor-row C without claiming compiler-layout identity."""
from pathlib import Path
import json
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.tests import game_neighbor_row_builder_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments import game_actor_pair_visibility_integration as integration
from tools.tests.game_owner_pool import normalized_pools
from tools.patch_generated_slice_ld import load_game_data_layout
from tools.experiments.game_actor_classifier_candidates import sections

source = guest.source


def public_stores(model):
    return [r for r in model.stores if not guest.STACK - 0x600 <= r[0] < guest.STACK + 0x100]


class NeighborRowBuilderRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / (source.BUILD + '/qualification')
        cls.values = source.freeze(cls.root, cls.out)
        cls.profiles = {}
        for normal in (False, True):
            name = 'normal' if normal else 'primary'
            cls.profiles[name] = source.compile_candidate(cls.root, cls.out, name, normal=normal)
        cls.retail = list(struct.unpack_from('>336I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_complete_profiles_not_match_credit(self):
        shapes = {n:(r['words'], r['frame'], r['differences']) for n, (_, _, r) in self.profiles.items()}
        self.assertEqual(shapes, {'primary':(293,184,330), 'normal':(346,192,327)})
        for _, _, row in self.profiles.values(): self.assertFalse(row['diagnostics'])
        self.receipts.update(raw_profiles=shapes, installed=False, matching_credit=0)

    def test_02_public_reference_calls_stores_and_integer_traps(self):
        completed, trapped, coverage, reordered = 0, 0, set(), 0
        for ordinal, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            result, wanted, calls, stores, _, trap = guest.reference(memory, case)
            for phase in (0, 8):
                for name, words in [('retail',self.retail)] + [(n,v[1]) for n,v in self.profiles.items()]:
                    with self.subTest(case=ordinal, profile=name, phase=phase):
                        model = guest.RowModel(words, memory, case, phase)
                        if trap:
                            with self.assertRaises(guest.BreakFault) as caught: model.run()
                            self.assertEqual(caught.exception.code, trap)
                            trapped += 1
                        else:
                            model.run(); self.assertEqual(model.r[2], result)
                            completed += 1
                        self.assertEqual(model.calls, calls)
                        actual_stores = public_stores(model)
                        if name == 'normal':
                            self.assertCountEqual(actual_stores, stores)
                            reordered += actual_stores != stores
                        else:
                            self.assertEqual(actual_stores, stores)
                        bad = [(a,model.memory.get(a),v) for a,v in guest.public(wanted).items()
                            if model.memory.get(a) != v]
                        self.assertEqual(bad[:8], [], 'Public RAM differs (%d bytes)' % len(bad))
                        if name == 'retail': coverage.update(model.visits)
        self.receipts.update(fixtures=len(self.corpus), completed_runs=completed,
            fired_integer_traps=trapped, retail_words_visited=len(coverage),
            normal_completed_store_order_divergences=reordered,
            normal_ordered_public_trace_qualified=False)

    def native(self, body, name, opt='-O2'):
        unit = self.out / (name + '.c'); executable = unit.with_suffix('.elf')
        unit.write_text(guest.native_harness(body, guest.native_cases()))
        command = native_command(opt) + [str(unit), '-o', str(executable)]
        command.extend(['-mstackrealign', '-fno-strict-aliasing', '-fno-math-errno'])
        compiled = subprocess.run(command, capture_output=True)
        self.assertEqual(compiled.returncode, 0, compiled.stderr.decode())
        run = subprocess.run([str(executable)], capture_output=True)
        self.native_diagnostic = tuple(struct.unpack('<3I',run.stdout)) if len(run.stdout)==12 else run.stdout
        return run.returncode

    def test_03_native32_profiles_and_effective_negatives(self):
        for opt in ('-O0','-O2','-O3'):
            code = self.native(source.SELECTED, 'native' + opt[1:], opt)
            self.assertEqual(code, 0, self.native_diagnostic)
        body = source.SELECTED
        controls = {
            'skip-rejected-minimum':body.replace('if (distance < nearest)', 'if ((score >= 0) && (distance < nearest))'),
            'cursor-greater-equal':body.replace('*(s32 *)(state + 0x10) == slot', 'slot >= *(s32 *)(state + 0x10)'),
            'old-tie-first':body.replace('scores[start + position] < score', 'scores[start + position] <= score'),
            'weighted-minimum':body.replace('if (distance < nearest)', 'if (score < nearest)').replace('nearest = distance;', 'nearest = score;'),
            'wrong-high-mask':body.replace('0x10000u <<', '1u <<'),
            'lost-primary-reload':body.replace('                    primaryCount = D_8008FD90;', ''),
            'capacity-clamp':body.replace('if (score >= 0)', 'if ((score >= 0) && (used < 16))'),
            'zero-score-padding':body.replace('neighbors[start + i] = -1;', 'neighbors[start + i] = -1; scores[start + i] = 0;'),
        }
        results = {}
        for name, changed in controls.items():
            self.assertNotEqual(changed, body)
            code = self.native(changed, 'negative-' + name)
            self.assertIn(code, (21,22,23,25,26), (name,self.native_diagnostic))
            results[name] = code
        self.receipts.update(native32_profiles=['O0','O2','O3'], UBSan=True,
            native_fixtures=len(guest.native_cases()), effective_negatives=results)

    def test_04_production_inputs_unchanged(self):
        for name, old in self.values.items(): self.assertEqual((self.root/name).read_bytes(), old, name)
        self.receipts['production_predecessor_unchanged'] = True

    def test_05_actual_retail_field_query_and_jump_table(self):
        rom = self.values['conker/conker.us.bin']
        helper = list(struct.unpack_from('>68I',rom,0xB2E5C))
        start,va,_,owners = load_game_data_layout(self.root/'conker')
        at = start + guest.FIELD_TABLE - va
        self.assertEqual(at,0x242460)
        owner = next(o for o in owners if o['address']<=guest.FIELD_TABLE<o['end'])
        self.assertEqual(owner['input'],'build/asm/data/242420.rodata.s.o(.rodata)')
        table = struct.unpack_from('>7I',rom,at)
        self.assertEqual(table[-1],0x15085A9C)
        connected = dict(zip(range(guest.FIELD,guest.FIELD+272,4),helper))
        runs = 0
        for case in (guest.Case(mode=0xB7,special=(1,)),
                guest.Case(mode=0xB7,special=(1,),primary=0),
                guest.Case(mode=0xB7,special=(1,),count=16)):
            memory = guest.fixture(case)
            for i,word in enumerate(table): guest.put(memory,guest.FIELD_TABLE+i*4,word,4)
            result,wanted,calls,stores,_,trap = guest.reference(memory,case,actual=True)
            self.assertIsNone(trap)
            for phase in (0,8):
                for name,words in [('retail',self.retail)]+[(n,v[1]) for n,v in self.profiles.items()]:
                    model = guest.RowModel(words,memory,case,phase,connected=connected).run()
                    self.assertEqual((model.r[2],model.calls),(result,calls))
                    self.assertEqual(guest.public(model.memory),guest.public(wanted))
                    if name!='normal': self.assertEqual(public_stores(model),stores)
                    self.assertIn(0x15085AB0,model.visits); runs += 1
        self.receipts.update(actual_retail_helper_runs=runs, original_helper_words=68,
            original_jump_table_rom=at, production_helper_still_stub=True)

    def test_06_both_owner_profiles_preserve_72_neighbors_and_pools(self):
        same = integration.mixed.candidate.source.neighbor.same_functions
        for name,normal in (('primary',False),('normal',True)):
            before,diagnostics = source.compile_profile(self.root,self.out,
                self.values[source.SOURCE].decode(),'before-'+name,normal)
            after,_,row = source.compile_candidate(self.root,self.out,'after-'+name,normal=normal,whole=True)
            self.assertFalse(diagnostics or row['diagnostics'])
            self.assertEqual(same(before,after,(source.FUNCTION,)),72)
            self.assertEqual(normalized_pools(before),normalized_pools(after))
            self.assertEqual(source.payload(after),source.payload(self.profiles[name][0]))
        self.receipts.update(owner_profiles=2, unchanged_raw_neighbors_per_profile=72,
            owner_pools_unchanged=True, typed_caller_prototype_preserves_caller=True)

    def test_07_first_private_access_gate_is_not_matching(self):
        witnesses=[]
        for name,words in [('retail',self.retail)]+[(n,v[1]) for n,v in self.profiles.items()]:
            model = guest.RowModel(words,guest.fixture(guest.Case()),guest.Case())
            model.fault=0
            with self.assertRaises(guest.core.AccessFault): model.run()
            self.assertEqual(model.accesses,0)
            self.assertIsNotNone(model.requested)
            witnesses.append((name,model.r[29]-guest.STACK,model.requested))
        self.assertEqual([r[1] for r in witnesses],[-168,-184,-192])
        self.assertNotEqual(witnesses[0][2],witnesses[1][2])
        self.receipts.update(fired_first_private_access_gates=3,
            private_frame_witnesses=witnesses, literal_private_matching=False)

    def test_08_GNU_retail_and_both_raw_profiles_on_independent_maps(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        lo=asm.index('glabel '+source.FUNCTION+'\n'); hi=asm.index('endlabel '+source.FUNCTION,lo)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        path=self.out/'GNU-retail.s';path.write_text(prelude+'\n.text\n'+asm[lo:hi])
        assembled=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],capture_output=True)
        self.assertEqual(assembled.returncode,0,assembled.stderr.decode())
        names={name for obj,_,_ in self.profiles.values() for rows in source.payload(obj)[1].values() for _,name in rows}
        anchors={name:int(name[2:],16) if name.startswith('D_') else int(name[5:],16) for name in names}
        runs=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x115CAC),(0x18FFF000,0x235CB0))):
            images=[]
            for name,obj,count in [('retail',path.with_suffix('.o'),336)]+[(k,v[0],v[2]['words']) for k,v in self.profiles.items()]:
                script=self.out/(name+'-GNU-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                linked=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(key,value+delta) for key,value in anchors.items()],'-o',str(elf),str(obj)],capture_output=True)
                self.assertEqual(linked.returncode,0,linked.stderr.decode())
                images.append((name,list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))))
            moved={key:getattr(guest,key)+delta for key in ('CONTEXT','PRIMARY','ACTORS','FIELD','FIELD_TABLE','FIELD_VALUES')}
            moved['BANKS']=tuple(b+delta for b in guest.BANKS)
            moved['SEGMENTS']=tuple((b+delta,size) for b,size in guest.SEGMENTS)
            with patch.multiple(guest,**moved):
                for case in (guest.Case(),guest.Case(enabled=0,cursor=127),guest.Case(mode=0xB7,special=(1,),mutation=1)):
                    memory=guest.fixture(case);result,wanted,calls,stores,_,trap=guest.reference(memory,case)
                    self.assertIsNone(trap)
                    for name,words in images:
                        model=guest.RowModel(words,memory,case,entry=entry).run()
                        self.assertEqual((model.r[2],model.calls),(result,calls))
                        self.assertEqual(guest.public(model.memory),guest.public(wanted))
                        if name!='normal':self.assertEqual(public_stores(model),stores)
                        runs+=1
        self.receipts.update(independent_GNU_maps=3, rebased_completed_runs=runs,
            rebased_symbol_count=len(anchors))

    def test_09_byte_stride_frontier_keeps_wide_rows_and_records_order_boundary(self):
        body=dict(source.shapes())['byte-fill-narrow']
        _,words,row=source.compile_candidate(self.root,self.out,'byte-fill-narrow',body,normal=True)
        self.assertEqual((row['words'],row['frame'],row['differences']),(330,176,315))
        self.assertFalse(row['diagnostics'])
        reordered=0
        for case in self.corpus:
            memory=guest.fixture(case);result,wanted,calls,stores,_,trap=guest.reference(memory,case)
            model=guest.RowModel(words,memory,case)
            if trap:
                with self.assertRaises(guest.BreakFault) as caught:model.run()
                self.assertEqual(caught.exception.code,trap)
            else:
                model.run();self.assertEqual(model.r[2],result)
            self.assertEqual(model.calls,calls)
            self.assertEqual(guest.public(model.memory),guest.public(wanted))
            self.assertCountEqual(public_stores(model),stores)
            reordered+=public_stores(model)!=stores
        self.assertEqual(reordered,266)
        self.assertEqual(self.native(body,'byte-fill-native'),0,self.native_diagnostic)
        rejected=body.replace('for (i = used * 4; i < 64;', 'for (i = used * 4; i != 64;')
        self.assertNotEqual(rejected,body)
        _,bad_words,_=source.compile_candidate(self.root,self.out,'negative-equality-fill',rejected,normal=True)
        wide=guest.Case(count=26,primary=0,points=((0.,0.),(3.,4.)))
        with self.assertRaisesRegex(AssertionError,'unmapped store'):
            guest.RowModel(bad_words,guest.fixture(wide),wide).run()
        self.receipts.update(byte_stride_frontier=dict(words=330,frame=176,differences=315,
            fixtures=len(self.corpus),public_store_order_divergences=reordered,native32_O2=True),
            unguarded_equality_fill_rejected_on_26_actor_case=True)

    def test_10_unsigned_cursor_negative_is_effective_in_guest_only_domain(self):
        body=source.SELECTED.replace('slot = *(s8 *)','slot = *(u8 *)')
        self.assertNotEqual(body,source.SELECTED)
        _,words,_=source.compile_candidate(self.root,self.out,'negative-unsigned-cursor',body)
        case=guest.Case(cursor=127,enabled=0);memory=guest.fixture(case)
        correct=guest.RowModel(self.retail,memory,case).run()
        wrong=guest.RowModel(words,memory,case).run()
        self.assertNotEqual(guest.public(correct.memory),guest.public(wrong.memory))
        self.receipts['effective_guest_unsigned_cursor_negative']=True


if __name__ == '__main__': unittest.main()
