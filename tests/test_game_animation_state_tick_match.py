"""Direct animation tick: signed arithmetic, lifecycle, ABI and image closure."""
from dataclasses import replace
import csv,itertools,json,struct,subprocess,unittest
from tools.experiments import game_animation_state_tick_candidates as candidate
from tools.experiments import game_animation_state_tick_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import game_animation_state_tick_oracle as g
from tools.tests import game_animation_state_tick_native as native
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=candidate.ROOT

def controls():
    b=candidate.SELECTED;line='    rate = *(s8 *)(state + 0x22);\n'
    return dict(unsigned_rate=b.replace('rate = *(s8 *)','rate = *(u8 *)'),
        floor_division=b.replace('*(s16 *)(state + 0x14) / 256','(*(s16 *)(state + 0x14) >> 8)'),
        positive_tie=b.replace('if (rate < remaining)','if (rate <= remaining)'),
        negative_tie=b.replace('if (cost < remaining)','if (cost <= remaining)'),
        unsigned_phase=b.replace('*(s16 *)(state + 0x14)','*(u16 *)(state + 0x14)'),
        cached_rate=b.replace(line,'').replace('    if (state[0x24] != 0) {',line+'    if (state[0x24] != 0) {'),
        callback_index=b.replace('D_8008CA20[state[0x24]]','D_8008CA20[state[0x24] ^ 1]'),
        no_backstep=b.replace('                *(s16 *)(state + 0x14) -= *(s16 *)(state + 0x16);',''),
        release_tie=b.replace('if (*(s16 *)(state + 0x14) / 256 >= (*(u8 **)(state + 0x10))[4])','if (*(s16 *)(state + 0x14) / 256 > (*(u8 **)(state + 0x10))[4])'))

class GameAnimationStateTickMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>69I',cls.rom,match.ROM));linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>69I',linked,fs[match.FUNCTION]['value']))
    def receipt(self,name,row):(self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,s=None,entry=match.ENTRY,connected=None,redirect=False):
        initial=g.fixture(c,s)if initial is None else initial;models=[]
        for body in images or(self.retail,self.words):
            m=g.Oracle(body,initial,c,s,entry,connected)
            try:m.run()
            except AssertionError as e:
                if not redirect or not e.args or not isinstance(e.args[0],tuple)or e.args[0][0]!='unowned jump':raise
            models.append(m)
        expected,calls=g.reference(initial,c,models[0].before[31],s,connected=bool(connected))
        for m in models:self.assertEqual((g.public(m.memory),m.calls),(g.public(expected),calls),c)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_direct_payload_complete_owner_and_literal_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['neighbors'],q['raw_neighbors']),(69,24,0,3,41,41));self.assertEqual(self.words,self.retail)
        raw,rs=match.function_blob(self.prepared['qualified_compact']);truth=match.original_bytes(ROOT)
        for i in range(276):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.checked_payload(bytes(bad),rs,truth)
        for i in rs:
            with self.assertRaises(ValueError):match.checked_payload(raw,{**rs,i:[('R_MIPS_26','wrong')]},truth)
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();self.assertEqual(match.strict_image(before,after,truth),204)
        for i in(0,0x80,match.elf_slot_offset(before,match.ENTRY,276)+276,len(after)-1):
            bad=bytearray(after);bad[i]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        with(ROOT/match.GUARDS).open()as stream:self.assertFalse([r for r in csv.DictReader(stream)if r['function']==match.FUNCTION])
    def test_02_all_rate_countdown_and_count_bytes_signed_boundaries(self):
        count=0;visits=set();steps=(-32768,-257,-1,0,1,255,256,32767)
        for raw in range(256):
            rate=g.signed8(raw);cost=abs(rate);limit=(0,1,3,127,128,255)[raw%6]
            for remaining,j in itertools.product((0,cost-1&255,cost&255,cost+1&255,255),range(8)):
                phase=(limit*256-1,limit*256,(limit-1)*256-1,(limit-1)*256,-257,-255,32767,-32768)[j]
                c=g.Case(rate=rate,remaining=remaining,phase_value=g.signed16(phase),step=steps[j],count=limit,index=raw%3,phase=(j&1)*8)
                m=self.compare(c);visits.update(m.visits);count+=1
        for value,rate in itertools.product(range(256),(-128,-1,0,1,127)):
            self.compare(g.Case(rate=rate,remaining=value,count=value,phase_value=g.signed16(value*256-1),step=1));count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+276,4)));self.receipt('guest-contract',dict(cases_per_body=count,reachable_words=69,all_rate_countdown_count_bytes=True,halfword_wrap_and_truncation=True))
    def test_03_provider_mutations_private_homes_and_descriptor_aliases(self):
        count=0
        for mutation,rate,index,phase in itertools.product(range(32),(-128,-1,0,1,127),(1,255),(0,8)):
            self.compare(g.Case(rate=rate,index=index,mutation=mutation,phase=phase));count+=1
        for offset,rate,phase,mutation in itertools.product((0x10,0x12,0x1E,0x1F,0x20),(-128,-1,0,1,127),(0,8),(0,1)):
            self.compare(g.Case(rate=rate,descriptor=g.STATE+offset,phase=phase,index=1,mutation=mutation));count+=1
        for offset,rate,phase in itertools.product((-0x10,-0x18,-0x1C,-0x20,-0x24),(-1,1),(0,8)):
            c=g.Case(actor=g.STACK+offset,rate=rate,index=0,phase=phase)
            if offset==-0x20 and phase==8:
                # Saving RA overwrites the index with 0xDE. Its provider's
                # outgoing homes then overwrite the descriptor with 0xB5000000.
                # This deliberately overlapping input faults, rather than returns.
                models=[]
                for body in(self.retail,self.words):
                    model=g.Oracle(body,g.fixture(c),c)
                    with self.assertRaises(AssertionError)as caught:model.run()
                    self.assertEqual(caught.exception.args,(('unmapped read',0xB5000004,1),));models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace)
            else:self.compare(c,redirect=True)
            count+=1
        self.receipt('aliases',dict(cases_per_body=count,returning_or_redirected_cases=758,expected_private_alias_faults=2,callback_rehome=True,descriptor_count_can_alias_phase_step_rate_or_countdown=True))
    def test_04_connected_original_release_unlink_and_fallback(self):
        code=g.connected_code(self.rom);count=0
        for kind,depth,rate,phase,index,mutation in itertools.product((0,1,3),(-1,0,1,3),(-1,0,1),(0,8),(0,1),(0,2)):
            c=g.Case(kind=kind,depth=depth,rate=rate,phase=phase,index=index,mutation=mutation,remaining=0,phase_value=512,step=256,count=3)
            self.compare(c,connected=code);count+=1
        self.receipt('connected',dict(cases_per_body=count,original_release_words=28,original_unlink_words=20,original_fallback_words=8,physical_reclamation_bounded=True))
    def test_05_original_type3_update_window_saved_next_and_two_banks(self):
        start,end=0x15167118,0x1516719C;caller=list(struct.unpack_from('>%dI'%((end-start)//4),self.rom,start-0x15000000+0x2D4B0));count=0
        for bank,length,index,mutation,phase in itertools.product((0,1),(0,1,2),(0,1),(0,16),(0,8)):
            c=g.Case(index=index,mutation=mutation,phase=phase,depth=1,rate=0,phase_value=0,step=1,count=3);initial=g.fixture(c);head=g.STATE if length else 0
            g.put(initial,g.STATE+8,g.OTHER if length==2 else 0);g.put(initial,g.OTHER+8,0);g.put(initial,0x800DCE50+bank*0x1A0+12,head)
            expected=dict(initial);expected[g.DEPTH]=2;expected_calls=[];node=head
            while node:
                g.put(expected,g.SLOTS+8,g.read(expected,node+8));expected_calls.append((match.ENTRY,(node,)))
                current=replace(c,actor=node,depth=2);expected,calls=g.reference(expected,current,0x15167178);expected_calls.extend(calls)
                node=g.read(expected,g.SLOTS+8)
            expected[g.DEPTH]=1;models=[]
            for body in(self.retail,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+276,4),body));code[end]=0
                m=g.Oracle(caller,initial,c,entry=start,connected=code)
                m.r[18]=g.CATALOG+3*52;m.r[21]=3;m.r[22]=bank;m.r[23]=0x800DCE50;m.r[19]=g.DEPTH;m.r[20]=g.SLOTS
                m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((g.public(m.memory),m.calls),(g.public(expected),expected_calls));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt('caller',dict(cases_per_body=count,window_words=33,catalog_row=3,banks=2,empty_single_double_lists=True,full_outer_dispatcher_not_claimed=True))
    def test_06_fired_access_prefixes_and_unread_callback_table(self):
        count=0
        for c in(g.Case(),g.Case(rate=-1,remaining=255,phase_value=512,step=256,count=3),g.Case(index=1,mutation=3,phase=8)):
            initial=g.fixture(c);done=g.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for body in(self.retail,self.words):
                    m=g.Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace);count+=1
        c=g.Case(index=0,rate=0);initial=g.fixture(c)
        for i in range(1024):initial.pop(g.TABLE+i)
        initial.pop(c.actor+0x23);self.compare(c,initial)
        self.receipt('fault-prefixes',dict(fired_prefixes=count,zero_index_needs_no_callback_table=True,zero_rate_needs_no_countdown=True))
    def test_07_independent_GNU_links_and_carry_edges(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('AnimationOriginal',(),dict(root=ROOT,out=self.out));original=ViewListSetupTests.original.__func__(ctx,'original-animation-tick',(ROOT/match.ASM).read_text(),match.FUNCTION);links=count=0
        for j,(entry,s)in enumerate(((match.ENTRY,g.syms()),(0x18017FFC,g.syms(0x800B7FFC,0x18038000)),(0x1A028000,g.syms(0x800C8000,0x1A048000)))):
            images=[]
            for k,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(j,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
                images.append(list(struct.unpack_from('>69I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for rate,index,mutation,phase in itertools.product((-128,-1,0,1,127),(0,1),(0,3),(0,8)):
                self.compare(g.Case(rate=rate,index=index,mutation=mutation,phase=phase),images=(images[0],images[1]),s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,all_three_bindings=True,both_HI_LO_carry_edges=True))
    def test_08_native32_signed_boundaries_aliases_and_typed_calls(self):
        for label,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text(native.source(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True);(self.out/('native-'+label+'-diagnostics.txt')).write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[:4000]);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,label)
        self.receipt('native-contract',dict(positive_executions=24816,profiles=['O0','O2','O3'],direct_and_typed=True,descriptor_aliases=3,controls=9,UBSan=True))
    def test_09_actual_IDO_semantic_controls(self):
        witnesses=[g.Case(rate=0,phase_value=-1,step=0,count=0),g.Case(rate=0,phase_value=-1,step=0,count=3),g.Case(rate=1,remaining=1,phase_value=0,step=0,count=3),
            g.Case(rate=-1,remaining=1,phase_value=512,step=256,count=3),g.Case(rate=-1,remaining=255,phase_value=512,step=256,count=3),
            g.Case(rate=0,phase_value=512,step=256,count=3),g.Case(index=1,mutation=1),g.Case(rate=-128,remaining=128,phase_value=256,step=256,count=2)]
        found={}
        for label,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+label);linked,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']));witness=False
            for c in witnesses:
                initial=g.fixture(c);m=g.Oracle(words,initial,c).run();expected,calls=g.reference(initial,c,m.before[31])
                if(g.public(m.memory),m.calls)!=(g.public(expected),calls):witness=True;break
            self.assertTrue(witness,label);found[label]=True
        self.receipt('compiled-controls',dict(effective_IDO_controls=found))
if __name__=='__main__':unittest.main()
