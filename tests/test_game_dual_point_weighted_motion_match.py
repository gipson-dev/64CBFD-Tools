"""Weighted motion: raw FP roles, saved-weight aliases, complete parent and image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_dual_point_weighted_motion_candidates as candidate
from tools.experiments import game_dual_point_weighted_motion_match as match
from tools.experiments import game_dual_point_weighted_motion_roles as roles
from tools.tests import game_dual_point_weighted_motion_oracle as g
from tools.tests import game_dual_point_weighted_motion_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses
class WeightedDualPointMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+268];cls.retail=list(struct.unpack('>67I',cls.truth))
        ctx=type('OriginalWeightedMotion',(),dict(root=ROOT,out=cls.out));cls.original=view_setup.ViewListSetupTests.original.__func__(ctx,'weighted-original',(ROOT/match.ASM).read_text(encoding='utf-8'),match.FUNCTION)
        cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),dict(D_800BE9A4=g.STEP));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),dict(D_800BE9A4=g.STEP));assert cls.words==cls.retail==match.bound_blob(*match.function_blob(cls.original),dict(D_800BE9A4=g.STEP))
    def receipt(self,n,**v):(self.out/('weighted-'+n+'.json')).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
    def compare(self,c=g.Case(),step=g.STEP,images=None,entry=match.ENTRY,initial=None):
        initial=g.fixture(c,step)if initial is None else initial;expected=g.reference(initial,c,step);models=[]
        for w in((self.retail,self.raw,self.words)if images is None else images):
            m=g.Oracle(w,initial,c,entry,step).run();self.assertTrue(g.equivalent(m.memory,expected,c,step),(c,hex(step)));self.assertEqual(m.r[2],1)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual(m.f[20:],m.before_f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[-1]));return models
    def test_01_complete_owner_derived_roles_and_fail_closed_guards(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(67,24,7,2,35))
        raw,b=match.function_blob(self.prepared['qualified_compact']);fitted,proof=roles.normalized(raw,b,self.truth);self.assertEqual(proof['alias_layouts'],163);self.assertFalse(proof['reassociation']);self.assertTrue(proof['instruction_permutation_identity'])
        for at in range(268):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):roles.normalized(bytes(bad),b,self.truth)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):roles.normalized(raw,bad,self.truth)
        rows=(self.out/'proposed-guards.csv').read_text(encoding='utf-8').splitlines()
        for i in range(7):
            bad=list(rows);parts=bad[-7+i].split(',');parts[3]=hex(int(parts[3],16)^1);bad[-7+i]=','.join(parts);p=self.out/('weighted-bad-guard-%d.csv'%i);p.write_text('\n'.join(bad)+'\n',encoding='utf-8')
            with self.assertRaises(ValueError):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        self.receipt('owner-controls',raw_corruptions=268,binding_corruptions=2,padder_expected_word_controls=7,raw_and_padded_neighbors=35,expression_alias_layouts=163,real_frame=24,weight_SP_offset=4,logical_adapter_not_emitted=True,compact_register_mask_change_pinned=True)
    def test_02_independent_rounded_reference_ABI_and_coverage(self):
        count=0;seen=set()
        for i,c in enumerate(g.cases()):
            c=replace(c,phase=8*(i&1));models=self.compare(c);seen.update(models[0].visits);count+=1
        self.assertEqual(seen,set(range(match.ENTRY,match.ENTRY+268,4)))
        self.receipt('guest-contract',cases_per_body=count,bodies=3,all_67_words=True,round_each_single_operation=True,signed_zero_subnormals_infinity_and_NaN_classes=True,raw_NaN_payloads_not_equated=True,normalized_full_private_state_equal=True,callee_saved_GPR_FPR_and_return1=True)
    def test_03_live_timestep_and_every_private_weight_overlap(self):
        count=0
        for layout,pattern,phase in itertools.product(range(0,0x144,4),(0,1,3,7),(0,8)):
            self.compare(g.Case(layout=layout,pattern=pattern,phase=phase));count+=1
        for off,pattern,phase in itertools.product(range(0,0x144,4),(1,3),(0,8)):
            self.compare(g.Case(at=g.STACK+phase-20-off,pattern=pattern,phase=phase));count+=1
        for phase in(0,8):
            step=g.STACK+phase-20;images=[match.bound_blob(*match.function_blob(o),dict(D_800BE9A4=step))for o in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])];self.compare(g.Case(phase=phase),step,images=images);count+=1
        self.receipt('aliases',cases_per_body=count,live_timestep_field_aliases=81,saved_weight_owner_aliases=81,stack_phases=[0,8],saved_weight_timestep_alias=True,raw_finite_memory_and_normalized_full_state=True)
    def test_04_prior_late_x_alias_rejected_and_fault_prefixes(self):
        late=self.out/'late-x-rejected-selected-screen.o';raw,b=match.function_blob(late);self.assertEqual(match.sha(raw),'6621808de8c945aa76b97dff0f5aee00d1a0dca54c866d4f1956394f613ae3de')
        c=g.Case(at=g.STACK-20-0x34);initial=g.fixture(c);old=g.Oracle(match.bound_blob(raw,b,dict(D_800BE9A4=g.STEP)),initial,c).run();good=self.compare(c,initial=initial)[0]
        self.assertNotEqual(g.read(old.memory,g.owner(c)+0x40),g.read(good.memory,g.owner(c)+0x40))
        original_x=hex(g.read(good.memory,g.owner(c)+0x40));late_x=hex(g.read(old.memory,g.owner(c)+0x40))
        from tools.experiments.game_linear_float_dataflow import derive
        with self.assertRaises(ValueError):derive(roles.logical(match.bound_blob(raw,b,dict(D_800BE9A4=g.STEP)),g.STACK),roles.logical(self.retail,g.STACK),[g.owner(c)])
        cuts=0
        for c in(g.Case(),g.Case(layout=0x130),g.Case(layout=0x134),g.Case(at=g.STACK-20-0x34),g.Case(at=g.STACK-20-0x40,phase=8)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));cuts+=1
        self.receipt('private-boundary',prior_late_x_witness_fired=True,original_x_result=original_x,late_x_result=late_x,fault_prefixes=cuts,normalized_literal_fault_states_equal=True,raw_fault_or_FCSR_parity_claimed=False)
    def test_05_complete_original_registered_parent_and_false_return(self):
        va=0x1513CFE4;body=list(struct.unpack_from('>195I',self.rom,0x16A494));count=0;seen=set()
        for active,slot,phase,pattern in itertools.product((0,1),(0,6),(0,8),(0,1,3,7)):
            c=g.Case(phase=phase,pattern=pattern);initial=g.fixture(c);a=g.owner(c);g.put(initial,a+0x10,active);g.put(initial,a+0x58,0);g.put(initial,a+0x24,0);initial[a+0x70]=slot;initial[a+0x71]=0;initial[a+0x72]=0;g.put(initial,g.TABLE+24,match.ENTRY);models=[]
            for w in(self.retail,self.words):
                m=g.Oracle(body,initial,c,entry=va,connected=dict(zip(range(match.ENTRY,match.ENTRY+268,4),w)));expected=dict(initial);sp=g.STACK+phase-32;g.put(expected,sp+0x14,m.before[31])
                if active and slot:g.put(expected,sp+0x20,a);g.put(expected,sp+0x1B,0,1);expected=g.reference(expected,c,home=sp-24)
                m.run();self.assertTrue(g.equivalent(m.memory,expected,c,home=sp-24));self.assertEqual(m.calls,[(match.ENTRY,(a,))]if active and slot else []);self.assertEqual(m.r[29],g.STACK+phase);models.append(m);seen.update(m.visits)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        c=g.Case();initial=g.fixture(c);a=g.owner(c)
        for off,v in((0x10,1),(0x58,0),(0x24,0)):g.put(initial,a+off,v)
        initial[a+0x70]=6;initial[a+0x71]=initial[a+0x72]=0;g.put(initial,g.TABLE+24,match.ENTRY);bad=list(self.retail);bad[22]=0x24020000;m=g.Oracle(body,initial,c,entry=va,connected=dict(zip(range(match.ENTRY,match.ENTRY+268,4),bad))).run()
        self.assertEqual([t for t,args in m.calls],[match.ENTRY,0x1516972C])
        self.receipt('caller',cases_per_body=count,whole_parent_words=195,covered_parent_words=len(seen&set(range(va,va+780,4))),slot=6,table_entries=42,return1_prevents_cleanup=True,false_return_cleanup_control=True,cleanup_body_opaque=True)
    def test_06_independent_GNU_rebases_and_weight_alias_proofs(self):
        links=count=0
        for k,(entry,step)in enumerate(((match.ENTRY,g.STEP),(0x18017FFC,0x89007FFC),(0x1A028000,0x89008000))):
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                t,fs,rs=match.parse_object(obj);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,dict(D_800BE9A4=step));self.assertFalse(unknown);p=self.out/('weighted-rebase-%d-%d'%(k,j));p.with_suffix('.s').write_text(asm,encoding='utf-8');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry,encoding='utf-8')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,'--defsym=D_800BE9A4=0x%X'%step,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>67I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);raw,b=match.function_blob(self.prepared['qualified_compact']);roles.normalized(raw,b,self.truth,step=step,home=g.STACK+8)
            for c in list(g.cases())[::127]:self.compare(c,step,images,entry);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,HI_LO_carry_boundaries=True,phase8_symbolic_alias_proof=True,normalized_words_equal=True)
    def test_07_native32_float_storage_aliases_and_effective_controls(self):
        controls=g.controls();p=self.out/'weighted-native.c';p.write_text(native.program(controls),encoding='utf-8')
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('weighted-native'+opt);r=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),opt);self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',positive_executions=12288,rows_per_profile=2048,direct_and_compatible_callback=True,profiles=['O0','O2','O3'],SDK_native32=True,UBSan=True,real_float_storage_aliases=12,controls=list(controls),NaN_output_classes_only=True)
    def test_08_actual_IDO_control_witnesses(self):
        before,_,_=candidate.source_states((ROOT/candidate.SOURCE).read_text(encoding='utf-8'));found={}
        witnesses=[g.Case(pattern=1,layout=n)for n in(-1,0x130,0x134,0x138,0x34,0x54,0x140)]
        for name,body in g.controls().items():
            obj,diag=candidate.compile_owner(ROOT,self.out,before.replace(candidate.OLD,body,1),'weighted-negative-'+name);self.assertEqual(candidate.diagnostics(diag),self.prepared['report']['diagnostics']);w=match.bound_blob(*match.function_blob(obj),dict(D_800BE9A4=g.STEP));fired=False
            for c in witnesses:
                initial=g.fixture(c);m=g.Oracle(w,initial,c).run();expected=g.reference(initial,c);a={k:v for k,v in m.memory.items()if not g.STACK-1024<=k<g.STACK+1024};b={k:v for k,v in expected.items()if not g.STACK-1024<=k<g.STACK+1024}
                if a!=b or m.r[2]!=1:fired=True;found[name]=c.layout;break
            self.assertTrue(fired,name)
        self.receipt('IDO-controls',effective=found,all_nine_controls_fired=True,external_state_or_return_witnesses=True)
    def test_09_literal_image_controls_and_stub_rejection(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),227);at=match.elf_slot_offset(after,match.ENTRY,268)
        for off in(0,at,at+267,at+268,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        stub=list(struct.unpack_from('>67I',before,at));m=g.Oracle(stub,g.fixture()).run();self.assertEqual(m.r[2],0);self.assertFalse(g.equivalent(m.memory,g.reference(g.fixture())))
        self.receipt('image',changed_bytes=227,exclusions=0,metadata_permutations=0,corruptions=5,old_stub_rejected=True)
if __name__=='__main__':unittest.main()
