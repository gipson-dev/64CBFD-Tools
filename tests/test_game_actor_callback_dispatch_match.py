"""Qualify the direct callback match, literal frame, and allocation provenance."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_callback_frame_trace as trace
from tools.tests import test_game_actor_callback_dispatch_recovery as prior

screen=prior.screen


class GameActorCallbackDispatchMatchTests(unittest.TestCase):
    run_native=prior.GameActorCallbackDispatchRecoveryTests.run_native
    native_source=prior.GameActorCallbackDispatchRecoveryTests.native_source

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-callback-dispatch-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,
            caller=screen.CALLER_SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',layout='conker/retail_layout.us.txt',makefile='conker/Makefile')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        assert cls.owner_before.count(screen.SELECTED)==1
        cls.owner_after=cls.owner_before.replace(screen.SELECTED,trace.MATCHED)
        cls.caller_before=cls.caller_after=(cls.out/'before-caller').read_text()
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'matched',trace.MATCHED)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>81I',cls.rom,screen.ROM))

    def receipt(self,name,**values):
        if name=='guest':
            values.update(private_accesses_logically_rebased=False,literal_frame_exact=True)
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_complete_direct_match_without_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(81,32,0,0,''))
        self.assertEqual(self.words,self.retail)
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertFalse([r for r in csv.DictReader(stream) if r['function']==screen.FUNCTION])

    def compare_case(self,memory,index,mode=0,phase=0):
        expected,calls=prior.reference(memory,index,mode,phase)
        pair=[prior.DispatchOracle(w,memory,index,mode,phase).run() for w in (self.retail,self.words)]
        for model in pair:
            self.assertEqual(prior.public(model.memory),prior.public(expected))
            self.assertEqual(model.calls,calls)
            self.assertEqual(prior.read(model.memory,prior.STACK+phase),prior.read(expected,prior.STACK+phase))
        self.assertEqual((pair[0].memory,pair[0].events,pair[0].r,pair[0].f,pair[0].visits),
                         (pair[1].memory,pair[1].events,pair[1].r,pair[1].f,pair[1].visits))
        return pair[0].visits

    def test_02_guest_types_mutations_and_literal_homes(self):
        prior.GameActorCallbackDispatchRecoveryTests.test_02_guest_all_types_live_mutations_and_incoming_home_contract(self)

    def test_03_literal_fault_prefixes_and_effective_frame_control(self):
        cuts=0
        for state,kind,flag,mode in ((0,4,0,3),(1,0,0,1),(0x22,0x70,0,0),(0,0x7B,7,2),(0,0x60,0,0)):
            memory,_=prior.fixture(state=state,kind=kind,flag=flag)
            for phase in (0,8):
                complete=prior.DispatchOracle(self.retail,memory,mode=mode,phase=phase).run()
                for cut in range(complete.accesses):
                    pair=[]
                    for words in (self.retail,self.words):
                        model=prior.DispatchOracle(words,memory,mode=mode,phase=phase)
                        model.fault=cut
                        with self.assertRaises(prior.AccessFault):
                            model.run()
                        self.assertEqual(model.accesses,cut)
                        pair.append(model)
                    self.assertEqual((pair[0].memory,pair[0].events,pair[0].calls,pair[0].r,pair[0].f),
                                     (pair[1].memory,pair[1].events,pair[1].calls,pair[1].r,pair[1].f))
                    cuts+=1
        old_meta,old=screen.compile_candidate(self.root,self.out,'old-frame',screen.SELECTED)
        self.assertEqual((old_meta['frame'],old_meta['differences']),(40,8))
        memory,_=prior.fixture()
        pair=[prior.DispatchOracle(w,memory).run() for w in (self.retail,old)]
        self.assertNotEqual(pair[0].memory,pair[1].memory)
        self.assertNotEqual(pair[0].events,pair[1].events)
        memory,actor=prior.fixture(enabled=0)
        for a in range(actor,actor+0x32C):
            if not actor+0x1D4<=a<actor+0x1D8:
                del memory[a]
        del memory[prior.DISABLED]
        for words in (self.retail,self.words):
            self.assertEqual(prior.DispatchOracle(words,memory).run().calls,[])
        self.receipt('faults',fired_pairs=cuts,literal_private_RAM_registers_events=True,
            provider_accesses_excluded=True,effective_old_frame_control=True,hardware_FCSR_not_claimed=True)

    def test_04_native_actual_source_and_effective_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(trace.MATCHED),profile),(0,''))
        expr='(D_800CC2D0 + (u32)index * 0x32C)'
        cached=trace.MATCHED.replace('    if (*(s32 *)'+expr+' == 1',
            '    s32 capturedType = '+expr+'[4];\n    if (*(s32 *)'+expr+' == 1').replace(
            'switch ((s32)'+expr+'[4])','switch (capturedType)')
        negatives={'cached-type':cached,
            'exclusive-state':trace.MATCHED.replace('    if (*(s32 *)'+expr+' == 0x22)',
                '    else if (*(s32 *)'+expr+' == 0x22)'),
            'nonzero-flag':trace.MATCHED.replace(expr+'[5] == 7',expr+'[5] != 0'),
            'recheck-disable':trace.MATCHED.replace('                func_15036310(0, index, 4, 0);',
                '                if (D_800BE616 == 0) func_15036310(0, index, 4, 0);')}
        for name,body in negatives.items():
            self.assertNotEqual(body,trace.MATCHED)
            self.assertIn(self.run_native('negative-'+name,self.native_source(body))[0],(1,2,3))
        self.receipt('native',cases_per_profile=32768,profiles=['O2','O0'],effective_negatives=4)

    def test_05_owners_neighbors_pools_and_both_padders(self):
        prior.GameActorCallbackDispatchRecoveryTests.test_05_both_owners_neighbors_pools_and_original_padders(self)

    def test_06_independent_rebased_links_match_all_words(self):
        original=(self.root/'conker/asm/61490.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        asm=self.out/'original.s'
        asm.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\nglabel '+screen.FUNCTION+'\n'+
            original.split('endlabel '+screen.FUNCTION,1)[0]+'endlabel '+screen.FUNCTION+'\n')
        obj=asm.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],check=True,capture_output=True)
        for i,entry,symbols in ((0,screen.ENTRY,screen.SYMBOLS),
            (1,0x152345E4,dict(screen.SYMBOLS,D_800CC2D0=0x80107FFC,D_800BE616=0x80218004)),
            (2,0x153345E4,dict(screen.SYMBOLS,D_800CC2D0=0x80318004,D_800BE616=0x80417FFC))):
            with patch.multiple(screen,ENTRY=entry,SYMBOLS=symbols):
                _,candidate=screen.compile_candidate(self.root,self.out,'rebase-'+str(i),trace.MATCHED)
            ld=self.out/('original-'+str(i)+'.ld')
            ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=ld.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            self.assertEqual(candidate,list(struct.unpack_from('>81I',prior.sections(elf)['.text'][1])))

    def test_07_literal_image_gate_only_eight_target_words_change(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/screen.SOURCE).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        offset=prior.elf_slot_offset(self.before,screen.ENTRY,324)
        self.assertEqual(offset,prior.elf_slot_offset(current,screen.ENTRY,324))
        if installed:
            expected[offset:offset+324]=struct.pack('>81I',*self.words)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        self.assertEqual((self.root/screen.CALLER_SOURCE).read_text(),self.caller_before)
        for name in ('guards','progress','layout','makefile'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        data=prior.audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        changed=[i for i,(a,b) in enumerate(zip(self.before,current)) if a!=b]
        if installed:
            self.assertEqual(changed,[offset+word+3 for word in screen.FRAME_WORDS])
        self.receipt('linked-audit',installed=installed,new_matching_credit=int(installed),
            changed_bytes=len(changed),symbol_size_changed=False,data=data)


class GameActorCallbackFrameTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-callback-frame-trace-test'
        cls.record=trace.trace(cls.root,cls.out,'matched',trace.MATCHED)
        cls.old=trace.trace(cls.root,cls.out,'selected',screen.SELECTED)

    def test_01_completed_identical_objects_and_fired_frame_watch(self):
        for record,frame,locals_size,home in ((self.old,40,16,-16),(self.record,32,8,-8)):
            self.assertTrue(record['code_unchanged'])
            self.assertFalse(record['installable'])
            self.assertEqual(record['compiler_sha256'],trace.COMPILERS)
            end=record['events'][-1]
            self.assertEqual((end['frame'],end['locals'],end['saved'],end['outgoing'],end['temporary'],end['pool']),
                             (frame,locals_size,8,16,0,[]))
            records=record['records']
            self.assertEqual([r['length'] for r in records['optimizer'] if r['name']=='def' and r['storage']=='M'],[locals_size])
            saves=[(r['name'],r['offset']) for r in records['optimizer'] if r['storage']=='M' and r['name'] in ('rstr','rlod')]
            self.assertEqual(saves,[('rstr',home),('rlod',home)]*2)
        self.assertEqual([r['offset'] for r in self.old['records']['frontend'] if r['name']=='vreg'],[-12])
        self.assertEqual([r['offset'] for r in self.record['records']['frontend'] if r['name']=='vreg'],[-4])

    def test_02_missing_gate_input_corruption_and_child_exit_rejected(self):
        source=self.out/'matched'
        log=(source/'debugger.txt').read_text()
        with self.assertRaisesRegex(ValueError,'gate'):
            trace.validate_observations(source,'\n'.join(line for line in log.splitlines() if not line.startswith('FRAME_TRACE ')))
        ugen=self.record['inputs'][1]['inferior']
        with self.assertRaisesRegex(ValueError,'completion'):
            trace.validate_observations(source,log.replace('TRACE_EXIT inferior=%d code=0'%ugen,'TRACE_EXIT inferior=%d code=1'%ugen))
        work=self.out/'corrupt'
        work.mkdir(exist_ok=True)
        for filename in ('ucode-table.json','ucode-types.json','frontend.ucode','optimizer.ucode'):
            shutil.copy2(source/filename,work/filename)
        data=bytearray((work/'optimizer.ucode').read_bytes())
        data[0]^=1
        (work/'optimizer.ucode').write_bytes(data)
        with self.assertRaisesRegex(ValueError,'integrity'):
            trace.validate_observations(work,log)


if __name__=='__main__':
    unittest.main()
