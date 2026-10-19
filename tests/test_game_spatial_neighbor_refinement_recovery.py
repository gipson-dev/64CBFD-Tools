"""Seven-argument spatial refinement, observed record return and explicit matching boundary."""
from dataclasses import replace
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_spatial_neighbor_refinement_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_spatial_neighbor_refinement_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command

FIND,QUERY=0x150A3194,0x150A1DA0


def public_stores(model):
    return [row for row in model.stores if not oracle.STACK-0x1600<=row[0]<oracle.STACK+0x400]


class ConnectedModel(oracle.RefinementModel):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.nested=[]

    def record_call(self,target):
        if target==FIND:
            self.nested.append((target,*self.args(5)));return
        if target==QUERY:
            packet,obj,zero=self.args(3)
            fields=tuple((at,oracle.read(self.memory,packet+at,4)) for at in (0x14,0x18,0x1C,0x2C,0x30,0x34,0x180))
            self.nested.append((target,obj,zero,fields));return
        super().record_call(target)

    def hook(self,target):
        if target==FIND:
            self.in_hook=True
            try:self.put(self.r[29]+16,0xBA005555,4)
            finally:self.in_hook=False
            super().hook(oracle.LOOKUP)
        elif target==QUERY:
            super().hook(oracle.INSIDE);self.r[2]=0 if self.case.inside else 1
        else:super().hook(target)


class SpatialNeighborRefinementRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD/'recovery'
        cls.values=source.freeze(cls.root,cls.out);cls.cases=list(oracle.cases())
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out)
        cls.raw,cls.bindings=source.payload(cls.obj);cls.rom=cls.values['conker/conker.us.bin']
        cls.retail=list(struct.unpack_from('>179I',cls.rom,source.ROM))

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_shape_interface_and_unmatched_boundary(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(176,112,164))
        self.assertEqual(self.row['raw_SHA256'],'f6147adcdba5d18669188d2c4c187c5e3142bd8a567a0abf5c7407b2974f05d0')
        self.assertFalse(self.row['diagnostics']);self.assertEqual(len(self.bindings),11)
        self.assertIn('s8 count, s8 option, u8 *list, u8 *state',source.SELECTED)
        self.assertIn('s32 func_15086C70',source.HELPER_NEW);self.assertIn('return func_150A3194',source.HELPER_NEW)
        self.assertEqual((-self.retail[0])&65535,112);self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',**self.row,retail_words=179,retail_frame=112,matching_credit=0,
            same_frame_does_not_prove_private_layout=True,production_installed=False)

    def test_02_public_reference_full_word_results_and_helper_effects(self):
        pairs=0;visited=set();band_words=set()
        for case in self.cases:
            memory=oracle.fixture(case);wanted,expected,calls,stores,_,_=oracle.reference(memory,case)
            for phase in (0,8):
                for words in (self.retail,self.words):
                    model=oracle.RefinementModel(words,memory,case,phase).run()
                    self.assertEqual(model.r[2],wanted,case);self.assertEqual(model.calls,calls,case)
                    self.assertEqual(oracle.public(model.memory),oracle.public(expected),case)
                    self.assertEqual(public_stores(model),stores,case)
                    raw=next(c for c in model.raw_calls if c[0]==oracle.CLOSEST)
                    self.assertEqual(raw[-1],case.band&0xFFFFFFFF);band_words.add(raw[-1])
                    if words is self.retail:visited|=model.visits
                pairs+=1
        unvisited=sorted(set(range(source.ENTRY,source.ENTRY+716,4))-visited)
        self.assertEqual(unvisited,[0x150861A0,0x150861A4,0x150861A8,0x150861F0])
        self.receipt('public',fixtures=len(self.cases),retail_raw_pairs=pairs,retail_words_visited=len(visited),
            preserved_unvisited_unsigned_fix_and_dead_minimum_copy=[hex(x) for x in unvisited],
            full_public_bytes_calls_order_and_results=True,physical_band_words=sorted(band_words),
            native_callee_band_view_is_signed_low_byte=True,synthetic_threshold_and_provider_mutations=True)

    def test_03_native_profiles_and_effective_behavioral_negatives(self):
        def run(name,body,opt='-O2',sanitize=False):
            program=self.out/(name+'.c');exe=program.with_suffix('.exe')
            program.write_text(oracle.native_harness(body,self.cases))
            built=subprocess.run(native_command(opt,sanitize)+['-mstackrealign','-fno-strict-aliasing',str(program),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertFalse(result.stderr,result.stderr);return result.returncode
        for name,opt,sanitize in (('native-O0','-O0',False),('native-O2','-O2',False),('native-UBSan','-O2',True)):
            self.assertEqual(run(name,source.SELECTED,opt,sanitize),0,name)
        negatives={
            'signed-index':source.SELECTED.replace('index = func_15085DF8(', 'index = (s8)func_15085DF8('),
            'truncate-refined-result':source.SELECTED.replace('    s32 refined =','    u8 refined ='),
            'unsigned-count':source.SELECTED.replace('count > 0','(u8)count > 0'),
            'signed-radius':source.SELECTED.replace('(f32)(u32)node[8]','(f32)(s8)node[8]'),
            'radius-equality':source.SELECTED.replace('minimum < radius * radius','minimum <= radius * radius'),
            'zero-projection':source.SELECTED.replace('projection > 0.0f','projection >= 0.0f'),
            'last-distance-tie':source.SELECTED.replace('distance < minimum','distance <= minimum'),
            'stop-on-FF':source.SELECTED.replace('                    if (candidate != 0xFF) {',
                '                    if (candidate == 0xFF) { break; }\n                    if (candidate != 0xFF) {'),
            'four-neighbors':source.SELECTED.replace('i < 5','i < 4'),
            'unsigned-coordinates':source.SELECTED.replace('*(s16 *)','*(u16 *)'),
            'accept-any-refinement':source.SELECTED.replace('if (object == selected)','if (1)'),
            'drop-record-return':source.SELECTED.replace('        object = func_15086C70(index);',
                '        func_15086C70(index);\n        object = 0;'),
            'early-node-base':source.SELECTED.replace('    s32 refined =',
                '    u8 *earlyNodes = D_800D2350;\n    s32 refined =').replace('nodes = D_800D2350;','nodes = earlyNodes;')}
        exits={}
        for name,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            exits[name]=run('negative-'+name,body);self.assertIn(exits[name],range(21,26),name)
        self.receipt('native',profiles=3,fixtures_each=len(self.cases),effective_negatives=exits,
            float32_expression_order_and_full_buffers=True,no_uninitialized_or_out_of_range_native_casts=True)

    def test_04_actual_height_record_wrapper_and_containment_packet(self):
        connected={}
        for entry,rom,n in ((oracle.HEIGHT,0xB3258,20),(oracle.LOOKUP,0xB4120,20),(oracle.INSIDE,0xD0764,31)):
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%n,self.rom,rom))})
        runs=0;witnesses=[]
        chosen=[oracle.Case(object=oracle.OBJECT,inside=hit,band=band,answer=2)
            for hit in (0,1) for band in (2,128,255)]
        for case in chosen:
            for words in (self.retail,self.words):
                memory=oracle.fixture(case)
                for i,value in enumerate((0.,10.,30.,1000000.,1e9,1e10)):
                    oracle.put(memory,0x800D2360+i*4,oracle.bits(value),4)
                    oracle.put(memory,0x800D237C+i,case.band,1)
                wanted,expected,calls,stores,_,_=oracle.reference(memory,case)
                model=ConnectedModel(words,memory,case,connected=connected).run()
                self.assertEqual(model.r[2],wanted);self.assertEqual(model.calls,calls)
                self.assertEqual(oracle.public(model.memory),oracle.public(expected));self.assertEqual(public_stores(model),stores)
                find=next(x for x in model.nested if x[0]==FIND)
                self.assertEqual(find,(FIND,3,11,0,0,0))
                query=next(x for x in model.nested if x[0]==QUERY)
                self.assertEqual(query[1:3],(oracle.OBJECT,0))
                vals=[oracle.bits(oracle.f32(math.trunc(oracle.f32(v)))) for v in case.point]
                self.assertEqual(dict(query[3]),dict(zip((0x14,0x18,0x1C,0x2C,0x30,0x34,0x180),(*vals,*vals,vals[1]))))
                runs+=1;witnesses.append(dict(band_word=case.band,contained=case.inside,lookup_result_observed=True))
        self.receipt('connected-helpers',actual_helper_words=71,completed_runs=runs,find_and_query_are_opaque=True,
            actual_record_return_consumed=True,seven_float_packet_fields_checked=True,witnesses=witnesses)

    def test_05_actual_seven_argument_caller_and_result_consumer(self):
        jal=0x0C000000|(source.ENTRY>>2)&0x3FFFFFF
        self.assertEqual([i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==jal],
            [0xA4AF8,0xC7B7C,0xC7E10])
        code={0x1509B484+i*4:w for i,w in enumerate(struct.unpack_from('>5I',self.rom,0xC8934))}
        window=list(struct.unpack_from('>22I',self.rom,0xC7B58))
        self.assertEqual(window[0],0x920F0213);runs=0
        for initial in (0,1,15,255):
            for mutation in (0,1,2):
                case=oracle.Case(count=0,initial=initial,mutation=mutation);memory=oracle.fixture(case)
                oracle.put(memory,oracle.CACHE,oracle.read(memory,oracle.ACTOR+0x213,1),1)
                value,wanted,calls,stores,_,_=oracle.reference(memory,case)
                oracle.put(wanted,oracle.ACTOR+0x213,value&255,1)
                expected=255 if value==255 else oracle.read(wanted,oracle.read(wanted,oracle.NODES,4)+value*16+7,1)
                for words in (self.retail,self.words):
                    mapping={source.ENTRY+i*4:w for i,w in enumerate(words)};mapping.update(code)
                    model=oracle.RefinementModel(window,oracle.fixture(case),case,connected=mapping,entry=0x1509A6A8)
                    sp=oracle.STACK-0x1E0;model.r[29]=sp;model.r[16]=oracle.ACTOR;model.r[2]=sp+0x173
                    oracle.put(model.memory,sp+0x48,model.before[16],4);oracle.put(model.memory,sp+0x4C,0xDEAD0000,4)
                    oracle.put(model.memory,sp+0x173,255,1)
                    model.run();self.assertEqual(model.r[2],expected);self.assertEqual(model.calls,calls)
                    self.assertEqual(oracle.public(model.memory),oracle.public(wanted))
                    self.assertEqual(model.caller_args,[(
                        *[oracle.bits(oracle.f32(v)) for v in case.point],0,0,sp+0x173,sp+0x173)])
                    runs+=1
        self.receipt('caller',actual_window_runs=runs,aligned_ROM_JALs=['0xA4AF8','0xC7B7C','0xC7E10'],
            executed_window='1509A6A8..1509A6FC plus actual five-word epilogue',caller_frame_live_in=480,
            cached_byte_setup_seven_argument_call_result_publication_fresh_category_lookup_and_return=True,
            actual_original_window_not_full_script_or_gameplay=True)

    def test_06_independent_GNU_code_global_and_helper_rebases(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);path=self.out/'retail.s'
        path.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+'\n.text\n'+asm[start:end])
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',
            str(self.root/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        pairs=0
        for n,(entry,delta) in enumerate(((source.ENTRY,0),(0x1621FFF4,0x115CAC),(0x18FFF000,0x235CB0))):
            anchors={name:int(name[2:],16)+delta if name.startswith('D_') else int(name[5:],16)+delta
                for entries in self.bindings.values() for _,name in entries}
            images=[]
            for label,obj,size in (('retail',path.with_suffix('.o'),179),('raw',self.obj,176)):
                script=self.out/('%s-map%d.ld'%(label,n));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                images.append(list(struct.unpack('>%dI'%size,sections(elf)['.text'][1][:size*4])))
            self.assertEqual(images[1],relocate(self.raw,self.bindings,anchors))
            shift=0x40000*n;moved={name:globals_value+delta for name,globals_value in (
                ('NODES',oracle.NODES),('LIMIT',oracle.LIMIT),('HEIGHT',oracle.HEIGHT),('CLOSEST',oracle.CLOSEST),
                ('LOOKUP',oracle.LOOKUP),('INSIDE',oracle.INSIDE),('REFINE',oracle.REFINE))}
            moved.update(BANKS=tuple(b+shift for b in oracle.BANKS),ACTOR=oracle.ACTOR+shift,
                OBJECT=oracle.OBJECT+shift,LIST=oracle.LIST+shift,STATE=oracle.STATE+shift)
            moved['SEGMENTS']=((moved['NODES'],4),(moved['LIMIT'],4),(oracle.CACHE,4),
                *((b,0x400) for b in moved['BANKS']),(moved['ACTOR'],0x400),(moved['OBJECT'],0x100))
            with patch.multiple(oracle,**moved):
                for case in self.cases[::11]:
                    case=replace(case,object=moved['OBJECT'] if case.object else 0)
                    memory=oracle.fixture(case);value,wanted,calls,stores,_,_=oracle.reference(memory,case)
                    for words in images:
                        model=oracle.RefinementModel(words,memory,case,entry=entry).run()
                        self.assertEqual(model.r[2],value);self.assertEqual(model.calls,calls)
                        self.assertEqual(oracle.public(model.memory),oracle.public(wanted));self.assertEqual(public_stores(model),stores)
                    pairs+=1
        self.receipt('GNU-maps',independent_maps=3,retail_raw_pairs=pairs,all11_bindings_including_five_helpers=True,
            independent_GNU_HI_LO_carries_and_code_rebase=True,no_normalized_or_byte_identity_claim=True)

    def test_07_owner_profiles_record_return_identity_and_real_Make_padding(self):
        same=mixed.candidate.source.neighbor.same_functions;objects={}
        for label,normal in (('primary',False),('normal',True)):
            before,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            after,_,row=source.compile_candidate(self.root,self.out,'after-'+label,whole=True,normal=normal)
            self.assertFalse(diag or row['diagnostics']);self.assertEqual(same(before,after,(source.FUNCTION,)),72)
            self.assertEqual(normalized_pools(before),normalized_pools(after));objects[label]=after
        self.assertEqual(source.payload(objects['primary']),(self.raw,self.bindings))
        guards=self.out/'qualified-guards.csv';guards.write_bytes(self.values['conker/retail_word_patches.us.csv'])
        padded=mixed.padded(self.root,self.out,objects['primary'],'qualified-padded',guards,objects['normal'])
        baseline=self.root/'conker/build/src/game/generated_B3020.c.o'
        a,fa=source.link_owner(self.root,self.out,baseline,source.OWNER);b,fb=source.link_owner(self.root,self.out,padded,source.OWNER)
        at=fb[source.FUNCTION]['value'];self.assertEqual(b[at:at+704],struct.pack('>176I',*self.words))
        self.assertEqual(b[at+704:at+716],b'\0'*12);self.assertEqual(fb[source.FUNCTION]['size'],704)
        self.assertEqual(a[:at],b[:at]);self.assertEqual(a[at+716:],b[at+716:]);self.assertEqual(same(baseline,padded,(source.FUNCTION,)),72)
        self.assertTrue(all(fa[n]['value']==fb[n]['value'] and (n==source.FUNCTION or fa[n]==fb[n]) for n in fa))
        helper=fb['func_15086C70']['value'];self.assertEqual(b[helper:helper+80],self.rom[0xB4120:0xB4170])
        self.assertEqual(normalized_pools(baseline),normalized_pools(padded))
        shutil.copyfile(objects['normal'],self.out/'override-normal.o');shutil.copyfile(objects['primary'],self.out/'primary-no-unroll.o')
        (self.out/'proposed-owner.c').write_text(source.recovered_owner(self.values[source.SOURCE].decode()))
        with patch.multiple(mixed,freeze=source.freeze,recovered_owner=source.recovered_owner,
                recovered_makefile=lambda v:v,recovered_guards=lambda before,*unused:before):shadow=mixed.make_shadow(self.root,self.out)
        shadow.pop('original_four_GLOBAL_ASM_bodies_preserved');shadow['GLOBAL_ASM_bodies_remaining']=0
        (self.out/'make-shadow.json').write_text(json.dumps(shadow,indent=2)+'\n')
        self.receipt('owner',profiles=2,neighbors_each=72,record_wrapper_return_type_fix_instruction_identical=True,
            all73_addresses_fixed=True,real_padder_and_seven_Make_commands=True,padding_bytes=12,new_guards=0,
            current_source_still_not_installable_as_match=True)

    def test_08_fired_private_mismatch_and_frozen_production(self):
        case=oracle.Case(count=0);memory=oracle.fixture(case);complete=oracle.RefinementModel(self.retail,memory,case).run()
        first=None
        for cut in range(complete.accesses):
            models=[]
            for words in (self.retail,self.words):
                model=oracle.RefinementModel(words,memory,case);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,cut);models.append(model)
            if models[0].requested!=models[1].requested:
                first=dict(cut=cut,retail=models[0].requested,raw=models[1].requested);break
        self.assertIsNotNone(first)
        for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        self.receipt('private-boundary',same112_byte_frame=True,first_fired_access_mismatch=first,
            no_literal_private_or_fault_prefix_identity=True,all_production_inputs_unchanged=True,
            matching_credit=0,three_missing_words_not_zero_padding_solution=True)


if __name__=='__main__':unittest.main()
