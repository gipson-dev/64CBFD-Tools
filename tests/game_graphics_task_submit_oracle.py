"""Ordered graphics submission semantics with explicit cache/queue/ucode contracts."""
import itertools

from tools.experiments import game_graphics_task_submit as source
from tools.tests import game_viewport_initialize_oracle as machine
from tools.tests import game_view_list_setup_oracle as lists

put, read, signed, STACK = machine.put, machine.read, machine.signed, machine.STACK
PAGE, ROWS, CURSOR, ENDS = 0x800BE9C0, 0x800BE9C8, 0x800BE9D0, 0x800BE9D8
TASK, TASKS, PROGRAM, VIEW_COUNT, DIRTY, COUNTER = 0x800BEAD4, 0x800BEAD8, 0x800BEBA0, 0x80082FA0, 0x800BE617, 0x800BEAA8
INIT, UCODE, CACHE, SEND = 0x1501A39C, 0x1501CC3C, 0x10024F10, 0x10023580
OTHER, THIRD, BUFFERS = 0x60000, 0x61000, 0x20000
REGIONS = ((0x800BE600, 0x1000), (BUFFERS, 0x9000), (OTHER, 0x200), (THIRD, 0x200),
    (0x80038080, 32), (0x8002AAE8, 1024), (VIEW_COUNT, 4))


def public(memory):
    return {a:v for a,v in memory.items() if not STACK - 0x400 <= a < STACK + 0x100}


def effects(memory, target, mode):
    if mode == 1 and target == INIT: memory[PAGE] ^= 1
    elif mode == 2 and target == UCODE:
        put(memory, TASK, OTHER); memory[PROGRAM] ^= 1
        put(memory, 0x800BEB9C, 0x80402340); put(memory, 0x800BEAD0, 0x80501230)
    elif mode == 3 and target == CACHE:
        put(memory, TASK, THIRD); memory[PAGE] ^= 1
    elif mode == 4 and target == SEND:
        memory[PAGE] = 255; put(memory, COUNTER, 0xFFFF, 2)
    elif mode == 5 and target == UCODE:
        memory[DIRTY] = 1; put(memory, VIEW_COUNT, 0x7FFFFFFF)
    elif mode == 6 and target == INIT:
        put(memory, ROWS + 4, (read(memory, ROWS + 4) + 800) & 0xFFFFFFFF)
    else: return False
    return True


def reference(initial, args, mode=0):
    memory, calls, fired = dict(initial), [], []
    def call(target, packet=()):
        nonlocal memory
        calls.append((target, tuple(p & 0xFFFFFFFF for p in packet)))
        if target == INIT: memory = lists.reference(memory)
        if effects(memory, target, mode): fired.append(target)
    def task(offset, value): put(memory, read(memory, TASK) + offset, value)
    def start(): return read(memory, ROWS + memory[PAGE] * 4)
    def commands():
        for word in (0xE9000000, 0xDF000000):
            pointer = read(memory, CURSOR)
            put(memory, CURSOR, (pointer + 8) & 0xFFFFFFFF)
            put(memory, pointer + 4, 0); put(memory, pointer, word)
    put(memory, TASK, TASKS + memory[PAGE] * 96); task(0, 0)
    capacity = signed((read(memory, ROWS + 4) - read(memory, ROWS)) & 0xFFFFFFFF) >> 3
    first = start(); used = signed((read(memory, CURSOR) - first) & 0xFFFFFFFF) >> 3
    if used < 0 or capacity < used:
        call(INIT); put(memory, CURSOR, read(memory, ENDS + memory[PAGE] * 4)); commands()
        first = start(); used = signed((read(memory, CURSOR) - first) & 0xFFFFFFFF) >> 3
    remaining = signed((capacity - 400) & 0xFFFFFFFF)
    if used < 0 or remaining < used:
        put(memory, CURSOR, (first + remaining * 8) & 0xFFFFFFFF); commands(); first = start()
    task(0x48, first)
    task(0x4C, (signed((read(memory, CURSOR) - start()) & 0xFFFFFFFF) >> 3) * 8 & 0xFFFFFFFF)
    call(UCODE)
    for offset, value in ((0x18, 1), (0x1C, 4), (0x20, 0x100290D0), (0x24, 0xD0)):
        task(offset, value)
    task(0x28, 0x800C1060 if memory[PROGRAM] else 0x800BEBB0)
    task(0x30, read(memory, 0x800BEB9C if memory[PROGRAM] else 0x800BEAD0))
    for offset, value in ((0x34, 0x800), (0x38, 0x800CBE10), (0x3C, 0x400),
            (0x40, read(memory, 0x80038090)), (0x44, read(memory, 0x80038094)),
            (0x50, 0x8003A5E8), (0x54, 0xC00), (0xC, 0x23)):
        task(offset, value)
    if args[1]: task(0xC, read(memory, read(memory, TASK) + 0xC) | 0x40)
    if memory[DIRTY]:
        task(0xC, read(memory, read(memory, TASK) + 0xC) | (((read(memory, VIEW_COUNT) + 1) << 16) & 0xFFFFFFFF))
        memory[DIRTY] = 0
    task(0x58, 0x800BEA10); task(0x5C, 0x800BEA68 + memory[PAGE] * 32)
    task(0x10, read(memory, 0x8002AAE8 + memory[PAGE] * 4))
    call(CACHE); call(SEND, (0x8003B1E8, read(memory, TASK), 1))
    if args[1]: memory[PAGE] ^= 1
    put(memory, COUNTER, (read(memory, COUNTER, 2) + 1) & 65535, 2)
    return memory, calls, fired


def fixture(capacity=1000, used=20, page=0, program=0, swap=1, dirty=0, views=0, counter=0, remainder=0):
    memory = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-0x400, 0x100)}
    for base, size in REGIONS: memory.update({base + i:0xA5 for i in range(size)})
    first = BUFFERS + 0x4000; second = first + capacity * 8
    for address, value in ((ROWS, first), (ROWS + 4, second), (CURSOR, (first if page == 0 else second) + used * 8 + remainder),
            (ENDS, first + 40), (ENDS + 4, second + 40), (TASK, THIRD), (VIEW_COUNT, views & 0xFFFFFFFF),
            (0x800BE9C4, 0x80300000), (0x800BE628, 0x80200000), (0x800BEAD0, 0x80340000),
            (0x800BEB9C, 0x80450000), (0x80038090, 0x80560000), (0x80038094, 0x80670000)):
        put(memory, address, value & 0xFFFFFFFF)
    for p in range(256): put(memory, 0x8002AAE8 + p * 4, 0x80700000 + p * 0x100)
    memory[PAGE], memory[PROGRAM], memory[DIRTY] = page, program, dirty
    put(memory, COUNTER, counter & 65535, 2)
    return memory, (0xDEADBEEF, swap & 0xFFFFFFFF)


def corpus():
    for capacity in (399, 400, 401, 1000):
        for used, page, program, swap, dirty in itertools.product((-1, 0, capacity - 400, capacity - 399, capacity, capacity + 1),
                (0, 1), (0, 1), (0, 1, 0x10000, 0x80000000), (0, 1)):
            yield fixture(capacity, used, page, program, swap, dirty)
    for views, counter, remainder in itertools.product((0, 1, 0x7FFFFFFF, -1),
            (0x7FFF, 0x8000, 0xFFFF), (1, 3, 7)):
        yield fixture(views=views, counter=counter, remainder=remainder, dirty=255)
    for capacity in (-100, 0, 1):
        for used, page in itertools.product((-1, 0, capacity, capacity + 1), (0, 1)):
            yield fixture(capacity=capacity, used=used, page=page, swap=0x10000, dirty=1, remainder=7)


class SubmitOracle(machine.InitializeOracle):
    def __init__(self, words, memory, args, helper=None, phase=0, mode=0, entry=source.ENTRY):
        super().__init__(words, memory, args, helper or {}, phase, entry=entry)
        self.mode = mode

    def record_call(self, target):
        assert target in (INIT, UCODE, CACHE, SEND), hex(target)
        packet = self.arguments(3) if target == SEND else ()
        self.calls.append((target, packet)); self.events.append(('CALL', target, packet))

    def hook(self, target):
        assert target in (INIT, UCODE, CACHE, SEND), hex(target)
        if target == INIT: self.memory = lists.reference(self.memory)
        if effects(self.memory, target, self.mode): self.fired.append(target)
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344
