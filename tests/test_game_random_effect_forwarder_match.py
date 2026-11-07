"""Source, private homes, original RNG/helper/callers, native32 and full image."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_random_effect_forwarder_candidates as candidate
from tools.experiments import game_random_effect_forwarder_match as match
from tools.tests import game_random_effect_forwarder_oracle as g
from tools.tests import game_random_effect_forwarder_native as native
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class RandomEffectForwarderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM));cls.words=match.bound_blob(*match.function_blob(cls.prepared['qualified_owner']),g.symbols());cls.raw=match.bound_blob(*match.function_blob(cls.prepared['qualified_compact']),g.symbols());assert cls.retail==cls.words and cls.raw!=cls.words
    def receipt(self,name,**v):(self.out/('match-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=g.Case(),images=None,s=None,entry=match.ENTRY,include_raw=True):
        s=g.symbols()if s is None else s;initial=g.fixture(c,s);expected=g.reference(initial,c,s);pair=[]
        for words in(self.retail,self.words,self.raw)if images is None and include_raw else(self.retail,self.words)if images is None else images:
            m=g.Oracle(words,initial,c,s=s,entry=entry,connected=g.helper_code(self.rom,c)).run();pair.append(m)
            self.assertEqual((g.public(m.memory,c),m.calls,m.payloads,m.r[2]),(g.public(expected['memory'],c),expected['calls'],[(expected['pair'],expected['templates'])],expected['result']),c)
        self.assertEqual(g.state(pair[0]),g.state(pair[1]));return pair
    def test_01_derived_homes_guards_owner_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(71,88,3,7,7));raw,bindings=match.function_blob(self.prepared['qualified_compact']);normalized,moved=match.derive(raw,bindings);self.assertEqual((normalized,moved),match.function_blob(self.prepared['qualified_owner']))
        proof=match.home_closure(raw,bindings);self.assertEqual(proof['word_accesses'],[0x7C,0x84,0x9C])
        for i in range(284):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.derive(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad[at]=[(bindings[at][0][0],'foreign')]
            with self.assertRaises(ValueError):match.derive(raw,bad)
        base=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(match.guard_manifest(base,raw,bindings),proposed);self.assertTrue(proposed.startswith(base))
        rows=list(match.csv.DictReader(match.io.StringIO(proposed.decode())));new=[r for r in rows if r['function']==match.FUNCTION];self.assertEqual(len(new),3);self.assertTrue(all(r['omit']=='false'and not r['insert_after']and r['expected_relocations']==r['replacement_relocations']=='-'for r in new))
        item=new[0];item['expected']='0x%08X'%(int(item['expected'],0)^1);stream=match.io.StringIO();w=match.csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);p=self.out/'match-bad-guard.csv';p.write_text(stream.getvalue())
        with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],'match-bad-guard-owner',p)
        self.receipt('homes-owner',byte_corruptions=284,binding_corruptions=18,expected_word_guard_rejected=True,guards=3,neighbors=7,all_raw_padded_pools_metadata_fixed=True,**proof)
    def test_02_raw_C_float_payload_and_literal_RNGs(self):
        count=0;seen=set();connected=0
        for c in g.cases():
            for m in self.compare(c):seen.update(m.visits)
            count+=1;connected+=bool(c.connected)
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+284,4))<=seen)
        self.assertTrue(set(range(g.INTEGER,g.INTEGER+72,4))<=seen);self.assertTrue(set(range(g.FLOAT,g.FLOAT+100,4))<=seen)
        self.receipt('guest',cases_per_body=count,bodies=3,connected_RNG_cases_per_body=connected,root_words_reached=71,original_integer_RNG_words=18,original_float_RNG_words=25,all_256_priority_bytes=True,all_five_draws_and_order=True,live_globals_templates_and_position=True,signed16_unsigned8_fullword_arguments=True,raw_C_public_contract=True,normalized_full_literal_state=True,no_FCSR_hardware_or_NaN_payload_guarantee=True)
    def test_03_private_homes_aliases_and_fault_prefixes(self):
        count=cuts=0
        for alias,phase,mutation in itertools.product(range(1,9),(0,8),(0,7)):
            c=g.Case(alias=alias,phase=phase,mutation=mutation);initial=g.fixture(c);pair=[g.Oracle(w,initial,c).run()for w in(self.retail,self.words)];self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        for c in(g.Case(),g.Case(mutation=7,connected=1),g.Case(alias=1),g.Case(alias=6,phase=8)):
            initial=g.fixture(c);code=g.helper_code(self.rom,c);full=g.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(full.all_accesses):
                pair=[]
                for w in(self.retail,self.words):
                    m=g.Oracle(w,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(g.state(pair[0]),g.state(pair[1]));cuts+=1
        self.receipt('faults',private_home_cases_per_body=count,fired_access_prefixes=cuts,all_eight_home_aliases=True,normalized_full_literal_state=True,private_raw_C_and_portable_fault_equivalence_not_claimed=True)
    def test_04_original_submit_helper_and_followup_widths(self):
        count=0;seen=set()
        for seed,owner,outcome,phase in itertools.product(g.SEEDS,(0,g.OWNER),(0,1),(0,8)):
            c=g.Case(seed=seed,owner=owner,outcome=outcome,phase=phase,connected=2);initial=g.fixture(c);expected=g.reference(initial,c);pair=[]
            for w in(self.retail,self.words):
                m=g.Oracle(w,initial,c,connected=g.helper_code(self.rom,c)).run();pair.append(m);seen.update(m.visits)
                self.assertEqual(m.calls[:6],expected['calls']);self.assertEqual(m.payloads,[(expected['pair'],expected['templates'])]);self.assertEqual(m.r[2],expected['result'])
                seed_after=seed
                for _ in range(6 if owner else 5):seed_after=g.next_seed(seed_after)
                self.assertEqual(g.read(m.memory,g.SEED,8),seed_after)
                if owner:
                    a=expected['calls'][-1][1];follow=next(args for target,args in m.calls if target==g.FOLLOWUP);self.assertEqual(follow,(a[5],255,a[7],g.POSITION,255,c.priority&255,g.u32(c.parameter)))
                    factory=next(args for target,args in m.calls if target==g.FACTORY);self.assertEqual(factory[1:6],(0x800A4AA0,0x29,0,0,0x16));self.assertIn(factory[6],(1,3));self.assertEqual(factory[7:],(0,0,48,c.priority&255,g.u32(c.parameter)))
                    if outcome:
                        copied=g.OUTPUT+0x110;self.assertEqual(g.read(m.memory,copied),g.OWNER);self.assertEqual(g.read(m.memory,copied+4,1),initial[g.OWNER+0x3B]);self.assertEqual(g.read(m.memory,copied+8),0);self.assertEqual(g.read(m.memory,copied+12,2),c.duration&65535)
                        self.assertEqual(tuple(g.read(m.memory,copied+24+4*i)for i in range(3)),tuple(g.read(initial,g.TEMPLATE+4*i)for i in range(3)))
                        self.assertEqual(tuple(g.read(m.memory,copied+36+4*i)for i in range(3)),tuple(g.read(initial,g.TEMPLATE+4*i)for i in range(3)))
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.assertTrue(set(range(g.SUBMIT,g.SUBMIT+536,4))<=seen)
        # Actual followup entry saves the forwarded words, calls the literal
        # RNG, then loads angle through LWC1 and position through LW.
        c=g.Case(connected=1);initial=g.fixture(c)
        for i in range(4):g.put(initial,0x80088BD0+4*i,0x12340000+i)
        angle=0x43876543;arguments=(8,255,angle,g.POSITION,255,127,0x87654321);end=g.FOLLOWUP+96
        body=struct.unpack_from('>24I',self.rom,0x130704);code=g.helper_code(self.rom,c);code[end]=0;m=g.Oracle(body,initial,c,entry=g.FOLLOWUP,arguments=arguments,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
        with self.assertRaises(WindowBoundary):m.run()
        self.assertEqual(m.f[2],angle);self.assertEqual(m.r[12],g.POSITION)
        self.receipt('provider',cases_per_body=count,original_submit_words=134,all_submit_words_reached=True,independent_14_argument_and_factory_followup_contracts=True,original_followup_entry_words=24,float_angle_and_position_loads=True,nullable_pointer_result=True,RNG_state_after_sixth_draw=True,allocator_and_followup_remainder_opaque=True)
    def test_05_both_original_callers(self):
        all_words=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);jal=0x0C000000|(match.ENTRY>>2&0x3FFFFFF);self.assertEqual([4*i for i,w in enumerate(all_words)if w==jal],[0x55D74,0x1F283C]);self.assertFalse(any(w in(match.ENTRY,0x08000000|(match.ENTRY>>2&0x3FFFFFF))for w in all_words))
        count=0
        for which,priority,parameter,phase,connected in itertools.product((0,1),(0,127,128,255),(0,0x80000000,0xFFFFFFFF),(0,8),(0,1)):
            c=g.Case(priority=priority,parameter=parameter,phase=phase,connected=connected);pair=[]
            for w in(self.retail,self.words):
                m=g.caller_machine(self.rom,w,c,which);preserved=tuple(m.r[r]for r in(*range(16,24),28,29,30))
                with self.assertRaises(WindowBoundary):m.run()
                a=m.calls[0][1];self.assertEqual(a,(g.OWNER,g.POSITION if which==0 else g.STACK+phase+0xD4,70,priority,1 if which==0 else parameter));expected=g.reference(m.original,replace(m.case,duration=70,parameter=a[4]),home=g.STACK+phase)
                self.assertEqual(m.calls[1:],expected['calls']);self.assertEqual(m.payloads,[(expected['pair'],expected['templates'])]);self.assertEqual(tuple(m.r[r]for r in(*range(16,24),28,29,30)),preserved);pair.append(m)
            self.assertEqual(g.state(pair[0]),g.state(pair[1]));count+=1
        self.receipt('callers',cases_per_body=count,original_call_windows=2,window_words=[7,6],all_five_arguments_verified=True,position_pointer_ownership=True,saved_integer_registers_GP_SP_FP_preserved=True,returns_ignored_by_original_callers=True,full_parents_remain_unqualified=True)
    def test_06_GNU_rebases_and_all_bindings(self):
        links=count=0
        for k,entry in enumerate((match.ENTRY,0x17007FFC,0x1A028000)):
            s=g.symbols()
            if k:s={n:(entry+0x10000*(1+j)if n.startswith('func_')else 0x81007FFC+0x10000*j)for j,n in enumerate(s)}
            images=[]
            for j,original in enumerate((True,False)):
                p=self.out/('match-rebase-%d-%d'%(k,j))
                if original:
                    rows=['.set noreorder','.text','.globl '+match.FUNCTION,match.FUNCTION+':']
                    for i,w in enumerate(self.retail):
                        if 4*i in match.BINDINGS:
                            typ,sym=match.BINDINGS[4*i][0];rows.append('.reloc ., '+typ+', '+sym);w&=0xFC000000 if typ=='R_MIPS_26'else 0xFFFF0000
                        rows.append('.word 0x%08X'%w)
                    asm='\n'.join(rows)+'\n'
                else:
                    t,fs,rs=match.parse_object(self.prepared['qualified_owner']);asm,unknown=emit_function(t,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                blob=sections(p.with_suffix('.elf'))['.text'][1];self.assertEqual(blob[284:],bytes(len(blob)-284));images.append(list(struct.unpack_from('>71I',blob)));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],match.bound_blob(*match.function_blob(self.prepared['qualified_owner']),s))
            for mutation,phase,outcome in itertools.product((0,1,7),(0,8),(0,1)):self.compare(g.Case(mutation=mutation,phase=phase,outcome=outcome),images=images,s=s,entry=entry,include_raw=False);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all_18_bindings=True,signed_low16_carry=True,JAL_region_rebase=True,standalone_zero_tail=True)
    def test_07_SDK_native32_and_controls(self):
        text,controls,count=native.program();p=self.out/'match-native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('match-native'+opt+'.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            (self.out/('match-native'+opt+'-compile.log')).write_text(r.stdout+r.stderr)
            self.assertEqual((r.returncode,bool(r.stdout),bool(r.stderr)),(0,False,False),(opt,(r.stdout+r.stderr)[-2000:]));self.assertEqual(subprocess.run([str(exe)]).returncode,0,opt)
        self.receipt('native',cases_per_profile=count,positive_executions=3*count,total_calls=27*count,controls=controls,checked_mask=255,SDK_native32=True,UBSan=True,independent_Python_rounded_payloads=True,typed_position_and_mixed_width_ABI=True,all_five_provider_calls=True,private_stack_and_nonfinite_hardware_not_claimed=True)
    def test_08_frame_provenance_full_image_and_stub(self):
        trace=json.loads((self.out/'frame-pointer-summary.json').read_text());receipt=json.loads((self.out/'frame-pointer/receipt.json').read_text());self.assertTrue(trace['code_unchanged']);self.assertEqual(receipt['exit_code'],0);self.assertEqual(receipt['baseline']['raw_sha256'],match.RAW_SHA)
        for n,h in receipt['compiler_sha256'].items():self.assertEqual(match.sha((ROOT/'ido/ido5.3_recomp'/n).read_bytes()),h)
        last=trace['events'][-1];self.assertEqual((last['frame'],last['locals'],last['outgoing'],last['saved']),(88,24,56,8));self.assertEqual([r['length']for r in trace['definitions']['frontend']if r['storage']=='M'],[20]);self.assertEqual([r['length']for r in trace['definitions']['optimizer']if r['storage']=='M'],[20])
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);self.assertEqual(delta,411);at=match.elf_slot_offset(before,match.ENTRY,284)
        for off in(0,at,at+283,at+284,0x29D100,len(after)-1):
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        initial=g.fixture();stub=list(struct.unpack_from('>71I',before,at));m=g.Oracle(stub,initial).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        self.receipt('frame-image',frame=88,real_CFE_and_UOPT_M_bytes=20,rounded_locals=24,outgoing=56,saved=8,owned_compiler_trace_completed=True,strict_changed_bytes=delta,exclusions=0,closed_metadata_pair_permutations=6,all_named_attributes_fixed=True,corruptions_rejected=6,stub_rejected=True)
if __name__=='__main__':unittest.main()
