"""Qualify owned native allocation decisions, not suppressed diagnostic numbers."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_dual_fade_allocation_choice as source


class AllocationChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.results={label:source.observe(cls.root,cls.out,label) for label in ('normal','home')}

    def test_01_actual_comparison_and_opposite_positive_control(self):
        normal,home=(self.results[label] for label in ('normal','home'))
        self.assertEqual(normal['roles']['record']['color'],14)
        self.assertEqual(home['roles']['weight']['color'],8)
        self.assertEqual(home['roles']['weight']['comparisons'],
            [dict(at=0x481500,cost_bits=0x40800000,best_bits=0x40000000),
             dict(at=0x481503,cost_bits=0x40800000,best_bits=0x40000000,cf=1,zf=0,pf=0)])
        self.assertEqual(normal['roles']['record']['comparisons'][-1]['cf'],0)
        self.assertEqual(normal['roles']['record']['comparisons'][-1]['zf'],0)
        self.assertEqual(normal['roles']['weight']['comparisons'],[])
        for row in self.results.values():
            self.assertTrue(row['code_unchanged'])
            self.assertFalse(row['installable'])
            self.assertEqual(row['source_flags'],['-O2','-g3'])
        self.assertEqual((normal['baseline']['target_sha256'],home['baseline']['target_sha256']),
            (source.home.previous.RAW_SHA,source.home.RAW_SHA))

    def test_02_missing_duplicate_misscoped_and_changed_witnesses_fail_closed(self):
        controls=0
        for label in self.results:
            work=self.out/label
            text=(work/'debugger.txt').read_text()
            listing=(work/'uoptlist').read_text()
            rows=source.events(text)
            for i in range(len(rows)):
                wrong=copy.deepcopy(rows);del wrong[i]
                with self.assertRaises(ValueError):source.qualify_events(wrong,listing,label)
                wrong=copy.deepcopy(rows);wrong.insert(i,wrong[i])
                with self.assertRaises(ValueError):source.qualify_events(wrong,listing,label)
                controls+=2
            for i,row in enumerate(rows):
                for key in ('header','identity','location','offset','first_use_bits','static_nodes',
                            'cost_bits','best_bits','color','reg','caller','at'):
                    if key not in row:continue
                    wrong=copy.deepcopy(rows);wrong[i][key]^=1
                    with self.assertRaises(ValueError):source.qualify_events(wrong,listing,label)
                    controls+=1
                if row['kind']=='compare' and row['at']==0x481503:
                    for bit in (1,4,64):
                        wrong=copy.deepcopy(rows);wrong[i]['flags']^=bit
                        with self.assertRaises(ValueError):source.qualify_events(wrong,listing,label)
                        controls+=1
            with self.assertRaises(ValueError):source.events(text+'FADE_CHOICE invalid-json\n')
            with self.assertRaises(ValueError):source.qualify_events([],listing,label)
            with self.assertRaises(ValueError):source.qualify_events(rows,listing+source.home.allocation_procedure(listing),label)
            controls+=3
            self.assertEqual(source.qualify_events(rows,listing,label),self.results[label]['roles'])
        (self.out/'event-controls.json').write_text(json.dumps(dict(positively_fired=controls),indent=2)+'\n')

    def test_03_compiler_identity_and_probe_cleanup_boundaries(self):
        with patch.object(source.trace,'compiler_fingerprints',return_value={}):
            with self.assertRaisesRegex(ValueError,'fingerprint'):source.observe(self.root,self.out,'home')
        for label in ('unknown','../home',''):
            with self.assertRaises(ValueError):source.observe(self.root,self.out,label)
        script=source.debugger_script(self.root)
        self.assertEqual(script.count('    install_choice()'),1)
        for address in source.ADDRESSES:
            self.assertIn("'*0x%x'"%address,script.split('# Remove UOPT-only native addresses')[1])
        self.assertNotIn('set $',source.PROBES)
        source.home.freeze(self.root,self.out)


if __name__=='__main__':unittest.main()
