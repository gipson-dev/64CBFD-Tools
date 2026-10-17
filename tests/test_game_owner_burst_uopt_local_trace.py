"""Qualify reservation provenance, fail-closed controls and rejected screens."""
import copy
import json
from pathlib import Path
import unittest

from tools.experiments import game_owner_burst_uopt_local_trace as target


class BurstLocalTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/target.BUILD
        cls.records={name:target.trace(cls.root,cls.out,name) for name in ('selected','aligned-pairs')}

    def inputs(self,name):
        work=self.out/name
        return ((work/'debugger.txt').read_text(),json.loads((work/'burst-summary.json').read_text()),
            json.loads((work/'receipt.json').read_text()),(work/'baseline.c').read_text())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_reservations_bind_actual_source_and_output(self):
        for name,record in self.records.items():
            measured=target.facts(*self.inputs(name))
            self.assertEqual(measured,record['facts'])
            self.assertEqual(measured['operations'],['actor-plus-0x28','owner-byte-0x222','owner-byte-integer-conversion'])
            self.assertEqual((measured['reserved_bytes'],measured['slots'],measured['slot_size']),(12,3,4))
            self.assertEqual(measured['explicit_output_M_accesses_to_slots'],0)
        self.receipt('provenance',forms=2,additional_bytes=12,reservations=3,
            source_and_wire_bound=True,complete_normal_object_identity=True,
            no_actual_spill_or_original_type_claim=True,installed=False,matching_credit=0)

    def test_02_effective_provenance_and_lifecycle_controls(self):
        count=0
        for name in self.records:
            log,summary,wire,content=self.inputs(name);rows=target.observations(log);bad_rows=[]
            for i in range(3,6):
                for field in ('cursor','requested','descriptor','node_cell'):
                    bad=copy.deepcopy(rows);bad[i][field]+=4;bad_rows.append(bad)
                bad=copy.deepcopy(rows);bad[i]['parents'][0]['pc']+=1;bad_rows.append(bad)
                bad=copy.deepcopy(rows);bad[i]['tree']['node']+=4;bad_rows.append(bad)
                bad=copy.deepcopy(rows);bad[i]['node_words'][4]^=1<<24;bad_rows.append(bad)
            for i in range(3):
                bad=copy.deepcopy(rows);bad[-1]['pool'][i]['fields'][1]+=4;bad_rows.append(bad)
                bad=copy.deepcopy(rows);bad[-1]['pool'][i]['fields'][4]^=4;bad_rows.append(bad)
            bad=copy.deepcopy(rows);bad[3]['tree']['operands'][1]['words'][4]=44;bad_rows.append(bad)
            bad=copy.deepcopy(rows);bad[4]['tree']['operands'][0]['words'][4]+=4;bad_rows.append(bad)
            bad=copy.deepcopy(rows);bad[5]['tree']['operands'][0]['node']+=4;bad_rows.append(bad)
            bad=copy.deepcopy(rows);bad[-1]['tail']=bad[-1]['head'];bad_rows.append(bad)
            for bad in bad_rows:
                iterator=iter(bad)
                corrupted='\n'.join('BURST_LOCAL '+json.dumps(next(iterator)) if line.startswith('BURST_LOCAL ') else line for line in log.splitlines())
                with self.assertRaises(ValueError):target.facts(corrupted,summary,wire,content)
                count+=1
            for prefix in ('BURST_LOCAL ','BURST_REMOVED '):
                bad='\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.assertRaises(ValueError):target.facts(bad,summary,wire,content)
                count+=1
            for field in ('pending','probes','exit_code'):
                lines=log.splitlines();i=next(i for i,s in enumerate(lines) if s.startswith('BURST_REMOVED '))
                value=json.loads(lines[i][14:]);value[field]+=1;lines[i]='BURST_REMOVED '+json.dumps(value)
                with self.assertRaises(ValueError):target.facts('\n'.join(lines),summary,wire,content)
                count+=1
            bad=copy.deepcopy(wire)
            extra=copy.deepcopy(next(r for r in wire['records']['optimizer'] if r['storage']=='M' and r['offset'] is not None))
            extra['offset']=-4096;bad['records']['optimizer'].append(extra)
            with self.assertRaises(ValueError):target.facts(log,summary,bad,content)
            count+=1
            bad=copy.deepcopy(wire)
            local=summary['layout']['frontend_local_bytes']
            next(r for r in bad['records']['frontend'] if r['name']=='str' and r['storage']=='M' and r['offset']==-local+4)['offset']+=4
            with self.assertRaises(ValueError):target.facts(log,summary,bad,content)
            count+=1
            with self.assertRaises(ValueError):target.facts(log,summary,wire,content.replace('owner = data->owner;','owner = other;'))
            count+=1
        self.receipt('negative-controls',effective_controls=count)

    def test_03_source_controls_rejected_not_installed(self):
        rows=target.screen(self.root,self.out);expected=[(288,352,85,0),(287,352,225,-1),
            (289,344,254,1),(290,344,254,2)]
        for row,shape in zip(rows,expected):
            self.assertEqual(tuple(row[k] for k in ('words','frame','differences','extent_gap')),shape)
        for label in ('direct-data-base','direct-data-copy-phase'):
            with self.assertRaises(ValueError):target.frame.source.padded_object(self.root,self.out,self.out/(label+'.o'),'reject-'+label)
        row=rows[-1]
        self.assertEqual((row['raw_words'],row['raw_frame'],row['unqualified_binding']),(288,352,'.rodata'))
        self.assertTrue(row['literal_pool_matches_retail_bytes'])
        self.assertTrue(all(r['installed'] is False for r in rows))
        self.receipt('source-control-rejections',measured_nonmatching_forms=4,actual_overflow_rejections=2,
            literal_binding_still_unqualified=True,new_guards=0,matching_credit=0)

    def test_04_complete_production_baseline_unchanged(self):
        from tools.tests import owner_burst_checkpoint as latest
        source=target.frame.source;source.freeze(self.root,self.root/source.BUILD)
        for key,path in source.PATHS.items():
            self.assertEqual(latest.previous_input((self.root/path).read_bytes(),path,self.root),(self.root/source.BUILD/('before-'+key)).read_bytes())
        self.receipt('baseline',protected_entries=len(source.PATHS),entire_production_ELF_unchanged=True,
            earlier_candidate_and_checkpoint_inputs_unchanged=True)


if __name__=='__main__':unittest.main()
