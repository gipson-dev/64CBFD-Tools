"""Spatial query, retained float ABI and explicit dependent-helper qualification."""
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_actor_type_query_candidates as candidate
from tools.experiments import game_actor_type_query_match as match
from tools.tests import game_actor_type_query_oracle as g
from tools.tests import game_actor_type_query_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT
class WindowStop(Exception):pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.stop:raise WindowStop
        return super().__getitem__(pc)
class ActorTypeQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+284]
        ctx=type('OriginalActorQuery',(),dict(root=ROOT,out=cls.out));original=view_setup.ViewListSetupTests.original.__func__(ctx,'query-original',(ROOT/match.ASM).read_text(),match.FUNCTION)
        cls.blobs=[match.function_blob(p)for p in(original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])];cls.images=[match.bound_blob(b,r,match.symbols())for b,r in cls.blobs];assert cls.images[0]==cls.images[2]==list(struct.unpack('>68I',cls.truth[:272]));cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'query-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def receipt(self,key,**v):self.receipts[key]=v
    def compare(self,c,images=None,s=None,connected=None):
        initial=g.fixture(c,s);models=[]
        for words in images or self.images:
            m=g.Oracle(words,initial,c,s=s,connected=connected);before=m.r[:];f=m.f[:];want,calls,value=g.reference(initial,c,before,f,s,connected is not None);m.run();self.assertEqual(m.memory,want,c);self.assertEqual(m.calls,calls,c);self.assertEqual(m.r[2],value,c);models.append(m)
        self.assertEqual(g.state(models[0]),g.state(models[2]));self.assertEqual(g.external(models[0].events),g.external(models[1].events),c);return models
    def test_01_body_origins_relocations_and_stale_guards(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['slot_words'],q['alignment_words'],q['frame'],q['guards'],q['neighbors']),(68,71,3,80,11,2));self.assertEqual(q['helper_new_matching_credit'],0)
        raw,b=self.blobs[1];normal,nb,rows,ledger=match.scheduling(raw,b);self.assertEqual(normal,self.blobs[2][0]);self.assertEqual(sorted(v['source']for v in ledger),list(range(68)))
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.scheduling(bytes(bad),b)
        for at in b:
            bad=dict(b);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.scheduling(raw,bad)
        before=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes();self.assertTrue(proposed.startswith(before));self.assertEqual(proposed,match.proposed_guards(before,rows));reader=csv.DictReader(proposed.decode().splitlines());fields=reader.fieldnames;all_rows=list(reader)
        for index in range(11):
            altered=[dict(v)for v in all_rows];at=len(altered)-11+index;altered[at]['expected']='0x%08X'%(int(altered[at]['expected'],0)^1);s=io.StringIO();writer=csv.DictWriter(s,fieldnames=fields);writer.writeheader();writer.writerows(altered);p=self.out/'query-stale-guards.csv';p.write_text(s.getvalue())
            with self.assertRaisesRegex(ValueError,'stale word patch'):match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        declaration='s32  func_15081574(struct127 *, f32, f32, s32 *, s32, s32);';self.assertIn(declaration,(ROOT/'conker/include/functions.h').read_text());self.assertIn('struct127 *origin',candidate.SELECTED);self.assertIn('s32 *foundActorAddress',candidate.SELECTED)
        self.receipt('owner',body_words=68,slot_words=71,guards=11,omissions=0,raw_byte_controls=272,binding_controls=8,stale_guards=11,neighbors=2,dependent_stub_audited=True,shared_declaration_matches=True)
    def test_02_guest_order_return_values_homes_and_float_bits(self):
        count=0;seen=set()
        cases=[g.Case(actor_type=byte,kind=byte,match_at=byte%26,part=(-1,0,2,22)[byte%4],result=(0,1,0x80000000,0xffffffff)[byte%4],forward=g.FLOATS[byte%10],radius=g.FLOATS[(byte+3)%10])for byte in range(256)]
        cases += [g.Case(actor_type=t,kind=k,match_at=at,part=p,result=v,phase=phase,mutation=m)for t,k,at,p,v,phase,m in itertools.product((0x53,0x100,0x80000000),(0x53,0),(0,24,25),(-1,0,22),(0,1),(0,8),(0,7,8,48))]
        cases += [g.Case(alias=a,part=0,result=v,mutation=m,phase=p)for a,v,m,p in itertools.product((0,1,2),(0,0xffffffff),(0,7,8),(0,8))]
        cases.append(g.Case(loaded=False))
        for c in cases:
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        reached=set(range(match.ENTRY,match.ENTRY+272,4))&seen;self.assertEqual(len(reached),68,[hex(p)for p in range(match.ENTRY,match.ENTRY+272,4)if p not in reached])
        self.receipt('guest',cases_per_body=count,all68_words=True,full_word_types_and_return_values=True,all256_actor_types=True,float_bits_passthrough=True,guest_argument_home_mutations=True,raw_external_order_and_complete_RAM=True,raw_full_fault_claim=False)
    def test_03_original_normalized_fault_prefixes_and_missing_tables(self):
        count=0
        for c in(g.Case(match_at=25),g.Case(busy=0),g.Case(loaded=False),g.Case(part=-1,match_at=24),g.Case(),g.Case(result=0,match_at=24),g.Case(mutation=7),g.Case(alias=1,phase=8)):
            initial=g.fixture(c);done=g.Oracle(self.images[0],initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.images[0],self.images[2]):
                    m=g.Oracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(g.state(models[0]),g.state(models[1]));count+=1
        c=g.Case(busy=0);initial=g.fixture(c)
        for p in list(initial):
            if g.META-32<=p<g.META+1024 or any(p==g.ACTORS+0x32c*i+0x1d4+j for i in range(25)for j in range(4)):del initial[p]
        for w in self.images:g.Oracle(w,initial,c).run()
        self.receipt('faults',literal_prefixes=count,disabled_actors_succeed_without_model_or_metadata_storage=True,original_normalized_complete_state=True)
    def test_04_original_part_lookup_and_both_caller_windows(self):
        code=g.lookup_code(self.rom);helper_addresses=set(code);seen=set();count=0
        for byte in range(256):
            c=g.Case(actor_type=byte,kind=byte,match_at=24 if byte&1 else 0,forward=g.FLOATS[byte%10],radius=g.FLOATS[(byte+1)%10],result=0x80000000,mutation=8 if byte&2 else 0)
            for m in self.compare(c,connected=code):seen.update(m.visits)
            count+=1
        before=(self.out/'match-frozen'/match.ELF).read_bytes();current=match.elf_slot_offset(before,0x150553d0,36);windows=[(0x150553b4,list(struct.unpack_from('>9I',self.rom,0x82864)),0x64),(0x150553d0,list(struct.unpack_from('>9I',before,current)),0x7c)];window_cases=0
        for entry,words,local in windows:
            for at,result,mutation,phase in itertools.product((0,24,25),(0,0xffffffff),(0,7,8),(0,8)):
                c=g.Case(match_at=at,result=result,mutation=mutation,phase=phase,output=g.STACK+phase+local);initial=g.fixture(c);models=[]
                for image in(self.images[0],self.images[2]):
                    code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),image));stop=entry+36;code[stop]=0;m=g.Oracle(words,initial,c,entry=entry,connected=code,arguments=(0,0,0,0));m.r[16]=c.origin;m.before[16]=c.origin;before_r=m.r[:];before_r[31]=stop;want,calls,value=g.reference(initial,c,before_r,m.f[:],ra=stop);m.stop=stop;m.code=WindowCode(dict(m.code),m)
                    with self.assertRaises(WindowStop):m.run()
                    self.assertEqual(m.memory,want);self.assertEqual(m.calls,[(match.ENTRY,(c.origin,c.forward,c.radius,c.output,15,83)),*calls]);self.assertEqual(m.r[2],value);models.append(m)
                self.assertEqual(g.state(models[0]),g.state(models[1]));window_cases+=1
        self.receipt('connected',lookup_cases_per_body=count,original_lookup_words=48,lookup_words_reached=len(helper_addresses&seen),caller_cases_per_literal_body=window_cases,original_and_current_windows=True,caller_window_words=9,query_provider_bounded=True,full_parent_and_geometry_helper_claim=False)
    def test_05_independent_GNU_links_and_all_bindings(self):
        cases=links=0
        for i,base in enumerate((0x81007ff0,0x82008010,0x8300fff0)):
            names=dict(D_800CC2D0=base,D_800D121C=base+25*0x32c,D_8009BD30=base+0x10000,func_1508108C=0x15180000+4*i,func_15080D20=0x15190000+4*i);symbols=dict(ACTORS=base,END=names['D_800D121C'],META=names['D_8009BD30'],LOOKUP=names['func_1508108C'],QUERY=names['func_15080D20']);images=[]
            for j,(raw,b)in enumerate(self.blobs):
                p=self.out/('query-rebase-%d-%d'%(i,j));s=p.with_suffix('.s');o=p.with_suffix('.o');elf=p.with_suffix('.elf');ld=p.with_suffix('.ld');asm,missing=emit_function(raw,dict(value=0,size=272),b,match.FUNCTION,names);self.assertFalse(missing);s.write_text(asm);subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(o),str(s)],check=True,capture_output=True);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a)for n,a in names.items()],'-o',str(elf),str(o)],check=True,capture_output=True);text=sections(elf)['.text'][1];image=list(struct.unpack('>68I',text[:272]));self.assertEqual(image,match.bound_blob(raw,b,names));self.assertEqual(text[272:],b'');images.append(image);links+=1
            for at,result,mutation in itertools.product((0,24),(0,0xffffffff),(0,7,8)):self.compare(g.Case(match_at=at,result=result,mutation=mutation),images,symbols);cases+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=cases,all8_bindings=True,signed_low16_carries=True,scan_extent_25actors=True)
    def test_06_SDK32_native_and_effective_source_controls(self):
        checks=[]
        for label,b,opt in [('selected',None,o)for o in('-O0','-O2','-O3')]+[(n,b,'-O2')for n,b in native.controls().items()]:
            p=self.out/('query-native-'+label+opt);s=p.with_suffix('.c');s.write_text(native.program(b));cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(s.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True);self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt));run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected' else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=9216,SDK32_UBSan=True,correct_shared_prototype_and_callback=True,typed_actor_and_output_backing=True,float_bits_preserved=True,controls_rejected=len(native.controls()),checks=checks)
    def test_07_dependent_stub_argument_homes(self):
        count=0;stub=list(struct.unpack('>7I',match.TYPED_STUB))
        for phase,forward,byte in itertools.product((0,8),g.FLOATS,range(256)):
            c=g.Case(phase=phase);h=g.STACK+phase;args=(g.ORIGIN,g.ACTORS,byte,forward,0x80000000,0xffffffff);initial={h+i:(i*17+165)&255 for i in range(-32,64)};g.put(initial,h+16,args[4]);g.put(initial,h+20,args[5]);m=g.Oracle(stub,initial,c,entry=match.HELPER_ENTRY,arguments=args);want=dict(initial)
            for i,v in enumerate(args[:4]):g.put(want,h+4*i,v)
            m.run();self.assertEqual(m.memory,want);self.assertEqual(m.r[2],0);self.assertFalse(m.calls);self.assertEqual(m.r[29],h);count+=1
        self.receipt('dependent',cases=count,old_stub_words=3,new_stub_words=7,four_argument_home_stores=True,retail_helper_still_unmatched=True,no_new_matching_credit=True)
    def test_08_strict_image_tracks_both_function_deltas(self):
        q=self.prepared['report'];self.assertEqual((q['strict_changed_bytes'],q['strict_exclusions'],q['functions']),(237,0,6052));before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),237)
        for at in(0,0x100,match.elf_slot_offset(after,match.ENTRY,284),match.elf_slot_offset(after,match.HELPER_ENTRY,28),len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        self.receipt('image',strict_bytes=237,exclusions=0,changed_bodies=[match.HELPER,match.FUNCTION],helper_extent_12_to28=True,target_extent_12_to272=True,all6052_addresses_fixed=True,protected_bytes=189088,protected_owners=720)
if __name__=='__main__':unittest.main()
