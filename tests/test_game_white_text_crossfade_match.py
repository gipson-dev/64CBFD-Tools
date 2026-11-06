"""Text-buffer fade ABI, original caller/color helper, private state and image gates."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_white_text_crossfade_candidates as candidate
from tools.experiments import game_white_text_crossfade_match as match
from tools.tests import game_white_text_crossfade_oracle as g
from tools.tests import game_white_text_crossfade_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses

class WhiteTextCrossfadeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>70I',cls.rom,match.ROM))
        ctx=type('OriginalFade',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'match-original-fade',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=g.bound(cls.prepared['qualified_compact']);cls.words=g.bound(cls.prepared['qualified_owner']);assert g.bound(cls.original)==cls.retail==cls.words
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),s=None,initial=None,images=None,entry=match.ENTRY):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s)if initial is None else initial;models=[]
        for words in((self.retail,self.words)if images is None else images):
            m=g.Oracle(words,initial,c,s,entry);m.run();models.append(m)
        for m in models[1:]:self.assertEqual(state(models[0]),state(m))
        return models
    def test_01_owner_closed_schedule_bindings_and_corruption(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(70,48,6,6));raw,b=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+280]
        self.assertEqual([4*i for i,(a,b)in enumerate(zip(self.raw,self.retail))if a!=b],[x[0]for x in match.SCHEDULE])
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),b,truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.checked(raw,bad,truth)
        guard_rows=(self.out/'proposed-guards.csv').read_text(encoding='utf-8').splitlines()
        for i in range(6):
            bad=list(guard_rows);fields=bad[len(bad)-6+i].split(',');fields[3]=hex(int(fields[3],16)^1);bad[len(bad)-6+i]=','.join(fields)
            p=self.out/('match-bad-guard-%d.csv'%i);p.write_text('\n'.join(bad)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p,rodata_symbol='D_800A0860')
        self.assertEqual(self.raw[0xB4//4],0x12000012);self.assertEqual(self.raw[0xD8//4],0x8FA20020)
        self.receipt('owner-controls',raw_corruptions=280,binding_corruptions=6,actual_padder_expected_word_controls=6,raw_neighbors=q['raw_neighbors'],padded_neighbors=q['neighbors'],all_pools_fixed=True,frame_and_pointer_home_fixed=True,closed_schedule_words=6,guard_history_preserved=True)
    def test_02_guest_external_reference_and_full_normalized_state(self):
        count=0;seen=set()
        for c in g.cases():
            initial=g.fixture(c);expected,calls,result=g.reference(initial,c)
            ms=self.compare(c,initial=initial);ms.append(g.Oracle(self.raw,initial,c).run())
            for m in ms:
                self.assertEqual((g.public(m.memory,c),m.calls,m.r[2]),(g.public(expected,c),calls,result))
                for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                self.assertEqual(m.f[20:],m.before_f[20:])
            seen.update(ms[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+280,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=3,all_70_words=True,raw_external_state_equal=True,normalized_full_RAM_registers_events_and_accesses_equal=True,all_count_bytes=True,extreme_tick_words=True,mutable_opaque_providers=True)
    def test_03_aliases_faults_and_previous_spill_control(self):
        count=cuts=0
        for phase,off,value,flags in itertools.product((0,8),range(0,52,4),(0,7,0xFFFFFFFF),(0,1)):
            c=g.Case(count=8,flags=flags,phase=phase,ticks=value);s=g.symbols();s['D_800BE9E4']=g.STACK+phase-48+off
            images=[g.bound(o,s)for o in(self.original,self.prepared['qualified_owner'])];self.compare(c,s,images=images);count+=1
        # The previously observed false write at SP+0x20 is eliminated before normalization.
        c=g.Case(count=0,flags=0,ticks=7);s=g.symbols();s['D_800BE9E4']=g.STACK-48+32;initial=g.fixture(c,s)
        for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner']):self.assertEqual(g.read(g.Oracle(g.bound(obj,s),initial,c,s).run().memory,s['D_800BE9E4']),7)
        class RedirectedHome(g.Oracle):
            def hook(self,t):
                super().hook(t)
                if t==g.COLOR:
                    n=sum(target==g.COLOR for target,args in self.calls)
                    self.put(self.r[29]+48,0x70000 if n==1 else g.OWNER,4)
        c=g.Case(count=8);initial=g.fixture(c);initial[0x7003D]=1;g.put(initial,0x70040,0xC0000);g.put(initial,0x70044,0xC0004);models=[]
        for words in(self.retail,self.words):
            m=RedirectedHome(words,initial,c).run();models.append(m)
            self.assertEqual([a[3]for t,a in m.calls if t==g.TEXT],[0xC0004,0xC0000])
        self.assertEqual(state(models[0]),state(models[1]))
        for c in(g.Case(),g.Case(count=8,flags=1,mutation=7,phase=8),g.Case(count=33)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for words in(self.retail,self.words):
                    m=g.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('aliases-faults',private_aliases_per_body=count,fired_prefixes=cuts,previous_raw_spill_witness_closed=True,incoming_owner_home_redirect_control=True,second_descriptor_captured_before_color=True,normalized_literal_fault_states_equal=True,portable_C_fault_claimed=False,raw_access_order_not_claimed=True)
    def test_04_complete_original_caller_and_return_control(self):
        va=0x150D0034;body=list(struct.unpack_from('>35I',self.rom,0xFD4E4));count=0;seen=set()
        stub=list(struct.unpack_from('>70I',self.prepared['predecessor_elf'].read_bytes(),match.elf_slot_offset(self.prepared['predecessor_elf'].read_bytes(),match.ENTRY,280)))
        for value,flags,index,phase,enabled in itertools.product((0,1,20,64,127,128,255),(0,1,255),(0,1),(0,8),(False,True)):
            c=g.Case(value,flags,7,index,0,phase);initial=g.fixture(c);initial[g.OWNER+0x4C]=2 if enabled else 255;g.put(initial,g.OWNER+14,100,2);g.put(initial,0x800888A8,match.ENTRY);models=[]
            for words in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+280,4),words));m=g.Oracle(body,initial,c,entry=va,connected=code,arguments=(0x12345678,g.OWNER,0xAABBCCDD));m.run();models.append(m);seen.update(m.visits)
                self.assertEqual(m.r[2],0x12345678);self.assertEqual(g.read(m.memory,g.OWNER+14,2),100);self.assertEqual(m.memory[g.OWNER+0x30],flags&254);self.assertEqual(m.r[29],g.STACK+phase)
                self.assertEqual([a for t,a in m.calls if t==match.ENTRY],[(g.OWNER,)]if enabled else [])
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        c=g.Case(count=0,flags=1);initial=g.fixture(c);initial[g.OWNER+0x4C]=2;g.put(initial,0x800888A8,match.ENTRY);g.put(initial,g.OWNER+14,100,2)
        m=g.Oracle(body,initial,c,entry=va,connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),stub)),arguments=(0x12345678,g.OWNER,0));m.run();self.assertEqual(g.read(m.memory,g.OWNER+14,2),65535)
        unvisited=set(range(va,va+140,4))-seen
        self.assertEqual(unvisited,{va+0x58,va+0x5C,va+0x60,va+0x64})
        self.receipt('caller-controls',cases_per_body=count,original_parent_words=35,covered_parent_words=31,expiry_branch_exercised_with_false_return_control=True,registered_slot=2,callback_return1_preserves_record=True,active_mask_cleared=True)
    def test_05_original_color_helper(self):
        helper=list(struct.unpack_from('>22I',self.rom,0x707DC));code=dict(zip(range(g.COLOR,g.COLOR+88,4),helper));count=0;seen=set()
        for value,flags,index in itertools.product(range(256),(0,1),(0,1)):
            c=g.Case(value,flags,7,index);initial=g.fixture(c)
            for i in range(4):initial[0x800CBD60+i]=0x5A
            expected,calls,result=g.reference(initial,c);models=[]
            for words in(self.retail,self.words):
                m=g.Oracle(words,initial,c,connected=code);m.run();models.append(m);seen.update(m.visits)
                self.assertEqual((m.calls,m.r[2],m.memory[g.PAYLOAD]),(calls,result,expected[g.PAYLOAD]));last=[a for t,a in calls if t==g.COLOR][-1]
                self.assertEqual(tuple(m.memory[0x800CBD60+i]for i in range(4)),last)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.assertEqual(set(range(g.COLOR,g.COLOR+88,4))-seen,set())
        self.receipt('helper-contract',cases_per_body=count,original_color_words=22,all_color_words_covered=True,independent_color_bytes_and_calls=True,text_renderer_opaque=True,whole_renderer_or_gameplay_claimed=False)
    def test_06_independent_GNU_rebases(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s.update(D_800BE9E4=0x89000000+(0x7FFC if k==1 else 0x8000),func_1504332C=entry+0x10000,func_15042D94=entry+0x20000)
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('match-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>70I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[1],match.bound_blob(*match.function_blob(self.prepared['qualified_compact']),s))
            for c in list(g.cases())[::127]:self.compare(c,s,entry=entry,images=(images[0],images[2]));count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_six_bindings=True,HI_LO_carry_boundary=True,raw_and_normalized_linker_binding_verified=True)
    def test_07_native32_semantics_and_effective_controls(self):
        with patch.object(g.source,'SELECTED',candidate.SELECTED):controls=g.controls()
        controls['same_buffer']=candidate.SELECTED.replace('secondText->index ^ 1','secondText->index')
        self.assertTrue(all(body!=candidate.SELECTED for body in controls.values()))
        effective=[]
        for name,body,opt,want in [('positive-'+x[1:],candidate.SELECTED,x,0)for x in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls.items()]:
            p=self.out/('match-native-'+name+'.c');p.write_text(native.program(body),encoding='utf-8');exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);r=subprocess.run([str(exe)]).returncode
            if want:self.assertEqual(r,1,name);effective.append(name)
            else:self.assertEqual(r,0,name)
        self.receipt('native-controls',cases_per_profile=20480,positive_executions=61440,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,compatible_callback_pointer=True,controls=effective)
    def test_08_literal_image_corruptions_and_old_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+280];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,280)
        for off in(0,at,at+279,at+280,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>70I',before,at));m=g.Oracle(stub,g.fixture(g.Case(count=8,flags=1)),g.Case(count=8,flags=1)).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        self.receipt('image-controls',literal_changed_bytes=delta,metadata_permutations=0,exclusions=0,corruptions=5,old_stub_rejected=True)

if __name__=='__main__':unittest.main()
