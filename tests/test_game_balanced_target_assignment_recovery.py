"""Qualify complete public semantics without crediting the unresolved private layout."""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_balanced_target_assignment_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_balanced_target_assignment_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command


def external_stores(model):
    return [s for s in model.stores if not oracle.STACK-0x500<=s[0]<oracle.STACK+0x100]


class BalancedTargetAssignmentRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'recovery'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'semantic')
        cls.raw,cls.bindings=source.payload(cls.obj)
        cls.rom=cls.values['conker/conker.us.bin']
        cls.retail=list(struct.unpack_from('>160I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_extent_and_explicit_nonmatching_boundary(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(160,224,123))
        self.assertEqual(self.row['raw_SHA256'],'c31e39062a3c82931d51d574c1106272083e651bfc04b8e796c6b31490009795')
        self.assertFalse(self.row['diagnostics']);self.assertEqual(len(self.bindings),2)
        self.assertEqual((-self.retail[0])&65535,176);self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',**self.row,retail_frame=176,matching_credit=0,production_installation=False)

    def test_02_independent_public_reference_and_ordered_stores(self):
        pairs=0;visited=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
            for phase in (0,8):
                for words in (self.retail,self.words):
                    model=oracle.AssignmentModel(words,memory,phase).run()
                    self.assertEqual(model.r[2],0,case);self.assertFalse(model.calls)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted),case)
                    self.assertEqual(external_stores(model),stores,case)
                    if words is self.retail:visited|=model.visits
                pairs+=1
        self.receipt('public',fixtures=len(self.cases),retail_raw_pairs=pairs,retail_words_visited=len(visited),
            all_public_bytes_and_ordered_stores_equal=True,no_helpers=True,
            positive_count_domain='1..40, counts above16 deliberately inactive and backed',
            not_all_inputs_or_private_state_equivalence=True)

    def test_03_native_profiles_and_effective_semantic_negatives(self):
        def run(name,body,opt='-O2',sanitize=False):
            program=self.out/(name+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(body,self.cases))
            built=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',
                str(program),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            if sanitize:self.assertFalse(result.stderr,result.stderr)
            return result.returncode
        for name,opt,sanitize in (('native-O0','-O0',False),('native-O2','-O2',False),('native-UBSan','-O2',True)):
            self.assertEqual(run(name,source.SELECTED,opt,sanitize),0)
        swapped=source.SELECTED.replace('pass == 0','pass == 99').replace('pass != 0','pass == 0').replace('pass == 99','pass != 0')
        negatives={
            'last-tie':source.SELECTED.replace('score < best','score <= best'),
            'swapped-passes':swapped,
            'no-reuse':source.SELECTED.replace('((u32)uses[candidate] & 31)','0'),
            'inactive-zero':source.SELECTED.replace('active[candidate] > 0','active[candidate] >= 0'),
            'same-team':source.SELECTED.replace('teams[candidate] != ownTeam','teams[candidate] == ownTeam'),
            'unsigned-score':source.SELECTED.replace('score < best','(u32)score < (u32)best'),
            'ignore-sentinel':source.SELECTED.replace('neighbors[scan] != -1','1'),
            'ignore-distance-minus-one':source.SELECTED.replace('if (score != -1)','if (1)'),
            'byte-flags':source.SELECTED.replace('flags[i] ==','(s8)flags[i] =='),
            'short-neighbor-row':source.SELECTED.replace('scan < limit','scan < limit - 1')}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertIn(run('negative-'+name,body),(21,25),name)
        self.receipt('native',profiles=3,fixtures_each=len(self.cases),effective_negatives=len(negatives),
            full_translated_buffers=True,UBSan_empty_diagnostics=True,no_private_frame_claim=True)

    def test_04_private_miss_cell_and_frame_only_negative(self):
        case=oracle.Case(count=5,active=(0,),flags=(2,))
        results=[]
        for poison in (0,0x7F,0xA5,0xFF):
            memory=oracle.fixture(case,poison);wanted,stores=oracle.reference(memory)
            models=[oracle.AssignmentModel(w,memory).run() for w in (self.retail,self.words)]
            for model in models:
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(external_stores(model),stores)
            misses=len(stores)//2;retail_cell=oracle.STACK-176+0x7B
            self.assertEqual(models[0].memory[retail_cell],(poison+misses)&255)
            raw_cell=oracle.STACK-224+0x8C
            self.assertEqual(models[1].memory[raw_cell],misses)
            self.assertNotEqual(models[0].memory,models[1].memory)
            results.append(dict(poison=poison,misses=misses,retail_cell=retail_cell,raw_cell=raw_cell))
        memory=oracle.fixture(oracle.Case(count=0))
        bad=self.words.copy();bad[0]=0x27BDFF50;bad[-1]=0x27BD00B0
        a=oracle.AssignmentModel(self.retail,memory).run();b=oracle.AssignmentModel(bad,memory).run()
        self.assertEqual(oracle.public(a.memory),oracle.public(b.memory));self.assertNotEqual(a.memory,b.memory)
        # Equal frame immediates restore saved addresses, not the remaining private homes.
        first=None
        for x,y in zip(a.stores,b.stores):
            if x!=y:first=dict(retail=x,frame_only=y);break
        self.assertIsNotNone(first)
        cuts=[]
        for cut,body in ((0,self.words),(13,bad)):
            pair=[]
            for words in (self.retail,body):
                model=oracle.AssignmentModel(words,memory);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,cut);pair.append(model.requested)
            self.assertNotEqual(*pair);cuts.append(dict(cut=cut,retail=pair[0],candidate=pair[1]))
        self.receipt('private-boundary',poison_runs=results,frame_only_public_equal=True,
            first_private_store_mismatch=first,fired_private_cut_mismatches=cuts,
            no_raw_or_frame_only_private_identity=True,
            retail_miss_cell_uninitialized_by_routine=True,native_miss_cell_deliberately_initialized=True)

    def test_05_actual_no_argument_returning_caller(self):
        jal=0x0C000000|(source.ENTRY>>2)&0x3FFFFFF
        self.assertEqual([i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==jal],[0xCB564])
        runs=0
        for case in self.cases[::11]:
            wanted,stores=oracle.reference(oracle.fixture(case))
            for words in (self.retail,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                connected.update({0x1509E3CC+i*4:w for i,w in enumerate(struct.unpack_from('>4I',self.rom,0xCB87C))})
                model=oracle.AssignmentModel(list(struct.unpack_from('>4I',self.rom,0xCB564)),oracle.fixture(case),
                    connected=connected,entry=0x1509E0B4)
                model.r[29]=oracle.STACK-72
                oracle.put(model.memory,oracle.STACK-36,0xDEAD0000,4)
                oracle.put(model.memory,oracle.STACK-40,model.before[16],4)
                model.run();self.assertEqual(model.caller_args,[()]);self.assertEqual(model.r[2],0)
                self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                self.assertEqual(external_stores(model),stores);runs+=1
        frame_only=self.words.copy();frame_only[0]=0x27BDFF50;frame_only[-1]=0x27BD00B0
        connected={source.ENTRY+i*4:w for i,w in enumerate(frame_only)}
        connected.update({0x1509E3CC+i*4:w for i,w in enumerate(struct.unpack_from('>4I',self.rom,0xCB87C))})
        model=oracle.AssignmentModel(list(struct.unpack_from('>4I',self.rom,0xCB564)),oracle.fixture(oracle.Case(count=0)),
            connected=connected,entry=0x1509E0B4)
        model.r[29]=oracle.STACK-72
        oracle.put(model.memory,oracle.STACK-36,0xDEAD0000,4)
        oracle.put(model.memory,oracle.STACK-40,model.before[16],4)
        with self.assertRaisesRegex(AssertionError,'unowned jump'):model.run()
        self.assertEqual(model.r[31],oracle.BANK+0x15C)
        self.receipt('caller',actual_window_runs=runs,aligned_JAL_sites=['0xCB564'],caller_frame_live_in=72,
            actual_JAL_NOP_branch_RA_S0_SP_JR_window=True,frame_only_corrupts_real_caller_RA_home=True,
            not_full_switch_or_gameplay=True)

    def test_06_independent_GNU_rebases(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start)
        path=self.out/'retail.s';path.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+'\n.text\n'+asm[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',
            str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,global_at,bank) in enumerate(((source.ENTRY,oracle.CONTEXT,oracle.BANK),
                (0x1621FFF4,0x80207FFC,0x28000),(0x18FFF000,0x80308000,0x32000))):
            images=[]
            for label,obj in (('retail',path.with_suffix('.o')),('raw',self.obj)):
                script=self.out/('%s-map%d.ld'%(label,n));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800D23B0=0x%X'%global_at,'-o',str(elf),str(obj)],check=True,capture_output=True)
                images.append(list(struct.unpack('>160I',sections(elf)['.text'][1][:640])))
            self.assertEqual(images[1],relocate(self.raw,self.bindings,{'D_800D23B0':global_at}))
            with patch.multiple(oracle,CONTEXT=global_at,BANK=bank,SEGMENTS=((global_at,4),(bank,0x2000))):
                for case in self.cases[::9]:
                    memory=oracle.fixture(case);wanted,stores=oracle.reference(memory)
                    for words in images:
                        model=oracle.AssignmentModel(words,memory,entry=entry).run()
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                        self.assertEqual(external_stores(model),stores)
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=3,retail_raw_rebased_pairs=pairs,
            two_global_bindings_and_HI_LO_carry=True,no_normalization_or_byte_identity_claim=True)

    def test_07_complete_owner_profiles_and_actual_padder(self):
        objects={};same=mixed.candidate.source.neighbor.same_functions
        for label,normal in (('primary',False),('normal',True)):
            before,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            after,_,row=source.compile_candidate(self.root,self.out,'after-'+label,whole=True,normal=normal)
            self.assertFalse(diag or row['diagnostics']);self.assertEqual(same(before,after,(source.FUNCTION,)),72)
            self.assertEqual(normalized_pools(before),normalized_pools(after));objects[label]=after
        self.assertEqual(source.payload(objects['primary']),(self.raw,self.bindings))
        guards=self.out/'unchanged-guards.csv';guards.write_bytes(self.values['conker/retail_word_patches.us.csv'])
        padded=mixed.padded(self.root,self.out,objects['primary'],'qualified-padded',guards,objects['normal'])
        baseline=self.root/'conker/build/src/game/generated_B3020.c.o'
        a,fa=source.link_owner(self.root,self.out,baseline,source.OWNER)
        b,fb=source.link_owner(self.root,self.out,padded,source.OWNER)
        at=fb[source.FUNCTION]['value'];self.assertEqual(b[at:at+640],struct.pack('>160I',*self.words))
        self.assertEqual(fb[source.FUNCTION]['size'],640)
        self.assertEqual(fa.keys(),fb.keys())
        self.assertTrue(all(fa[n]['value']==fb[n]['value'] and (n==source.FUNCTION or fa[n]==fb[n]) for n in fa))
        self.assertEqual(a[:at],b[:at]);self.assertEqual(a[at+640:],b[at+640:])
        self.assertEqual(normalized_pools(baseline),normalized_pools(padded));self.assertEqual(same(baseline,padded,(source.FUNCTION,)),72)
        shutil.copyfile(objects['normal'],self.out/'override-normal.o')
        shutil.copyfile(objects['primary'],self.out/'primary-no-unroll.o')
        shutil.copyfile(guards,self.out/'qualified-guards.csv')
        (self.out/'proposed-owner.c').write_text(source.recovered_owner(self.values[source.SOURCE].decode()))
        with patch.multiple(mixed,freeze=source.freeze,recovered_owner=source.recovered_owner,
                recovered_makefile=lambda value:value,recovered_guards=lambda before,*unused:before):
            shadow=mixed.make_shadow(self.root,self.out)
        shadow.pop('original_four_GLOBAL_ASM_bodies_preserved')
        shadow['GLOBAL_ASM_bodies_remaining']=0
        (self.out/'make-shadow.json').write_text(json.dumps(shadow,indent=2)+'\n')
        self.receipt('owner',profiles=2,neighbors_each_profile=72,actual_padder_fits640_byte_slot=True,
            all73_addresses_fixed=True,other_padded_bytes_extents_and_pools_fixed=True,
            actual_expanded_Make_commands=shadow['actual_expanded_Make_commands'],
            source_complete_but_not_installable_as_match=True,new_guards=0)

    def test_08_all_production_inputs_still_immutable(self):
        for name,before in self.values.items():self.assertEqual((self.root/name).read_bytes(),before,name)
        self.receipt('unchanged-production',fingerprints={n:hashlib.sha256(v).hexdigest() for n,v in self.values.items()},
            source_guards_Makefile_assembly_ROM_and_ELF_unchanged=True,matching_credit=0)


if __name__=='__main__':unittest.main()
