"""Bounded byte-DMA contract for the uninstalled microcode-loader candidate."""
import itertools

from tools.experiments import game_microcode_loader as source
from tools.tests import game_graphics_task_submit_oracle as submit

put, read, signed, STACK = submit.put, submit.read, submit.signed, submit.STACK
STATE, STATE_OBJECT, TABLE = 0x800B0DF0, 0x70000, 0x80084078
FLAG, CACHE, PAIR_CACHE = 0x800BEB98, 0x80084070, 0x80084074
PRIMARY, SECONDARY, PRIMARY_DATA, SECONDARY_DATA = 0x800C1060, 0x800BEBB0, 0x800BEB9C, 0x800BEAD0
DMA, ROM_BASE = 0x10004514, 0x2D4B0
RETAIL_TABLE = (
    (0x4560, 0x5A70, 0x10460, 0x10B20), (0x6F80, 0x84B0, 0x111E0, 0x118A0),
    (0x5A70, 0x6F80, 0x10B20, 0x111E0), (0x84B0, 0x99E0, 0x118A0, 0x11F60),
    (0x99E0, 0xAE80, 0x11F60, 0x12620), (0xC320, 0xD7C0, 0x12CE0, 0x133A0),
    (0xAE80, 0xC320, 0x12620, 0x12CE0), (0xD7C0, 0xEC60, 0x133A0, 0x13A60))


def selectors(value, flag):
    variant, paired = (value - 2, 0) if value >= 2 else (value, 4)
    if flag == 1: variant += 2
    return variant, paired


def snapshot(memory):
    return (memory[CACHE], memory[PAIR_CACHE], read(memory, PRIMARY_DATA), read(memory, SECONDARY_DATA))


def payload(address, count):
    return bytes(((address + i) * 37 + ((address + i) >> 8) * 13 + 0x59) & 255 for i in range(count))


def transfer(memory, packet):
    address, destination, count, block = packet
    if block != 1 or count > 0x2000 or not all(destination + i in memory for i in range(count)):
        raise ValueError('DMA outside the explicit research fixture')
    for i, byte in enumerate(payload(address, count)): memory[destination + i] = byte


def effects(memory, number, variant, paired, mode):
    if number == 1 and mode & 1:
        row = TABLE + variant * 16
        for field, increment in ((4, 8), (8, 16), (12, 24)):
            put(memory, row + field, read(memory, row + field) + increment)
        memory[STATE_OBJECT + 43] = 255; put(memory, FLAG, 0x10001)
        put(memory, PRIMARY_DATA, 0x80405678)
    elif number == 2 and mode & 2:
        memory[CACHE], memory[PAIR_CACHE] = 0x80, 0xFE
    elif number == 3 and mode & 4:
        row = TABLE + (variant + paired) * 16
        for field, increment in ((4, 8), (8, 16), (12, 24)):
            put(memory, row + field, read(memory, row + field) + increment)
        put(memory, SECONDARY_DATA, 0x80506789)
    elif number == 4 and mode & 8:
        memory[CACHE], memory[PAIR_CACHE] = 0x81, 0xFD
        put(memory, PRIMARY_DATA, 0x8060789A); put(memory, SECONDARY_DATA, 0x807089AB)
    else: return False
    return True


def reference(initial, mode=0):
    memory, calls, observations, fired = dict(initial), [], [], []
    variant, paired = selectors(memory[read(memory, STATE) + 43], read(memory, FLAG))
    signed_byte = lambda value:(value ^ 128) - 128
    if variant == signed_byte(memory[CACHE]) and paired == signed_byte(memory[PAIR_CACHE]):
        return memory, calls, observations, fired
    def dma(start, end, destination):
        packet = ((start + ROM_BASE) & 0xFFFFFFFF, destination, (end - start) & 0xFFFFFFFF, 1)
        calls.append((DMA, packet)); observations.append(snapshot(memory))
        transfer(memory, packet)
        if effects(memory, len(calls), variant, paired, mode): fired.append(len(calls))
    row = TABLE + variant * 16
    dma(read(memory, row), read(memory, row + 4), PRIMARY)
    put(memory, PRIMARY_DATA, (PRIMARY + read(memory, row + 4) - read(memory, row)) & 0xFFFFFFFF)
    dma(read(memory, row + 8), read(memory, row + 12), read(memory, PRIMARY_DATA))
    memory[CACHE] = variant & 255; memory[PAIR_CACHE] = paired
    row = TABLE + (variant + paired) * 16
    dma(read(memory, row), read(memory, row + 4), SECONDARY)
    put(memory, SECONDARY_DATA, (SECONDARY + read(memory, row + 4) - read(memory, row)) & 0xFFFFFFFF)
    dma(read(memory, row + 8), read(memory, row + 12), read(memory, SECONDARY_DATA))
    return memory, calls, observations, fired


def fixture(value=0, flag=0, cache_mode=0, retail=False):
    memory = {STACK + i:(i * 17 + 0xA5) & 255 for i in range(-0x400, 0x100)}
    for base, count in ((STATE, 4), (STATE_OBJECT, 64), (CACHE, 8), (TABLE, 260 * 16),
            (FLAG, 8), (SECONDARY_DATA, 4), (PRIMARY, 0x3000), (SECONDARY, 0x2200)):
        memory.update({base + i:0xA5 for i in range(count)})
    put(memory, STATE, STATE_OBJECT); memory[STATE_OBJECT + 43] = value; put(memory, FLAG, flag & 0xFFFFFFFF)
    put(memory, PRIMARY_DATA, 0x80401230); put(memory, SECONDARY_DATA, 0x80502340)
    for index in range(260):
        record = RETAIL_TABLE[index] if retail and index < 8 else (
            0x2000 + index * 64, 0x2010 + index * 64, 0x10000 + index * 32, 0x10008 + index * 32)
        for field, word in enumerate(record): put(memory, TABLE + index * 16 + field * 4, word)
    variant, paired = selectors(value, flag & 0xFFFFFFFF)
    memory[CACHE], memory[PAIR_CACHE] = ((255, 255), (variant & 255, paired),
        (variant & 255, paired ^ 4), (128, 254), ((variant + 1) & 255, paired))[cache_mode]
    return memory


def corpus():
    for value, flag, cache_mode in itertools.product((0, 1, 2, 3, 4, 5, 7, 127, 128, 129, 255),
            (0, 1, 2, 0x10000, 0x10001, 0xFFFFFFFF, 0x80000001), range(5)):
        yield fixture(value, flag, cache_mode)


class LoaderOracle(submit.machine.InitializeOracle):
    def __init__(self, words, memory, phase=0, mode=0):
        super().__init__(words, memory, (0xDEADBEEF, 0x12345678), {}, phase, entry=source.ENTRY)
        self.variant, self.paired = selectors(memory[read(memory, STATE) + 43], read(memory, FLAG))
        self.loader_mode = mode

    def execute(self, word):
        if word >> 26 != 32: return super().execute(word)
        self.dispatched_word, self.own_instruction = word, True
        try:
            register, base = word >> 16 & 31, word >> 21 & 31
            offset = ((word & 65535) ^ 32768) - 32768
            byte = self.get((self.r[base] + offset) & 0xFFFFFFFF, 1)
            self.r[register] = ((byte ^ 128) - 128) & 0xFFFFFFFF
            self.r[0] = 0
        finally:
            self.own_instruction = False

    def record_call(self, target):
        if target != DMA: raise ValueError('Unexpected microcode provider: %X' % target)
        packet = self.arguments(4)
        self.calls.append((target, packet)); self.events.append(('CALL', target, packet))
        self.observations.append(snapshot(self.memory))

    def hook(self, target):
        transfer(self.memory, self.calls[-1][1])
        if effects(self.memory, len(self.calls), self.variant, self.paired, self.loader_mode):
            self.fired.append(len(self.calls))
        for i in range(4): self.put(self.r[29] + i * 4, 0xB5000000 + i, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = 0x11223344
