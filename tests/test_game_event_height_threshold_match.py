"""Guarded height threshold: semantic C, scheduling origins and literal image."""
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_event_height_threshold_candidates as candidate
from tools.experiments import game_event_height_threshold_match as match
from tools.tests import game_event_height_threshold_oracle as g
from tools.tests import game_event_height_threshold_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
def state(m):return complete(m),m.current_pc,m.delay_of,m.root_accesses,m.trace
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x150A2778:raise WindowStop
        return super().__getitem__(pc)
class EventHeightThresholdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280];cls.retail=list(struct.unpack('>70I',cls.truth))
        ctx=type('OriginalHeight',(),dict(root=ROOT,out=cls.out));original=view_setup.ViewListSetupTests.original.__func__(ctx,'height-original',(ROOT/match.ASM).read_text(),match.FUNCTION)
        cls.blobs=[match.function_blob(o)for o in(original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])];cls.images=[match.bound_blob(b,r,match.symbols())for b,r in cls.blobs];assert cls.images[0]==cls.retail==cls.images[2];cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'height-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def receipt(self,key,**v):self.receipts[key]=v
    def compare(self,c,images=None,s=g.SYMS,connected=None):
        initial=g.fixture(c);models=[]
        for i,words in enumerate(images or self.images):
            m=g.Oracle(words,initial,c,entry=g.RAW_ENTRY if i==1 else match.ENTRY,s=s,connected=connected);before=m.r[:];f=m.f[:];want,calls,reads=g.reference(initial,c,ra=before[31],s=s,connected=connected is not None);m.run()
            self.assertEqual(m.memory,want,c);self.assertEqual(m.calls,calls,c);self.assertEqual(g.table_reads(m),reads,c)
            self.assertTrue(all(m.r[r]==before[r]for r in(*range(16,24),26,27,28,29,30,31)));self.assertEqual(m.f[20:],f[20:]);models.append(m)
        self.assertEqual(state(models[0]),state(models[2]));self.assertEqual(models[0].trace,models[1].trace,c);return models
    def test_01_body_origins_guard_history_and_owner(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['omissions'],q['raw_neighbors'],q['neighbors']),(72,70,80,18,2,51,51));self.assertTrue(q['compact_pools_and_metadata_unchanged'])
        raw,b=self.blobs[1];normal,nb,rows,ledger=match.scheduling(raw,b);match.checked(normal,nb,self.truth,True);self.assertEqual(normal,self.blobs[2][0]);self.assertEqual(nb,match.BINDINGS);self.assertEqual(len(ledger),70)
        for at in range(288):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.scheduling(bytes(bad),b)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.scheduling(raw,bad)
        baseline=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertEqual(proposed,match.proposed_guards(baseline,rows));self.assertTrue(proposed.startswith(baseline))
        fields=list(csv.DictReader(proposed.decode().splitlines()).fieldnames)
        for index in range(18):
            altered=[dict(v)for v in rows];altered[index]['expected']='0x%08X'%(int(altered[index]['expected'],0)^1);s=io.StringIO();writer=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(altered);p=self.out/'height-stale-guards.csv';p.write_text(s.getvalue())
            with self.assertRaisesRegex(ValueError,'stale word patch'):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        for omitted in(39,65):
            altered=[dict(v)for v in rows];next(v for v in altered if int(v['offset'],0)==omitted*4)['omit']='false';s=io.StringIO();writer=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(altered);p=self.out/'height-missing-omission.csv';p.write_text(s.getvalue())
            with self.assertRaisesRegex(ValueError,'retail span'):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        self.receipt('owner',raw_words=72,normalized_words=70,guards=18,omissions=2,raw_corruptions=288,binding_corruptions=4,stale_guards_rejected=18,missing_omissions_rejected=2,raw_padded_neighbors=51,all_pools_and_metadata_unchanged=True,preexisting_guard_bytes_preserved=True,existing_warnings=8)
    def test_02_semantic_memory_signed_bytes_and_ordered_floats(self):
        seen=[set(),set(),set()];count=0
        for c in g.cases():
            for i,m in enumerate(self.compare(c)):seen[i].update(m.visits)
            count+=1
        self.assertTrue(set(range(match.ENTRY,match.ENTRY+280,4))-{match.ENTRY+45*4}<=seen[0]);self.assertNotIn(match.ENTRY+45*4,seen[0]);self.assertTrue(set(range(g.RAW_ENTRY,g.RAW_ENTRY+288,4))-{g.RAW_ENTRY+46*4}<=seen[1])
        self.receipt('guest',cases_per_body=count,bodies=3,all69_reachable_retail_words=True,unreachable_word_literal_pinned=True,all256_values_of_four_byte_fields=True,raw_separate_entry=hex(g.RAW_ENTRY),raw_original_normalized_complete_memory_calls_and_access_sequence=True,raw_full_register_PC_parity_claim=False,original_normalized_complete_state_equal=True,NaN_infinity_signed_zero_subnormal_overflow=True,live_owner_and_actor_home_mutations=True)
    def test_03_literal_fault_prefixes_and_return_epilogue(self):
        count=0
        cases=[g.Case(found=False),g.Case(count=0),g.Case(count=128),g.Case(),g.Case(limit=0),g.Case(flags=0),g.Case(flags=0,limit=0x7f800000),g.Case(flags=0,y=0x7fc12345),g.Case(mutation=7),g.Case(mutation=16),g.Case(phase=8,flags=0)]
        for c in cases:
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for image in(self.images[0],self.images[2]):
                    m=g.Oracle(image,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('faults',own_access_prefixes=count,original_normalized_complete_state_equal=True,raw_full_fault_parity_claim=False,shared_RA_epilogue_both_float_outcomes=True,lookup_null_and_nonpositive_count_and_mutated_homes=True)
    def test_04_original_lookup_and_position_helpers(self):
        code=g.helper_code(self.rom);count=0;seen=set()
        for byte in range(256):
            c=g.Case(actor_id=byte,found=True,flags=8 if byte&1 else 0,count=1,column=byte%104,lookup_phase=byte&1,context=(0,0x12345678,0x80000000,0xffffffff)[byte%4],y=g.FLOAT_CASES[byte%12][0],limit=g.FLOAT_CASES[byte%12][2],radius_half=(0,-1,32767,-32768)[byte%4],height_half=(1,32767,-32768,-1)[byte%4],offset_half=(0,-1,32767,-32768)[byte%4],previous=0 if byte&2 else 1,fallback=byte,current=byte)
            for m in self.compare(c,connected=code):seen.update(m.visits)
            count+=1
        for column,phase in itertools.product((0,103),(0,1)):
            self.compare(g.Case(found=False,column=column,lookup_phase=phase),connected=code);count+=1
        self.receipt('helpers',cases_per_body=count,original_lookup_words=39,original_position_words=41,helper_words_reached=len(set(code)&seen),all256_actor_ids=True,columns_0_to103_and_both_lookup_phases=True,signed_half_extremes=True,wrong_kind_and_context_nodes=True,independent_complete_memory_reference=True,whole_helper_path_and_FCSR_hardware_claim=False,dispatch_provider_bounded=True)
    def test_05_original_three_word_caller_window(self):
        window=list(struct.unpack_from('>3I',self.rom,0xcfc1c));count=0
        for found,flags,values,mutation,phase in itertools.product((False,True),(0,8),g.FLOAT_CASES[:4],(0,7),(0,8)):
            y,height,limit=values;c=g.Case(found=found,flags=flags,y=y,height=height,limit=limit,mutation=mutation,phase=phase);initial=g.fixture(c);want,calls,reads=g.reference(initial,c,ra=0x150a2778);models=[]
            for words in(self.images[0],self.images[2]):
                code=dict(zip(range(match.ENTRY,match.ENTRY+280,4),words));code[0x150a2778]=0;m=g.Oracle(window,initial,c,entry=0x150a276c,connected=code,arguments=(0,0,0,0));m.r[16]=g.EVENT;m.r[17]=c.actor;m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(m.memory,want);self.assertEqual(m.calls,[(match.ENTRY,(c.actor,g.EVENT)),*calls]);self.assertEqual(g.table_reads(m),reads);self.assertEqual((m.r[16],m.r[17],m.r[31]),(g.EVENT,c.actor,0x150a2778));models.append(m)
            self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('caller',cases_per_body=count,original_window_words=3,actor_S1_event_S0_explicit_preconditions=True,literal_original_normalized=True,full_parent_and_raw_literal_window_claim=False)
    def test_06_independent_GNU_links_and_rebases(self):
        count=links=0
        for i,base in enumerate((0x10004000,0x15018000,0x1fff0000)):
            syms=dict(func_151CE634=base,func_1515C1A0=base+0x40,func_1505D024=base+0x80);images=[]
            for j,(raw,b)in enumerate(self.blobs):
                entry=g.RAW_ENTRY if j==1 else match.ENTRY;n=len(raw);p=self.out/('height-rebase-%d-%d'%(i,j));s=p.with_suffix('.s');o=p.with_suffix('.o');elf=p.with_suffix('.elf');ld=p.with_suffix('.ld');asm,missing=emit_function(raw,dict(value=0,size=n),b,match.FUNCTION,syms);self.assertFalse(missing);s.write_text(asm)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(o),str(s)],check=True,capture_output=True);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(name,a)for name,a in syms.items()],'-o',str(elf),str(o)],check=True,capture_output=True)
                text=sections(elf)['.text'][1];w=list(struct.unpack('>%dI'%(n//4),text[:n]));self.assertEqual(w,match.bound_blob(raw,b,syms));rows=[f for _,name,f,_ in match.symbol_rows(elf.read_bytes())if name==match.FUNCTION];self.assertEqual(len(rows),1);self.assertEqual(rows[0][1:3],(entry,n));self.assertEqual(text[n:],bytes((-n)%16));images.append(w);links+=1
            for flags,limit,mutation in itertools.product((0,8),(0,0x7fc12345),(0,7)):
                self.compare(g.Case(flags=flags,limit=limit,mutation=mutation),images,s=syms);count+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=count,all4_R26_bindings=True,raw_nonoverlapping_entry_and_288_byte_extent=True,normalized_280_byte_extent_and_alignment_tails_pinned=True)
    def test_07_native32_SDK_backing_and_controls(self):
        checks=[]
        for label,b,opt in[('selected',None,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in native.controls().items()]:
            p=self.out/('height-native-'+label+opt);s=p.with_suffix('.c');s.write_text(native.program(b));cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(s.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt));run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected'else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=98304,SDK32_UBSan=True,all256_values_four_byte_fields=True,all_used_offsets_asserted=True,negative_indices_backed_by_complete_array=True,post_query_mutations_and_ordered_NaNs=True,null_actor_with_missing_lookup=True,complete_objects_tables_and_guards=True,direct_compatible_callback=True,controls_rejected=10,checks=checks)
    def test_08_literal_image_and_nonsemantic_changes_rejected(self):
        q=self.prepared['report'];self.assertEqual((q['strict_changed_bytes'],q['strict_exclusions'],q['functions']),(216,0,6052));before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),216)
        for at in(0,0x100,match.elf_slot_offset(after,match.ENTRY,280),len(after)//2,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        bs,ns,_=candidate.source_states((ROOT/match.SOURCE).read_text());old,od=candidate.compile_owner(ROOT,self.out,bs,'height-former-stub')
        with self.assertRaises(ValueError):match.scheduling(*match.function_blob(old))
        wrong,d=candidate.compile_owner(ROOT,self.out,ns.replace('command = 0x60019','command = 0x60018'),'height-wrong-command');self.assertEqual(match.diagnostic(d),match.diagnostic(od))
        with self.assertRaises(ValueError):match.scheduling(*match.function_blob(wrong))
        self.receipt('image',changed_bytes=216,exclusions=0,all6052_addresses_fixed=True,protected_bytes=189088,protected_owners=720,image_corruptions=5,former_stub_and_wrong_command_rejected=True,Make_and_conversion_CSV_unchanged=True,only18_new_guard_rows=True)
if __name__=='__main__':unittest.main()
