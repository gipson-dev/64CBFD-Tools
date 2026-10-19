"""Qualify direct frame recovery and explicit retail four-way row loops."""
from pathlib import Path
import json
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_neighbor_row_builder_home_candidates as homes
from tools.tests import test_game_neighbor_row_builder_recovery as previous
from tools.experiments.game_route_projection_layout_normalizer import relocate

source,guest = homes.source,previous.guest


class NeighborRowBuilderHomeTests(unittest.TestCase):
    native = previous.NeighborRowBuilderRecoveryTests.native
    test_02_public_reference_calls_stores_and_integer_traps = previous.NeighborRowBuilderRecoveryTests.test_02_public_reference_calls_stores_and_integer_traps
    test_04_production_inputs_unchanged = previous.NeighborRowBuilderRecoveryTests.test_04_production_inputs_unchanged
    test_07_original_field_query_and_jump_table = previous.NeighborRowBuilderRecoveryTests.test_05_actual_retail_field_query_and_jump_table
    test_08_independent_GNU_maps = previous.NeighborRowBuilderRecoveryTests.test_08_GNU_retail_and_both_raw_profiles_on_independent_maps

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/(homes.BUILD+'/qualification')
        cls.values = source.freeze(cls.root,cls.out)
        cls.profiles = {name:source.compile_candidate(cls.root,cls.out,name,homes.SELECTED,normal=normal)
            for name,normal in (('primary',False),('normal',True))}
        cls.retail = list(struct.unpack_from('>336I',cls.values['conker/conker.us.bin'],source.ROM))
        cls.corpus,cls.receipts = tuple(guest.cases()),{}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'qualification.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_frame168_and_closed_explicit_unroll_source(self):
        shapes={name:(r['words'],r['frame'],r['differences']) for name,(_,_,r) in self.profiles.items()}
        self.assertEqual(shapes,{'primary':(345,168,312),'normal':(433,168,432)})
        for _,words,row in self.profiles.values():
            self.assertFalse(row['diagnostics']);self.assertEqual(words[0],self.retail[0])
        self.assertEqual(homes.SELECTED,dict(homes.candidates())['compact-all-quad'])
        self.assertNotIn('u8 *actor;',homes.SELECTED);self.assertNotIn('u8 *selected;',homes.SELECTED)
        self.assertNotIn('register ',homes.SELECTED);self.assertNotIn('volatile ',homes.SELECTED)
        self.assertIn('if (used < 16)',homes.SELECTED)
        self.assertIn('} while (copy != position);',homes.SELECTED)
        self.receipts.update(raw_profiles=shapes, direct_frame168=True, explicit_four_way_loops=3,
            selected_profile='existing-primary-no-unroll', new_profile_override=False,
            installed=False,matching_credit=0)

    def test_03_native_profiles_and_effective_semantic_negatives(self):
        with patch.object(source,'SELECTED',homes.SELECTED):
            previous.NeighborRowBuilderRecoveryTests.test_03_native32_profiles_and_effective_negatives(self)

    def test_05_both_complete_owner_profiles_preserve_neighbors_and_pools(self):
        with patch.object(source,'SELECTED',homes.SELECTED):
            previous.NeighborRowBuilderRecoveryTests.test_06_both_owner_profiles_preserve_72_neighbors_and_pools(self)

    def test_06_fired_private_gate_closes_frame_not_save_area(self):
        witnesses=[]
        for phase in (0,8):
            for name,words in [('retail',self.retail)]+[(n,v[1]) for n,v in self.profiles.items()]:
                case=guest.Case();model=guest.RowModel(words,guest.fixture(case),case,phase)
                model.fault=0
                with self.assertRaises(guest.core.AccessFault):model.run()
                self.assertEqual(model.accesses,0)
                self.assertEqual(model.r[29],guest.STACK+phase-168)
                expected=guest.STACK+phase-(0x6C if name=='primary' else 0x74)
                self.assertEqual(model.requested,('W',expected,4))
                witnesses.append((phase,name,model.requested))
        selected=self.profiles['primary'][1]
        self.assertTrue(any(w>>26==43 and w>>21&31==29 and w>>16&31==30 for w in selected))
        self.assertFalse(any(w>>26==43 and w>>21&31==29 and w>>16&31==30 for w in self.retail))
        self.receipts.update(fired_first_private_access_gates=6, frame_boundary_closed=True,
            private_save_area_witnesses=witnesses, remaining_extra_S8_save=True,
            literal_private_matching=False)

    def test_09_unsigned_cursor_guest_negative(self):
        with patch.object(source,'SELECTED',homes.SELECTED):
            previous.NeighborRowBuilderRecoveryTests.test_10_unsigned_cursor_negative_is_effective_in_guest_only_domain(self)

    def test_10_wide_rows_skip_final_padding_and_reject_lost_guard(self):
        body=homes.SELECTED.replace('    if (used < 16) {','    if (1) {')
        self.assertNotEqual(body,homes.SELECTED)
        _,words,_=source.compile_candidate(self.root,self.out,'negative-wide-padding',body)
        case=guest.Case(count=26,primary=0,points=((0.,0.),(3.,4.)))
        memory=guest.fixture(case)
        good=guest.RowModel(self.profiles['primary'][1],memory,case).run()
        self.assertEqual(guest.public(good.memory),guest.public(guest.reference(memory,case)[1]))
        with self.assertRaisesRegex(AssertionError,'unmapped store'):
            guest.RowModel(words,memory,case).run()
        self.receipts['effective_guest_lost_wide_row_guard_negative']=True

    def test_11_wrapped_null_actor_address_and_effective_guest_negative(self):
        original_bindings={0x120:[('R_MIPS_HI16','D_800CC2D0')],
            0x124:[('R_MIPS_LO16','D_800CC2D0')]}
        self.assertEqual((self.retail[0x120//4],self.retail[0x124//4]),(0x3C14800D,0x2694C2D0))
        retail=relocate(struct.pack('>336I',*self.retail),original_bindings,{'D_800CC2D0':0})
        images=[('retail',retail)]
        for name,(obj,_,_) in self.profiles.items():
            raw,bindings=source.payload(obj)
            anchors={n:(0 if n=='D_800CC2D0' else int(n[2:],16) if n.startswith('D_') else int(n[5:],16))
                for rows in bindings.values() for _,n in rows}
            images.append((name,relocate(raw,bindings,anchors)))
        changed=homes.SELECTED.replace('(u32)(D_800CC2D0 + (u32)i * 0x32C) != 0','1')
        self.assertNotEqual(changed,homes.SELECTED)
        bad_obj,_,_=source.compile_candidate(self.root,self.out,'negative-null-actor',changed)
        raw,bindings=source.payload(bad_obj)
        anchors={n:(0 if n=='D_800CC2D0' else int(n[2:],16) if n.startswith('D_') else int(n[5:],16))
            for rows in bindings.values() for _,n in rows}
        bad_words=relocate(raw,bindings,anchors)
        regions=tuple((0 if b==guest.ACTORS else b,n) for b,n in guest.SEGMENTS)
        runs=0
        with patch.multiple(guest,ACTORS=0,SEGMENTS=regions):
            case=guest.Case(cursor=0,count=2,primary=0,mask=0)
            memory=guest.fixture(case);result,wanted,calls,stores,_,trap=guest.reference(memory,case)
            self.assertIsNone(trap)
            for phase in (0,8):
                for name,words in images:
                    model=guest.RowModel(words,memory,case,phase).run()
                    self.assertEqual((model.r[2],model.calls),(result,calls))
                    self.assertEqual(guest.public(model.memory),guest.public(wanted))
                    if name!='normal':self.assertEqual(previous.public_stores(model),stores)
                    if name=='retail':self.assertIn(source.ENTRY+0x1DC,model.visits)
                    runs+=1
            wrong=guest.RowModel(bad_words,memory,case).run()
            self.assertNotEqual(guest.public(wrong.memory),guest.public(wanted))
        self.receipts.update(zero_actor_base_completed_guest_runs=runs,
            retail_null_fallback_executed=True,effective_guest_null_address_negative=True,
            zero_actor_base_excluded_from_native_C=True)


if __name__=='__main__':unittest.main()
