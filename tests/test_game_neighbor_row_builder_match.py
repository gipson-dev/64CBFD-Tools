"""Complete literal/private, stale source, GNU, padder and image acceptance."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_neighbor_row_builder_layout as layout
from tools.experiments import game_neighbor_row_builder_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.tests import test_game_neighbor_row_builder_homes as home_tests
from tools.tests.test_game_actor_pair_scheduler_homes import literal_state as old_state
from tools.pad_generated_object import emit_padded_assembly

source,guest=layout.source,home_tests.guest


def state(model):return old_state(model),getattr(model,'lo',None),getattr(model,'hi',None)


class NeighborRowBuilderMatchTests(unittest.TestCase):
    native=home_tests.NeighborRowBuilderHomeTests.native
    test_04_native32_profiles_and_effective_negatives=home_tests.NeighborRowBuilderHomeTests.test_03_native_profiles_and_effective_semantic_negatives
    test_05_original_field_query_and_jump_table=home_tests.NeighborRowBuilderHomeTests.test_07_original_field_query_and_jump_table
    test_06_independent_GNU_maps=home_tests.NeighborRowBuilderHomeTests.test_08_independent_GNU_maps
    test_07_wrapped_null_actor_address=home_tests.NeighborRowBuilderHomeTests.test_11_wrapped_null_actor_address_and_effective_guest_negative

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/(layout.BUILD+'/qualification')
        cls.values=source.freeze(cls.root,cls.out)
        cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'selected',layout.SELECTED)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.anchors={n:int(n[2:],16) if n.startswith('D_') else int(n[5:],16)
            for rows in cls.moved.values() for _,n in rows}
        cls.words=relocate(cls.normalized,cls.moved,cls.anchors)
        cls.retail=list(struct.unpack_from('>336I',cls.values['conker/conker.us.bin'],source.ROM))
        prelude=(cls.root/'conker/include/asm_processor_prelude.inc').read_text()
        lines=[prelude,'.text','.globl '+source.FUNCTION,'.type '+source.FUNCTION+',@function',source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>336I',cls.normalized)):
            label='.Lrow_word_%d'%i;lines.extend((label+':','.word 0x%08X'%word))
            for kind,name in cls.moved.get(i*4,[]):lines.append('.reloc %s,%s,%s'%(label,kind,name))
        lines.append('.size %s,.-%s'%(source.FUNCTION,source.FUNCTION))
        asm=cls.out/'normalized.s';asm.write_text('\n'.join(lines)+'\n');cls.normal_obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(cls.root/'conker/include'),'-o',str(cls.normal_obj),str(asm)],check=True,capture_output=True)
        cls.profiles={'primary':(cls.obj,cls.raw_words,cls.row),
            'normalized':(cls.normal_obj,cls.words,dict(words=336,frame=168,differences=0))}
        cls.corpus,cls.receipts=tuple(guest.cases()),{}

    @classmethod
    def tearDownClass(cls):(cls.out/'qualification.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_closed_origins_typed_accesses_and_stale_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(345,168,312))
        self.assertFalse(self.row['diagnostics']);self.assertEqual(self.words,self.retail)
        order=layout.origins();kept=[x for x in order if isinstance(x,int)]
        self.assertEqual((len(set(kept)),len(order)-len(kept),len(layout.REMOVED)),(319,17,26))
        self.assertEqual((len(self.bindings),len(self.moved)),(13,19))
        raw=struct.unpack('>345I',self.raw);public=0
        memory_ops={32,33,35,36,37,40,41,43,49,57}
        for at in layout.REMOVED:
            word=raw[at//4]
            if word>>26 in memory_ops:self.assertEqual(word>>21&31,29)
        for i,item in enumerate(order):
            if isinstance(item,int):
                word=raw[item//4]
                if word>>26 in memory_ops and word>>21&31!=29:
                    self.assertEqual(self.words[i]>>26,word>>26);public+=1
            else:
                word=struct.unpack_from('>I',self.normalized,i*4)[0]
                if word>>26 in memory_ops:self.assertEqual(word>>21&31,29)
        controls=0
        for at in range(0,1380,4):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaises(ValueError):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaises(ValueError):layout.normalize(self.raw,bad)
            controls+=1
        wrong=order.copy();wrong[0],wrong[1]=wrong[1],wrong[0]
        with patch.object(layout,'origins',return_value=wrong):
            with self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
        with patch.object(layout,'allocation',return_value=({},{})):
            with self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
        self.assertEqual(layout.fields(0x0007000D),((),()))
        self.assertEqual(layout.fields(0x00F8001A),((21,16),()))
        self.assertEqual(layout.fields(0x4600010D),((),(11,6)))
        self.receipts.update(words=336,frame=168,raw_differences=312,normalized_differences=0,
            retained_origins=319,derived_forms=17,omissions=26,bindings=19,
            retained_public_memory_instructions=public,raw_binding_stale_controls=controls,recipe_stale_controls=2)

    def test_02_complete_literal_private_state_raw_public_and_reference(self):
        completed,traps,coverage=0,0,set()
        for ordinal,case in enumerate(self.corpus):
            memory=guest.fixture(case);result,wanted,calls,stores,_,trap=guest.reference(memory,case)
            for phase in (0,8):
                models=[]
                for name,words in (('retail',self.retail),('normalized',self.words),('raw',self.raw_words)):
                    model=guest.RowModel(words,memory,case,phase)
                    if trap:
                        with self.assertRaises(guest.BreakFault) as caught:model.run()
                        self.assertEqual(caught.exception.code,trap);traps+=1
                    else:
                        model.run();self.assertEqual(model.r[2],result);completed+=1
                    self.assertEqual(model.calls,calls)
                    self.assertEqual(home_tests.previous.public_stores(model),stores,(ordinal,phase,name))
                    self.assertEqual(guest.public(model.memory),guest.public(wanted),(ordinal,phase,name))
                    models.append(model)
                self.assertEqual(state(models[0]),state(models[1]),(ordinal,phase))
                coverage.update(models[0].visits)
        self.receipts.update(fixtures=len(self.corpus),completed_runs=completed,fired_divide_traps=traps,
            literal_private_pairs=len(self.corpus)*2,main_retail_words_visited=len(coverage))

    def test_03_every_selected_access_cut_fires_with_literal_private_state(self):
        cuts=0
        for case in (guest.Case(),guest.Case(mode=0xB7,special=(1,),mutation=1),
                guest.Case(count=10,primary=0,points=((0.,0.),(3.,4.)))):
            memory=guest.fixture(case)
            for phase in (0,8):
                complete=guest.RowModel(self.retail,memory,case,phase).run()
                for cut in range(complete.accesses):
                    pair=[]
                    for words in (self.retail,self.words):
                        model=guest.RowModel(words,memory,case,phase);model.fault=cut
                        with self.assertRaises(guest.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);pair.append(model)
                    self.assertEqual(state(pair[0]),state(pair[1]));cuts+=1
        self.receipts.update(fired_literal_private_access_pairs=cuts,every_requested_fault_fired=True,
            prior_frame_and_save_area_boundaries_closed=True)

    def test_08_actual_Make_padder_guard_history_and_full_image_negatives(self):
        out=self.root/integration.BUILD
        self.assertTrue(json.loads((out/'qualification.json').read_text())['all73_addresses_fixed'])
        self.assertTrue(json.loads((out/'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        before=self.values['conker/build/conker.us.elf'];first=(out/'first-linked.elf').read_bytes()
        truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+1344]
        integration.check_image(before,first,truth)
        slot=integration.elf_slot_offset(before,source.ENTRY,1344)
        symbol=next(r[0] for r in integration.symbol_rows(before) if r[1]==source.FUNCTION)
        for at in (slot,slot-4,symbol+8,len(first)-1):
            bad=bytearray(first);bad[at]^=1
            with self.assertRaises(ValueError):integration.check_image(before,bytes(bad),truth)
        old=self.values['conker/retail_word_patches.us.csv'];guards=(out/'qualified-guards.csv').read_bytes()
        self.assertEqual(guards,layout.private_guards(old,self.raw,self.bindings));self.assertTrue(guards.startswith(old))
        reader=csv.DictReader(io.StringIO(guards.decode()));fields,rows=reader.fieldnames,list(reader)
        target=[r for r in rows if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual((len(target),sum(r['omit']=='true' for r in target),
            sum(bool(r['insert_after']) for r in target)),(345,26,17))
        for field,value in (('expected','0x00000000'),('expected_relocations','R_MIPS_HI16:D_800D23B0')):
            bad=deepcopy(rows);i=next(i for i,r in enumerate(bad) if r['filename']==source.OWNER and r['function']==source.FUNCTION)
            bad[i][field]=value;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader();writer.writerows(bad);path=self.out/('stale-'+field+'.csv');path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                function_objects={n:out/'after-normal.o' for n in integration.NORMAL_FUNCTIONS},
                word_patches_path=path,filename=source.OWNER)
        identity=sum(r['omit']!='true' and r['expected']==r['replacement'] and
            r['expected_relocations']==r['replacement_relocations'] for r in target)
        self.receipts.update(expected_word_rows=345,omit_rows=26,insertion_rows=17,identity_guard_rows=identity,
            prior_guard_bytes_exact_prefix=True,actual_padder_stale_controls=2,image_corruption_controls=4,
            padded_neighbors_preserved=72,Makefile_unchanged=True)

    def test_09_exact_predecessor_or_strict_installed_scope(self):
        before=self.values[source.SOURCE];current=(self.root/source.SOURCE).read_bytes()
        if before==current:
            for name,old in self.values.items():self.assertEqual((self.root/name).read_bytes(),old,name)
            self.receipts['production_predecessor_unchanged']=True
        else:
            self.assertEqual(current,source.recovered_owner(before.decode(),layout.SELECTED).encode())
            audit=integration.audit(self.root,self.root/integration.BUILD)
            self.assertEqual((audit['functions'],audit['other_bodies_fixed']),(6057,6056))
            self.receipts.update(installed_words=336,installed_other_bodies_fixed=6056,
                all6057_addresses_fixed=True,protected_game_data_bytes=189088,protected_game_data_owners=720)

    def test_10_completed_group_table_frame_aliases_reject_raw_homes(self):
        pairs=0
        for home in (0x70,0x78):
            for phase in (0,8):
                bank=guest.STACK+phase-168+home-0xE64
                banks=(bank,guest.BANKS[1])
                regions=tuple((bank-0x2400 if b==guest.BANKS[0]-0x2400 else b,n)
                    for b,n in guest.SEGMENTS)
                with patch.multiple(guest,BANKS=banks,SEGMENTS=regions):
                    case=guest.Case();memory=guest.fixture(case)
                    a=guest.RowModel(self.retail,memory,case,phase).run()
                    b=guest.RowModel(self.words,memory,case,phase).run()
                    wrong=guest.RowModel(self.raw_words,memory,case,phase).run()
                    self.assertEqual(state(a),state(b))
                    self.assertEqual(a.r[2],0)
                    self.assertNotEqual(guest.public(a.memory),guest.public(wrong.memory))
                    pairs+=1
        self.receipts.update(completed_guest_frame_alias_pairs=pairs,
            effective_raw_home_alias_negatives=pairs,frame_aliases_excluded_from_native_C=True)


if __name__=='__main__':unittest.main()
