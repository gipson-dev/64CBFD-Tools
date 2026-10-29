"""Record effect packet: captured bytes, expiration dispatcher, aliases, real helpers and image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,struct,subprocess,unittest
from tools.experiments import game_record_effect_packet_six_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import game_record_effect_packet_six_oracle as oracle
from tools.tests.game_record_effect_packet_six_oracle import (Case,fixture,public,capture_and_spawn,parent_reference,PacketOracle,controls,native_harness,VALUES,RECORD,EFFECT,UPDATE,FREE)
ROOT=Path(__file__).resolve().parents[2]
class RecordEffectPacketSixTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>51I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>51I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def linked(self,entry,factory,copy):
        key=(entry,factory,copy)
        if not hasattr(self,'links'):self.links={}
        if key in self.links:return self.links[key]
        symbols=dict(func_151491F4=factory,memcpy=copy);pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>51I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,factory=source.FACTORY,copy=source.COPY):
        initial=fixture(c);want,calls,snapshot,copied=capture_and_spawn(initial,c);calls=[(factory if t==source.FACTORY else copy,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=PacketOracle(words,initial,c,entry,factory,copy).run();self.assertEqual((public(m.memory),m.calls,m.snapshot,m.copied),(public(want),calls,snapshot,copied),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_Make_callback_ABI_and_literal_registration(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.words[0],0x27BDFFA0)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),39)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),38);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_1CC440.c.o.compact'),39);self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22EF90]);self.assertEqual(struct.unpack_from('>I',self.rom,0x22EF80+4*4)[0],source.ENTRY)
        self.assertIn('extern void (*D_8008A4C0[])(struct260*);',(ROOT/'conker/include/variables.h').read_text());self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=51,frame=96,bindings=2,guards=0,neighbors=38,compact_functions=39,GLOBAL_ASM_routines=6,Make_commands=5,typed_void_struct260_callback=True,registered_table_slot=4,no_diagnostics=True)
    def test_02_complete_packet_snapshot_aliases_and_provider_changes(self):
        count=0;visits=set()
        for byte,pattern,allocated,phase in itertools.product(range(256),range(8),(False,True),(0,8)):
            m=self.compare(Case(byte=byte,pattern=pattern,word=(byte*257)^0x8000,allocated=allocated,phase=phase));visits.update(m.visits);count+=1
        for layout,mutation,allocated,phase in itertools.product((1,2,3),range(8),(False,True),(0,8)):
            self.compare(Case(input_layout=layout,mutation=mutation,allocated=allocated,phase=phase));count+=1
        for destination,mutation,pattern,allocated,phase in itertools.product(range(4),range(8),range(4),(False,True),(0,8)):
            self.compare(Case(destination=destination,mutation=mutation,pattern=pattern,allocated=allocated,phase=phase));count+=1
        for word,allocated,phase in itertools.product(VALUES,(False,True),(0,8)):
            self.compare(Case(word=word,allocated=allocated,phase=phase));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+204,4)));self.receipt['guest']=dict(cases=count,all51words_visited=True,all_slot_context_bytes_and_halfword_boundaries=True,complete36byte_snapshot_and_no_unwritten_packet_bytes=True,four_input_and_returned_record_layouts=True,source_snapshot_precedes_factory=True,late_packet_changes_and_forward_copy_overlap=True,full_private_state_and_access_trace=True,null_still_captures_source_packet=True)
    def test_03_full_original_dispatcher_and_retained_factory_chain(self):
        old=self.values['conker/build/conker.us.elf'];caller=list(struct.unpack_from('>45I',self.rom,0x176714));self.assertEqual(caller,list(struct.unpack_from('>45I',old,source.elf_slot_offset(old,source.CALLER,180))));count=0;visited=set()
        for flags,age,ticks,update,death,mode,allocated,mutation,phase in itertools.product((0,1),(-1,0,-32768,32767),(0,1,0xFFFFFFFF),(-1,2),(-1,4),range(3),(False,True),(0,4),(0,8)):
            c=Case(flags=flags,age=age,ticks=ticks,update=update,death=death,update_mode=mode,allocated=allocated,mutation=mutation,phase=phase);initial=fixture(c);want,calls=parent_reference(initial,c);pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=PacketOracle(caller,initial,c,entry=source.CALLER,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(want,calls),c);visited.update(p for p in m.visits if source.CALLER<=p<source.CALLER+180);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        self.assertEqual(visited,set(range(source.CALLER,source.CALLER+180,4)))
        descriptions=((source.FACTORY,0x1766A4,28),(source.CONSTRUCTOR,0x1765E0,49),(source.ALLOC,0x194F18,28),(source.COPY,0x22EC0,11));connected={};helper_visits={entry:set()for entry,_,_ in descriptions}
        for entry,rom,words in descriptions:
            body=list(struct.unpack_from('>%dI'%words,self.rom,rom));self.assertEqual(body,list(struct.unpack_from('>%dI'%words,old,source.elf_slot_offset(old,entry,words*4))));connected.update({entry+4*i:w for i,w in enumerate(body)})
        helpers=0
        for byte,allocated,mutation,phase in itertools.product((0,1,127,128,255),(False,True),(0,1,2,4),(0,8)):
            c=Case(byte=byte,word=0x8000|byte,allocated=allocated,mutation=mutation,phase=phase);initial=fixture(c);pair=[]
            for target in(self.truth,self.words):
                m=PacketOracle(target,initial,c,connected=connected).run();a=m.factory_packet;self.assertEqual([v for t,v in m.calls if t==source.CONSTRUCTOR],[(a[0],a[1],a[2],0xFFFFFFFF,a[3],a[4],a[5],a[6],a[7])]);self.assertEqual([v for t,v in m.calls if t==source.ALLOC],[(35,a[7],76,1,a[6],1)]);self.assertEqual([v for t,v in m.calls if t==source.HEAP],[(76,1,1,0,1)])
                if allocated:
                    self.assertEqual([v for t,v in m.calls if t==source.REGISTER],[(EFFECT,35)]);self.assertEqual(m.memory[EFFECT+1],a[7]&255);self.assertEqual(m.memory[EFFECT+12],a[6]);self.assertEqual(read(m.memory,EFFECT+14,2),a[0]&65535);self.assertEqual(bytes(m.memory[EFFECT+i]for i in(13,16,17,18,19)),bytes((1,255,4,255,0)));self.assertTrue(all(m.memory[EFFECT+20+i]==0 for i in range(16)));self.assertEqual(bytes(m.memory[EFFECT+40+i]for i in range(36)),m.copied)
                else:self.assertFalse(any(t in(source.REGISTER,source.ZERO,source.COPY)for t,a in m.calls))
                for entry,_,words in descriptions:helper_visits[entry].update(p for p in m.visits if entry<=p<entry+4*words)
                pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));helpers+=1
        self.receipt['caller']=dict(original_and_retained_dispatcher_words=45,cases=count,all45dispatcher_words_visited=True,actual_indirect_slot4_and_void_return=True,late_lifetime_reload_and_update_cleanup_gates=True,original_and_retained_helpers_words=116,helper_cases=helpers,helper_visited_words={hex(e):len(v)for e,v in helper_visits.items()},real_header_and_complete_payload_copy=True,bounded_heap_registration_bzero_updater_and_cleanup=True,no_full_heap_dispatcher_provider_or_gameplay_claim=True)
    def test_04_native32_all_halfwords_defined_packet_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=524288,effective_controls=len(controls()),trapping_UBSan=True,all65536_halfword_values_and_slot_context_pairs=True,all36_defined_packet_bytes_and_arena_fences=True,source_changes_after_capture=True,valid_disjoint_objects_and_two_destinations=True,no_guest_stack_overlap_or_FCSR_claim=True)
    def test_05_fired_access_prefixes_and_null_destination_suppression(self):
        cuts=0
        for c in(Case(),Case(allocated=False),Case(mutation=7),Case(input_layout=1),Case(input_layout=2,mutation=1),Case(destination=1),Case(destination=2),Case(destination=3)):
            initial=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=PacketOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case(allocated=False);initial={a:b for a,b in fixture(c).items()if not EFFECT-16<=a<EFFECT+176}
        for words in(self.truth,self.words):m=PacketOracle(words,initial,c).run();self.assertEqual(len(m.calls),1);self.assertEqual(len(m.snapshot),36)
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,null_still_reads_all_source_fields_but_needs_no_child_mapping=True)
    def test_06_actual_padder_corruptions_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,rs|{156:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,factory,copy in((source.ENTRY,source.FACTORY,source.COPY),(0x17007FFC,0x171491F4,0x10028000),(0x2500FFFC,0x251491F4,0x20022EC0)):
            images=self.linked(entry,factory,copy)
            for c in(Case(),Case(allocated=False),Case(mutation=7),Case(input_layout=2),Case(destination=2),Case(destination=3)):self.compare(c,images,entry,factory,copy);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,two_call_bindings_and_J26_layouts=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_actually_compiled_late_capture_is_rejected(self):
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()['late_capture'],'negative-late-capture');self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);f=fs[source.FUNCTION];words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']));c=Case(mutation=1);m=PacketOracle(words,fixture(c),c).run();want=capture_and_spawn(fixture(c),c)[3];self.assertNotEqual(m.copied,want);self.receipt['negative_capture']=dict(actually_compiled_late_capture_rejected=True,snapshot_must_precede_constructor=True,result_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+204];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,204);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+100,at+204,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),153);self.receipt['image']=dict(changed_bytes=153,code_bytes=152,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_and_shared_headers_unchanged=True)
