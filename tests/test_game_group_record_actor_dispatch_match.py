"""Group loop ABI, dynamic providers, native C and literal image boundaries."""
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest
from tools.experiments import game_group_record_actor_dispatch_candidates as candidate
from tools.experiments import game_group_record_actor_dispatch_match as match
from tools.tests import game_group_record_actor_dispatch_oracle as g
from tools.tests import game_group_record_actor_dispatch_native as native
from tools.tests import test_game_view_list_setup as view_setup
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary,TrackedCode
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ROOT=candidate.ROOT

class WindowStop(Exception): pass
class WindowCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==0x1501da6c: raise WindowStop
        return super().__getitem__(pc)

class GroupRecordActorDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.truth=cls.rom[match.ROM:match.ROM+280];cls.retail=list(struct.unpack('>70I',cls.truth))
        ctx=type('OriginalGroupRecord',(),dict(root=ROOT,out=cls.out))
        original=view_setup.ViewListSetupTests.original.__func__(ctx,'group-original',(ROOT/match.ASM).read_text(),match.FUNCTION)
        cls.blobs=[match.function_blob(o) for o in (original,cls.prepared['qualified_compact'],cls.prepared['qualified_owner'])]
        cls.images=[match.bound_blob(b,r,match.symbols()) for b,r in cls.blobs]
        assert cls.images[0]==cls.retail==cls.images[2];cls.receipts={}
    @classmethod
    def tearDownClass(cls): (cls.out/'group-suite-receipt.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def receipt(self,key,**v): self.receipts[key]=v
    def compare(self,c,images=None,s=None,connected=None):
        initial=g.connected_fixture(c) if connected else g.fixture(c,s);models=[]
        for words in images or self.images:
            m=g.Oracle(words,initial,c,s=s,connected=connected);before=m.r[:];want,calls=g.reference(initial,c,before,s,connected is not None);m.run()
            self.assertEqual(m.memory,want,c);self.assertEqual(m.calls,calls,c)
            self.assertTrue(all(m.r[r]==before[r] for r in (*range(16,24),28,29,30,31)));models.append(m)
        self.assertEqual(g.state(models[0]),g.state(models[2]));self.assertEqual(g.external(models[0].events),g.external(models[1].events),c)
        return models
    def test_01_closed_register_cycle_owner_and_fail_closed_guards(self):
        q=self.prepared['report'];self.assertEqual((q['raw_words'],q['words'],q['frame'],q['guards'],q['omissions'],q['raw_neighbors'],q['neighbors']),(70,70,64,21,0,56,56))
        raw,b=self.blobs[1];normal,nb,rows,ledger=match.scheduling(raw,b);match.checked(normal,nb,self.truth);self.assertEqual(normal,self.blobs[2][0]);self.assertEqual(sorted(v['source'] for v in ledger),list(range(70)))
        for at in range(280):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError): match.scheduling(bytes(bad),b)
        for at in b:
            bad=dict(b);bad[at]=[(b[at][0][0],'wrong_binding')]
            with self.assertRaises(ValueError): match.scheduling(raw,bad)
        baseline=(self.out/'match-frozen'/match.GUARDS).read_bytes();proposed=(self.out/'proposed-guards.csv').read_bytes()
        self.assertEqual(proposed,match.proposed_guards(baseline,rows));self.assertTrue(proposed.startswith(baseline));fields=csv.DictReader(proposed.decode().splitlines()).fieldnames
        all_rows=list(csv.DictReader(proposed.decode().splitlines()))
        for index in range(21):
            altered=[dict(v) for v in all_rows];at=len(altered)-21+index;self.assertEqual(altered[at]['function'],match.FUNCTION);altered[at]['expected']='0x%08X'%(int(altered[at]['expected'],0)^1);s=io.StringIO();writer=csv.DictWriter(s,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(altered);p=self.out/'group-stale-guards.csv';p.write_text(s.getvalue())
            with self.assertRaisesRegex(ValueError,'stale word patch'): match.emit_padded_assembly(self.prepared['qualified_compact'],ROOT/match.ASM,filename=match.FILENAME,word_patches_path=p)
        self.receipt('owner',raw_and_padded_neighbors=56,guards=21,omissions=0,body_byte_controls=280,binding_controls=len(b),stale_guards_rejected=21,actual_existing_no_unroll_profile=True)
    def test_02_guest_dynamic_count_masks_kinds_and_selectors(self):
        count=0;seen=set()
        for byte in range(256):
            for c in (g.Case(count=byte,pattern=1,phase=8 if byte&1 else 0),g.Case(actor_id=byte,count=3,kind=2)):
                for m in self.compare(c): seen.update(m.visits)
                count+=1
        for group,edge,mode,phase in itertools.product((0,1,0xffffffff,0x7fffffff,0x80000000),(0,1,2,0x100,0x8000,0xffff),range(7),(0,8)):
            c=g.Case(group=group,mask1=edge,mask2=edge if mode&1 else 1,kind=edge if mode&2 else 2,mode=mode,phase=phase,alias=mode&1)
            for m in self.compare(c):seen.update(m.visits)
            count+=1
        reached=len(set(range(match.ENTRY,match.ENTRY+280,4))&seen);self.assertEqual(reached,70)
        self.receipt('guest',cases_per_body=count,root_words_reached=reached,all256_counts_and_actor_ids=True,halfword_edges=True,full_word_guest_groups=True,live_count_and_pointer_mutations=True,raw_full_fault_parity_claim=False)
    def test_03_literal_fault_prefixes_and_unmapped_inactive_tables(self):
        cuts=0
        for c in (g.Case(count=0),g.Case(mask1=0),g.Case(mask2=0),g.Case(kind=0x102),g.Case(),g.Case(mode=1),g.Case(mode=3),g.Case(mode=5,phase=8)):
            initial=g.fixture(c);done=g.Oracle(self.images[0],initial,c).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in (self.images[0],self.images[2]):
                    m=g.Oracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(g.state(models[0]),g.state(models[1]));cuts+=1
        c=g.Case(count=0);initial=g.fixture(c)
        for p in g.slots(c)[:3]:
            for i in range(4):del initial[p+i]
        for words in self.images:g.Oracle(words,initial,c).run()
        c=g.Case(mask1=0);initial=g.fixture(c)
        for p in g.slots(c)[1:3]:
            for i in range(4):del initial[p+i]
        for words in self.images:g.Oracle(words,initial,c).run()
        self.receipt('faults',original_normalized_prefixes=cuts,empty_and_disabled_missing_tables_fail_closed=True)
    def test_04_original_lookup_and_original_caller_window(self):
        code=g.lookup_code(self.rom);seen=set();count=0
        for byte in range(256):
            c=g.Case(actor_id=byte,count=1,phase=8 if byte&1 else 0)
            for m in self.compare(c,connected=code):seen.update(m.visits)
            count+=1
        window=list(struct.unpack_from('>2I',self.rom,0x4af14));windows=0
        for group,mode,phase in itertools.product((0,1,0xffffffff,0x80000000),range(7),(0,8)):
            c=g.Case(group=group,mode=mode,phase=phase);initial=g.fixture(c);models=[]
            for words in (self.images[0],self.images[2]):
                connected=dict(zip(range(match.ENTRY,match.ENTRY+280,4),words));connected[0x1501da6c]=0
                m=g.Oracle(window,initial,c,entry=0x1501da64,connected=connected,arguments=(0,));m.r[21]=c.group&0xffffffff;m.before[21]=m.r[21];before=m.r[:];before[31]=0x1501da6c;want,calls=g.reference(initial,c,before);m.code=WindowCode(dict(m.code),m)
                with self.assertRaises(WindowStop):m.run()
                self.assertEqual(m.memory,want);self.assertEqual(m.calls,[(match.ENTRY,(c.group&0xffffffff,)),*calls]);models.append(m)
            self.assertEqual(g.state(models[0]),g.state(models[1]));windows+=1
        self.receipt('connected',lookup_cases_per_body=count,original_lookup_words=72,lookup_words_reached=len(set(code)&seen),caller_windows=windows,original_caller_words=2,caller_parent='func_1501D348',update_provider_bounded=True,full_parent_update_and_gameplay_claim=False)
    def test_05_independent_GNU_links_and_rebases(self):
        links=cases=0
        for i,base in enumerate((0x81007ff0,0x82008010,0x8300fff0)):
            syms={n:base+0x100*j for j,n in enumerate(match.symbols()) if n.startswith('D_')};syms.update(func_15083E90=0x15180000+4*i,func_1502178C=0x15190000+4*i);images=[]
            for j,(raw,b) in enumerate(self.blobs):
                p=self.out/('group-rebase-%d-%d'%(i,j));s=p.with_suffix('.s');o=p.with_suffix('.o');elf=p.with_suffix('.elf');ld=p.with_suffix('.ld');asm,missing=emit_function(raw,dict(value=0,size=280),b,match.FUNCTION,syms);self.assertFalse(missing);s.write_text(asm)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(o),str(s)],check=True,capture_output=True);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%match.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%(n,a) for n,a in syms.items()],'-o',str(elf),str(o)],check=True,capture_output=True)
                text=sections(elf)['.text'][1];words=list(struct.unpack('>70I',text[:280]));self.assertEqual(words,match.bound_blob(raw,b,syms));self.assertEqual(text[280:],bytes(8));images.append(words);links+=1
            for mode in range(7):self.compare(g.Case(mode=mode),images,syms);cases+=1
        self.receipt('rebases',GNU_links=links,layouts=3,cases_per_body=cases,all10_bindings=True,signed_low16_carries=True)
    def test_06_native_SDK32_UBSan_and_semantic_controls(self):
        checks=[]
        for label,b,opt in [('selected',None,o) for o in ('-O0','-O2','-O3')]+[(n,b,'-O2') for n,b in native.controls().items()]:
            p=self.out/('group-native-'+label+opt);s=p.with_suffix('.c');s.write_text(native.program(b));cp=subprocess.run(native_command(opt)+['-o',str(p.relative_to(ROOT)),str(s.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((cp.returncode,cp.stdout,cp.stderr),(0,'',''),(label,opt));run=subprocess.run([str(p)],cwd=ROOT,capture_output=True,text=True);self.assertEqual((run.returncode,run.stdout,run.stderr),(0 if label=='selected' else 42,'',''),(label,opt));checks.append(dict(label=label,opt=opt,exit=run.returncode))
        self.receipt('native',positive_calls=26880,SDK32_UBSan=True,complete_arrays_and_records=True,all256_counts_and_actor_ids=True,dynamic_counts_and_pointer_tables=True,alias_masks=True,controls_rejected=len(native.controls()),checks=checks)
    def test_07_strict_image_and_wrong_body_rejection(self):
        q=self.prepared['report'];self.assertEqual((q['strict_changed_bytes'],q['strict_exclusions'],q['functions']),(221,0,6052));before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,self.truth),221)
        for at in (0,0x100,match.elf_slot_offset(after,match.ENTRY,280),len(after)//2,len(after)-1):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.truth)
        self.receipt('image',strict_bytes=221,exclusions=0,changed_bodies=[match.FUNCTION],all6052_addresses_fixed=True,protected_data_bytes=189088,owners=720,other_code_data_and_metadata_unchanged=True)

if __name__=='__main__': unittest.main()
