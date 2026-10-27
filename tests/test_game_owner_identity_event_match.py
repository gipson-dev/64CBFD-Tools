"""Owner identity events: byte ABI, ordered aliases, real dispatcher and strict retail image."""
from pathlib import Path
import csv,io,itertools,json,os,struct,subprocess,time,types,unittest
from tools.experiments import game_owner_identity_event_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_record_identity_event_match as base
from tools.tests.test_game_record_identity_event_match import Case,addresses,fixture,mutation,outgoing_homes,public
from tools.tests.test_game_record_identity_event_match import PAIR,OWNER,RELEASE,BOOKKEEP,FALLBACK,CALLBACK,RELEASE_TABLE,VALUES
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2]
PARENT,TABLE=source.PARENT,source.TABLE

# Reuse the established guest/provider model without mutating its module globals.
class RecordEventOracle(base.RecordEventOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=source.ENTRY,connected=None,arguments=None,release=RELEASE,providers=()):
        super().__init__(words,memory,c,phase,entry,connected,arguments,release,())
        self.providers=set(providers)-{0,source.ENTRY}
    def record_call(self,target):
        self.attempted.append(target)
        assert target in(source.ENTRY,self.release,BOOKKEEP,FALLBACK,CALLBACK)or target in self.providers,hex(target)
        args=self.arguments(3 if target==source.ENTRY or target in self.providers else 1)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

def reference(initial,c,phase=0,chain=False,incoming_sp=None,incoming_command=None):
    owner,event=addresses(c,phase);m=dict(initial);calls=[]
    sp=STACK+phase if incoming_sp is None else incoming_sp
    incoming=c.command if incoming_command is None else incoming_command
    put(m,sp+8,incoming);command=incoming&255;state=owner+0x28
    if command==45:
        current=read(m,state);first=read(m,event)
        if first==current:put(m,state,read(m,event+4));m[state+4]=m[event+9]
        elif read(m,event+4)==current:put(m,state,first);m[state+4]=m[event+8]
    elif command in(0,24):
        first=read(m,event);current=read(m,state)
        if first==current or m[state+4]==m[event+4]:
            calls.append((RELEASE,(owner,)))
            if chain:
                calls.append((BOOKKEEP,(owner,)));mutation(m,c,owner);outgoing_homes(m,sp-48)
                if m[owner]>=2:calls.append((CALLBACK if c.callback else FALLBACK,(owner,)))
            else:mutation(m,c,owner);outgoing_homes(m,sp-24)
    return m,calls


def controls():
 b=source.SELECTED
 result=dict(wrong_release_24=b.replace('value == 0x18','value == 0x19'),wrong_release_0=b.replace('command == 0 ||','command == 1 ||'),
  and_gate=b.replace('value == *(s32 *)state || state[4] == event[4]','value == *(s32 *)state && state[4] == event[4]'),
  wrong_command=b.replace('value == 0x2D','value == 0x2E'),wrong_release_key=b.replace('state[4] == event[4]','state[4] == event[5]'),
  wrong_first_key=b.replace('state[4] = event[9]','state[4] = event[8]'),wrong_second_key=b.replace('state[4] = event[8]','state[4] = event[9]'),
  missing_second=b.replace('*(s32 *)(event + 4) == current','0'),wrong_owner=b.replace('func_1516972C((struct102 *)owner);','func_1516972C((struct102 *)event);'),
  early_key=b.replace('*(s32 *)state = *(s32 *)(event + 4);\n            state[4] = event[9];','state[4] = event[9];\n            *(s32 *)state = *(s32 *)(event + 4);'))
 assert all(v!=b for v in result.values()),[n for n,v in result.items()if v==b]
 return result


def native_harness(values):
    # The shared builder has an isolated global dictionary and the current target.
    scope=dict(vars(base));scope.update(source=source,controls=controls)
    text=types.FunctionType(base.native_harness.__code__,scope)(values)
    changes=(('target=selector==256?0x151B1FACu:registry','target=selector==256?0x151D08F0u:registry'),
        ('invoke=target==0x151B1FACu;','invoke=target==0x151D08F0u;'),
        ('release=invoke&&(u8)command==0&&','release=invoke&&((u8)command==0||(u8)command==24)&&'),
        ('full?256u:3u','full?256u:4u'),('(u32[]){0,45,255}[c]','(u32[]){0,24,45,255}[c]'),
        ('void func_1516972C(void*p)','void func_1516972C(struct102*p)'),
        ('!expectedRelease||p!=currentOwner','!expectedRelease||(void*)p!=currentOwner'),
        ('__builtin_offsetof(RecordIdentity1DD500,key)==4&&','sizeof(u8)==1&&'))
    for before,after in changes:
        if text.count(before)!=1:raise ValueError('Owner identity-event native builder changed: '+before)
        text=text.replace(before,after,1)
    return text


class OwnerIdentityEventTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        source.check_inputs(ROOT,cls.out,cls.installed);source.verify_prepared(cls.out)
        cls.fresh=cls.out/('fresh-run-'+str(os.getpid())+'-'+str(time.time_ns()));cls.fresh.mkdir()
        cls.obj,diag=source.compile_owner(ROOT,cls.fresh,source.HEADERS+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        source.checked_payload(*source.payload(cls.obj))
        rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>46I',rom,source.ROM))
        cls.parent=list(struct.unpack_from('>23I',rom,0x1768E4));cls.registry=struct.unpack_from('>74I',rom,source.TABLE_ROM)
        cls.helper=list(struct.unpack_from('>28I',rom,0x196BDC))
        data,fs=source.link_owner(ROOT,cls.fresh,cls.obj,source.OWNER)
        cls.raw=list(struct.unpack_from('>46I',data,fs[source.FUNCTION]['value']));cls.words=cls.raw[:]
        for at,(expected,replacement)in source.GUARDS.items():
            if cls.words[at//4]!=expected:raise ValueError('Owner identity-event fresh guard changed')
            cls.words[at//4]=replacement
        old=cls.values['conker/build/conker.us.elf']
        cls.retained_parent=list(struct.unpack_from('>23I',old,source.elf_slot_offset(old,PARENT,92)))
        cls.retained_helper=list(struct.unpack_from('>28I',old,source.elf_slot_offset(old,RELEASE,112)))
    @classmethod
    def tearDownClass(cls):
        (cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def initial(self,c,phase=0):
        return fixture(c,phase,self.registry)
    def compare(self,c=Case(),phase=0,chain=False,images=None,entry=source.ENTRY,release=RELEASE):
        initial=self.initial(c,phase);expected,calls=reference(initial,c,phase,chain);models=[]
        for words in images or(self.truth,self.words):
            connected={RELEASE+4*i:w for i,w in enumerate(self.helper)}if chain else None
            m=RecordEventOracle(words,initial,c,phase,entry,connected,release=release).run()
            self.assertEqual(public(m.memory,c,phase),public(expected,c,phase),c)
            normalized=[(RELEASE if t==release else t,a)for t,a in m.calls];self.assertEqual(normalized,calls,c);models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]
    def test_01_complete_owner_actual_Make_registry_and_ABI(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(self.parent,self.retained_parent);self.assertEqual(self.helper,self.retained_helper)
        raw,bindings=source.checked_payload(*source.payload(self.obj))
        self.assertEqual(source.payload(self.out/'after-owner.o'),(raw,bindings))
        self.assertEqual(source.payload(self.out/('original-'+source.FUNCTION+'.o')),source.normalized_payload(raw,bindings))
        q=json.loads((self.out/'qualification.json').read_text());mk=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['guards'],q['preserved_neighbors']),(46,24,1,51))
        self.assertEqual((mk['commands'],mk['compact_functions_equal'],mk['complete_padded_object_equal']),(3,52,True))
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),51)
        self.assertEqual((self.out/'make-shadow/src/game/generated_1FA770.c.o').read_bytes(),(self.out/'qualified-padded.o').read_bytes())
        self.assertEqual(self.registry[49],source.ENTRY)
        old=self.values['conker/build/conker.us.elf'];self.assertEqual(struct.unpack_from('>74I',old,source.elf_slot_offset(old,TABLE,296)),self.registry)
        proposed=(self.out/'proposed-owner.c').read_text();self.assertIn('void func_1516972C(struct102 *);',proposed)
        self.assertIn('func_1516972C((struct102 *)*(s32 volatile *)(temp_a1 + 0xA8));',proposed)
        direct=[];literal=[];call=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        for i,(word,)in enumerate(struct.iter_unpack('>I',self.values['conker/conker.us.bin'])):
            if word==source.ENTRY:literal.append(i*4)
            if word==call:direct.append(i*4)
        self.assertEqual((direct,literal),([],[0x22F45C]))
        # The existing zero-return placeholder does not implement the retarget event.
        c=Case(45,1,0);initial=self.initial(c);at=source.elf_slot_offset(old,source.ENTRY,12)
        stub=RecordEventOracle(struct.unpack_from('>3I',old,at),initial,c).run()
        self.assertNotEqual(public(stub.memory,c),public(reference(initial,c)[0],c))
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=46,frame=24,guards=1,bindings=1,neighbors=51,actual_Make_commands=3,
            canonical_ABI='void(struct260*,s32,u8)',actual_provider_ABI='void(struct102*)',word_neutral_existing_provider_cast=True,
            inherited_warning_712_count=8,target_diagnostics_empty=True,actual_registry_index=49,registry_entries=74,
            direct_sites=direct,literal_sites=literal)
    def test_02_byte_ABI_identity_priority_keys_and_aliases(self):
        count=0;visits=set()
        cases=[(Case(upper|command,command%8,command%4,(0,127,128,255)[command%4],alias),phase)
            for command,alias,(upper,phase)in itertools.product(range(256),(0,6,7,8),((0,0),(0xA5A50000,8)))]
        cases.extend((Case(upper|command,pattern,match,key,alias,True),phase)
            for command,pattern,match,key,alias,(upper,phase)in itertools.product((0,24,45),range(8),range(4),(0,127,128,255),range(9),((0,0),(0x87650000,8))))
        cases.extend((Case(command,2,2,key),0)for command,key in itertools.product((0,24,45),range(256)))
        for c,phase in cases:
            m=self.compare(c,phase);visits.update(m.visits)
            raw=RecordEventOracle(self.raw,self.initial(c,phase),c,phase).run();expected,calls=reference(self.initial(c,phase),c,phase)
            self.assertEqual(public(raw.memory,c,phase),public(expected,c,phase));self.assertEqual(raw.calls,calls);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+184,4))-{source.ENTRY+96,source.ENTRY+144})
        self.receipt['guest']=dict(cases=count,all_command_bytes=True,all_key_bytes=True,full_incoming_command_home=True,
            alias_layouts=9,guest_matrix_is_partitioned=True,supported_commands_full_pattern_match_key_alias_matrix=True,
            raw_C_public_semantics_checked=True,fitted_full_private_state_equal=True,reachable_words=44,dead_words=[24,36])
    def test_03_retained_release_helper_and_late_kind(self):
        self.assertEqual(self.helper,self.retained_helper);visits=set();count=0
        for command,kind,mutate,callback,phase in itertools.product((0,24),(0,1,2,255),(False,True),(False,True),(0,8)):
            c=Case(command,1,0,255,0,mutate,kind,callback);m=self.compare(c,phase,True);visits.update(m.visits);count+=1
        self.assertTrue(set(range(RELEASE,RELEASE+112,4))<=visits)
        self.receipt['release']=dict(cases=count,all_28_original_and_retained_words_visited=True,late_kind_reload=True,
            pre_bookkeeping_and_callback_fallback_are_bounded_contracts=True,no_new_helper_credit=True)
    def caller_compare(self,parent,c,index,phase=0):
        owner,event=addresses(c,phase);initial=self.initial(c,phase);initial[owner+0x13]=index
        expected=dict(initial);put(expected,STACK+phase+8,c.command)
        chosen=self.registry[index if index<74 else 0];command=c.command&255;calls=[]
        if chosen==source.ENTRY:
            expected,tail=reference(expected,c,phase,incoming_sp=STACK+phase-24,incoming_command=command)
            calls=[(source.ENTRY,(owner,event,command)),*tail]
        elif chosen:
            put(expected,owner+0x34,chosen^command);outgoing_homes(expected,STACK+phase-24)
            calls=[(chosen,(owner,event,command))]
        pair=[]
        for words in(self.truth,self.words):
            connected={source.ENTRY+4*i:w for i,w in enumerate(words)}
            m=RecordEventOracle(parent,initial,c,phase,PARENT,connected,providers=self.registry).run()
            self.assertEqual(m.calls,calls,(c,index));self.assertEqual(public(m.memory,c,phase,True),public(expected,c,phase,True),(c,index));pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));return pair[0]
    def test_04_original_and_retained_full_dispatchers(self):
        count=0
        cases=[(Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
            for command,index,phase in itertools.product((0,24,45,255),range(256),(0,8))]
        cases.extend((Case(0xA5000000|command,command%8,command%4,command,0,True),index,phase)
            for command,index,phase in itertools.product(range(256),(0,1,49,73,74,255),(0,8)))
        cases.extend((Case(upper|command,pattern,match,255,alias,True),index,phase)
            for command,pattern,match,alias,index,(upper,phase)in itertools.product((0,24,45,255),(0,7),range(4),range(1,9),(0,49),((0,0),(0x87650000,8))))
        for parent in(self.parent,self.retained_parent):
            for c,index,phase in cases:self.caller_compare(parent,c,index,phase);count+=1
        self.receipt['caller']=dict(cases=count,original_words=23,retained_words=23,actual_table_entries=74,
            all_selector_bytes=True,all_command_bytes=True,guest_matrix_is_partitioned=True,
            clamp_to_NULL_slot_zero=True,all_nonzero_provider_addresses_checked=True,
            canonical_callback_signature='void(struct260*,s32,u8)',byte_mask_before_indirect_call=True,
            other_providers_are_bounded_contracts=True,whole_parent_gameplay_claimed=False)
    def test_05_native32_actual_C_release_and_typed_dispatch(self):
        text=native_harness(self.values)
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(text);binary=p.with_suffix('')
            result=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            p.with_suffix('.diagnostics.txt').write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(subprocess.run([str(binary)],timeout=120).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],target_cases_per_profile=256*256*6*2,
            dispatcher_cases_per_profile=256*256*2,effective_controls=len(controls()),trap_UBSan=True,actual_retained_release_C=True,
            heap_backed_typeless_fixture=True,canonical_function_pointer_interface=True,all_selector_bytes=True,
            all_32_pattern_match_pairs_per_command_runtime_verified=True)
    def test_06_fault_prefixes_and_effective_compiled_negatives(self):
        count=0
        for c in(Case(0,0,0),Case(24,0,0),Case(0,0,2),Case(24,0,3),Case(45,1,0),Case(45,3,1),Case(45,2,2),Case(45,2,0,255,3),Case(24,1,0,255,6)):
            initial=self.initial(c);m=self.compare(c)
            for fault in range(m.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    x=RecordEventOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);pair.append(x)
                self.assertEqual(complete(pair[0]),complete(pair[1]));count+=1
        for command,phase in itertools.product((x for x in range(256)if x not in(0,24,45)),(0,8)):
            c=Case(command);initial={a:b for a,b in self.initial(c,phase).items()if STACK-2048<=a<STACK+512}
            for words in(self.truth,self.words,self.raw):RecordEventOracle(words,initial,c,phase).run()
        bad=source.SELECTED.replace('    s32 value = command;','    s32 value = command;\n    (void)*(volatile s32 *)state;')
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+bad,'negative-hoisted-read');self.assertFalse(diag)
        data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs[source.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        c=Case(255);initial={a:b for a,b in self.initial(c).items()if STACK-2048<=a<STACK+512}
        with self.assertRaisesRegex(AssertionError,'unmapped read'):RecordEventOracle(words,initial,c).run()
        text=self.values[source.CALLER_SOURCE].decode();lo,hi=source.function_span(text,'func_15149434');parent=text[lo:hi]
        controls_={'bound':parent.replace('idx >= 74','idx >= 75'),'NULL':parent.replace('D_8008A8D8[idx] != 0','1')}
        for name,body in controls_.items():
            self.assertNotEqual(body,parent)
            obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+'extern void(*D_8008A8D8[74])(struct260*,s32,u8);\n'+body,'negative-parent-'+name)
            self.assertFalse(diag);data,fs=source.link_owner(ROOT,self.fresh,obj,source.OWNER);info=fs['func_15149434']
            words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
            c=Case(255);initial=self.initial(c);initial[OWNER+0x13]=74 if name=='bound'else 0
            x=RecordEventOracle(words,initial,c,entry=PARENT,providers=self.registry)
            with self.assertRaisesRegex(AssertionError,'unmapped read'if name=='bound'else'0x0'):x.run()
            if name=='NULL':self.assertEqual(x.attempted[-1],0)
        self.receipt['faults']=dict(prefix_pairs=count,ignored_modes_need_no_packet_or_owner_mapping=True,
            actual_compiled_MIPS_early_read_negative_effective=True,compiled_parent_bound_and_NULL_negatives_effective=True,
            emitted_guest_access_order_only=True)
    def test_07_checked_guard_actual_padder_and_GNU_rebases(self):
        raw,bindings=source.checked_payload(*source.payload(self.obj));fitted,_=source.normalized_payload(raw,bindings)
        manifest=source.guarded_manifest(self.values['conker/retail_word_patches.us.csv'],raw,bindings)
        self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes())
        with self.assertRaises(ValueError):source.guarded_manifest(manifest,raw,bindings)
        bad=bytearray(raw);bad[148]^=1
        with self.assertRaises(ValueError):source.normalized_payload(bytes(bad),bindings)
        with self.assertRaises(ValueError):source.normalized_payload(raw,{80:[('R_MIPS_26','wrong')]})
        with self.assertRaises(ValueError):source.normalized_payload(raw[:-4],bindings)
        with self.assertRaises(ValueError):source.guarded_manifest(self.values['conker/retail_word_patches.us.csv']+b'\n',raw,bindings)
        rows=list(csv.DictReader(io.StringIO(manifest.decode())));selected=next(i for i,row in enumerate(rows)if row['function']==source.FUNCTION)
        for field,value in(('expected','0x548A0004'),('expected_relocations','R_MIPS_26:wrong'),('offset','0x90')):
            changed=[dict(row)for row in rows];changed[selected][field]=value;s=io.StringIO(newline='');writer=csv.DictWriter(s,changed[0].keys(),lineterminator='\n');writer.writeheader();writer.writerows(changed);path=self.fresh/(field+'-bad-guards.csv');path.write_text(s.getvalue())
            with self.assertRaises(ValueError):emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        asm,missing=emit_function(fitted,dict(value=0,size=184),bindings,source.FUNCTION,dict(func_1516972C=RELEASE));self.assertFalse(missing)
        p=self.fresh/'independent-fitted.s';p.write_text(asm);obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-o',str(obj),str(p)],capture_output=True,check=True)
        links=count=0
        for i,(entry,release)in enumerate(((source.ENTRY,RELEASE),(source.ENTRY+0x200000,RELEASE+0x300000),(source.ENTRY+0x500000,RELEASE+0x700000))):
            images=[]
            for j,object_ in enumerate((self.out/('original-'+source.FUNCTION+'.o'),obj)):
                p=self.fresh/('rebase-%d-%d.ld'%(i,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=func_1516972C=0x%X'%release,'-o',str(elf),str(object_)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>46I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(*images)
            for command,pattern,match,alias,phase in itertools.product((0,24,45,255),(0,7),range(4),(0,3,6,8),(0,8)):
                self.compare(Case(command,pattern,match,255,alias,True),phase,images=images,entry=entry,release=release);count+=1
        self.receipt['guards_links']=dict(guard_and_input_negative_controls=8,independent_GNU_links=links,layouts=3,rebased_guest_cases=count,call_binding_rebased=True)
    def test_08_strict_full_image_frozen_inputs_and_corruptions(self):
        values=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out)
        before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+184]
        expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        at=source.elf_slot_offset(before,source.ENTRY,184);symbol=next(pos+8 for pos,name,f,_ in source.symbol_rows(before)if name==source.FUNCTION and f[1:3]==(source.ENTRY,12))
        for offset in(20,at,at+184,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        for bad in(expected[:-1],expected+bytes([0])):
            with self.assertRaises(ValueError):source.check_image(before,bad,truth)
        for b,t in((before[:-1],truth),(before,truth[:-1]),(before,bytes([truth[0]^1])+truth[1:])):
            with self.assertRaises(ValueError):source.check_image(b,expected,t)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual((q['changed_bytes'],q['code_bytes'],q['metadata_bytes'],q['exclusions']),(128,127,1,0))
        self.receipt['strict']=dict(changed_bytes=128,code_bytes=127,metadata_bytes=1,exclusions=0,corruptions=7,wrong_input_controls=3,focused_inputs=len(values))

if __name__=='__main__':unittest.main()
