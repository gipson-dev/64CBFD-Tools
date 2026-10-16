"""Ordered word-memory model for the fixed two-row graphics setup."""
from tools.tests.game_view_render_pass_oracle import RenderOracle, STACK, put, read
from tools.experiments import game_view_list_setup as source

GLOBALS, GLOBAL_BYTES = 0x800BE600, 0x400
BUFFERS, BUFFER_BYTES = 0x20000, 0x2000
DISPLAY, DISPLAY_BYTES = 0x8002C930, 64
INPUT, OUTPUT, END, DEPTH, VIEWS = 0x800BE9C8, 0x800BE9D8, 0x800BE9E0, 0x800BE9C4, 0x800BE628
REGIONS = ((GLOBALS,GLOBAL_BYTES),(BUFFERS,BUFFER_BYTES),(DISPLAY,DISPLAY_BYTES))


def fixture(first=BUFFERS+32,second=BUFFERS+0x1020,depth=0x12345678,views=0x80000000):
    memory = {STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,size in REGIONS:memory.update({base+i:0xA5 for i in range(size)})
    for address,value in ((INPUT,first),(INPUT+4,second),(DEPTH,depth),(VIEWS,views)):
        put(memory,address,value)
    return memory


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


def reference(initial):
    memory = dict(initial)
    for row in range(2):
        cursor = read(memory,INPUT+row*4)
        for offset in (0,8):
            put(memory,(cursor+offset)&0xFFFFFFFF,0xDB060000)
            put(memory,(cursor+offset+4)&0xFFFFFFFF,0)
        put(memory,(cursor+16)&0xFFFFFFFF,0xDE000000)
        put(memory,(cursor+20)&0xFFFFFFFF,DISPLAY)
        put(memory,(cursor+24)&0xFFFFFFFF,0xFE000000)
        depth = read(memory,DEPTH)
        put(memory,(cursor+28)&0xFFFFFFFF,depth)
        put(memory,(cursor+32)&0xFFFFFFFF,0xDC080008)
        viewport = (read(memory,VIEWS)+row*16+64)&0xFFFFFFFF
        put(memory,(cursor+36)&0xFFFFFFFF,viewport)
        put(memory,OUTPUT+row*4,(cursor+40)&0xFFFFFFFF)
    return memory


def corpus():
    normal = [(BUFFERS+64,BUFFERS+0x1020)]+[(BUFFERS+96,BUFFERS+96+delta) for delta in range(-48,49,4)]
    aliases = sorted(set(range(VIEWS-40,VIEWS+5,4))|set(range(DEPTH-48,DEPTH+9,4))|
        set(range(OUTPUT-16,OUTPUT+9,4)))
    pairs = normal+[(a,BUFFERS+0x1020) for a in aliases]+[(BUFFERS+64,a) for a in aliases]
    values = ((0,0),(0x80000000,0x7FFFFFF0),(0xFFFFFFFF,0xFFFFFFC0),(0x12345678,0x80000000))
    for first,second in pairs:
        for depth,views in values:
            memory = fixture(first,second,depth,views)
            final = reference(memory)
            # Qualify complete runs only when every command store stays mapped.
            if set(final)==set(memory):yield memory,(first,second,depth,views)
    for index in range(32):
        args = (BUFFERS+32,BUFFERS+0x1020,(index*1664525+1013904223)&0xFFFFFFFF,
            (index*22695477+1)&0xFFFFFFFF)
        yield fixture(*args),args


class ListSetupOracle(RenderOracle):
    def __init__(self,words,memory,phase=0,entry=source.ENTRY,connected=None):
        self.trace = []
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(0x12345678,0xFEDCBA98),connected=connected)

    def get(self,address,size):
        value = super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:
            assert all(address+i in self.memory for i in range(size)),('unmapped graphics store',address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def record_call(self,target):
        assert target==source.ENTRY,hex(target)
        self.calls.append((target,()))

    def hook(self,target):
        raise AssertionError('Unexpected provider in leaf graphics setup')
