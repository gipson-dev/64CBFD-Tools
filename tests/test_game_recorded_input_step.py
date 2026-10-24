"""Recorded-input playback: ordering, signed gates, private caller and guards."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_recorded_input_step as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
SYMBOLS=dict(D_800E0A70=0x800E0A70,D_800E0A74=0x800E0A74,D_800E0BD2=0x800E0BD2,D_800BE748=0x800BE748,D_800BE9E4=0x800BE9E4)
WINDOW,END,WINDOW_ROM=0x1501BEE0,0x1501BF1C,0x49390
INDEXES=(0,1,498,499,500,0xFFFFFFFE,0x7FFFFFFF,0x80000000)
TIMES=(0,1,255,256,65535,0xFFFFFFFF,0x80000000,0x7FFFFFFF)
BUTTONS=tuple(sorted({0,0xFFFF,0xA5A5,0x5A5A,*(1<<i for i in range(16))}))
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000


@dataclass(frozen=True)
class Case:
    index:int=0
    previous:int=1
    next:int=300
    current:int=17
    buttons:int=0xA53C
    held:int=0xFFFF
    x:int=0x80
    y:int=0x7F
    layout:int=0


def fixture(c,s=None):
    s=s or SYMBOLS;ptr,cursor,gap,pad,time=(s[n]for n in SYMBOLS)
    record=(0x40000,pad-2,pad,gap-4,cursor-2,time-2,time-8,ptr-2)[c.layout]
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base,size in((record-16,64),(pad,12),(ptr,8),(gap,2),(time,4)):
        m.update({base+i:(i*13+0xA5)&255 for i in range(size)})
    put(m,record,c.x,1);put(m,record+1,c.y,1);put(m,record+2,c.current,2);put(m,record+4,c.buttons,2);put(m,record+8,c.next,2)
    put(m,ptr,(record-6*signed(c.index))&0xFFFFFFFF);put(m,cursor,c.index);put(m,time,c.previous)
    put(m,pad,c.held,2);put(m,gap,0xA5,1)
    return m,record


def reference(initial,s=None):
    s=s or SYMBOLS;ptr,cursor,gap,pad,time=(s[n]for n in SYMBOLS);m=dict(initial)
    index=read(m,cursor);record=(read(m,ptr)+6*index)&0xFFFFFFFF
    x=read(m,record,1);held=read(m,pad,2);put(m,pad+2,x,1)
    y=read(m,record+1,1);put(m,pad+3,y,1)
    buttons=read(m,record+4,2);put(m,gap,0,1);put(m,pad,buttons|(held&0x1000),2)
    if signed(index)<499:
        nxt=read(m,record+8,2);previous=read(m,time)
        if signed(previous)<nxt:put(m,gap,(nxt-previous)&255,1)
    current=read(m,record+2,2);put(m,time,current)
    index=(index+1)&0xFFFFFFFF;put(m,cursor,index)
    if signed(index)>=499:put(m,cursor,499)
    return m


def observable(m):return m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,tuple(m.r[i]for i in(*range(16,24),28,29,30,31))


class InputOracle(RayOracle):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(0x87654321,0xFEDCBA98,0xA5A5A5A5,0x5A5A5A5A),connected=connected)

    def record_call(self,target):
        assert target==source.ENTRY,hex(target)
        self.calls.append((target,()));self.events.append(('CALL',target,()))

    def hook(self,target):raise AssertionError(('unowned recorded-input helper',hex(target)))


class WindowBoundary(Exception):pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==END:raise WindowBoundary
        return super().__getitem__(pc)


def corpus():
    for index,previous,nxt,phase in itertools.product(INDEXES,TIMES,(0,1,255,256,65535),(0,8)):
        yield Case(index,previous,nxt),phase
    for byte,axis,phase in itertools.product(range(256),(0,1),(0,8)):
        yield Case(x=byte if axis==0 else 0x80,y=byte if axis==1 else 0x7F),phase
    for buttons,held,phase in itertools.product(BUTTONS,BUTTONS,(0,8)):
        yield Case(buttons=buttons,held=held),phase
    for layout,index,previous,nxt,phase in itertools.product(range(8),(0,498,499,0xFFFFFFFE),(0,0x80000000),(1,65535),(0,8)):
        yield Case(index,previous,nxt,layout=layout),phase


def native_cases():
    for index,previous,nxt,buttons,held in itertools.product((0,1,498,499,500,0xFFFFFFFE),TIMES,(0,1,256,65535),(0,0xA53C,0xFFFF),(0,0x1000,0xFFFF)):
        yield Case(index,previous,nxt,17,buttons,held,(nxt^0x80)&255,(previous^0x7F)&255)


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,wrong_start=b.replace('0x1000','0x2000'),drop_start=b.replace('(held & 0x1000)','(held & 0)'),
        wrong_button_field=b.replace('buttons = record->buttons;','buttons = record->ticks;'),wrong_y=b.replace('stick_y = record->y','stick_y = record->x'),
        missing_gap_clear=b.replace('D_800E0BD2 = 0;','(void)buttons;'),inverted_time=b.replace('previous < next','previous > next'),
        unsigned_time=b.replace('previous < next','(u32)previous < (u32)next'),wrong_cap=b.replace('499','498'),
        wrong_timestamp=b.replace('D_800BE9E4 = record->ticks;','D_800BE9E4 = record[1].ticks;'),
        no_advance=b.replace('(u32)index + 1U','(u32)index + 0U'),unsigned_index=b.replace('if (index < 499)','if ((u32)index < 499U)'))


def native_harness():
    rows=[]
    for c in native_cases():
        initial,_=fixture(c);expected=reference(initial)
        vals=(c.index,c.previous,c.next,c.current,c.buttons,c.held,c.x,c.y,
            read(expected,SYMBOLS['D_800BE748'],2),read(expected,SYMBOLS['D_800BE748']+2,1),read(expected,SYMBOLS['D_800BE748']+3,1),
            read(expected,SYMBOLS['D_800E0BD2'],1),read(expected,SYMBOLS['D_800BE9E4']),read(expected,SYMBOLS['D_800E0A74']))
        rows.append('{'+','.join('0x%Xu'%v for v in vals)+'}')
    text=source.HEADERS+source.DECLARATIONS+'''
RecordedInput20A990 *D_800E0A70;
s32 D_800E0A74,D_800BE9E4;
u8 D_800E0BD2;
OSContPad D_800BE748;
typedef char record_size[sizeof(RecordedInput20A990)==6?1:-1];
typedef char tick_offset[__builtin_offsetof(RecordedInput20A990,ticks)==2?1:-1];
typedef char pad_x[__builtin_offsetof(OSContPad,stick_x)==2?1:-1];
static struct{u32 left[4];RecordedInput20A990 records[505];u32 right[4];} actual,saved;
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError(name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    text+='''typedef struct{u32 index,previous,next,current,buttons,held,x,y,ob,ox,oy,og,ot,oi;} Row;
static const Row rows[]={
'''+',\n'.join(rows)+'''};
static int variant(void(*fn)(void)){
 u32 i,j;const Row*r;RecordedInput20A990 *record;u8*p=(u8*)&actual,*q=(u8*)&saved;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  r=rows+i;for(j=0;j<sizeof(actual);j++)p[j]=(u8)(j*13+0xA5);
  D_800E0A70=actual.records+2;D_800E0A74=(s32)r->index;D_800BE9E4=(s32)r->previous;D_800E0BD2=0xA5;
  D_800BE748.button=(u16)r->held;D_800BE748.stick_x=1;D_800BE748.stick_y=2;D_800BE748.errno=0x5A;
  record=D_800E0A70+(s32)r->index;record->x=(s8)r->x;record->y=(s8)r->y;record->ticks=(u16)r->current;
  record->buttons=(u16)r->buttons;record[1].ticks=(u16)r->next;
  for(j=0;j<sizeof(actual);j++)q[j]=p[j];
  fn();
  if(D_800BE748.button!=r->ob||(u8)D_800BE748.stick_x!=r->ox||(u8)D_800BE748.stick_y!=r->oy)return 23;
  if(D_800E0BD2!=r->og||(u32)D_800BE9E4!=r->ot||(u32)D_800E0A74!=r->oi)return 23;
  if(D_800BE748.errno!=0x5A||D_800E0A70!=actual.records+2)return 23;
  for(j=0;j<sizeof(actual);j++)if(p[j]!=q[j])return 23;
 }return 0;
}
int run(void){
'''
    for i,label in enumerate(controls()):text+='if(variant(%s)!=%d)return %d;\n'%(label,0 if label=='selected'else 23,i+1)
    return text+'return 0;}\n'+START,len(rows)


class RecordedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()==cls.values[source.SOURCE]:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        else:source.audit(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM));cls.images=[]
        for obj in(cls.out/'after-owner.o',cls.out/'qualified-padded.o',cls.out/'make-shadow-target/src/game/generated_20A990.c.o'):
            data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER);cls.images.append(list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value'])))

    def compare(self,c,phase=0):
        initial,_=fixture(c);expected=reference(initial);models=[]
        for words in(self.truth,*self.images):
            m=InputOracle(words,initial,phase).run();self.assertEqual(m.memory,expected,c);self.assertFalse(m.calls);models.append(m)
        for i in(2,3):self.assertEqual(complete(models[0]),complete(models[i]))
        self.assertEqual(observable(models[0]),observable(models[1]));return models[0]

    def test_01_derived_roles_schedule_bindings_and_all_corruptions(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(source.normalized(raw,rs),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        for i in range(43):
            bad=bytearray(raw);bad[i*4]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
        for at in rs:
            bad=dict(rs);bad.pop(at)
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        with self.assertRaises(ValueError):source.normalized(raw[:-4],rs)
        bad=dict(rs);bad[172]=[('R_MIPS_HI16','D_800E0A74')]
        with self.assertRaises(ValueError):source.normalized(raw,bad)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],3)
        self.assertEqual(q['alignment_words'],1);self.assertEqual(self.rom[source.ROM+172:source.ROM+176],bytes(4))
        self.receipt.update(words=43,slot_words=44,alignment_words=1,frame=0,bindings=12,new_guards=40,compiler_only=False,
            preserved_neighbors=3,normalizer_corruptions=57,branch_target_derived_from_permutation=True)

    def test_02_signed_ticks_buttons_all_stick_bytes_and_eight_alias_layouts(self):
        count=0;visits=set()
        for c,phase in corpus():m=self.compare(c,phase);visits.update(m.visits);count+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+172,4))<=visits)
        self.receipt.update(guest_root_phases=count,all_43_words_visited=True,stick_bytes=256,button_masks=len(BUTTONS),alias_layouts=8,
            signed_time_and_index_boundaries=True,raw_volatile_GPRs_and_fault_PC_not_equated=True)

    def test_03_actual_original_mode_gate_and_call_window(self):
        ptr=struct.pack('>I',source.ENTRY);self.assertFalse(any(self.rom[i:i+4]==ptr for i in range(0,len(self.rom),4)))
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x493B4])
        original=list(struct.unpack_from('>15I',self.rom,WINDOW_ROM));count=0
        modes={(a,b)for value in range(256)for a,b in((value,0),(0,value),(value,2),(2,value))}
        for (a,b),index,phase in itertools.product(sorted(modes),(0,499),(0,8)):
            c=Case(index=index);initial,_=fixture(c);put(initial,0x800E0B94,a,1);put(initial,0x800E0B95,b,1)
            active=a==2 or b==2;expected=reference(initial)if active else dict(initial);sp=STACK+phase
            if active:put(expected,sp+0x54,1)
            models=[]
            for words in(self.truth,*self.images):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=InputOracle(original,initial,phase,WINDOW,connected);m.r[10]=7;m.code=WindowCode(m.code,m)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.memory,expected);self.assertEqual(m.r[9],int(active));self.assertEqual(m.r[10],7)
                self.assertEqual(m.calls,[(source.ENTRY,())]if active else[]);models.append(m)
            for k in(2,3):self.assertEqual(complete(models[0]),complete(models[k]))
            self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        caller=self.values['conker/src/game/generated_48FD0.c'].decode();lo,hi=source.function_span(caller,'func_1501BBB8')
        self.assertEqual(caller[lo:hi],'s32 func_1501BBB8() {\n    return 0;\n}')
        self.receipt.update(original_caller_window_words=15,actual_window_phases=count,mode_bytes=256,no_argument_void_callback=True,
            full_parent_C_or_gameplay_claimed=False)

    def test_04_native32_wrapping_integer_arithmetic_and_defined_controls(self):
        text,count=native_harness();unit=self.out/'native32.c';unit.write_text(text)
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:12000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=count,native_optimizations=['O0','O2','O3'],effective_wrong_C_controls=11,
            trap_UBSan=True,complete_allocated_record_storage=True,explicit_unsigned_gap_and_cursor_arithmetic=True,
            native_private_alias_or_out_of_array_pointer_claimed=False)

    def test_05_fired_literal_access_prefixes_preserve_complete_fitted_state(self):
        count=0
        for c,phase in itertools.product((Case(),Case(index=499),Case(previous=0x80000000),Case(layout=2),Case(layout=3)),(0,8)):
            initial,_=fixture(c);done=InputOracle(self.truth,initial,phase).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.truth,*self.images):
                    m=InputOracle(words,initial,phase);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                for k in(2,3):self.assertEqual(complete(models[0]),complete(models[k]))
                self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        self.receipt.update(fired_root_access_prefixes=count,complete_fitted_private_state_equal=True,portable_C_fault_semantics_claimed=False)

    def test_06_independent_GNU_links_aliases_and_HI_LO_carries(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        from tools.experiments.game_actor_classifier_candidates import sections
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'after-owner.o',self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_20A990.c.o');links=count=0
        layouts=((source.ENTRY,SYMBOLS),(0x18017FFC,dict(zip(SYMBOLS,(0x800A7FFC,0x800A8000,0x800C7FFE,0x800B8000,0x800D8000)))),
            (0x1A028000,dict(zip(SYMBOLS,(0x800A8000,0x800A8004,0x800C8000,0x800B7FFC,0x800D7FFC)))))
        for i,(entry,s)in enumerate(layouts):
            images=[]
            for k,obj in enumerate(objects):
                data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(i,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            for k in(2,3):self.assertEqual(images[0],images[k])
            for layout,index,previous,phase in itertools.product((0,2,3),(0,499),(0,0x80000000),(0,8)):
                c=Case(index=index,previous=previous,layout=layout);initial,_=fixture(c,s);expected=reference(initial,s);models=[]
                for words in images:
                    m=InputOracle(words,initial,phase,entry).run();self.assertEqual(m.memory,expected);models.append(m)
                for k in(2,3):self.assertEqual(complete(models[0]),complete(models[k]))
                self.assertEqual(observable(models[0]),observable(models[1]));count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,HI_LO_carry_boundaries=True)

    def test_07_compiled_bad_capture_controls_and_terminal_read_gate(self):
        body=source.SELECTED[source.FUNCTION]
        wrong={'clear_before_buttons':body.replace('    buttons = record->buttons;\n    D_800E0BD2 = 0;',
            '    D_800E0BD2 = 0;\n    buttons = record->buttons;'),
            'early_current_tick':body.replace('    u16 buttons;','    u16 buttons;\n    u16 early;').replace('    D_800BE748.stick_x',
                '    early = record->ticks;\n    D_800BE748.stick_x',1).replace('D_800BE9E4 = record->ticks;','D_800BE9E4 = early;')}
        for name,b in wrong.items():
            obj,diag=source.compile_owner(ROOT,self.out,source.HEADERS+source.DECLARATIONS+b,'wrong-'+name);self.assertFalse(diag)
            raw,_=source.payload(obj,source.FUNCTION);data,fs=source.link_owner(ROOT,self.out,obj,source.OWNER)
            words=list(struct.unpack_from('>%dI'%(len(raw)//4),data,fs[source.FUNCTION]['value']))
            c=Case(layout=3 if name=='clear_before_buttons'else 2);initial,_=fixture(c)
            self.assertNotEqual(InputOracle(words,initial).run().memory,reference(initial),name)
        for index in(499,500,0x7FFFFFFF):
            c=Case(index=index);initial,record=fixture(c)
            for at in(record+8,record+9):initial.pop(at,None)
            for words in(self.truth,*self.images):self.assertEqual(InputOracle(words,initial).run().memory,reference(initial))
        self.receipt.update(compiled_capture_negative_controls=2,terminal_next_record_read_suppressed=True)

    def test_08_strict_image_closed_metadata_cycles_and_actual_padder_controls(self):
        old=self.values['conker/build/conker.us.elf'];bodies=source.truths(self.values);expected=source.predicted_image(old,bodies)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        named={name:at for at,name,fields,loc in source.symbol_rows(expected)}
        offsets=[0,len(expected)-1,source.elf_slot_offset(expected,source.ENTRY,176),*[named[n]+4 for n in('D_800E0A70','D_8009A0A8','D_80099260','D_800A3560','D_800A3108','D_800E0A74','D_800E0A31','D_80099264','D_800A3564')]]
        for at in offsets:
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(bad),bodies)
        guard=self.values['conker/retail_word_patches.us.csv'];raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION);new=source.guard_bytes(guard,raw,rs)
        rows=list(csv.DictReader(io.StringIO(new.decode())));prior=list(csv.DictReader(io.StringIO(guard.decode())))
        self.assertEqual(rows[:-40],prior);self.assertTrue(new.startswith(guard));self.assertTrue(all(r['function']==source.FUNCTION for r in rows[-40:]))
        from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
        blob=bytearray((self.out/'after-owner.o').read_bytes());h=ELF_HEADER.unpack_from(blob);ss=[SECTION_HEADER.unpack_from(blob,h[6]+i*h[11])for i in range(h[12])]
        sn=ss[h[13]];names=blob[sn[4]:sn[4]+sn[5]];text=next(s for s in ss if read_c_string(names,s[0])=='.text')
        _,fs,_=source.parse_object(self.out/'after-owner.o');blob[text[4]+fs[source.FUNCTION]['value']+1]^=1
        p=self.out/'wrong-expected.o';p.write_bytes(blob)
        with self.assertRaises(ValueError):source.emit_padded_assembly(p,ROOT/source.ASM,word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        rows[-40]['expected_relocations']='-';stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[-1]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
        bad=self.out/'wrong-relocation.csv';bad.write_text(stream.getvalue())
        with self.assertRaises(ValueError):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=bad,filename=source.OWNER)
        with self.assertRaises(ValueError):source.guard_bytes(guard+b'\n',raw,rs)
        self.receipt.update(strict_image_corruptions=len(offsets),closed_symbol_cycles=[5,4],metadata_exclusions=0,actual_padder_corruptions=2,old_guard_prefix_byte_identical=True)
