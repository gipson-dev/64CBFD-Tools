"""Signed bend, float helper ABI, closed allocation proof and complete image."""
import itertools,json,math,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_bending_quad_1513f114_candidates as c
from tools.experiments import game_bending_quad_1513f114_match as m
from tools.experiments import game_bending_quad_1513f114_roles as roles
from tools.tests import game_bending_quad_1513f114_oracle as g
from tools.tests.game_bending_quad_1513f114_native import harness,LINK_FLAGS
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

class BendingQuadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=c.ROOT;cls.out=cls.root/c.BUILD;cls.q=m.prepare(cls.root);cls.rom=(cls.root/m.ROM_IMAGE).read_bytes();cls.truth=list(struct.unpack_from('>231I',cls.rom,0x16C5C4));cls.raw,cls.refs=m.function_blob(cls.q['qualified_compacts'][0]);cls.normal,cls.nr=m.derive(cls.raw,cls.refs);cls.words=m.bound_blob(cls.normal,cls.nr,g.symbols());cls.compact=m.bound_blob(cls.raw,cls.refs,g.symbols());cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'target-suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def compare(self,case,initial=None):
        initial=g.fixture(case)if initial is None else initial;e=g.reference(initial,case);machines=[]
        for body in(self.truth,self.words):
            v=g.Oracle(body,initial,case);sr=v.r[:];sf=v.f[:];v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);self.assertEqual(v.r[16:24],sr[16:24]);self.assertEqual((v.r[29],v.r[31]),(sr[29],sr[31]));self.assertEqual(v.f[20:],sf[20:]);machines.append(v)
        self.assertEqual(g.state(machines[0]),g.state(machines[1]));return machines
    def test_01_closed_roles_owner_and_effective_proof_controls(self):
        q=self.q['report'];t=q['targets'][0];self.assertEqual((q['frozen_inputs'],q['functions'],q['strict_changed_bytes'],q['strict_exclusions']),(181,6052,764,0));self.assertEqual((t['words'],t['frame'],t['guards'],t['bindings'],t['raw_neighbors'],t['padded_neighbors']),(231,144,61,15,58,58));self.assertEqual(t['diagnostics'],dict(before=43,after=43,new=[]));self.assertEqual(self.words,self.truth);self.assertEqual(self.nr,self.refs)
        a=list(struct.unpack('>231I',self.raw));b=list(struct.unpack('>231I',self.normal));self.assertEqual(sum(x!=y for x,y in zip(a,b)),61);self.assertEqual(a[:6],b[:6]);self.assertEqual(a[225:],b[225:])
        branch=lambda w:w>>26 in(1,3,4,5,6,7,20,21)or(w>>26==17 and w>>21&31==8)
        self.assertEqual([(i,w)for i,w in enumerate(a)if branch(w)],[(i,w)for i,w in enumerate(b)if branch(w)])
        proof=roles.prove_upper(a[164:212],roles.upper_schedule());self.assertEqual((proof['words'],proof['ordered_stores'],proof['live_FP_outputs']),(48,5,[6,8]));self.assertTrue(proof['no_reassociation'])
        controls={};good=roles.upper_schedule()
        bad=good[:];bad[13]=roles.fp(2,4,10,4);controls['wrong_upper_cos']=bad
        bad=good[:];bad[10],bad[22]=bad[22],bad[10];controls['reordered_output_stores']=bad
        bad=good[:];bad[-3:]=[roles.fp(0,6,10,16),roles.fp(0,8,4,6),good[-1]];controls['reassociated_last_Y']=bad
        bad=good[:];bad[4]=roles.mem(57,8,29,0x8C);controls['escaped_cursor_overwrite']=bad
        bad=good[:];bad[0]=roles.fp(2,20,10,4);controls['callee_saved_FP_overwrite']=bad
        bad=good[:];bad[-4]=roles.mfc(14,0);controls['lost_pending_Y_pointer']=bad
        for name,body in controls.items():
            with self.assertRaises(ValueError,msg=name):roles.prove_upper(a[164:212],body)
        with patch.object(roles,'prove_upper',side_effect=ValueError('proof failed')):
            with self.assertRaises(ValueError):m.derive(self.raw,self.refs)
        for i in range(231):
            bad=bytearray(self.raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):m.derive(bytes(bad),self.refs)
        for at in self.refs:
            refs=dict(self.refs);refs[at]=[('R_MIPS_26','wrong_symbol')]
            with self.assertRaises(ValueError):m.derive(self.raw,refs)
        with self.assertRaises(ValueError):m.guard_manifest(b'changed guard history')
        blob=self.q['qualified_compacts'][0].read_bytes()
        for section in('.reginfo','.options'):
            shape,data=m.dependent_sections(blob)[section];bad=bytearray(blob);bad[shape[4]+len(data)-1]^=1;p=self.out/('bad'+section+'.o');p.write_bytes(bad)
            with self.assertRaises(ValueError):m.pools(self.out/'match-predecessor-0.o',p)
        before,after,installed=c.source_states((self.root/c.TARGETS[0]['source']).read_text());self.assertEqual(c.source_states(after),(before,after,True))
        self.receipts['owner']=q;self.receipts['roles']=dict(proof=proof,effective_symbolic_negatives=list(controls),guarded_words=61,branch_call_frame_and_saved_lifetimes_fixed=True,binding_changes=0)
    def test_02_ordered_model_signed_zero_clamp_and_original_helpers(self):
        seen=set();count=raw_count=0
        for case in g.cases():
            initial=g.fixture(case);e=g.reference(initial,case);seen.update(self.compare(case,initial)[0].visits);count+=1
            if not case.private and case.alias not in(3,4):
                v=g.Oracle(self.compact,initial,case);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(e['observed'],e['calls'],e['value']),case);raw_count+=1
        self.assertTrue(set(range(g.ENTRY,g.ENTRY+924,4))<=seen)
        for entry,at,n in((g.COPY,0x22EC0,11),(g.BACKEND,0x203210,52),(g.COS,0x750B0,88),(g.SIN,0x75210,104)):
            before=self.q['predecessor_elf'].read_bytes();p=m.elf_slot_offset(before,entry,n*4);self.assertEqual(before[p:p+n*4],self.rom[at:at+n*4])
        missing=set(range(g.BACKEND,g.BACKEND+208,4))-seen;self.assertEqual(missing,{g.BACKEND+13*4});self.assertTrue(set(range(g.COPY,g.COPY+44,4))<=seen)
        for address in(g.CLAMP,g.LIMIT):
            p=m.elf_slot_offset(self.q['predecessor_elf'].read_bytes(),address,4);self.assertEqual(self.q['predecessor_elf'].read_bytes()[p:p+4],bytes.fromhex('3fc90fdb'))
        sqrt_words=[i for i,w in enumerate(self.truth)if w>>26==17 and w>>21&31==16 and w&63==4];self.assertEqual(len(sqrt_words),2)
        for x,expected in((11.5,{sqrt_words[0]}),(9.5,{sqrt_words[1]})):
            case=g.Case(targetX=g.bits(x),targetZ=g.bits(3.75),bend=g.bits(1));v=self.compare(case)[0];self.assertEqual({i for i in sqrt_words if g.ENTRY+i*4 in v.visits},expected)
        edge_cases=[]
        for gain,expected in((g.bits(1),0),(g.bits(-1),0x80000000)):
            case=g.Case(targetX=g.bits(10.5),targetZ=g.bits(3.75),bend=0x80000000,gain=gain);v=self.compare(case)[0];self.assertEqual(next(a[0]for t,a in v.calls if t==g.SIN),expected);edge_cases.append(expected)
        for gain,x,expected in((0x3FC90FDA,11.5,0xBFC90FDA),(0x3FC90FDB,11.5,0xBFC90FDB),(0x3FC90FDC,11.5,0xBFC90FDB),(0x3FC90FDC,9.5,0x3FC90FDB)):
            case=g.Case(gain=gain,targetX=g.bits(x),targetZ=g.bits(3.75),bend=g.bits(1));v=self.compare(case)[0];self.assertEqual(next(a[0]for t,a in v.calls if t==g.SIN),expected)
        case=g.Case(success=0);initial=g.fixture(case);initial={p:v for p,v in initial.items()if g.STACK-2048<=p<g.STACK+512};self.compare(case,initial)
        self.receipts['guest']=dict(cases_per_body=count+1,raw_valid_object_cases=raw_count,all_target_words_executed=231,normalized_retail_full_private_identity=True,original_copy_backend_words_compared=63,helper_words_executed=62,unreachable_nonnull_fresh_fallback_words=1,original_cos_sin_words_compared=192,trig_helpers_already_exact=True,trig_execution_bounded=True,both_sqrt_arms_and_likely_annul=True,signed_zero_argument_words=edge_cases,adjacent_clamp_boundaries=True,private_spill_aliases_modeled=True,canonical_nan_contract_only=True,FCSR_and_payload_not_emulated=True)
    def test_03_original_renderer_slot_three_and_FP_return_ABI(self):
        jal=0x0C000000|((g.ENTRY>>2)&0x3FFFFFF);direct=[];pointers=[]
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.rom)):
            if word==jal:direct.append(i*4)
            if g.ENTRY<=word<g.ENTRY+924:pointers.append((i*4,word))
        self.assertEqual((direct,pointers),([] ,[(0x22E8E8,g.ENTRY)]));self.assertEqual(struct.unpack_from('>I',self.rom,0x22E978)[0],0xE7000000)
        caller=list(struct.unpack_from('>295I',self.rom,0x16AFB0));seen=set();count=target_calls=0
        configs=[(*r,255,1)for r in itertools.product((0,8,0x1000000,0xC000,0x20000000,0x7FFFFFE0),(0,1),(0,1),(0,1),(0,255),(0,1,2))];configs.extend((8,1,1,1,255,0,0,b)for b in(0,1))
        for flags,enabled,view,success,animation,attached,visible,buffer in configs:
            case=g.Case(view=view,success=success,mutation=3,redirect=1);initial=g.caller_fixture(case,flags,enabled,visible,attached,animation)
            if not buffer:g.wr(initial,g.slot(case),0,4)
            reference=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),reference_leaf=True);reference.run();machines=[]
            for body in(self.truth,self.words,self.compact):
                code=dict(zip(range(g.ENTRY,g.ENTRY+924,4),body));v=g.Oracle(caller,initial,case,entry=g.CALLER,arguments=(g.GFX,g.ACTOR,g.u32(case.view)),connected=code);v.run();self.assertEqual((g.public(v.memory,case),v.calls,v.r[2]),(g.public(reference.memory,case),reference.calls,reference.r[2]));machines.append(v)
            self.assertEqual(g.state(machines[0]),g.state(machines[1]));seen.update(machines[0].visits);target_calls+=sum(t==g.ENTRY for t,a in machines[0].calls);count+=1
        missing={i for i in range(295)if g.CALLER+i*4 not in seen};self.assertEqual(missing,{115,146});self.assertGreater(target_calls,0)
        for branch in(111,142):self.assertEqual((caller[branch]>>26,caller[branch+2]>>26,caller[branch]&65535,caller[branch+2]&65535),(1,4,4,2))
        self.receipts['caller']=dict(cases_per_body=count,bodies=3,actual_target_calls_per_body=target_calls,renderer_words_compared=295,renderer_words_executed=293,unreachable_duplicate_defaults=sorted(missing),actual_table_prefix_entries=39,slot=3,actor_s16_view_pointer_return_ABI=True,F12_arguments_F0_returns_and_F20_preserved=True,independent_leaf_counterpart=True,other_renderer_services_bounded=True,production_renderer_still_stub=True)
    def test_04_access_prefixes_lifetimes_and_raw_counterexample(self):
        cuts=delays=0
        for case in(g.Case(success=0),g.Case(fresh=0),g.Case(targetX=g.bits(11.5),bend=g.bits(1)),g.Case(private=2),g.Case(private=3),g.Case(alias=3),g.Case(alias=4),g.Case(mutation=7,redirect=1),g.Case(connected=5)):
            initial=g.fixture(case);full=g.Oracle(self.truth,initial,case);full.run()
            for cut in range(full.all_accesses):
                machines=[]
                for body in(self.truth,self.words):
                    v=g.Oracle(body,initial,case);v.cut=cut
                    with self.assertRaises(AccessBoundary):v.run()
                    machines.append(v)
                self.assertEqual(g.state(machines[0]),g.state(machines[1]));cuts+=1;delays+=machines[0].delay_of is not None
        case=g.Case();initial=g.fixture(case);v=g.Oracle(self.truth,initial,case);v.run();cut=next(i+1 for i,row in enumerate(v.trace)if row[:3]==('W',g.STACK-144+0x40,4));different=[]
        for body in(self.truth,self.compact):
            v=g.Oracle(body,initial,case);v.cut=cut
            with self.assertRaises(AccessBoundary):v.run()
            different.append(v)
        self.assertNotEqual(g.state(different[0]),g.state(different[1]))
        self.receipts['faults']=dict(fired_cuts=cuts,delay_cuts=delays,full_memory_register_PC_delay_and_access_prefixes=True,frame=144,S0_RA_F20_pair_lifetimes=True,math_call_homes_and_escaped_fields=True,original_copy_backend_prefixes=True,effective_raw_private_prefix_counterexample=True,raw_fault_identity_not_claimed=True)
    def test_05_native32_typed_float_helpers_and_effective_controls(self):
        def run(label,body,opt):
            path=self.out/(label+'.c');path.write_text(harness(body));exe=path.with_suffix('.elf');p=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(path.relative_to(self.root)),*LINK_FLAGS,'-o',str(exe.relative_to(self.root))],cwd=self.root,capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout+p.stderr,'');return subprocess.run([str(exe)],timeout=20).returncode
        for opt in('-O0','-O2','-O3'):self.assertEqual(run('native'+opt,None,opt),0,opt)
        s=c.SELECTED;clamp='        if (D_800A51BC < angle) {\n            angle = D_800A51C0;\n        }\n';self.assertIn(clamp,s)
        wrong_clamp=s.replace(clamp,'').replace('        angle *= directionSign;','        angle *= directionSign;\n'+clamp.rstrip())
        copy_cached=s.replace('            memcpy(*(u8 **)(actor + 0x100 + view * 4),','            u8 *copyBuffer = *(u8 **)(actor + 0x100 + view * 4);\n            memcpy(copyBuffer,',1).replace('memcpy(*(u8 **)(actor + 0x100 + view * 4) + 0x40,','memcpy(copyBuffer + 0x40,')
        lost_cursor=s.replace('    f32 side,','    Vtx *snapshot;\n    f32 side,',1).replace('        scratch.first = scratch.cursor;','        scratch.first = scratch.cursor;\n        snapshot = scratch.cursor;').replace('scratch.cursor[','snapshot[')
        variants=dict(stub=s[:s.index('{')+1]+'\nreturn NULL;\n}',wrong_sign=s.replace('directionSign = -1.0f;','directionSign = 1.0f;'),missing_abs=s.replace('bend = -bend;','bend = bend;'),clamp_after_sign=wrong_clamp,wrong_gain=s.replace('sqrtf(bend) * *(f32 *)(actor + 0x4C)','sqrtf(bend) * *(f32 *)(actor + 0x50)'),cached_copy_destination=copy_cached,reloaded_forward_global=s.replace('forward = scratch.savedForward;','forward = D_800DD1D8[view];'),missing_flags=s.replace('scratch.cursor[3].v.flag = 0;',''),lost_live_cursor=lost_cursor,wrong_return=s.replace('return scratch.first;','return scratch.cursor;'))
        rejected={}
        for label,body in variants.items():self.assertNotEqual(body,s,label);answer=run('negative-'+label,body,'-O2');self.assertEqual(answer,1,label);rejected[label]=answer
        self.receipts['native']=dict(optimizations=3,cases_per_executable=len(g.native_cases()),SDK_Vtx16_pointer32_typed_callback_slot3=True,typed_sqrt_and_float_math_returns=True,trace_checks_float_argument_bits=True,escaped_saved_forward_first_and_cursor_mutations=True,finite_casts_only=True,UBSan_and_round_to_nearest_no_FTZ_DAZ=True,semantic_negatives=rejected,private_homes_aliases_and_exceptional_casts_guest_only=True,trig_functions_bounded=True)
    def test_06_independent_GNU_links_all_fifteen_bindings(self):
        from tools.experiments.game_remaining_donor_candidates import sections
        moved=dict(func_151D5D60=0x17508010,memcpy=0x10431000,sinf=0x17518000,cosf=0x17519000,D_800DD1D8=0x81238000,D_800DD1E8=0x81237FF8,D_800BE9A8=0x8133FFF8,D_800A51BC=0x81438000,D_800A51C0=0x81447FFC)
        for i,(entry,symbols)in enumerate(((g.ENTRY,g.symbols()),(0x17407F50,moved))):
            lines=['.set noreorder','.set noat','.text','.globl func_1513F114','func_1513F114:']
            for j,(word,)in enumerate(struct.iter_unpack('>I',self.normal)):
                refs=self.nr.get(j*4,[])
                if not refs:line='.word 0x%08X'%word
                else:
                    self.assertEqual(len(refs),1);kind,name=refs[0];rt,rs=word>>16&31,word>>21&31
                    if kind=='R_MIPS_26':line='jal '+name
                    elif kind=='R_MIPS_HI16':line='lui $%d, %%hi(%s)'%(rt,name)
                    else:self.assertEqual(word>>26,49);line='lwc1 $f%d, %%lo(%s)($%d)'%(rt,name,rs)
                lines.append(line)
            p=self.out/('rebase-'+str(i));p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),*['--defsym=%s=0x%X'%(n,v)for n,v in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True);self.assertEqual(list(struct.unpack_from('>231I',sections(p.with_suffix('.elf'))['.text'][1])),m.bound_blob(self.normal,self.nr,symbols))
        self.receipts['relocations']=dict(independent_links=2,bindings=15,calls=5,global_HI_LO_pairs=5,signed_LO_carry=True,binding_changes=0,guarded_LO_word_retains_binding=True)
    def test_07_literal_image_named_metadata_and_corruptions(self):
        before=self.q['predecessor_elf'].read_bytes();after=self.q['qualified_elf'].read_bytes();self.assertEqual(m.strict_image(before,after,self.rom),764);slot=[p for p,n,f,s in m.symbol_rows(before)if n=='func_1513F114'];self.assertEqual(len(slot),1)
        self.assertEqual(m.METADATA_GROUPS,((2759516,('func_150EC45C','D_8009D900'),(1,0)),(2850188,('D_800A51BC','D_8009CDEC'),(1,0)),(2852908,('D_800A51C0','D_8009CDF0','D_800A9DF0'),(1,2,0))))
        aa=m.dependent_sections(before);bb=m.dependent_sections(after);changes={n:sum(x!=y for x,y in zip(d,bb[n][1]))for n,(s,d)in aa.items()if d!=bb[n][1]};self.assertEqual(changes,{'.game':687,'.symtab':38,'.strtab':39})
        for offset in(64,m.elf_slot_offset(before,g.ENTRY,924),slot[0]+8,2759520,2850193,2852913,3046271,3120372,3122698):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):m.strict_image(before,bytes(bad),self.rom)
        self.receipts['image']=dict(changed_bytes=764,exclusions=0,body_bytes=687,symbol_bytes=38,string_bytes=39,complete_named_metadata_permutations=3,named_definitions_fixed_except_target_size=True,corruptions_rejected=9)

if __name__=='__main__':unittest.main()
