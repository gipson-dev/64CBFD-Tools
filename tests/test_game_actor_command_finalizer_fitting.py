"""Qualify the original extent/frame and restored observable first-word home."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_fitting as fitting
from tools.tests import test_game_actor_command_finalizer_recovery as recovery
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout


class GameActorCommandFinalizerFittingTests(unittest.TestCase):
    run_native=recovery.GameActorCommandFinalizerRecoveryTests.run_native
    native_source=recovery.GameActorCommandFinalizerRecoveryTests.native_source
    compare=recovery.GameActorCommandFinalizerRecoveryTests.compare
    test_02_all_types_channels_field_boundaries_and_call_mutations=(
        recovery.GameActorCommandFinalizerRecoveryTests.test_02_all_types_channels_field_boundaries_and_call_mutations)
    test_03_full_word_selectors_and_output_aliases=(
        recovery.GameActorCommandFinalizerRecoveryTests.test_03_full_word_selectors_and_output_aliases)
    test_10_actual_parent_calls_complete_finalizer=(
        recovery.GameActorCommandFinalizerRecoveryTests.test_10_actual_parent_calls_complete_finalizer)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-fitting-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=recovery.screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            caller='conker/src/game/generated_61490.c',rodata='conker/asm/data/23C630.rodata.s')
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
        cls.owner_after=fitting.recovered_owner(cls.owner_before)
        cls.meta,cls.words=fitting.compile_candidate(cls.root,cls.out,'fitted',fitting.FITTED)
        _,cls.old_words=fitting.compile_candidate(cls.root,cls.out,'old',fitting.BASE)
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),recovery.screen.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def test_01_extent_frame_full_word_parameters_and_no_guards(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(405,72,342,0,''))
        self.assertEqual(self.words[:5],self.retail[:5])
        self.assertEqual(self.words[-4:],self.retail[-4:])
        with (self.root/self.paths['guards']).open(newline='') as source:
            self.assertFalse([r for r in csv.DictReader(source) if r['function']==recovery.screen.FUNCTION])
        self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',words=405,frame=72,differences=342,matching_credit=0,
            third_word_home_store_restored=True,no_inserted_padding=True)

    def test_04_live_first_parameter_home_aliases_and_effective_old_control(self):
        cases=0
        controls=0
        for phase in (0,8):
            for offset in (0,8,10,12,14):
                for kind in (0,0x42,0x70,0x7C):
                    for first,second in ((1,2),(255,2),(1,255),(0x80000000,0xFFFFFFFF)):
                        memory,_=recovery.fixture(kind,1,first,second)
                        output=recovery.STACK+phase+offset
                        args=(output,recovery.ACTOR,first,second)
                        pair=[recovery.FinalizerOracle(w,memory,args,phase,0xFFFFFFFF).run()
                            for w in (self.retail,self.words)]
                        for model in pair:
                            self.assertEqual(model.r[2],pair[0].r[2])
                            self.assertEqual(model.calls,pair[0].calls)
                            self.assertEqual(recovery.public(model.memory),recovery.public(pair[0].memory))
                            self.assertEqual(bytes(model.memory[output+i] for i in range(16)),
                                bytes(pair[0].memory[output+i] for i in range(16)))
                        old=recovery.FinalizerOracle(self.old_words,memory,args,phase,0xFFFFFFFF).run()
                        if bytes(old.memory[output+i] for i in range(16))!=bytes(pair[0].memory[output+i] for i in range(16)):
                            controls+=1
                        cases+=1
        self.assertGreater(controls,0)
        memory,args=recovery.fixture(first=255,second=255)
        pair=[recovery.FinalizerOracle(w,memory,args).run() for w in (self.retail,self.words)]
        for model in pair:
            self.assertEqual(recovery.stream.read(model.memory,recovery.STACK+8),255)
            self.assertEqual(recovery.stream.read(model.memory,recovery.STACK+12),255)
        body=fitting.FITTED.replace('volatile s32 first,','s32 first,',1)
        meta,unqualified=fitting.compile_candidate(self.root,self.out,'unqualified-shape-control',body)
        self.assertEqual((meta['body_words'],meta['frame']),(403,72))
        self.assertNotEqual(unqualified,self.words)
        memory,args=recovery.fixture(0,1,1,2)
        sample=[recovery.FinalizerOracle(w,memory,args,seed=0xFFFFFFFF).run()
            for w in (self.retail,self.words,unqualified)]
        for model in sample:
            self.assertEqual(recovery.public(model.memory),recovery.public(sample[0].memory))
            self.assertEqual(sum(e[0]=='R' and e[1]==recovery.STACK+8 and e[2]==4 for e in model.events),3)
        self.receipt('homes',cases=cases,old_control_failures=controls,
            incoming_first_and_second_homes_exact=True,unqualified_control_words=403,
            unqualified_control_is_shape_only=True,qualifier_not_proven_required_for_home=True,
            entire_private_RAM_or_fault_match=False)

    def test_05_native32_actual_source_and_effective_controls(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(fitting.FITTED),profile)[0],0)
        negatives={
            'narrow-first':fitting.FITTED.replace('if (first != limit)','if ((u8)first != limit)'),
            'unsigned-jitter':fitting.FITTED.replace('*(s8 *)(actor + 0x202) * actor[0x1FE]',
                'actor[0x202] * actor[0x1FE]'),
            'wrong-suppression':fitting.FITTED.replace('value == 0x70','value == 0x71'),
            'wrong-sign':fitting.FITTED.replace('sign = -1;','sign = 1;'),
            'signed-modulo':fitting.FITTED.replace('(u32)func_150ADA20() %','func_150ADA20() %')}
        for name,body in negatives.items():
            self.assertNotEqual(body,fitting.FITTED,name)
            self.assertNotEqual(self.run_native(name,self.native_source(body))[0],0,name)
        self.receipt('native',cases=8192,profiles=['O2','O0'],effective_controls=len(negatives),
            native_private_stack_alias_claim=False)

    def test_06_owned_frame_observation_identity_and_corruption_gates(self):
        receipts=[]
        for name,body in (('old',fitting.BASE),('fitted',fitting.FITTED)):
            record=fitting.trace(self.root,self.out,name,body)
            self.assertTrue(record['code_unchanged'])
            self.assertEqual(record['compiler_sha256'],fitting.observer.COMPILERS)
            writes=[e for e in record['events'] if e['event']=='frame-write']
            self.assertEqual([e['frame'] for e in writes],[8,24,64 if name=='old' else 72])
            self.assertEqual((writes[-1]['saved'],writes[-1]['outgoing'],writes[-1]['locals'],writes[-1]['temporary']),
                (8,16,40 if name=='old' else 48,0))
            work=self.out/name
            log=(work/'debugger.txt').read_text()
            for bad in ('\n'.join(line for line in log.splitlines() if not line.startswith('FRAME_TRACE ')),
                    log.replace('TRACE_EXIT inferior=1 code=0','TRACE_EXIT inferior=1 code=1')):
                with self.assertRaises(ValueError):
                    self.reject_trace(work,bad)
            input_path=work/'optimizer.ucode'
            data=input_path.read_bytes()
            try:
                input_path.write_bytes(bytes((data[0]^1,))+data[1:])
                with self.assertRaises(ValueError):
                    self.reject_trace(work,log)
            finally:
                input_path.write_bytes(data)
            receipts.append(dict(name=name,inputs=record['inputs'],locals=writes[-1]['locals']))
        self.receipt('frame',observations=receipts,object_identity=True,saved=8,outgoing=16,
            old_frame=64,new_frame=72,negative_controls=6,no_full_saved_role_or_fault_match=True)

    @staticmethod
    def reject_trace(work,log):
        if 'TRACE_EXIT inferior=1 code=0' not in log.splitlines():
            raise ValueError('Driver did not complete')
        return fitting.observer.validate_observations(work,log)

    def test_07_owner_neighbors_pools_and_both_padders(self):
        objects=[recovery.screen.compile_owner(self.root,self.out,source,'owner-'+name)
            for name,source in (('before',self.owner_before),('after',self.owner_after))]
        self.assertEqual(objects[0][1],objects[1][1])
        old,new=(parse_object(obj) for obj,_ in objects)
        names=set(old[1])-{recovery.screen.FUNCTION}
        self.assertEqual(names,set(new[1])-{recovery.screen.FUNCTION})
        for name in names:
            a,b=old[1][name],new[1][name]
            self.assertEqual(old[0][a['value']:a['value']+a['size']],
                new[0][b['value']:b['value']+b['size']],name)
            relocations=lambda obj,meta:{off-meta['value']:items for off,items in obj[2].items()
                if meta['value']<=off<meta['value']+meta['size']}
            self.assertEqual(relocations(old,a),relocations(new,b),name)
        self.assertEqual(normalized_pools(objects[0][0]),normalized_pools(objects[1][0]))
        padded=[]
        for script in ('pad_c_object.py','pad_generated_object.py'):
            assembly=self.out/(script+'.s')
            args=[str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),'generated_61D10',str(assembly)] if script=='pad_c_object.py' else [
                str(objects[1][0]),str(self.root/'conker/asm/61D10.s'),str(assembly),'--filename','generated_61D10']
            result=subprocess.run([sys.executable,str(self.root/'tools'/script),*args,'--word-patches',
                str(self.root/self.paths['guards'])],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            obj=assembly.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),
                '-o',str(obj),str(assembly)],check=True,capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0],padded[1])
        self.assertEqual(padded[0][1][recovery.screen.FUNCTION]['size'],1620)
        self.receipt('owner',neighbors=len(names),both_full_padders=True,pools_fixed=True,
            diagnostics_unchanged=True,full_extent=1620)

    def test_08_literal_image_and_all_protected_inputs_unchanged(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/self.paths['source']).read_text()
        expected=bytearray(self.before)
        installed=source==self.owner_after
        if installed:
            offset=elf_slot_offset(self.before,recovery.screen.ENTRY,1620)
            self.assertEqual(offset,elf_slot_offset(current,recovery.screen.ENTRY,1620))
            expected[offset:offset+1620]=struct.pack('>405I',*self.words)
            with patch.multiple(descriptor.screen,FUNCTION=recovery.screen.FUNCTION,ENTRY=recovery.screen.ENTRY):
                size=descriptor.size_field(self.before)
            struct.pack_into('>I',expected,size,1620)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        for name in set(self.paths)-{'source','elf'}:
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,matching_credit=0,guard_rows_added=0,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data)

    def test_09_actual_fitted_source_independent_original_rebases(self):
        original_compile=recovery.screen.compile_candidate
        def compile_fitted(root,out,name,body=None):
            return original_compile(root,out,name,fitting.FITTED if body is None else body)
        with patch.object(recovery.screen,'compile_candidate',compile_fitted):
            recovery.GameActorCommandFinalizerRecoveryTests.test_08_independent_original_links_and_carry_sensitive_rebases(self)


if __name__=='__main__':
    unittest.main()
