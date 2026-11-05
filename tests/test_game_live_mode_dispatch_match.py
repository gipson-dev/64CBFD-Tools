"""Live-mode callback: direct C, repeated state reads, literal owner and ELF."""
import itertools,json,struct,subprocess,unittest
from dataclasses import replace
from tools.experiments import game_live_mode_dispatch_candidates as candidate
from tools.experiments import game_live_mode_dispatch_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_live_mode_dispatch_oracle as model
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=candidate.ROOT
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses,m.observations
class LiveModeDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>72I',cls.rom,match.ROM));cls.raw=model.bound(cls.prepared['qualified_compact'],model.symbols());cls.words=model.bound(cls.prepared['qualified_owner'],model.symbols())
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('OriginalLiveMode',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(context,'original-live-mode',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert model.bound(cls.original,model.symbols())==cls.retail==cls.raw==cls.words
    def receipt(self,name,**v):(self.out/(name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
    def compare(self,c,initial=None,s=None,entry=match.ENTRY,images=None,helpers=None):
        s=model.symbols()if s is None else s;initial=model.fixture(c,s)if initial is None else initial;expected=model.reference(initial,c,s);ms=[]
        for words in(self.retail,self.raw,self.words)if images is None else images:
            m=model.Oracle(words,initial,c,s,entry,model.helper_code(self.rom,c)if helpers is None else helpers).run()
            self.assertEqual(m.calls,expected['calls'],c);self.assertEqual(m.observations,expected['observations'],c);self.assertEqual(model.public(m.memory),model.public(expected['memory']),c);ms.append(m)
        for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
        return ms
    def test_01_complete_owner_bindings_and_original_table(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['bindings']),(72,32,0,32));self.assertEqual(q['raw_neighbors'],q['neighbors'])
        raw,bindings=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+288]
        for at in range(288):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),bindings,truth)
        for at in bindings:
            bad=dict(bindings);bad[at]=[('R_MIPS_26','foreign')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.assertEqual(struct.unpack_from('>12I',self.rom,0x2348AC),model.HANDLERS)
        self.receipt('owner-controls',words=72,frame=32,guards=0,bindings=32,neighbors=q['neighbors'],raw_byte_corruptions=288,binding_corruptions=32,callback_table_entries=12,rodata_symbol=q['rodata_symbol'])
    def test_02_independent_live_protocol_all_countdown_bytes_and_coverage(self):
        count=0;seen=set()
        for c in model.cases():seen.update(self.compare(c)[0].visits);count+=1
        self.assertEqual(set(range(match.ENTRY,match.ENTRY+288,4))-seen,set());self.assertTrue(set(range(model.CMD,model.CMD+28,4))<=seen);self.assertTrue(set(range(model.LEAF,model.LEAF+8,4))<=seen)
        self.receipt('guest-contract',cases_per_body=count,bodies=3,all_72_words=True,all_256_countdown_bytes=True,all_7_original_command_helper_words=True,original_leaf_callback=True,phase_snapshots=True,wrapping_timer=True)
    def test_03_aliases_fault_prefixes_and_invalid_callback_slots(self):
        aliases=cuts=invalid=0
        for left,right in(('D_800E0B9A','D_800BE930'),('D_800E0A90','D_800BE9E4'),('D_8008FE28','D_800E0BDC'),('D_8003C8E0','D_800E0A90')):
            s=model.symbols();s[left]=s[right]
            images=[model.bound(obj,s)for obj in(self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])]
            for c in(model.Case(),model.Case(mode=7,countdown=128),model.Case(mode=8,mutation=7,after_callback=0)):
                self.compare(c,s=s,images=images);aliases+=1
        for c in(model.Case(),model.Case(mode=8,countdown=1,after_render=7),model.Case(mode=7,after_callback=0,mutation=7),model.Case(command_real=True,mode=2,leaf=True)):
            initial=model.fixture(c);code=model.helper_code(self.rom,c);done=model.Oracle(self.retail,initial,c,connected=code).run()
            for cut in range(done.all_accesses):
                ms=[]
                for words in(self.retail,self.raw,self.words):
                    m=model.Oracle(words,initial,c,connected=code);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    ms.append(m)
                for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
                cuts+=1
        for mode in(12,13,14,15,127,128,255):
            c=model.Case(mode=mode);initial=model.fixture(c)
            if mode in(12,13,14):model.put(initial,0x8008FDEC+mode*4,0x3F800000 if mode<14 else 0)
            ms=[]
            for words in(self.retail,self.raw,self.words):
                m=model.Oracle(words,initial,c)
                with self.assertRaises((AssertionError,KeyError)):m.run()
                ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            invalid+=1
        self.receipt('aliases-faults',mapped_global_aliases=aliases,fired_access_prefixes=cuts,invalid_physical_callback_indices=invalid,portable_invalid_access_claimed=False)
    def test_04_original_caller_before_after_gate(self):
        self.assertEqual(match.census(ROOT)['call'],0x15018890);pc=0x15018884;body=list(struct.unpack_from('>10I',self.rom,0x45D34));count=0
        for initial_flag,after,mode,phase in itertools.product((0,1),(0,1),(0,7,8),(0,8)):
            c=model.Case(mode=mode,caller_after=after,phase=phase,after_callback=7 if mode==8 else 8);initial=model.fixture(c);initial[0x800BE615]=initial_flag;expected=model.reference(initial,c);ms=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+288,4),target));m=model.Oracle(body,initial,c,entry=pc,connected=code);m.r[16]=0x800BE615;m.before=m.r[:]
                for end in(0x150188AC,0x15018DDC):m.code[end]=0
                m.code=model.WindowCode(m.code,m);m.code.ends=(0x150188AC,0x15018DDC)
                with self.assertRaises(model.WindowBoundary):m.run()
                self.assertEqual(m.calls,[]if initial_flag else[(match.ENTRY,())]+expected['calls'])
                self.assertEqual(m.current_pc,0x15018DDC if initial_flag or after else 0x150188AC)
                self.assertEqual(model.public(m.memory),model.public(initial)if initial_flag else model.public(expected['memory']));ms.append(m)
            for m in ms[1:]:self.assertEqual(state(ms[0]),state(m))
            count+=1
        self.receipt('caller',original_words=10,cases_per_body=count,precall_and_postcall_gate=True,whole_parent_or_gameplay_claimed=False,unchanged_caller_functions=self.prepared['report']['caller_functions_unchanged'])
    def test_05_independent_GNU_rebases_all_bindings(self):
        links=count=0
        for i,(entry,base)in enumerate(((match.ENTRY,0x81007FFC),(0x18018000,0x82018000),(0x1A02FFFC,0x8300FFFC))):
            s=model.symbols()
            for j,name in enumerate((*model.WIDTHS,'D_8008FDEC')):s[name]=base+j*0x10000
            s['func_15042D78']=0x17008000+i*0x200000;s['func_151E6964']=s['func_15042D78']+0x10000;images=[]
            self.assertNotIn(entry,(s['func_15042D78'],s['func_151E6964']))
            for j,obj in enumerate((self.original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=match.parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(i,j));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,*['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>72I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            cases=[replace(c,command_real=False,leaf=False)for c in list(model.cases())[::37]]+[model.Case(mode=m)for m in range(256)]
            for c in cases:self.compare(c,s=s,entry=entry,images=images,helpers={});count+=1
        self.receipt('rebases',GNU_links=links,cases_per_body=count,all_32_bindings=True,all_256_synthetic_mode_slots=True,physical_table_still_12_entries=True,HI_LO_carries=True)
    def test_06_native_and_effective_IDO_controls(self):
        witnesses=list(model.cases());effective=[]
        for name,body in model.controls().items():
            text=candidate.source_states((ROOT/candidate.SOURCE).read_text())[1].replace(candidate.SELECTED,body,1);obj,_=candidate.compile_owner(ROOT,self.out,text,'negative-'+name);words=model.bound(obj,model.symbols());fired=False
            for c in witnesses:
                initial=model.fixture(c);expected=model.reference(initial,c)
                try:
                    m=model.Oracle(words,initial,c,connected=model.helper_code(self.rom,c)).run();fired=m.calls!=expected['calls']or m.observations!=expected['observations']or model.public(m.memory)!=model.public(expected['memory'])
                except(AssertionError,IndexError,KeyError):fired=True
                if fired:break
            self.assertTrue(fired,name);effective.append(name)
        rows=[replace(c,command_real=False,leaf=False)for c in witnesses if not c.phase]
        for name,body,opt,wanted in [('positive-'+o[1:],candidate.SELECTED,o,0)for o in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in model.controls().items()]:
            p=self.out/('native-'+name+'.c');p.write_text(native_source(body,rows));exe=p.with_suffix('.elf')
            r=subprocess.run([*native_command(opt),'-mstackrealign','-fno-strict-aliasing',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''),name);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,name)
        self.receipt('native-controls',rows_per_profile=len(rows),executions=3*len(rows),profiles=['O0','O2','O3'],native_controls=len(effective),IDO_controls=effective,UBSan=True)
    def test_07_literal_image_serialization_and_stub(self):
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+288]
        delta=match.strict_image(before,after,truth);at=match.elf_slot_offset(after,match.ENTRY,288)
        offsets=(0,at,at+287,at+288,len(after)-1,*[p for p,names,order in match.SYMBOL_GROUPS],*[string for pos,name,fields,string in match.symbol_rows(after)if name in('D_800E0BDC','D_800BE930','func_15187978')])
        for off in offsets:
            bad=bytearray(after);bad[off]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        stub=list(struct.unpack_from('>72I',before,match.elf_slot_offset(before,match.ENTRY,288)));c=model.Case();m=model.Oracle(stub,model.fixture(c),c).run();self.assertFalse(m.calls);self.assertEqual(len(model.reference(model.fixture(c),c)['calls']),3)
        self.receipt('image-controls',literal_changed_bytes=delta,named_serialization_bytes=71,exclusions=0,corruptions=len(offsets),old_stub_rejected=True)

def native_source(body,cases):
    fields=list(model.WIDTHS);rows=[]
    for c in cases:
        initial=model.fixture(c);expected=model.reference(initial,c);values=[model.read(expected['memory'],model.symbols()[n],model.WIDTHS[n])for n in fields]
        calls=[(0 if t==model.CMD else 1 if t==model.RENDER else 2+model.HANDLERS.index(t),a[0]if a else 0)for t,a in expected['calls']]
        observations=[v for t,snapshot in expected['observations']for v in snapshot]
        rows.append('{%d,%d,%d,0x%Xu,0x%Xu,%d,%d,%d,%d,%d,{%s},{%s},{%s}}'%(c.mode,c.countdown,c.buttons,c.timer,c.ticks,c.after_command,c.after_render,c.after_callback,c.mutation,c.table_change,','.join('0x%Xu'%v for v in values),','.join('{%d,0x%Xu}'%q for q in calls),','.join('0x%Xu'%v for v in observations)))
    declarations='''extern u8 D_800E0B94,D_800E0B95;
extern s8 D_8008FE28;
extern s16 D_800E0B9A;
extern s32 D_800E0A90,D_800BE9E4;
'''
    globals='u8 D_800E0B94,D_800E0B95,D_800E0BDC,D_800CBD74,D_800BE615; s8 D_8008FE28; u16 D_800BE930; s16 D_800E0B9A; s32 D_800E0A90,D_800BE9E4,D_8003C8E0;\n'
    read_fields=','.join('(u32)'+('(u16)'if model.WIDTHS[n]==2 else'(u8)'if model.WIDTHS[n]==1 else'')+n for n in fields)
    return '#include <ultra64.h>\n'+declarations+candidate.DECLARATIONS+body+'\n'+globals+r'''
typedef struct {u32 id,arg;} Call;
typedef struct {u8 mode,count;u16 buttons;u32 timer,ticks;s32 cmd,render,callback;u32 mutation,change;u32 result[11];Call calls[3];u32 observations[33];} Row;
static const Row rows[]={
'''+',\n'.join(rows)+r'''
};
static const Row *row;static u32 ordinal;static int error;
void(*D_8008FDEC[256])(void);
static void(*callbacks[12])(void);
static void snapshot(u32 *values){u32 v[11]={'''+read_fields+r'''};for(int i=0;i<11;i++)values[i]=v[i];}
static void effect(u32 phase){s32 mode=phase==0?row->cmd:phase==1?row->render:row->callback;
 if(mode>=0)D_800E0B94=(u8)mode;
 if(row->mutation&(1u<<phase)){
  static const u32 times[3]={0x80000000u,0xFFFFFFFEu,0x7FFFFFFFu},ticks[3]={0xFFFFFFFFu,3,0x80000001u};
  D_800E0A90=(s32)times[phase];D_800BE9E4=(s32)ticks[phase];
  if(phase==0){D_8008FE28=-1;D_800BE930=0x8001;}else{D_800E0B9A=(s16)(phase==1?0x4321:0x8765);D_800E0BDC=(u8)(0x30+phase);}
 }
 if(phase==1&&row->change)D_8008FDEC[D_800E0B94]=callbacks[(D_800E0B94+1)%12];
}
static void logcall(u32 id,u32 arg,u32 phase){
 if(ordinal>=3){error=1;return;}u32 values[11];snapshot(values);
 if(row->calls[ordinal].id!=id||row->calls[ordinal].arg!=arg)error=1;
 for(int i=0;i<11;i++)if(values[i]!=row->observations[ordinal*11+i])error=1;
 ordinal++;effect(phase);
}
void func_15042D78(u8 arg){logcall(0,arg,0);D_800CBD74=arg;}
s32 func_151E6964(s32 arg){logcall(1,(u32)arg,1);return(s32)0x87654321;}
'''+ '\n'.join('static void cb%d(void){logcall(%d,0,2);}'%(i,i+2)for i in range(12))+r'''
static void(*volatile probe)(void)=func_151E51EC;
typedef char widths[sizeof(void*)==4&&sizeof(s8)==1&&sizeof(s16)==2&&sizeof(s32)==4?1:-1];
static int run(void){
'''+ '\n'.join('callbacks[%d]=cb%d;'%(i,i)for i in range(12))+r'''
 for(u32 n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];ordinal=0;error=0;
  D_800E0B94=row->mode;D_800E0B95=0xD3;D_800E0BDC=0x31;D_800BE930=row->buttons;D_800E0B9A=0x5A5A;
  D_800E0A90=(s32)row->timer;D_800BE9E4=(s32)row->ticks;D_8008FE28=(s8)row->count;D_8003C8E0=(s32)0x87654321;D_800CBD74=0x42;D_800BE615=0;
  for(u32 i=0;i<256;i++)D_8008FDEC[i]=callbacks[i%12];
  probe();u32 values[11];snapshot(values);if(error||ordinal!=3)return 1;
  for(int i=0;i<11;i++)if(values[i]!=row->result[i])return 1;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
if __name__=='__main__':unittest.main()
