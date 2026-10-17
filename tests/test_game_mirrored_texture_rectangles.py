"""Complete uninstalled SDK recovery, actual retail packets and private-match gap."""
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_mirrored_texture_rectangles as source
from tools.tests import game_mirrored_texture_oracle as model
from tools.tests import game_mirrored_texture_native as native
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.check_game_data_layout import audit_layout


class MirroredTextureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.words,cls.row=source.candidate(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>633I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-mirrored',
            (cls.out/'before-color_provider_original').read_text(),source.FUNCTION)
        script=cls.out/'original-retail.ld';elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
            '--defsym=D_800BE628=0x800BE628','--defsym=D_800DDDE8=0x800DDDE8','-o',str(elf),str(cls.original)],
            capture_output=True,check=True)
        assert source.projection.sections(elf)['.text'][1][:2532]==cls.rom[source.ROM:source.ROM+2532]

    def receipt(self,name,**row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_complete_candidate_is_not_a_match_or_installed_and27_neighbors_stay_identical(self):
        self.assertEqual((self.row['words'],self.row['differences'],self.row['frame']),(626,604,216))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],27)
        self.assertFalse(self.row['installed']);self.assertFalse(self.row['matching_credit']);self.assertFalse(self.row['byte_exact'])
        self.assertEqual(self.row['new_guards'],0);self.assertNotEqual(self.words,self.truth)
        before=(self.out/'before-color_owner').read_text();lo,hi=source.build.function_span(before,source.FUNCTION)
        self.assertEqual(before[lo:hi],'s32 func_1517FB9C() {\n    return 0;\n}')
        self.assertEqual((self.root/source.PATHS['color_owner']).read_bytes(),(self.out/'before-color_owner').read_bytes())
        source.checked_parts(*source.parts(self.obj),source.projection.sections(self.obj)['.rodata'][1])
        self.receipt('status',candidate_words=626,original_words=633,frame=216,ordinal_differences=604,
            installed=False,byte_exact=False,matching_credit=False,guards=0,unchanged_raw_padded_neighbors=27,
            not_an_installation_qualification=True)

    def test_02_all24_words_independent_guest_reference_wrap_aliases_and_control_restore(self):
        count=0;seen=[set(),set()];conversions=set();control_writes=set()
        for ordinal,(memory,args) in enumerate(model.cases()):
            expected,result,words,step=model.reference(memory,args)
            for phase in (0,8):
                fcsr=(0,3,0x800004,0xA5A50003)[ordinal%4]
                for index,target in enumerate((self.truth,self.words)):
                    m=model.MirroredOracle(target,memory,args,phase,fcsr).run()
                    self.assertEqual(model.public(m.memory),model.public(expected),(args,phase,index))
                    self.assertEqual(m.r[2],result);self.assertFalse(m.calls)
                    public=[(at,size,value) for _,at,size,value in m.store_sites if not model.STACK-0x300<=at<model.STACK+0x120]
                    self.assertEqual(public,[((args[0]+i*4)&model.MASK,4,value) for i,value in enumerate(words)])
                    self.assertEqual(m.fcsr,fcsr);conversions.update(value&0x78 for _,value in m.conversions)
                    seen[index].update(m.visits)
                    control_writes.add(len(m.conversions))
                count+=1
        self.assertIn(0,conversions);self.assertIn(0x40,conversions);self.assertIn(1,control_writes);self.assertIn(2,control_writes)
        missing=[[pc-source.ENTRY for pc in range(source.ENTRY,source.ENTRY+length*4,4) if pc not in seen[i]]
            for i,length in enumerate((633,626))]
        self.receipt('guest',paired_cases=count,output_words_each=24,cursor_advance=96,all_public_words_and_store_order=True,
            no_private_equality_claim=True,bounded_conversion_statuses=sorted(conversions),conversion_counts=sorted(control_writes),
            original_missing_offsets=missing[0],candidate_missing_offsets=missing[1],not_hardware_FCSR_or_gameplay=True)

    def test_03_native32_complete_sdk_candidate_typed_caller_and_eight_controls(self):
        caller=self.out/'native-caller.c';caller.write_text(native.CALLER)
        driver=self.out/'native-driver.c';driver.write_text(native.program());exits={}
        sdk=(self.out/'before-sdk_gbi').read_text() if (self.out/'before-sdk_gbi').exists() else (self.root/'conker/include/2.0L/PR/gbi.h').read_text()
        self.assertIn('conker/include/2.0L/PR/gbi.h',source.PATHS.values())
        macro='#define gSPScisTextureRectangle'+sdk.split('#define gSPScisTextureRectangle',1)[1].split('#define gsSPTextureRectangleFlip',1)[0]
        self.assertEqual(macro.count('(((yl) < 0)'),1)
        wrong='#undef gSPScisTextureRectangle\n'+macro.replace('(((yl) < 0)','(((s16)(yl) < 0)')+'\n'
        forms=[('o2','-O2',source.SELECTED,''),('o0','-O0',source.SELECTED,'')]+[
            (name,'-O2',body,'') for name,body in native.controls(source.SELECTED).items()]+[('narrowed_y_sign','-O2',source.SELECTED,wrong)]
        for label,opt,body,header in forms:
            unit=self.out/('native-'+label+'.c');unit.write_text(native.HEADER+header+body+'\n');exe=unit.with_suffix('.elf')
            built=subprocess.run([*native_command(opt),'-g','-mstackrealign','-malign-double','-fno-strict-aliasing',
                *[str(p.relative_to(self.root)) for p in (unit,caller,driver)],'-o',str(exe.relative_to(self.root))],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([str(exe)],capture_output=True,text=True,timeout=120);exits[label]=ran.returncode
            self.assertEqual(ran.returncode,0 if label in ('o2','o0') else 22,(label,ran.stderr))
        self.receipt('native',cases_each=sum(1 for _ in native.cases()),exits=exits,UBSan=True,no_LTO_or_fwrapv=True,
            separate_complete_SDK_body_and_typed_caller=True,all24_words_and_full_banks=True,
            aligned_viewport_and_projection_output_aliases=True,invalid_indices_conversions_and_private_aliases_guest_only=True)

    def test_04_three_independent_original_C_global_rebases_preserve_public_packets_not_word_identity(self):
        raw,bindings=source.parts(self.obj);sets=[]
        for index,base in enumerate((0x80107FFC,0x80118004,0x80127FD0)):
            anchors={'D_800BE628':base,'D_800DDDE8':base+0x10008};images=[]
            text,unresolved=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved);path=self.out/('rebase-C-%d.s'%index);path.write_text(text);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
            for label,target in (('original',self.original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(index,label));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],capture_output=True,check=True)
                data=source.projection.sections(elf)['.text'][1];length=633 if label=='original' else 626
                images.append(list(struct.unpack_from('>%dI'%length,data)))
            self.assertNotEqual(*images)
            def relocate(memory):
                result={}
                for at,value in memory.items():
                    if model.BASE-16<=at<model.BASE+24:at=base+at-model.BASE
                    elif model.PROJECTED-16<=at<model.PROJECTED+64:at=anchors['D_800DDDE8']+at-model.PROJECTED
                    result[at]=value
                return result
            count=0
            for view in (0,1,3):
                for center in (0,2,3,4):
                    memory,args=model.fixture(view,3,65535,center,1);expected,result,_,_=model.reference(memory,args)
                    for words in images:
                        m=model.MirroredOracle(words,relocate(memory),args).run()
                        self.assertEqual(model.public(m.memory),model.public(relocate(expected)));self.assertEqual(m.r[2],result)
                    count+=1
            sets.append(count)
        self.receipt('rebases',independent_original_C_link_pairs=3,paired_public_cases=sum(sets),
            both_global_anchors_changed_with_signed_low_carries=True,no_word_or_private_equality_claim=True)

    def test_05_private_home_gap_and_positively_fired_original_and_C_faults_are_not_hidden(self):
        rows=[];faults_fired=0
        for phase in (0,8):
            memory,args=model.fixture(1,32,64,0,1);models=[model.MirroredOracle(words,memory,args,phase).run() for words in (self.truth,self.words)]
            private=lambda m:[(pc-source.ENTRY,at-(model.STACK+phase-216),size,value) for pc,at,size,value in m.store_sites if model.STACK-0x300<=at<model.STACK+0x120]
            old,new=map(private,models);first=next(i for i,pair in enumerate(zip(old,new)) if pair[0][1:]!=pair[1][1:])
            self.assertEqual(first,2);self.assertEqual(old[first][1],0x54);self.assertEqual(new[first][1],0x60)
            self.assertNotEqual(models[0].memory,models[1].memory)
            for version,(words,complete) in enumerate(zip((self.truth,self.words),models)):
                for fault in range(complete.all_accesses):
                    m=model.MirroredOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault);faults_fired+=1
            rows.append(dict(phase=phase,first_private_store_index=first,original=old[first],candidate=new[first],
                original_accesses=models[0].all_accesses,candidate_accesses=models[1].all_accesses))
        self.receipt('private-gap',rows=rows,positively_fired_faults=faults_fired,
            private_state_equal=False,not_an_instruction_guard_or_installation_certificate=True)

    def test_06_complete_word_bindings_pool_and_all156_inputs_fail_closed_with_unchanged_production(self):
        raw,bindings=source.parts(self.obj);pool=source.projection.sections(self.obj)['.rodata'][1]
        for i in range(626):
            bad=bytearray(raw);bad[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(bad),bindings,pool)
        for i in range(len(pool)):
            bad=bytearray(pool);bad[i]^=1
            with self.assertRaises(ValueError):source.checked_parts(raw,bindings,bytes(bad))
        for at in (*bindings,-4):
            bad=dict(bindings);bad[at]=[('R_MIPS_HI16','wrong')]
            with self.assertRaises(ValueError):source.checked_parts(raw,bad,pool)
        self.assertEqual(len(source.PATHS),156);read=Path.read_bytes
        for relative in source.PATHS.values():
            target=self.root/relative
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==target else read(p)):
                with self.assertRaises(ValueError):source.freeze(self.root,self.out)
        source.freeze(self.root,self.out)
        self.assertEqual(hashlib.sha256((self.root/source.PATHS['elf']).read_bytes()).hexdigest(),source.BASELINE['elf'])
        layout=audit_layout(self.root/source.PATHS['elf'],self.root/'conker')
        self.assertEqual((layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']),(True,189088,720,0))
        self.receipt('inputs',word_controls=626,binding_controls=5,pool_byte_controls=16,protected_input_entries=156,
            distinct_paths=len(set(source.PATHS.values())),all_fail_closed=True,production_unchanged=True,protected_layout=layout)

    def test_07_all_four_actual_caller_packets_mixed_float_words_and_signed_size_divisions(self):
        sites=(0x15181044,0x151810F8,0x151811F8,0x15181214)
        text=(self.out/'before-color_provider_original').read_text()
        self.assertEqual(tuple(int(pc,16) for pc in re.findall(
            r'/\* [0-9A-F]+ ([0-9A-F]+) [0-9A-F]+ \*/  jal        func_1517FB9C',text)),sites)
        starts=(0x15181030,0x151810DC,0x151811D0,0x15181200)
        class Join(Exception):pass
        class Code(faults.TrackedCode):
            def __getitem__(self,pc):
                if pc==self.owner.join:raise Join
                return super().__getitem__(pc)
        count=0;covered=set()
        divide=lambda v,d:(abs(v)//d)*(-1 if v<0 else 1)
        for index,(entry,site) in enumerate(zip(starts,sites)):
            join=site+8;length=(join-entry)//4;packet=list(struct.unpack_from('>%dI'%length,self.rom,entry-0x15000000+0x2D4B0))
            for view in (0,1,3):
                for size in (1,3,32,-1):
                    for offset in (0.,3.25):
                        for phase in (0,8):
                            memory,_=model.fixture(view,size,64,0,0);f20=model.bits(offset)
                            passed=(model.OUTPUT,(size if index in (0,3) else divide(size,2 if index==1 else 4))&model.MASK,
                                64 if index<2 else 32,model.bits(28.) if index==3 else f20,
                                model.bits(28.) if index==2 else f20,view)
                            expected,result,_,_=model.reference(memory,passed)
                            for target in (self.truth,self.words):
                                code=dict(zip(range(source.ENTRY,source.ENTRY+len(target)*4,4),target));code[join]=0
                                args=(model.OUTPUT,size&model.MASK,64,f20,f20,view)
                                m=model.MirroredOracle(packet,memory,args,phase,entry=entry,connected=code);m.join=join
                                m.r[2]=model.OUTPUT;m.r[18]=size&model.MASK;m.r[21]=model.OUTPUT;m.r[23]=view
                                m.f[20]=f20;model.put(m.memory,model.STACK+phase+0x68,size&model.MASK)
                                m.code=Code(m.code,m)
                                with self.assertRaises(Join):m.run()
                                self.assertEqual(m.calls,[(source.ENTRY,passed)],(index,size,offset,phase))
                                self.assertEqual(model.public(m.memory),model.public(expected));self.assertEqual(m.r[2],result)
                                self.assertEqual(m.r[18],(divide(size,4) if index==2 else size)&model.MASK)
                                self.assertEqual(m.r[29],model.STACK+phase);self.assertEqual(m.r[31],join);self.assertEqual(m.f[20],f20)
                                self.assertEqual([model.read(m.memory,model.STACK+phase+at) for at in (8,16,20,0x68)],
                                    [passed[2],passed[4],passed[5],size&model.MASK])
                                covered.update(m.visits)
                            count+=1
        self.assertTrue(all(set(range(start,site+8,4))<=covered for start,site in zip(starts,sites)))
        self.receipt('callers',original_sites=4,packet_words=[(pc+8-start)//4 for start,pc in zip(starts,sites)],paired_cases=count,
            actual633_and_complete626_bodies=True,all_six_word_packets_and_signed_division_routes=True,
            caller_F20_S2_home_state_preserved=True,not_full_parent_or_private_callee_equality=True)


if __name__=='__main__':unittest.main()
