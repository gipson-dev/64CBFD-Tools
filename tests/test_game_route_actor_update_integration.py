"""Private 604-word guard stream, real Make and bounded first-link metadata proof."""
import csv
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_route_actor_update_integration as source
from tools.tests.test_game_one_shot_timer_match import canonical_symbols


class RouteActorUpdateIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        source.bank_successor(cls.root,cls.out)
        context = source.historical_view(cls.root,cls.out)
        context.__enter__()
        cls.addClassCleanup(context.__exit__,None,None,None)
        cls.qualification = source.qualify(cls.root,cls.out)
        cls.make = source.make_shadow(cls.root,cls.out)
        cls.prediction = source.predict(cls.root,cls.out)
        cls.values = source.freeze(cls.root,cls.out)

    def test_01_guard_stream_covers_every_raw_word_and_all_derived_outputs(self):
        raw,bindings = source.source.checked(self.out/'qualified-cursor.o')
        normalized,moved = source.layout.normalize(raw,bindings)
        before = self.values['conker/retail_word_patches.us.csv']
        after = (self.out/'qualified-guards.csv').read_bytes()
        self.assertEqual(after,source.layout.private_guards(before,raw,bindings))
        self.assertTrue(after.startswith(before))
        rows = [row for row in csv.DictReader(io.StringIO(after.decode()))
            if (row['filename'],row['function'])==(source.OWNER,source.FUNCTION)]
        self.assertEqual(len(rows),594)
        self.assertEqual(sum(bool(row['insert_after']) for row in rows),10)
        words,relocations = [],{}
        def decode(value):
            return [] if value=='-' else [tuple(item.split(':',1)) for item in value.split(';')]
        for i,row in enumerate(rows):
            self.assertEqual(int(row['offset'],0),i*4)
            self.assertEqual(int(row['expected'],0),struct.unpack_from('>I',raw,i*4)[0])
            self.assertEqual(decode(row['expected_relocations']),bindings.get(i*4,[]))
            for value,spec in ((row['replacement'],row['replacement_relocations']),
                    (row['insert_after'],row['insert_after_relocations'])):
                if value:
                    if decode(spec):relocations[len(words)*4] = decode(spec)
                    words.append(int(value,0))
        self.assertEqual(struct.pack('>604I',*words),normalized)
        self.assertEqual(relocations,moved)
        with self.assertRaisesRegex(ValueError,'already present'):
            source.layout.private_guards(after,raw,bindings)

    def test_02_actual_padding_Make_and_original_first_prediction(self):
        self.assertTrue(self.qualification['all604_words_equal'])
        self.assertEqual(self.qualification['primary_and_normal_neighbors'],72)
        self.assertTrue(self.qualification['baseline_matches_production_owner'])
        self.assertEqual(self.make['actual_expanded_Make_commands'],7)
        self.assertTrue(self.make['all73_primary_functions_equal'])
        self.assertTrue(self.make['padded_code_and_metadata_equal'])
        self.assertEqual(len(self.make['inherited_Make_warnings']),2)
        self.assertEqual(self.prediction['linked_SHA256'],'44ecb171bef3c1e2c5f3afb2345953cf70d15224a51db37a1d4fc62c60105e0c')
        self.assertTrue(self.prediction['first_link_reused'])
        self.assertTrue(self.prediction['exact_whole_image_prediction'])
        self.assertEqual(self.prediction['metadata_order_groups'],5)
        self.assertEqual(self.prediction['changed_ELF_bytes'],2067)
        initial = json.loads((self.out/'prediction-mismatch.json').read_text())
        self.assertEqual(initial['different_common_bytes'],134)
        self.assertEqual(initial['linked_SHA256'],self.prediction['linked_SHA256'])
        self.assertFalse(initial['first_link_reused'])
        source.freeze(self.root,self.out)

    def test_03_only_bounded_symbol_order_changes_and_effective_controls(self):
        before = self.values['conker/build/conker.us.elf']
        rom = self.values['conker/conker.us.bin']
        span = rom[source.ROM:source.ROM+2416]
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Prediction must not read linked image')):
            predicted = source.predicted_image(before,span)
        self.assertEqual(predicted,(self.out/'first-linked.elf').read_bytes())
        meaning = canonical_symbols(before)
        row = next((name,*fields[1:]) for _,name,fields,_ in source.prior.symbol_rows(before) if name==source.FUNCTION)
        meaning[row] -= 1
        if not meaning[row]:del meaning[row]
        replacement = list(row);replacement[2] = 2416
        meaning[tuple(replacement)] += 1
        self.assertEqual(canonical_symbols(predicted),meaning)
        with patch.object(source,'SERIALIZATION',source.SERIALIZATION[1:]):
            self.assertNotEqual(source.predicted_image(before,span),predicted)
        names,order,fields = source.SERIALIZATION[0]
        changed = list(fields);changed[0] = (fields[0][0]+4,*fields[0][1:])
        with patch.object(source,'SERIALIZATION',((names,order,tuple(changed)),)+source.SERIALIZATION[1:]):
            with self.assertRaisesRegex(ValueError,'meaning'):
                source.predicted_image(before,span)

    def test_04_actual_installed_image_audit(self):
        result = source.audit(self.root,self.out)
        self.assertEqual((result['functions'],result['other_bodies_fixed']),(6057,6056))
        self.assertTrue(result['all_addresses_fixed'] and result['first_link_reproduced'])
        self.assertEqual((result['target_words'],result['metadata_order_groups']),(604,5))
        self.assertEqual(result['game_data']['different_bytes'],0)


if __name__=='__main__':
    unittest.main()
