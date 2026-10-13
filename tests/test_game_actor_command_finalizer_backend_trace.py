"""Qualify the owned finalizer backend boundary and reject unsupported provenance."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_backend_trace as backend
from tools.tests import test_game_text_measurer_ugen_nodes as previous


class GameActorCommandFinalizerBackendTraceTests(previous.GameTextMeasurerUgenNodeTests):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-backend-test'
        cls.paths=('conker/src/game/generated_61D10.c','conker/build/conker.us.elf',
            'conker/retail_word_patches.us.csv','conker/Makefile','conker/progress.csv')
        cls.before={p:hashlib.sha256((cls.root/p).read_bytes()).hexdigest() for p in cls.paths}
        assert cls.before[cls.paths[0]]=='76c0c333b9c1de6e9c9cbd3865dc84ea2742692f1b4add3ef6f3a52ef43da27f'
        assert cls.before[cls.paths[1]]=='9c75bf09dcf23dcfb2266396a565a8ca6196a4d41be59eff9ca1c6d3ae58a52b'
        cls.records={name:backend.trace(cls.root,cls.out,name,body) for name,body in
            (('late',backend.schedule.SELECTED),('early',backend.schedule.early_lower(backend.schedule.SELECTED)))}
        cls.valid=cls.out/'late'
        cls.log=(cls.valid/'debugger.txt').read_text()

    def test_01_real_probes_fire_on_already_assigned_register_nodes(self):
        for name,differences,position in (('late',267,184),('early',261,165)):
            record=self.records[name]
            self.assertEqual((record['baseline']['body_words'],record['baseline']['frame'],
                record['baseline']['differences']),(405,72,differences))
            self.assertTrue(record['code_unchanged'])
            self.assertFalse(record['installable'])
            self.assertEqual((record['event_count'],record['emitter_event_count']),(200,68))
            self.assertEqual(record['correlation']['correlated_events'],68)
            self.assertEqual(record['correlation']['lower_record']['record'],position)
            self.assertEqual({r['opcode'] for r in record['events']},{82})
            self.assertEqual(record['as1_input']['files'][0]['bytes'],10048)
            records=backend.instruction_records((self.out/name/'as1-input-11.bin').read_bytes())
            tags=[r['record'] for r in records if (r['opcode'],r['register0'],r['register1'],r['word3'])==(42,12,29,80)]
            self.assertEqual(tags[0],189)
            indices=[i for i,e in enumerate(record['emitter_events']) if e['probe']=='immediate'
                and (e['raw']['rdx'],e['raw']['rcx'],e['raw']['r8'])==(41,7,40)]
            self.assertEqual(indices,[10])

    def test_03_effective_text_function_relocation_and_all_pool_controls(self):
        with patch.object(previous.trace,'screen',backend.screen_adapter()):
            super().test_03_effective_text_function_relocation_and_all_pool_controls()

    def test_04_event_parser_rejects_malformed_or_impossible_register_nodes(self):
        events=self.records['late']['events']
        register=next(e for e in events if e['type_storage']>>5==3)
        with patch.dict(self.records['late'],events=[register,*events]):
            super().test_04_event_parser_rejects_malformed_or_impossible_register_nodes()

    def test_06_read_only_recipe_and_unchanged_production(self):
        super().test_06_read_only_recipe_and_unchanged_production()
        script=backend.debugger_script(self.root,self.valid)
        for forbidden in ('write_memory','\ncall ','\nattach ','target remote','\nshell '):
            self.assertNotIn(forbidden,script)
        self.assertIn('capture_as1()',script)

    def test_07_emitter_events_reject_missing_unfired_or_late_probes(self):
        for name in backend.PROBES:
            for marker in ('FINALIZER_EMIT_INSTALLED ','FINALIZER_EMIT_REMOVED '):
                with self.subTest(name=name,marker=marker),self.assertRaises(ValueError):
                    backend.emitter_events(self.log.replace(marker+name,''))
            lines=[line for line in self.log.splitlines() if not (line.startswith(backend.PREFIX)
                and json.loads(line.removeprefix(backend.PREFIX))['probe']==name)]
            with self.assertRaises(ValueError):backend.emitter_events('\n'.join(lines))
        event=copy.deepcopy(self.records['late']['emitter_events'][0])
        for field,value in (('caller',0),('probe','other'),('raw',{})):
            with self.subTest(field=field),self.assertRaises(ValueError):
                backend.emitter_events(self.log+'\n'+backend.PREFIX+json.dumps(dict(event,**{field:value})))

    def test_08_as1_digest_profile_lifetime_and_record_controls(self):
        marker=next(line for line in self.log.splitlines() if line.startswith('FINALIZER_AS1 '))
        event=json.loads(marker.removeprefix('FINALIZER_AS1 '))
        for key,value in (('inferior',1),('files',[]),('arguments',['as1','-O1'])):
            changed=dict(event,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):
                backend.validate_as1(self.valid,self.log.replace(marker,'FINALIZER_AS1 '+json.dumps(changed)))
        for invalid in (None,[],{},dict(event,files=None),dict(event,inferior=True)):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                backend.validate_as1(self.valid,self.log.replace(marker,'FINALIZER_AS1 '+json.dumps(invalid)))
        data=(self.valid/'as1-input-11.bin').read_bytes()
        read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:data+b'\0' if p==self.valid/'as1-input-11.bin' else read(p)):
            with self.assertRaises(ValueError):backend.validate_as1(self.valid,self.log)
        for invalid in (b'',data[:-1]):
            with self.assertRaises(ValueError):backend.instruction_records(invalid)
        records=backend.instruction_records(data)
        events=copy.deepcopy(self.records['late']['emitter_events'])
        events[0]['raw']['r8']^=1
        with self.assertRaises(ValueError):backend.correlate(records,events)
        lower=self.records['late']['correlation']['lower_record']['record']
        with self.assertRaises(ValueError):backend.correlate([r for r in records if r['record']!=lower],
            self.records['late']['emitter_events'])


if __name__=='__main__':
    unittest.main()
