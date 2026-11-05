"""Sequence catch-up: live reloads, exact prologue, caller and native ABI."""
import hashlib,itertools,json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_sequence_catchup_candidates as candidate
from tools.experiments import game_sequence_catchup_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_sequence_catchup_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT

def bound(obj,s):
    raw,rs=match.function_blob(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    for at,rows in rs.items():
        if len(rows)!=1:raise ValueError('Unexpected catch-up binding pair')
        kind,name=rows[0];value=s[name]
        if kind=='R_MIPS_HI16':words[at//4]=(words[at//4]&0xFFFF0000)|((value+0x8000)>>16&65535)
        elif kind=='R_MIPS_LO16':words[at//4]=(words[at//4]&0xFFFF0000)|(value&65535)
        elif kind=='R_MIPS_26':words[at//4]=(words[at//4]&0xFC000000)|(value>>2&0x3FFFFFF)
        else:raise ValueError('Unknown catch-up binding kind')
    return words

def state(m):return complete(m),m.trace,m.observations,m.current_pc,m.delay_of,m.all_accesses

class SequenceCatchupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM));cls.raw=bound(cls.prepared['qualified_compact'],model.symbols())
        cls.words=bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalCatchup',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-catchup',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert bound(cls.original,model.symbols())==cls.retail==cls.words
    def receipt(self,name,result):(self.out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s)if initial is None else initial
        m=model.Oracle(words,initial,c,s,entry).run();wanted,calls,observations=model.reference(initial,c,s)
        self.assertEqual((model.public(m.memory),m.calls,m.observations),(model.public(wanted),calls,observations),c)
        for r in(*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
        return m
    def compare(self,c,initial=None,s=None,images=None,entry=match.ENTRY):
        images=(self.retail,self.words)if images is None else images
        ms=[self.contract(words,c,initial,s,entry)for words in images];self.assertEqual(state(ms[0]),state(ms[1]));return ms
    def test_01_complete_owner_bindings_and_closed_schedule(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['raw_neighbors'],q['neighbors']),(66,56,17,14,56,56))
        self.assertEqual(q['caller']['unchanged_functions'],16);self.assertTrue(q['caller']['unchanged_padded_object'])
        self.assertEqual(set(match.PERMUTATION),set(match.PERMUTATION.values()));self.assertEqual(self.raw[20:],self.retail[20:])
        raw,rs=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+264]
        for i in range(264):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),rs,truth)
        for i in rs:
            bad=dict(rs);bad[i]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.receipt('owner-contract',dict(words=66,frame=56,guards=17,bindings=14,owner_neighbors=56,caller_functions=16,byte_controls=264,binding_controls=14))
    def test_02_signed_gates_live_transitions_and_slot_zero_restart(self):
        visited=set();count=0
        for c in model.cases():
            ms=self.compare(c)
            self.contract(self.raw,c)
            visited.update(ms[0].visits);count+=1
        # The duplicated li at +0xD8 follows an unconditional loop branch.
        reachable=set(range(match.ENTRY,match.ENTRY+264,4))-{match.ENTRY+0xD8}
        self.assertEqual(visited,reachable)
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,reachable_words=65,unreachable_literal_offset='0xD8',signed_boundaries=True,live_helper_changes=True,slot_zero_restart=True))
    def test_03_all_active_and_flag_bytes(self):
        count=0
        for slot,value,phase in itertools.product((0,1),range(256),(0,8)):
            self.compare(model.Case(slot=slot,active=value,phase=phase));self.compare(model.Case(slot=slot,flag=value,phase=phase));count+=2
        self.receipt('byte-gates',dict(original_fitted_cases=count,all_active_and_flag_bytes=True))
    def test_04_aliases_private_frames_and_nonterminating_prefix(self):
        count=0;bounded_aliases=0
        offsets=(-56,-52,-48,-44,-40,-36,-32,-28,-24,-20,-16,-4,0,4,8)
        for name,offset,phase in itertools.product(('D_800C35EA','D_800C35B0','D_800C3640','D_800C3C8C'),offsets,(0,8)):
            s=model.symbols();s[name]=model.STACK+phase+offset;c=model.Case(phase=phase,call_limit=12)
            initial=model.fixture(c,s);images=(bound(self.original,s),bound(self.prepared['qualified_owner'],s));ms=[];outcomes=[]
            for words in images:
                m=model.Oracle(words,initial,c,s)
                try:m.run();outcomes.append('return')
                except WindowBoundary:outcomes.append('bounded calls')
                except AssertionError as error:
                    if not error.args or not isinstance(error.args[0],tuple)or error.args[0][0]not in('unowned jump','saved register'):raise
                    outcomes.append(error.args)
                ms.append(m)
            self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(state(ms[0]),state(ms[1]));count+=1
        for left,right in(('D_800C35B0','D_800C3640'),('D_800C35EA','D_800C3C8C'),('D_800C3C8C','D_800C35B0')):
            s=model.symbols();s[left]=s[right]
            for c in(model.Case(),model.Case(slot=1,flag=1),model.Case(mode=3)):
                c=model.replace(c,call_limit=12);ms=[];bounded=[]
                for words in(bound(self.original,s),bound(self.prepared['qualified_owner'],s)):
                    m=model.Oracle(words,model.fixture(c,s),c,s)
                    try:m.run();bounded.append(False)
                    except WindowBoundary:bounded.append(True)
                    ms.append(m)
                self.assertEqual(bounded[0],bounded[1]);self.assertEqual(state(ms[0]),state(ms[1]));count+=1;bounded_aliases+=bounded[0]
        c=model.Case(mode=8,call_limit=12);ms=[]
        for words in(self.retail,self.words):
            m=model.Oracle(words,model.fixture(c),c)
            with self.assertRaises(WindowBoundary):m.run()
            ms.append(m)
        self.assertEqual(state(ms[0]),state(ms[1]));self.assertEqual(len(ms[0].calls),12)
        self.receipt('aliases',dict(original_fitted_layouts=count,bounded_aliases=bounded_aliases,nonterminating_prefix_calls=12,natural_private_fault_parity_not_claimed=True))
    def test_05_fired_access_prefixes(self):
        count=0
        for c in(model.Case(active=0),model.Case(flag=1),model.Case(mode=0),model.Case(mode=6,phase=8)):
            initial=model.fixture(c);done=model.Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.words):
                    m=model.Oracle(words,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[1]));count+=1
        self.receipt('fault-prefixes',dict(fired_prefixes=count,scope='original/fitted instructions'))
    def test_06_original_frame_caller_and_transition_prefixes(self):
        start,end=0x150191F0,0x15019210;body=list(struct.unpack_from('>8I',self.rom,0x466A0));count=0
        for mode,flag,phase,result in itertools.product(range(8),(0,1,128,255),(0,8),(0,0xFFFFFFFF)):
            c=model.Case(mode=mode,phase=phase,result=result);initial=model.fixture(c);put=model.put
            put(initial,0x800D23A9,flag,1);ms=[]
            for words in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+264,4),words));m=model.Oracle(body,initial,c,entry=start,connected=code)
                m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.calls[0],(match.ENTRY,(0,)))
                self.assertEqual(sum(t==0x15087CC0 for t,a in m.calls),int(flag!=0));ms.append(m)
            self.assertEqual(state(ms[0]),state(ms[2]));count+=1
        connected=0
        for helper,rom,words,stop,frame in((model.A,0x4BCCC,26,0x15169040,72),(model.B,0x4B8B0,28,0x1501E1B4,40)):
            code=dict(zip(range(helper,helper+words*4,4),struct.unpack_from('>%dI'%words,self.rom,rom)))
            for slot,phase,countdown in itertools.product((0,1),(0,8),(0,1,255)):
                c=model.Case(slot=slot,phase=phase,mode=1);initial=model.fixture(c);model.put(initial,0x800C3A58,countdown,1)
                ms=[]
                for target in(self.retail,self.raw,self.words):
                    m=model.Oracle(target,initial,c,connected=code)
                    with self.assertRaises(WindowBoundary):m.run()
                    t,args,sp=m.prefix[-1];self.assertEqual((t,sp),(stop,m.before[29]-56-frame))
                    if helper==model.A:self.assertEqual(args,(sp+0x40,16));self.assertEqual(m.memory[sp+0x40],initial[0x800C35E8+slot])
                    else:
                        self.assertEqual(args[0],0);self.assertEqual(m.memory[0x800C3A58],max(countdown-1,0))
                        self.assertEqual(model.read(m.memory,0x800C35B8),model.read(initial,0x800C35B0))
                    ms.append(m)
                self.assertEqual(state(ms[0]),state(ms[2]));connected+=1
        self.receipt('callers',dict(original_caller_window_words=8,cases_per_body=count,transition_prefix_words=[26,28],connected_cases_per_body=connected,remaining_helpers_bounded=True,full_parents_not_claimed=True))
    def test_07_independent_links_and_carry_rebases(self):
        links=count=0
        for index,(entry,base)in enumerate(((match.ENTRY,0x800C7FF8),(0x18017FFC,0x80208000),(0x1A028000,0x80407FFC))):
            s=model.symbols()
            for i,name in enumerate(('D_800C35B0','D_800C3640','D_800C35EA','D_800C3C8C')):s[name]=base+i*0x10000
            for i,name in enumerate(model.NAMES):s[name]=(entry&0xF0000000)+0x03000000+i*0x1000
            images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2])
            for c in(model.Case(),model.Case(slot=1,mode=6),model.Case(flag=255),model.Case(active=0),model.Case(stamp=0x80000000,limit=0x7FFFFFFF)):
                self.compare(c,s=s,images=(images[0],images[2]),entry=entry);self.contract(images[1],c,s=s,entry=entry);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,bindings=14,HI_LO_carry_edges=True))
    def test_08_native_typed_calls_and_compiled_controls(self):
        for name,body,opt,wanted in [('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]+[(name,body,'-O2',1)for name,body in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(model.native_source(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-'+name+'-diagnostics.txt')).write_text(result.stdout+result.stderr);self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[:3000])
            self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        witnesses=(model.Case(),model.Case(active=0),model.Case(flag=1),model.Case(slot=1,mode=7),model.Case(slot=1,mode=0),model.Case(stamp=0x7FFFFFFF,limit=0x80000000),model.Case(stamp=0x80000000,limit=0x7FFFFFFF),model.Case(stamp=0xFFFFFFFF,limit=0),model.Case(mode=0))
        for name,body in model.controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+name);words=bound(obj,model.symbols());effective=False
            for c in witnesses:
                initial=model.fixture(c);wanted,calls,observations=model.reference(initial,c);m=model.Oracle(words,initial,c)
                try:m.run()
                except WindowBoundary:effective=True
                if (model.public(m.memory),m.calls,m.observations)!=(model.public(wanted),calls,observations):effective=True
                if effective:break
            self.assertTrue(effective,name)
        self.receipt('native-contract',dict(positive_executions=sum(not c.phase for c in model.cases())*2*3,profiles=['O0','O2','O3'],native_controls=len(model.controls()),IDO_controls=len(model.controls()),typed_and_direct=True))
    def test_09_literal_image_and_actual_guard_rejections(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+264]
        self.assertEqual(match.strict_image(before,after,truth),207);at=match.elf_slot_offset(after,match.ENTRY,264)
        symbol=next(off for off,name,fields,string in match.symbol_rows(before)if name==match.FUNCTION)
        for offset in(0,at,at+264,symbol+8,len(after)-1):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        rows=self.prepared['qualified_rows'];fields=self.prepared['fields'];checked=0
        for index,row in enumerate(rows):
            if row['function']!=match.FUNCTION:continue
            bad=[dict(r)for r in rows];bad[index]['expected']='0x00000000'
            with patch.multiple(match.harness,FILENAME=match.FILENAME,ASM=match.ASM):
                with self.assertRaises(ValueError):match.harness.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],bad,fields,'bad-owner')
            checked+=1
        self.assertEqual(checked,17);self.receipt('strict-controls',dict(literal_ELF_changes=207,named_symbol_serialization_bytes=0,exclusions=0,image_corruptions=5,padder_preimages=17))

if __name__=='__main__':unittest.main()
