#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef int8_t s8;
typedef uint8_t u8;
typedef int16_t s16;
typedef uint16_t u16;
typedef int32_t s32;
typedef uint32_t u32;
typedef float f32;

typedef struct {
    s16 firstAngleBase;
    s16 firstAngleRange;
    s16 secondAngleBase;
    s16 secondAngleRange;
} AngularTrailInput;

typedef struct {
    f32 position[3];
    f32 timeBase;
    f32 timeRange;
    f32 scaleBase;
    f32 scaleRange;
    f32 radiusBase;
    f32 radiusRange;
    s16 countBase;
    s16 countRange;
    s16 requestSelectorBase;
    s16 requestSelectorRange;
    s16 durationBase;
    s16 durationRange;
    s16 modeBase;
    s16 modeRange;
    u8 selector;
    u8 private35[3];
    f32 opaqueChance;
    s16 firstValue;
    s16 secondValue;
    s32 requestValue;
} LocalizedTrailInput;

typedef struct {
    u8 before[16];
    AngularTrailInput angular;
    LocalizedTrailInput value;
    u8 after[16];
} GuardedInput;

typedef struct {
    u8 config[68];
    u8 velocity[12];
    u32 words[18];
} Capture;

typedef struct {
    GuardedInput input;
    Capture captures[2];
    u32 marks[2];
    s32 captureCount;
    s32 integerCount;
    s32 floatCount;
    s32 mutation;
    s32 seed;
    u8 channel;
    s32 error;
} State;

_Static_assert(sizeof(LocalizedTrailInput) == 68, "localized input extent");
_Static_assert(offsetof(LocalizedTrailInput, requestValue) == 64, "localized input layout");
_Static_assert(sizeof(AngularTrailInput) == 8, "angular input extent");
_Static_assert(offsetof(GuardedInput, value) == 24, "overlapping caller view");

static State state;
f32 D_800A6000;

static u32 bits(f32 value) {
    u32 result;
    memcpy(&result, &value, sizeof(result));
    return result;
}

static u32 rngValue(s32 index) {
    static const u32 values[8] = {0, 1, 2, 5, 17, 255, UINT32_MAX, 3};
    return values[(index + state.seed) & 7];
}

static f32 floatValue(s32 index) {
    static const f32 values[8] = {0.0f, 0.25f, 0.5f, 0.75f, -0.5f, 1.25f, -1.5f, 2.0f};
    return values[(index + state.seed) & 7];
}

static void setFields(LocalizedTrailInput *input, s32 late) {
    state.input.angular.firstAngleBase = late ? -37 : 11;
    state.input.angular.firstAngleRange = late ? 5 : 7;
    state.input.angular.secondAngleBase = late ? 72 : -23;
    state.input.angular.secondAngleRange = late ? 3 : 9;
    input->position[0] = late ? -8.0f : 1.25f + (f32)state.seed;
    input->position[1] = late ? 9.0f : -2.5f - (f32)state.seed;
    input->position[2] = late ? -10.0f : 3.75f + (f32)state.seed * 0.5f;
    input->timeBase = late ? -2.0f : 1.5f;
    input->timeRange = late ? 1.25f : 0.75f;
    input->scaleBase = late ? 5.0f : -1.25f;
    input->scaleRange = late ? -0.5f : 2.0f;
    input->radiusBase = late ? 4.0f : 0.5f;
    input->radiusRange = late ? 1.5f : 0.25f;
    input->countBase = late ? 1 : 0;
    input->countRange = late ? 1 : 2;
    input->requestSelectorBase = late ? -30 : 5;
    input->requestSelectorRange = late ? 2 : 3;
    input->durationBase = late ? -70 : 20;
    input->durationRange = late ? 2 : 4;
    input->modeBase = late ? 55 : 15;
    input->modeRange = late ? 3 : 5;
    input->selector = late ? 0x91 : 0x44;
    input->private35[0] = late ? 0x92 : 0x45;
    input->private35[1] = late ? 0x93 : 0x46;
    input->private35[2] = late ? 0x94 : 0x47;
    input->opaqueChance = late ? 0.6f : 0.4f;
    input->firstValue = late ? -1234 : 0x1234;
    input->secondValue = late ? 2345 : -4321;
    input->requestValue = late ? (s32)0x87654321u : 0x12345678;
}

static void mutate(s32 mask) {
    if (state.mutation & mask) {
        setFields(&state.input.value, 1);
    }
}

void func_15143794(s16 first, s16 second, f32 radius, f32 *output) {
    u32 word;
    word = (u32)(s32)first;
    memcpy(&output[0], &word, 4);
    word = (u32)(s32)second;
    memcpy(&output[1], &word, 4);
    output[2] = radius;
    mutate(2);
}

s32 func_150ADA20(void) {
    u32 result = rngValue(state.integerCount++);
    return (s32)result;
}

f32 func_150ADA68(void) {
    return floatValue(state.floatCount++);
}

u8 *func_151DA6F8(void *position, void *velocity, f32 scale, s16 duration,
                   s32 mode, f32 time, s32 requestSelector, s32 opaque,
                   f32 firstConstant, f32 secondConstant, s32 one, s32 selector,
                   s32 arg2, s16 firstValue, s16 secondValue, s32 requestValue,
                   s32 channel, s32 arg4) {
    Capture *capture;
    if (position != &state.input.value || state.captureCount >= 2) {
        state.error = position != &state.input.value ? 3 : 4;
        return 0;
    }
    capture = &state.captures[state.captureCount];
    memcpy(capture->config, &state.input.value, 68);
    memset(capture->config + 0x35, 0, 3);
    memcpy(capture->velocity, velocity, 12);
    capture->words[0] = 0x494E5054u;
    capture->words[1] = 0x56454C4Fu;
    capture->words[2] = bits(scale);
    capture->words[3] = (u32)(s32)duration;
    capture->words[4] = (u32)mode;
    capture->words[5] = bits(time);
    capture->words[6] = (u32)requestSelector;
    capture->words[7] = (u32)opaque;
    capture->words[8] = bits(firstConstant);
    capture->words[9] = bits(secondConstant);
    capture->words[10] = (u32)one;
    capture->words[11] = (u32)selector;
    capture->words[12] = (u32)arg2;
    capture->words[13] = (u32)(s32)firstValue;
    capture->words[14] = (u32)(s32)secondValue;
    capture->words[15] = (u32)requestValue;
    capture->words[16] = (u32)channel;
    capture->words[17] = (u32)arg4;
    state.marks[state.captureCount] = (u32)state.captureCount + 1;
    state.captureCount++;
    mutate(4);
    return 0;
}

void func_15153F18(AngularTrailInput *arg0, LocalizedTrailInput *arg1,
                    s32 arg2, s32 arg3, s32 arg4) {
    f32 velocity[3];
    f32 temp_f20;
    f32 temp_f22;
    f32 temp_f24;
    s32 remaining;
    u32 secondRandom;
    u32 firstRandom;
    u32 requestRandom;
    u32 modeRandom;
    u32 durationRandom;

    remaining = (u32)func_150ADA20() % ((u32)arg1->countRange + 1U)
                + arg1->countBase;
    if (remaining != 0) {
        temp_f24 = D_800A6000;
        do {
            firstRandom = (u32)func_150ADA20();
            secondRandom = (u32)func_150ADA20();
            func_15143794(
                (s16)(firstRandom % ((u32)arg0->firstAngleRange + 1U)
                      + arg0->firstAngleBase),
                (s16)(secondRandom % ((u32)arg0->secondAngleRange + 1U)
                      + arg0->secondAngleBase),
                func_150ADA68() * arg1->radiusRange + arg1->radiusBase,
                velocity);
            temp_f22 = func_150ADA68();
            durationRandom = (u32)func_150ADA20();
            modeRandom = (u32)func_150ADA20();
            temp_f20 = func_150ADA68();
            requestRandom = (u32)func_150ADA20();
            func_151DA6F8(
                arg1, velocity,
                temp_f22 * arg1->scaleRange + arg1->scaleBase,
                (s16)(durationRandom % ((u32)arg1->durationRange + 1U) + arg1->durationBase),
                modeRandom % ((u32)arg1->modeRange + 1U) + arg1->modeBase,
                temp_f20 * arg1->timeRange + arg1->timeBase,
                requestRandom % ((u32)arg1->requestSelectorRange + 1U) + arg1->requestSelectorBase,
                func_150ADA68() < arg1->opaqueChance,
                temp_f24, temp_f24, 1, arg1->selector, arg2,
                arg1->firstValue, arg1->secondValue, arg1->requestValue,
                ((u8 *)&arg3)[3], arg4);
            remaining--;
        } while (remaining != 0);
    }
}

static void model(AngularTrailInput *angular, LocalizedTrailInput *input,
                  s32 arg2, u8 channel, s32 arg4) {
    f32 velocity[3];
    s32 remaining;
    u32 firstRandom, secondRandom, durationRandom, modeRandom, requestRandom;
    f32 scaleRandom, timeRandom;
    remaining = (u32)func_150ADA20() % ((u32)input->countRange + 1U) + input->countBase;
    while (remaining != 0) {
        firstRandom = (u32)func_150ADA20();
        secondRandom = (u32)func_150ADA20();
        func_15143794(
            (s16)(firstRandom % ((u32)angular->firstAngleRange + 1U) + angular->firstAngleBase),
            (s16)(secondRandom % ((u32)angular->secondAngleRange + 1U) + angular->secondAngleBase),
            func_150ADA68() * input->radiusRange + input->radiusBase, velocity);
        scaleRandom = func_150ADA68();
        durationRandom = (u32)func_150ADA20();
        modeRandom = (u32)func_150ADA20();
        timeRandom = func_150ADA68();
        requestRandom = (u32)func_150ADA20();
        func_151DA6F8(
            input, velocity, scaleRandom * input->scaleRange + input->scaleBase,
            (s16)(durationRandom % ((u32)input->durationRange + 1U) + input->durationBase),
            modeRandom % ((u32)input->modeRange + 1U) + input->modeBase,
            timeRandom * input->timeRange + input->timeBase,
            requestRandom % ((u32)input->requestSelectorRange + 1U) + input->requestSelectorBase,
            func_150ADA68() < input->opaqueChance, D_800A6000, D_800A6000, 1,
            input->selector, arg2, input->firstValue, input->secondValue,
            input->requestValue, channel, arg4);
        remaining--;
    }
}

static void initialize(s32 index) {
    memset(&state, 0, sizeof(state));
    memset(state.input.before, 0xA5, sizeof(state.input.before));
    memset(state.input.after, 0x5A, sizeof(state.input.after));
    state.seed = index & 7;
    state.mutation = (index / 8) & 7;
    state.channel = (u8)index;
    setFields(&state.input.value, 0);
    D_800A6000 = 0.125f;
}

static s32 canaries(void) {
    s32 index;
    for (index = 0; index < 16; index++) {
        if (state.input.before[index] != 0xA5 || state.input.after[index] != 0x5A) return 0;
    }
    return 1;
}

int main(void) {
    State expected;
    s32 index;
    for (index = 0; index < 256; index++) {
        u32 repeated = (u32)index * 0x01010101u;
        s32 arg2 = (s32)(0x81000000u | (u32)(index & 7));
        s32 arg4 = (s32)(0xD4000000u | (u32)(index & 7) * 0x101u);
        initialize(index);
        model(&state.input.angular, &state.input.value, arg2, (u8)index, arg4);
        expected = state;
        initialize(index);
        func_15153F18(&state.input.angular, &state.input.value, arg2, (s32)repeated, arg4);
        if (state.error || !canaries() || memcmp(&state, &expected, sizeof(state)) != 0) {
            size_t at;
            const u8 *left = (const u8 *)&state;
            const u8 *right = (const u8 *)&expected;
            fprintf(stderr, "case=%d error=%d canaries=%d captures=%d/%d ints=%d/%d floats=%d/%d\n",
                    index, state.error, canaries(), state.captureCount, expected.captureCount,
                    state.integerCount, expected.integerCount, state.floatCount, expected.floatCount);
            for (at = 0; at < sizeof(state); at++) {
                if (left[at] != right[at]) {
                    fprintf(stderr, "first difference offset=%zu actual=%02X expected=%02X\n",
                            at, left[at], right[at]);
                    break;
                }
            }
            return index + 1;
        }
    }
    printf("{\"success\":true,\"cases\":256}\n");
    return 0;
}
