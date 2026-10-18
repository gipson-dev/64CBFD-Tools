"""Isolated normalized byte match, complete observational proof and rebases."""
import hashlib
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_projection_joint_extent_fit as screens
from tools.experiments import game_route_projection_layout_normalizer as layout
from tools.experiments import game_route_projection_suffix_proof as proof


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/screens.BUILD
        layout.source.prior.freeze(cls.root,cls.out)
        cls.raw,cls.bindings=layout.source.checked(cls.root/layout.source.BUILD/'qualified.o')
        cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>321I',rom,layout.source.source.ROM))
        cls.helpers={entry:list(struct.unpack_from('>%dI'%count,rom,entry-0x14FD2B50)) for entry,count in proof.HELPERS.items()}

    def test_01_closed_recipe_matches_all_321_retail_words(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Normalizer must not read retail or files')):
            actual,bindings=layout.normalize(self.raw,self.bindings)
        words=layout.relocate(actual,bindings,proof.ANCHORS)
        self.assertEqual(words,self.truth)
        self.assertEqual(hashlib.sha256(actual).hexdigest(),layout.NORMALIZED_SHA)
        origins=layout.origins(list(struct.unpack('>335I',self.raw)))
        self.assertEqual((len(origins),len(set(origins))),(321,321))
        self.assertEqual(len(self.moved),18)
        self.assertEqual([at for at,entries in self.moved.items() if entries[0][0]=='R_MIPS_26'],[660,780,976,1212])
        (self.out/'isolated-normalized-match.json').write_text(json.dumps(dict(
            raw_words=335,normalized_words=321,frame=120,retail_word_differences=0,
            raw_SHA256=layout.source.RAW_SHA,normalized_unlinked_SHA256=layout.NORMALIZED_SHA,
            source_words_removed=14,register_words=len(set(layout.GP)|set(layout.FP)),
            payload_address_forms=11,bindings=18,retail_not_read_by_normalizer=True,
            guards_emitted=False,installed=False,matching_credit=0),indent=2)+'\n')

    def test_02_actual_recipe_has_the_composed_observational_proof(self):
        result=proof.prove(layout.relocate(self.raw,self.bindings,proof.ANCHORS),
            layout.relocate(self.normalized,self.moved,proof.ANCHORS),self.helpers)
        self.assertEqual((result['cycle_paths'],result['loop_paths'],result['common_paths']),(1,10242,6832))
        (self.out/'normalizer-proof.json').write_text(json.dumps(result,indent=2)+'\n')

    def test_03_independent_complete_data_and_call_rebases(self):
        maps=(
            dict(zip(proof.ANCHORS,(0x80097FFC,0x80098000,0x800D8004,0x800D7FFC,0x800A8000,0x800F7FFC,0x15305000,0x15406000))),
            dict(zip(proof.ANCHORS,(0x18000,0x17FFC,0x28004,0x27FFC,0x38000,0x47FFC,0x15508000,0x15609000))),
        )
        results=[]
        for anchors in maps:
            independent=list(self.truth)
            for hi,lo,name in ((11,14,'D_8008FDBC'),(15,19,'D_80087290'),(29,30,'D_800D2350'),
                    (33,34,'D_800D23A8'),(151,153,'D_800D2350'),(152,154,'D_8009DA08'),(199,201,'D_800D2350')):
                address=anchors[name]
                independent[hi]=independent[hi]&0xFFFF0000|((address+0x8000)>>16)&65535
                independent[lo]=independent[lo]&0xFFFF0000|address&65535
            for index,name in ((165,'func_1508907C'),(195,'func_1512D560'),(244,'func_1508907C'),(303,'func_1512D560')):
                independent[index]=independent[index]&0xFC000000|(anchors[name]>>2)&0x3FFFFFF
            actual=layout.relocate(self.normalized,self.moved,anchors)
            self.assertEqual(actual,independent)
            result=proof.prove(layout.relocate(self.raw,self.bindings,anchors),actual,self.helpers,anchors)
            self.assertEqual((result['cycle_paths'],result['loop_paths'],result['common_paths']),(1,10242,6832))
            results.append(dict(anchors={k:'%08X'%v for k,v in anchors.items()},prefix=result['prefix'],
                cycle_paths=result['cycle_paths'],loop_paths=result['loop_paths'],common_paths=result['common_paths']))
        (self.out/'normalizer-full-rebases.json').write_text(json.dumps(dict(independent_complete_maps=2,
            root_and_both_actual_helpers_rebased=True,results=results),indent=2)+'\n')

    def test_04_all_words_bindings_and_recipe_edits_fail_closed(self):
        words=list(struct.unpack('>335I',self.raw))
        for index in range(len(words)):
            bad=list(words);bad[index]^=1
            with self.assertRaisesRegex(ValueError,'Unknown joint projection'):layout.normalize(struct.pack('>335I',*bad),self.bindings)
        for at in self.bindings:
            bad=dict(self.bindings);bad.pop(at)
            with self.assertRaisesRegex(ValueError,'Unknown joint projection'):layout.normalize(self.raw,bad)
        changes=0
        for table in (layout.GP,layout.FP):
            for index,rename in list(table.items()):
                bad=dict(rename);key=next(iter(bad));bad[key]^=1
                with patch.dict(table,{index:bad}),self.assertRaises(ValueError):layout.normalize(self.raw,self.bindings)
                changes+=1
        self.assertEqual(changes,151)
        (self.out/'normalizer-input-controls.json').write_text(json.dumps(dict(word_changes=335,
            binding_removals=18,register_recipe_changes=changes),indent=2)+'\n')

    def test_05_invalid_code_rebases_and_overlaps_fail_closed(self):
        for value in (0x5005000,0x15305001):
            bad=dict(proof.ANCHORS,func_1508907C=value)
            with self.assertRaisesRegex(ValueError,'Invalid projection call rebase'):layout.relocate(self.normalized,self.moved,bad)
        bad=dict(proof.ANCHORS,func_1508907C=layout.source.source.ENTRY)
        helpers=proof.rebased_helpers(self.helpers,bad)
        with self.assertRaisesRegex(ValueError,'Overlapping helper code ranges'):
            proof.Suffix(layout.relocate(self.raw,self.bindings,bad),helpers,proof.prefix.Expressions(),anchors=bad)
        bad=dict(proof.ANCHORS,func_1508907C=proof.ANCHORS['func_1512D560'])
        with self.assertRaisesRegex(ValueError,'Overlapping helper entry addresses'):proof.rebased_helpers(self.helpers,bad)
        with self.assertRaisesRegex(ValueError,'Unknown projection liveness call map'):
            proof.prefix.gp_liveins(self.truth,{0x1508907C:5,0x1512D560:3})


if __name__=='__main__':unittest.main()
