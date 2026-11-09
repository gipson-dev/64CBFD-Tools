"""Position sound: original callback, strict image, arithmetic and typed native ABI."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from unittest.mock import patch
from tools.experiments import game_position_sound_150f20f0_match as match
from tools.tests import game_position_sound_150f20f0_oracle as guest
from tools.tests import test_game_attachment_effect_150eee00_match as linking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=match.ROOT

def controls():
    b=match.SELECTED;pairs={
      'normal_distance':('    x *= x;\n    z *= z;\n',''),
      'inclusive_threshold':('x > D_800A191C','x >= D_800A191C'),
      'unsigned_tick_compare':('D_800BE9E4 < D_800D98F0','(u32)D_800BE9E4 < (u32)D_800D98F0'),
      'negative_tick_return':('    x = D_800CC2D0[index].x_position;','    if (D_800BE9E4 < 0) return;\n    x = D_800CC2D0[index].x_position;'),
      'wrong_height':('(s32)D_800CC2D0[index].y_position','(s32)D_800CC2D0[index].x_position'),
      'spatial_limit':('32767,20000,19000','32767,19999,19000'),
      'output_increment':('(u32)output0 + 128','(u32)output0 + 127'),
      'cooldown_mask':('func_150ADA20() & 127','func_150ADA20() & 63'),
      'cooldown_base':('(func_150ADA20() & 127) + 128','(func_150ADA20() & 127) + 127'),
      'signed_choice':('(u32)func_150ADA20()%3','func_150ADA20()%3'),
      'choice_modulus':('func_150ADA20()%3','func_150ADA20()%4'),
      'sound_base':('%3 + 108','%3 + 109'),
      'volume':(',24000,',',23999,'),
      'sound_flags':('(u8)output0,0,0);','(u8)output0,0,1);'),
    };rows={n:b.replace(a,z)for n,(a,z)in pairs.items()}
    rows['cached_output']=b.replace('    s32 output2;','    s32 output2;\n    u8 cached;').replace('        D_800D98F0 = (func_150ADA20()','        cached = (u8)output0;\n        D_800D98F0 = (func_150ADA20()').replace('(u8)output0,0,0);','cached,0,0);')
    rows['single_random']=b.replace('    s32 output2;','    s32 output2;\n    u32 random;').replace('        D_800D98F0 = (func_150ADA20() & 127) + 128;','        random = (u32)func_150ADA20();\n        D_800D98F0 = (random & 127) + 128;').replace('(u32)func_150ADA20()%3','random%3')
    assert all(v!=b for v in rows.values()),[n for n,v in rows.items()if v==b];return rows

def linked(obj,entry,s,label,out,negative=False):
    with patch.object(linking,'match',match):return linking.linked(obj,entry,s,label,out,negative)

def unsequenced_control():
    return match.SELECTED.replace('    s32 soundId;\n','').replace('        soundId = (u32)func_150ADA20()%3 + 108;\n        func_10010F30(soundId,24000,(u8)output0,0,0);','        func_10010F30((u32)func_150ADA20()%3 + 108,24000,(u8)output0,0,0);')
def code(words,entry):return dict(zip(range(entry,entry+4*len(words),4),words))
def state(m):return m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word
def check(test,m,initial,c,home=None,s=guest.SYMS,semantic=False):
    expected,calls,snaps,_=guest.reference(initial,c,home,s);actual_calls=m.calls;actual_snaps=m.snapshots
    if semantic and calls:
        # Incorrect source variants may allocate another valid private frame.
        # Compare their logical provider values, not differing local addresses.
        def normalized(t,a):return a[:6]+calls[0][1][6:]if t==s['func_100114D0']else a
        actual_calls=[(t,normalized(t,a))for t,a in m.calls]
        actual_snaps=[(z[0],normalized(s['func_100114D0']if z[0]==0 else 0,z[1]),*z[2:])for z in m.snapshots]
    test.assertEqual((guest.public(m.memory),actual_calls,actual_snaps),(guest.public(expected),calls,snaps),c)

class SoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/'conker/conker.us.bin').read_bytes();cls.truth=list(struct.unpack_from('>80I',cls.rom,match.ROM));cls.raw,_=linked(cls.out/'qualified-owner.o',match.ENTRY,guest.SYMS,'raw-suite',cls.out);assert cls.raw==cls.truth;cls.actual,_,_=match.load_elf_functions(str(ROOT/match.ELF),'mips-linux-gnu-objdump')
    def receipt(self,n,v):(self.out/(n+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def test_01_owner_actual_Make_image_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['diagnostics']),(80,88,0,43,43,0));self.assertEqual((q['actual_Make']['commands'],q['actual_Make']['functions'],q['metadata_reorders'],q['named_metadata_rows'],q['exclusions']),(3,44,3,7,0))
        blob,refs=match.payload(self.out/'qualified-owner.o')
        for j in range(320):
            bad=bytearray(blob);bad[j]^=1
            with self.assertRaises(ValueError):match.checked(bytes(bad),refs)
        for a in refs:
            bad=dict(refs);bad[a]=[(refs[a][0][0],'wrong')]
            with self.assertRaises(ValueError):match.checked(blob,bad)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+320]
        ats=[0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,320)];ats.extend(p for p,n,_,_ in match.symbol_rows(before)if n in sum(match.SYMBOL_ORDER,()))
        for a in ats:
            bad=bytearray(after);bad[a]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        bad=bytearray(truth);bad[0]^=1
        with self.assertRaises(ValueError):match.strict_image(before,after,bytes(bad))
    def test_02_cooldown_threshold_randoms_and_retained_outputs(self):
        visits=set();n=accesses=0
        for c in guest.cases():
            initial=guest.fixture(c);pair=[]
            for ws in(self.truth,self.raw):
                m=guest.Oracle(ws,initial,c).run();check(self,m,initial,c);pair.append(m);visits.update(m.visits)
            self.assertEqual(state(pair[0]),state(pair[1]));n+=1;accesses+=len(pair[0].trace)
        self.assertEqual((n,len(visits)),(1348,80));self.receipt('guest-contract',dict(cases_per_body=n,visited_words=80,accesses_per_body=accesses,all_256_cooldown_bytes=True,signed_tick_and_unsigned_wrap=True,actual_threshold_below_equal_above=True,quartic_RNE_model=True,retained_output_pointer_mutations=True,full_literal_state_equal=True,invalid_float_and_index_cases_guest_only=True,FCSR_or_gameplay_claim=False))
    def test_03_GNU_rebases_aliases_and_fault_prefixes(self):
        selected=[guest.Case(),guest.Case(mutation=127),guest.Case(cooldown=255,ticks=0x80000000),guest.Case(index=0xFFFFFFFF),guest.Case(x=0x7FC01234)]
        n=0
        for j in range(6):
            entry=match.ENTRY+j*0x10000;s={k:(v+j*0x20000 if k.startswith('func_')else v+j*0x108000)for k,v in guest.SYMS.items()};ws,_=linked(self.out/'qualified-owner.o',entry,s,'rebase-'+str(j),self.out)
            for c in selected:
                initial=guest.fixture(c,s);m=guest.Oracle(ws,initial,c,entry,s).run();check(self,m,initial,c,s=s);n+=1
        fired=delay=0
        for c in selected:
            initial=guest.fixture(c);full=guest.Oracle(self.truth,initial,c).run()
            for cut in range(full.all_accesses):
                pair=[]
                for ws in(self.truth,self.raw):
                    m=guest.Oracle(ws,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    pair.append(m)
                self.assertEqual(state(pair[0]),state(pair[1]));fired+=1;delay+=pair[0].delay_of is not None
        self.receipt('rebases-aliases-faults',dict(GNU_links=6,rebased_candidate_cases=n,fired_fault_pairs=fired,delay_slot_cuts=delay,wrapped_negative_indices_and_counter_alias_guest_only=True,retained_private_outputs_valid_native_C=True))
    def test_04_complete_frame_layer_caller_and_table(self):self.receipt('callers',caller_checks(self))
    def test_05_original_spatial_and_audio_wrapper_connections(self):self.receipt('connections',connection_checks(self))
    def test_06_compiled_controls_with_semantic_counterexamples(self):
        rows={};cases=list(guest.cases())
        for name,b in controls().items():
            obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+b,'negative-'+name);self.assertFalse(diag);ws,pools=linked(obj,match.ENTRY,guest.SYMS,'negative-link-'+name,self.out,True);witness=None
            for c in cases:
                initial=guest.fixture(c);initial.update(pools);m=guest.Oracle(ws,initial,c).run()
                try:check(self,m,initial,c,semantic=True)
                except AssertionError:witness=c;break
            self.assertIsNotNone(witness,name);rows[name]=dict(compiled=True,counterexample=vars(witness),private_frame_pointer_differences_not_a_witness=True,pool_bytes=len(pools))
        self.receipt('compiled-controls',rows)
    def test_07_native32_layout_callbacks_and_live_outputs(self):
        obj,diag=match.compile_owner(ROOT,self.out,match.HEADER+unsequenced_control(),'native-unsequenced-IDO');self.assertFalse(diag);match.checked(*match.payload(obj))
        text,n=native_program();p=self.out/'native.c';p.write_text(text)
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin','-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);self.assertEqual(v.returncode,0,v.stderr);self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0,opt)
        self.receipt('native-contract',dict(cases_per_profile=n,profiles=['O0','O2','O3'],record_size=812,record_count=26,record_offsets=[20,24,28],typed_void_s32_callback=True,all_record_bytes_and_globals=True,retained_output_pointers_live=True,finite_height_conversions=True,compiled_controls=len(controls())+1,mandatory_IDO_controls=len(controls()),unsequenced_same_IDO_words_native_only=True,all_controls_effective=True,UBSan_traps=True,portable_outside_array_or_hardware_claim=False))


FRAME_ENTRY,TABLE,DESC,ALT_DESC=0x151749F8,0x8008CD04,0x50000,0x51000
FRAME_PROVIDERS=(0x15165F70,0x15195FF0,0x1510C8A8,0x1517DE5C,0x151880C0)
def frame_effect(m,plan,stage,home):
    if stage==0:
        if plan&1:guest.put(m,0x800B0E00,0xAABBCCDD);guest.put(m,0x800B0E04,0x01234567)
        if plan&2:guest.put(m,0x800B0DF0,ALT_DESC)
    elif stage==2:
        if plan&4:
            p=guest.read(m,0x800B0DF0)+11;m[p]=0 if m[p]else 25
        if plan&8:guest.put(m,home+4,2)
        m[0x800BE616]=1 if plan&16 else 0
    elif stage in(3,4)and plan&32:
        guest.put(m,guest.TICKS,0x7FFFFFFF if stage==3 else 0xFFFFFFFF);guest.put(m,0x800CBD4E,0xFEDC if stage==3 else 0x1234,2)

def caller_checks(test):
    words=list(struct.unpack_from('>43I',test.rom,0x1A1EA8));test.assertEqual(test.actual['func_151749F8'],words)
    class Caller(guest.Oracle):
        def record_call(self,t):
            if t==guest.ENTRY:
                a=tuple(map(guest.u32,self.arguments(1)));self.calls.append((t,a));self.case=replace(self.frame_case,index=a[0]);self.outputs=None;self.draw=0
            elif t in FRAME_PROVIDERS:self.calls.append((t,tuple(map(guest.u32,self.arguments(2 if t==FRAME_PROVIDERS[1]else 0)))))
            else:super().record_call(t)
        def hook(self,t):
            if t not in FRAME_PROVIDERS:return super().hook(t)
            frame_effect(self.memory,self.plan,FRAME_PROVIDERS.index(t),self.parent_home)
            for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
    n=0
    for index,plan,phase in itertools.product((0,25,0xFFFFFFFF),range(64),(0,8)):
        c=guest.Case(index=index,phase=phase,mutation=(plan*3)&127);initial=guest.fixture(c)
        for p in(DESC,ALT_DESC):initial.update({p+j:0xA5 for j in range(64)})
        initial[DESC+11]=25;initial[ALT_DESC+11]=0;initial[0x800BE616]=0;guest.put(initial,0x800B0DF0,DESC);guest.put(initial,0x800B0E00,0x11112222);guest.put(initial,0x800B0E04,0x33334444);guest.put(initial,0x800CBD4E,0xFF80,2)
        initial.update({TABLE+j:b for j,b in enumerate(test.rom[0x2317C4:0x231834])});home=guest.STACK+phase;expected=dict(initial);calls=[];snaps=[];guest.put(expected,home,0x87654321);guest.put(expected,home+4,index)
        for stage in range(3):
            args=(guest.read(expected,0x800B0E00),guest.read(expected,0x800B0E04))if stage==1 else();calls.append((FRAME_PROVIDERS[stage],args));frame_effect(expected,plan,stage,home)
        if expected[guest.read(expected,0x800B0DF0)+11]:
            child=replace(c,index=guest.read(expected,home+4));calls.append((guest.ENTRY,(guest.u32(child.index),)));expected,inner,snaps,_=guest.reference(expected,child,home-24);calls.extend(inner)
        if not expected[0x800BE616]:
            for stage in(3,4):calls.append((FRAME_PROVIDERS[stage],()));frame_effect(expected,plan,stage,home)
        guest.put(expected,0x800CBD4E,(guest.read(expected,0x800CBD4E,2)+(guest.read(expected,guest.TICKS)<<6))&65535,2)
        for ws in(test.truth,test.raw):
            m=Caller(words,initial,c,entry=FRAME_ENTRY,connected=code(ws,guest.ENTRY),arguments=(0x87654321,index));m.frame_case=c;m.plan=plan;m.parent_home=home;m.semantic_home=home-24;m.run();test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),calls,snaps))
        n+=1
    before,after=test.prepared['predecessor_elf'].read_bytes(),test.prepared['qualified_elf'].read_bytes();at=match.elf_slot_offset(before,TABLE,112);test.assertEqual(before[at:at+112],test.rom[0x2317C4:0x231834]);test.assertEqual(before[at:at+112],after[at:at+112]);test.assertEqual(guest.read({j:b for j,b in enumerate(before)},at+25*4),guest.ENTRY)
    test.assertEqual((ROOT/match.CALLER_OBJECT).read_bytes(),(test.out/'frozen'/match.CALLER_OBJECT).read_bytes())
    return dict(cases_per_body=n,complete_caller_words=43,complete_table_entries=28,entry=25,baseline_exact=True,typed_void_s32_callback=True,view_has_no_range_gate=True,provider_reloads_phase_wrap_and_private_view_home_checked=True,caller_source_and_object_unchanged=True)

def connection_checks(test):
    spatial=list(struct.unpack_from('>85I',test.rom,0x114D0));audio=list(struct.unpack_from('>22I',test.rom,0x10F30));test.assertEqual(test.actual['func_100114D0'],spatial);test.assertEqual(test.actual['func_10010F30'],audio)
    class Connected(guest.Oracle):
        def record_call(self,t):
            if t in(guest.INNER,guest.PLAY):self.calls.append((t,tuple(map(guest.u32,self.arguments(12 if t==guest.INNER else 7)))))
            else:super().record_call(t)
        def hook(self,t):
            if t==guest.INNER:
                a=self.calls[-1][1]
                for p,w in zip(a[9:],(self.case.outputs[0],self.case.attenuation,self.case.outputs[2])):guest.put(self.memory,p,w)
                guest.effect(self.memory,self.case,0,self.semantic_home,self.syms,self.outputs)
            elif t==guest.PLAY:guest.effect(self.memory,self.case,3,self.semantic_home,self.syms,self.outputs)
            else:return super().hook(t)
            for j in range(4):self.put(self.r[29]+j*4,0xB5000000+j,4)
            for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
    program=code(spatial,guest.SPATIAL);program.update(code(audio,guest.AUDIO));visits=set();n=0
    for count,y,mu,phase in itertools.product((0,1,3),(-8.5,0.,100.25),(0,127),(0,8)):
        c=guest.Case(index=25,listeners=count,y=guest.bits(y),mutation=mu,phase=phase);volume=((c.attenuation*32767)&0xFFFFFFFF)>>15;c=replace(c,outputs=(c.outputs[0],volume,c.outputs[2]));initial=guest.fixture(c)
        if count==1 and y==0:
            for index,dy in ((0,1),(1,-1)):
                for off,w in ((12,0),(16,dy),(20,0)):guest.put(initial,guest.LISTENERS+index*28+off,guest.u32(w))
        yy=guest.trunc(c.y);selected=0;nearest=0xFFFFFFFF
        if count:
            for j in range(count+1):
                a=guest.LISTENERS+j*28;d=[guest.u32(v-guest.read(initial,a+o))for v,o in ((0,12),(yy,16),(0,20))];distance=sum(v*v for v in d)&0xFFFFFFFF
                if distance<nearest:nearest=distance;selected=j
        a=guest.LISTENERS+selected*28;h=guest.STACK+phase
        inner=tuple(guest.u32(v-guest.read(initial,a+o))for v,o in ((0,12),(yy,16),(0,20)))+(guest.read(initial,a+24),)+tuple(guest.u32(v-guest.read(initial,a+o))for v,o in ((0,0),(yy,4),(0,8)))+(20000,19000,h-12,h-116,h-20)
        expected,calls,snaps,_=guest.reference(initial,c);full=[calls[0],(guest.INNER,inner),*calls[1:]];full.append((guest.PLAY,(0,*calls[-1][1],initial[guest.VOICE])))
        pair=[]
        for ws in(test.truth,test.raw):
            m=Connected(ws,initial,c,connected=program).run();test.assertEqual((guest.public(m.memory),m.calls,m.snapshots),(guest.public(expected),full,snaps));visits.update(m.visits);pair.append(m)
        test.assertEqual(state(pair[0]),state(pair[1]));n+=1
    rng=list(struct.unpack_from('>18I',test.rom,0xDAED0));test.assertEqual(test.actual['func_150ADA20'],rng)
    return dict(cases_per_body=n,spatial_words=85,spatial_visited_words=sum(guest.SPATIAL<=a<guest.SPATIAL+340 for a in visits),audio_wrapper_words=22,audio_wrapper_visited_words=sum(guest.AUDIO<=a<guest.AUDIO+88 for a in visits),inclusive_listener_loop_and_first_tie=True,three_output_words_and_unsigned_scale=True,full_seven_word_audio_submission=True,random_baseline_exact_words=18,low_level_spatial_playback_and_RNG_are_providers=True,whole_audio_or_hardware_acceptance=False)


def native_program():
    edge=guest.edge_pairs();chosen=[guest.Case(),guest.Case(cooldown=1,ticks=0xFFFFFFFF),guest.Case(cooldown=255,ticks=0x80000000),guest.Case(randoms=(0,0)),guest.Case(mutation=6),*[guest.Case(x=x,z=z)for x,z in edge]]
    profiles=[(guest.bits(0.),0),(guest.bits(50.),0),(guest.bits(51.),0),(guest.bits(-100.),guest.bits(25.)),(guest.bits(1e10),0),*edge]
    for j in range(512):
        x,z=profiles[j%len(profiles)];chosen.append(guest.Case(index=j%26,x=x,z=z,cooldown=0 if j%3==0 else j&255,ticks=(0,1,255,256,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[j%7],mutation=j&127,randoms=((0,1,127,128,0xFFFFFFFF)[j%5],(0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[j%6]),outputs=((0,0x7FFFFFFF,0xFFFFFFFF,0xFFFFFF80)[j%4],0x87654321,0xFEDCBA98)))
    arr=lambda a:'{'+','.join('0x%Xu'%guest.u32(v)for v in a)+'}';rows=[]
    for c in chosen:
        initial=guest.fixture(c);after,calls,snaps,_=guest.reference(initial,c);ss=[]
        for stage in range(4):
            z=next((v for v in snaps if v[0]==stage),None);ss.append((z[2],z[3],*z[4],*(z[5]if z[5]is not None else(0,0,0)))if z else(0,)*8)
        values=[str(guest.u32(v))for v in(c.index,c.x,c.y,c.z,c.cooldown,c.ticks,c.mutation,len(calls),guest.read(after,guest.COOLDOWN,1),guest.read(after,guest.TICKS))]
        values.extend((arr(c.randoms),arr(c.outputs),arr(c.overrides),arr(tuple(guest.read(after,guest.record(c)+o)for o in(20,24,28))),str(calls[0][1][1]if calls else 0),arr(calls[-1][1]if calls else(0,)*5),'{'+','.join(arr(s)for s in ss)+'}'));rows.append('{'+','.join(values)+'}')
    text=match.HEADER+r'''
typedef char layout[sizeof(void*)==4&&sizeof(struct127)==812&&__builtin_offsetof(struct127,x_position)==20&&__builtin_offsetof(struct127,y_position)==24&&__builtin_offsetof(struct127,z_position)==28?1:-1];
typedef struct {u32 index,x,y,z,cooldown,ticks,mutation,calls,finalCooldown,finalTicks,randoms[2],outputs[3],overrides[2],position[3],spatialY,audio[5],snapshots[4][8];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
struct127 D_800CC2D0[26];u8 D_800D98F0;s32 D_800BE9E4;f32 D_800A191C=6760000;
static const Row *current;static s32 *outputs[3];static u32 calls,draws,bad;static u8 before[sizeof(D_800CC2D0)];
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static void observe(u32 stage){const u32 *s=current->snapshots[stage];u32 j;if(calls++!=stage||D_800D98F0!=s[0]||(u32)D_800BE9E4!=s[1]||word(D_800CC2D0[current->index].x_position)!=s[2]||word(D_800CC2D0[current->index].y_position)!=s[3]||word(D_800CC2D0[current->index].z_position)!=s[4])bad=1;if(stage)for(j=0;j<3;j++)if((u32)*outputs[j]!=s[5+j])bad=1;}
void func_100114D0(s32 x,s32 y,s32 z,s32 volume,s32 nearLimit,s32 farLimit,s32*a,s32*b,s32*c){u32 j;outputs[0]=a;outputs[1]=b;outputs[2]=c;observe(0);if(x||z||(u32)y!=current->spatialY||volume!=32767||nearLimit!=20000||farLimit!=19000||a==b||a==c||b==c)bad=1;for(j=0;j<3;j++)*outputs[j]=(s32)current->outputs[j];if(current->mutation&1)D_800D98F0=0x31;if(current->mutation&32){D_800BE9E4=(s32)0x80000000U;D_800CC2D0[current->index].x_position=-100;D_800CC2D0[current->index].y_position=20;D_800CC2D0[current->index].z_position=50;}}
s32 func_150ADA20(void){u32 result;if(draws>1){bad=1;return 0;}observe(1+draws);result=current->randoms[draws];if(draws==0){if(current->mutation&2)*outputs[0]=(s32)current->overrides[0];if(current->mutation&64)D_800D98F0=0x55;}else{if(current->mutation&4)*outputs[0]=(s32)current->overrides[1];if(current->mutation&8)D_800D98F0=0x23;}draws++;return(s32)result;}
void func_10010F30(s32 id,u16 volume,u8 pan,s16 pitch,u8 flags){observe(3);if((u32)id!=current->audio[0]||volume!=current->audio[1]||pan!=current->audio[2]||(u32)(s32)pitch!=current->audio[3]||flags!=current->audio[4])bad=1;if(current->mutation&16)D_800D98F0=0x6A;}
'''
    unsequenced=unsequenced_control()
    assert unsequenced!=match.SELECTED
    functions=dict(selected=match.SELECTED,**controls(),unsequenced=unsequenced)
    for name,b in functions.items():text+=b.replace(match.FUNCTION,name,1)+'\n'
    text+=r'''
typedef void(*FrameLayerCallback)(s32);
static int check(FrameLayerCallback fn,const Row*r){u32 i,j;u8*p=(u8*)D_800CC2D0;current=r;calls=draws=bad=0;outputs[0]=outputs[1]=outputs[2]=0;
for(i=0;i<26;i++){for(j=0;j<812;j++)p[i*812+j]=(u8)(j*29+i*13+90);D_800CC2D0[i].x_position=0;D_800CC2D0[i].y_position=0;D_800CC2D0[i].z_position=0;}
D_800CC2D0[r->index].x_position=real(r->x);D_800CC2D0[r->index].y_position=real(r->y);D_800CC2D0[r->index].z_position=real(r->z);for(i=0;i<sizeof(before);i++)before[i]=p[i];D_800D98F0=(u8)r->cooldown;D_800BE9E4=(s32)r->ticks;
fn((s32)r->index);
if(calls!=r->calls||draws!=(r->calls?2U:0U)||D_800D98F0!=r->finalCooldown||(u32)D_800BE9E4!=r->finalTicks||word(D_800A191C)!=0x4ACE4C80U||word(D_800CC2D0[r->index].x_position)!=r->position[0]||word(D_800CC2D0[r->index].y_position)!=r->position[1]||word(D_800CC2D0[r->index].z_position)!=r->position[2])bad=1;
for(i=0;i<sizeof(before);i++)if((i<r->index*812+20||i>=r->index*812+32)&&p[i]!=before[i])bad=1;
return !bad;}
static int run(void){u32 i,j,killed['''+str(len(functions))+r''']={0};FrameLayerCallback functions[]={'''+','.join(functions)+r'''};
for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){if(!check(functions[0],rows+i))return 1;for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j]&&!check(functions[j],rows+i))killed[j]=1;}
for(j=1;j<sizeof(functions)/sizeof(functions[0]);j++)if(!killed[j])return 80+j;return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,len(chosen)


if __name__=='__main__':unittest.main()
