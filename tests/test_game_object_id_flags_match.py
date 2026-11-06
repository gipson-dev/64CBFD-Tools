"""Closed five-word schedule, unsigned IDs, table priority and exact images."""
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_object_id_flags_candidates as candidate
from tools.experiments import game_object_id_flags_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_object_id_flags_oracle as model
from tools.tests import game_object_id_flags_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations

def reachable(words):
    pending=[0];seen=set()
    while pending:
        at=pending.pop()
        if at in seen:continue
        assert 0<=at<len(words)*4
        seen.add(at);w=words[at//4];op=w>>26
        if op==0 and w&63==8:
            assert w>>21&31==31;seen.add(at+4)
        elif op in(4,5,20,21):
            seen.add(at+4);pending.extend((at+8,at+4+4*(((w&65535)^32768)-32768)))
        else:pending.append(at+4)
    return seen

class ObjectIDFlagsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>71I',cls.rom,match.ROM))
        cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True);cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('OriginalObjectIDFlags',(),dict(root=ROOT,out=cls.out));cls.original=ViewListSetupTests.original.__func__(ctx,'original-id-flags',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.fitted==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c=model.Case(),s=None,entry=match.ENTRY,images=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s);expected,trace=model.reference(initial,c,s);ms=[]
        for words in(self.retail,self.raw,self.fitted,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry).run()
            self.assertEqual(model.public(m.memory),model.public(expected),c);self.assertEqual(m.trace,trace,c);self.assertFalse(m.calls)
            for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            ms.append(m)
        # Raw C's opening address registers differ on the state rejection path.
        for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_owner_guards_and_fail_closed_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings'],q['raw_neighbors'],q['neighbors'],q['caller_functions_unchanged']),(71,0,5,12,4,4,89))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+284]
        for at in range(284):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_LO16','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old);self.assertTrue(new.startswith(old));rows=list(csv.DictReader(io.StringIO(new.decode())))
        self.assertEqual(len([r for r in rows if r['function']==match.FUNCTION]),5)
        for offset,*_ in match.PATCHES:
            for field in('expected','expected_relocations'):
                bad=[dict(r)for r in rows];row=next(r for r in bad if r['function']==match.FUNCTION and int(r['offset'],0)==offset);row[field]='0x0'if field=='expected'else'R_MIPS_HI16:foreign';out=io.StringIO(newline='');writer=csv.DictWriter(out,bad[0].keys());writer.writeheader();writer.writerows(bad)
                with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],out.getvalue().encode(),'bad-%d-%s'%(offset,field))
        self.receipt('owner-controls',raw_corruptions=284,binding_corruptions=12,guard_corruptions=10,closed_schedule_words=5,raw_and_padded_neighbors=4,caller_functions_unchanged=89,compact_T5_mask_added=True,padded_pools_unchanged=True)
    def test_02_unsigned_priority_all_entries_and_reachable_words(self):
        seen=set();count=0
        for c in model.cases():
            ms=self.compare(c);seen.update(p-match.ENTRY for p in ms[0].visits);count+=1
        live=reachable(self.retail);self.assertEqual(live,set(range(0,284,4))-{180,208,236});self.assertEqual(seen,live)
        self.receipt('guest-contract',cases_per_body=count,bodies=4,reachable_words=68,unreachable_words=[180,208,236],all_71_words_preserved=True,all_88_lower_entries=True,all_3_primary_entries=True,actual_E9_primary_priority=True,synthetic_unsigned_and_singleton_second_path=True,ordered_memory=True,raw_private_equality_claimed=False)
    def test_03_aliases_sparse_gates_and_fault_prefixes(self):
        aliases=cuts=sparse=0;s=model.symbols()
        for owner in(s['D_80098780']+3-0x2FB,s['D_80098830']+3-0x2FB,s['D_80098780']-0x84,s['D_80098830']-0x84):
            self.assertEqual(owner%4,0)
            for identity in(233,model.table()[2],0xFFFF):self.compare(model.Case(identity=identity,owner=owner));aliases+=1
        for c in[model.Case(v,dataset=d)for d in(0,1)for v in(model.table(d)[90],model.table(d)[0],model.table(d)[1],*model.table(d)[2:6],model.table(d)[89],0)]:
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.fitted,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                self.assertEqual((model.public(ms[0].memory),ms[0].trace),(model.public(ms[1].memory),ms[1].trace));cuts+=1
        for c in(model.Case(state=0),model.Case(state=0xFFFFFFFF)):
            initial={};model.put(initial,c.owner,c.state)
            for words in(self.retail,self.raw,self.fitted,self.words):
                m=model.Oracle(words,initial,c).run();self.assertEqual(m.trace,[('R',c.owner,4,c.state)]);self.assertEqual(m.memory,initial)
            sparse+=1
        for identity in(0,0xFFFF):
            c=model.Case(identity);initial=model.fixture(c)
            for p in range(s['D_80098836'],s['D_80098836']+18):initial.pop(p,None)
            for words in(self.retail,self.raw,self.fitted,self.words):
                m=model.Oracle(words,initial,c).run();self.assertEqual(m.memory,initial)
            sparse+=1
        for owner in(0,0x30001):
            c=model.Case(owner=owner);initial={}if owner==0 else model.fixture(c);ms=[]
            for words in(self.retail,self.fitted,self.words):
                m=model.Oracle(words,initial,c)
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            sparse+=1
        self.receipt('aliases-faults',alias_cases=aliases,fired_prefixes=cuts,sparse_cases=sparse,no_null_guard=True,sentinel_unread=True,guest_only_invalid_accesses=True)
    def test_04_complete_original_caller_and_null_child_consumer(self):
        body=list(struct.unpack_from('>11I',self.rom,0x8FC84));consumer=dict(zip(range(model.CONSUMER,model.CONSUMER+520,4),struct.unpack_from('>130I',self.rom,0x67178)));count=0;seen=set()
        # VA/ROM translation checked independently of a retained standalone ASM.
        self.assertEqual(consumer[model.CONSUMER],0x8C820324);self.assertEqual(consumer[model.CONSUMER+512],0x03E00008)
        for c in[model.Case(v,f,state,d,phase=phase,effect=effect)for v,f,state,d,phase,effect in itertools.product((0,72,233,0x8001),(0,255),(0,1),(0,1),(0,8),(0,4))]:
            for connected in(False,True):
                initial=model.fixture(c);initial[c.owner+0x2FB]=0;expected,_=model.reference(initial,c);flag=expected[c.owner+0x2FB]
                if not connected:
                    expected[c.owner+0x2FB]|=c.effect
                    if c.effect:model.put(expected,c.owner+0x84,0xBEEF,2)
                ms=[]
                # The actual wrapper clears flags before both calls.
                initial=model.fixture(c)
                for words in(self.retail,self.raw,self.fitted,self.words):
                    code=dict(zip(range(match.ENTRY,match.ENTRY+284,4),words))
                    if connected:code.update(consumer)
                    m=model.Oracle(body,initial,c,entry=model.CALLER,connected=code).run();self.assertEqual(model.public(m.memory),model.public(expected));self.assertEqual(m.calls,[(match.ENTRY,(c.owner,)),(model.CONSUMER,(c.owner,))]);self.assertEqual(m.observations,[(c.owner,flag)]);ms.append(m)
                    for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                for m in ms[2:]:self.assertEqual(state(ms[0]),state(m))
                if connected:seen.update(ms[0].visits)
                count+=1
        self.assertTrue(set(range(model.CALLER,model.CALLER+44,4))<=seen)
        self.assertTrue({model.CONSUMER,model.CONSUMER+4,model.CONSUMER+8,model.CONSUMER+512,model.CONSUMER+516}<=seen)
        self.receipt('caller-controls',cases_per_body=count,bodies=4,complete_caller_words=11,original_consumer_null_gate_words=5,opaque_effects_preserved=True,whole_consumer_claimed=False)
    def test_05_independent_GNU_rebases_with_contiguous_aliases(self):
        links=count=0
        for i,(entry,base)in enumerate(((match.ENTRY,0x81007F78),(0x18018000,0x8200FFF8),(0x1A02FFFC,0x83017FF0))):
            s=model.symbols(base);images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);f=fs[match.FUNCTION]
                if j==2:
                    raw,bindings=match.function_blob(obj);text=bytearray(text);text[f['value']:f['value']+284]=match.normalized(raw,bindings,self.rom[match.ROM:match.ROM+284]);rs={at:r for at,r in rs.items()if not f['value']<=at<f['value']+284};rs.update({f['value']+at:r for at,r in match.fitted_bindings().items()})
                asm,unknown=emit_function(text,f,rs,match.FUNCTION,s);self.assertFalse(unknown);p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>71I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2]);self.assertEqual(images[0],images[3]);self.assertEqual(images[1],model.bound(self.prepared['qualified_compact'],s));self.assertEqual(images[0],model.bound(self.original,s))
            for c in list(model.cases())[::19]:self.compare(c,s=s,entry=entry,images=images);count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,HI_LO_carries=True,lower_plus_176_alias=True,contiguous_188_byte_table_preserved=True)
    def test_06_effective_IDO_and_native_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            self.assertNotEqual(body,candidate.SELECTED,name);text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,diag=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);self.assertFalse(diag);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected,trace=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c).run();fired=m.trace!=trace or model.public(m.memory)!=model.public(expected)
                except(AssertionError,KeyError,IndexError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native.source(body));exe=p.with_suffix('.elf');r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',exhaustive_IDs=65536,flag_samples=8,all_256_flags_for_wrong_states=True,datasets=2,root_executions_per_profile=1061888,wrapper_executions_per_profile=512,positive_executions=3187200,profiles=['O0','O2','O3'],IDO_controls=effective,native_controls=len(effective),UBSan=True,canonical_struct127_ABI=True)
    def test_07_literal_image_metadata_corruption_and_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+284];delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,284)
        offsets=(0,at,at+283,at+284,len(after)-1,*[p+4 for p,n,o in match.SYMBOL_GROUPS],*[next(s for p,n,f,s in match.symbol_rows(after)if n==names[0])for off,names,order in match.SYMBOL_GROUPS])
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>71I',before,match.elf_slot_offset(before,match.ENTRY,284)));initial=model.fixture();m=model.Oracle(stub,initial).run();expected,_=model.reference(initial);self.assertNotEqual(model.public(m.memory),model.public(expected))
        self.receipt('image-controls',literal_changed_bytes=delta,metadata_bytes=161,closed_symbol_groups=6,exclusions=0,corruptions=len(offsets),old_stub_rejected=True)
if __name__=='__main__':unittest.main()
