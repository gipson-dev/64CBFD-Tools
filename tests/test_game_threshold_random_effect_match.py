"""Signed threshold callback: closed frame, original ABI, timing and production."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_threshold_random_effect_candidates as candidate
from tools.experiments import game_threshold_random_effect_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_threshold_random_effect_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.number,m.submissions
class ThresholdRandomEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>68I',cls.rom,match.ROM));cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        cls.fitted=model.bound(cls.prepared['qualified_compact'],model.symbols(),True)
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalThresholdEffect',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-threshold-effect',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.words==cls.fitted
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def contract(self,words,c,initial=None,s=None,entry=match.ENTRY,helpers=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s)if initial is None else initial
        code=model.helper_code(self.rom,c)if helpers is None else helpers;m=model.Oracle(words,initial,c,s,entry,code).run();expected=model.reference(initial,c,s)
        self.assertEqual(m.calls,expected['calls'],c);self.assertEqual(m.submissions,[expected['submission']]if expected['submission']else[],c)
        self.assertEqual(m.number,expected['number']);self.assertEqual(model.public(m.memory),model.public(expected['memory']))
        return m
    def compare(self,c,initial=None,s=None,entry=match.ENTRY,images=None,helpers=None):
        ms=[self.contract(w,c,initial,s,entry,helpers)for w in((self.retail,self.words,self.fitted)if images is None else images)]
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_complete_owner_frame_guards_and_corruptions(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['raw_frame'],q['frame'],q['guards'],q['bindings'],q['neighbors']),(68,72,80,9,3,3))
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+272]
        for at in range(272):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        for at,a,b in match.PATCHES:
            self.assertEqual(a>>16,b>>16);self.assertEqual(a>>21&31,29)
        old=(self.out/'frozen'/match.GUARDS).read_bytes();new=match.guard_manifest(old)
        self.assertTrue(new.startswith(old));self.assertEqual(len(new.splitlines())-len(old.splitlines()),9)
        for at,a,b in match.PATCHES:
            token=(','+hex(at)+','+hex(a)+',').encode();self.assertIn(token,new[len(old):])
            bad=new[:len(old)]+new[len(old):].replace(token,(','+hex(at)+','+hex(a^1)+',').encode(),1)
            with self.assertRaises(ValueError):match.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],bad,'bad-frame-%x'%at)
        # The raw frame is insufficient for literal original private-state parity.
        c=model.Case();a=self.contract(self.retail,c);b=self.contract(self.raw,c);self.assertNotEqual(state(a),state(b))
        self.assertEqual(model.read(a.memory,model.STACK-80+0x48),c.randoms[0]%3)
        self.assertEqual(model.read(a.memory,model.STACK-80+0x44),c.scale)
        self.assertEqual(model.read(a.memory,model.STACK),c.actor)
        self.receipt('owner-controls',words=68,raw_frame=72,original_frame=80,guards=9,raw_byte_corruptions=272,binding_corruptions=3,guard_expected_word_corruptions=9,three_neighbors=True,raw_private_frame_rejected=True)
    def test_02_signed_gate_draw_order_snapshot_and_consumers(self):
        count=0;seen=set();consumers={}
        for c in model.cases():
            seen.update(self.compare(c)[0].visits);self.contract(self.raw,c);count+=1;consumers[str(c.consumer)]=consumers.get(str(c.consumer),0)+1
        dead={match.ENTRY+i for i in(156,160,164,168)}
        self.assertEqual(set(range(match.ENTRY,match.ENTRY+272,4))-seen,dead)
        self.assertTrue(set(range(model.RANDOM,model.RANDOM+72,4))<=seen)
        self.receipt('guest-contract',cases_per_body=count,bodies=4,reachable_target_words=64,retained_unreachable_unsigned_conversion_words=4,all_18_original_RNG_words=True,consumer_modes=consumers,all_360_angle_residues=True,all_256_scale_bytes=True)
    def test_03_private_aliases_fired_cuts_and_unmapped_early_exit(self):
        cuts=aliases=0;raw_difference=False
        for shift,phase in itertools.product((-64,-56,-48,-40),(0,8)):
            c=model.Case(actor=model.STACK+phase+shift,phase=phase);initial=model.fixture(c);ms=[]
            for words in(self.retail,self.words,self.fitted,self.raw):
                m=model.Oracle(words,initial,c);m.cut=22
                try:m.run();ended='return'
                except(faults.AccessBoundary,AssertionError,KeyError)as e:ended=type(e).__name__
                ms.append((m,ended))
            self.assertEqual((state(ms[0][0]),ms[0][1]),(state(ms[1][0]),ms[1][1]));self.assertEqual((state(ms[0][0]),ms[0][1]),(state(ms[2][0]),ms[2][1]))
            raw_difference|=(state(ms[0][0]),ms[0][1])!=(state(ms[3][0]),ms[3][1]);aliases+=1
        self.assertTrue(raw_difference)
        for c in(model.Case(value=767),model.Case(mutation=3),model.Case(connected=True,consumer=3),model.Case(redirect=3)):
            initial=model.fixture(c);code=model.helper_code(self.rom,c);done=model.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.words,self.fitted):
                    m=model.Oracle(words,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        c=model.Case(value=-1);initial={model.STACK+i:0xA5 for i in range(-0x100,0x40)};model.put(initial,c.actor+0x14,0xFFFF,2)
        self.compare(c,initial)
        self.receipt('aliases-faults',private_stack_aliases=aliases,fired_access_prefixes=cuts,raw_alias_or_private_state_rejected=True,early_exit_needs_only_gate_field=True,portable_stack_alias_claimed=False)
    def test_04_actual_registered_dispatchers(self):
        row=match.census(ROOT);self.assertEqual(row['index'],3)
        table=match.elf_slot_offset(self.prepared['qualified_elf'].read_bytes(),row['table'],44)
        self.assertEqual(self.prepared['qualified_elf'].read_bytes()[table:table+44],self.rom[0x2314E0:0x23150C])
        windows=((0x15167B44,12,(0x15167B74,),0x24,False),(0x151680CC,13,(0x15168100,0x1516810C),0x48,True),
          (0x15168BAC,14,(),0xE4,False),(0x15169988,12,(0x151699B8,),0x40,False))
        count=0
        for (pc,n,ends,field,sentinel),active,value,phase in itertools.product(windows,(False,True),(767,768),(0,8)):
            c=model.Case(value=value,phase=phase,mutation=3);initial=model.fixture(c);initial[c.actor+field]=3 if active else(255 if sentinel else 0)
            expected=model.reference(initial,c);body=list(struct.unpack_from('>%dI'%n,self.rom,pc-0x15000000+0x2D4B0));ms=[]
            for target in(self.retail,self.words,self.fitted):
                code=dict(zip(range(match.ENTRY,match.ENTRY+272,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code);m.r[7]=1;m.before=m.r[:]
                if ends:
                    for end in ends:m.code[end]=0
                    m.code=model.WindowCode(m.code,m);m.code.ends=ends
                    with self.assertRaises(model.WindowBoundary):m.run()
                else:m.run()
                self.assertEqual(m.calls,[(match.ENTRY,(c.actor,))]+expected['calls']if active else[])
                self.assertEqual(m.submissions,[expected['submission']]if active and expected['submission']else[])
                self.assertEqual(model.public(m.memory),model.public(expected['memory'])if active else model.public(initial));ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            count+=1
        self.receipt('dispatchers',original_contexts=4,cases_per_body=count,complete_wrapper_words=14,registered_index=3,full_other_parents_or_gameplay_claimed=False)
    def test_05_three_call_rebases(self):
        count=links=0
        for i,(entry,base)in enumerate(((match.ENTRY,0x17007FFC),(0x18018000,0x19018000),(0x1A02FFFC,0x1B00FFFC))):
            s=model.symbols();s['func_150ADA20']=base;s['func_15171D4C']=base+0x10000;images=[]
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj)
                if j==1:
                    text=bytearray(text);f=fs[match.FUNCTION];raw,bind=match.function_blob(obj);text[f['value']:f['value']+272]=match.normalized(raw,bind,self.rom[match.ROM:match.ROM+272])
                asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>68I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for c in list(model.cases())[::47]:
                c=replace(c,connected=False,consumer=0);self.compare(c,s=s,entry=entry,images=images,helpers={});count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_three_R26_bindings=True)
    def test_06_native_and_effective_IDO_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,_=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c)).run()
                    fired=m.calls!=expected['calls']or model.public(m.memory)!=model.public(expected['memory'])
                except(AssertionError,IndexError,KeyError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        rows=[c for c in witnesses if not c.phase and not c.redirect and not c.consumer]
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native_source(body,rows));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',rows_per_profile=len(rows),all_signed_halfword_gates_per_profile=65536,profiles=['O0','O2','O3'],executions=3*(len(rows)+65536),native_controls=len(effective),IDO_controls=effective,UBSan=True)
    def test_07_literal_image_and_old_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+272]
        self.assertEqual(match.strict_image(before,after,truth),208);at=match.elf_slot_offset(after,match.ENTRY,272)
        for offset in(0,at,at+271,at+272,match.elf_slot_offset(after,model.RANDOM,72),match.elf_slot_offset(after,0x8008CA20,44),len(after)-1):
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>68I',before,match.elf_slot_offset(before,match.ENTRY,272)));c=model.Case();m=model.Oracle(stub,model.fixture(c),c).run();self.assertFalse(m.calls);self.assertEqual(len(model.reference(model.fixture(c),c)['calls']),3)
        self.receipt('image-controls',literal_changed_bytes=208,exclusions=0,corruptions=7,old_stub_rejected=True)

def native_source(body,cases):
    rows=[]
    for c in cases:
        expected=model.reference(model.fixture(c),c);submission=expected['submission']or(0,)*14
        rows.append('{%d,%d,{%s},{%s},%d,%d,0x%XULL,{%s},%d}'%(model.half(c.value),c.scale,','.join(map(str,c.point)),','.join('0x%Xu'%model.u32(v)for v in c.randoms),c.mutation,c.connected,c.seed,','.join('0x%Xu'%v for v in submission),expected['number']))
    return '#include <ultra64.h>\n'+candidate.DECLARATIONS+body+r'''
typedef struct {s16 value;u8 scale;s16 point[3];u32 randoms[2];int mutation,connected;u64 seed;u32 expect[14];u32 draws;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static u8 record[0x100] __attribute__((aligned(16)));static const Row *row;static u32 draws,submissions;static u64 seed;static int error;
typedef union {f32 f;u32 u;} Float;
static u32 bits(f32 x){Float v;v.f=x;return v.u;}
__attribute__((noinline)) s32 func_150ADA20(void){u32 n=draws++;if(n>=2){error=1;return 0;}
 if(row->mutation&(1<<n)){
  record[0x25]=n?17:200;*(s16 *)(record+0x14)=-1;
  static const s16 positions[2][3]={{32767,-32768,123},{-101,202,-303}};
  for(int i=0;i<3;i++)*(s16 *)(record+0x18+i*2)=positions[n][i];
  record[0x0C]=n?0x55:0x90;record[1]=n?0xFF:0x80;
 }
 if(row->connected){u64 mixed=((seed&1)<<32)|((seed>>1)&0xFFFFFFFFULL);mixed^=(seed&0xFFFFFULL)<<12;seed=mixed^((mixed>>20)&0xFFF);return(s32)seed;}
 return(s32)row->randoms[n];
}
__attribute__((noinline)) void func_15171D4C(f32 x,f32 y,f32 z,s16 a,u16 b,u8 c,f32 angle,s32 d,s32 e,s32 f,s32 g,s32 h,u8 i,s32 j){
 u32 args[14]={bits(x),bits(y),bits(z),(u32)(s32)a,b,c,bits(angle),(u32)d,(u32)e,(u32)f,(u32)g,(u32)h,i,(u32)j};
 submissions++;for(int k=0;k<14;k++)if(args[k]!=row->expect[k])error=1;
}
static void setup(const Row *r){row=r;draws=submissions=0;error=0;seed=r->seed;
 for(int i=0;i<0x100;i++)record[i]=(u8)(i*29+123);
 *(s16 *)(record+0x14)=r->value;record[0x25]=r->scale;record[0x0C]=17;record[1]=0x80;
 for(int i=0;i<3;i++)*(s16 *)(record+0x18+i*2)=r->point[i];
}
static void(*volatile probe)(u8 *)=func_1516A538;
typedef char widths[sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4?1:-1];
static int run(void){
 for(u32 i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  setup(&rows[i]);probe(record);if(error||draws!=row->draws||submissions!=(row->draws!=0))return 1;
 }
 const Row *active=0;for(u32 i=0;i<sizeof(rows)/sizeof(rows[0]);i++)if(rows[i].draws==2&&rows[i].mutation==0){active=&rows[i];break;}
 if(!active)return 2;
 for(u32 value=0;value<65536;value++){
  setup(active);*(s16 *)(record+0x14)=(s16)(u16)value;probe(record);int enabled=(s16)(u16)value>=768;
  if(error||draws!=(enabled?2u:0u)||submissions!=(u32)enabled)return 1;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
if __name__=='__main__':unittest.main()
