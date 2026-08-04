/**
* Amtasukaze Avisynth Source Plugin
* Copyright (c) 2017-2019 Nekopanda
*
* This software is released under the MIT License.
* http://opensource.org/licenses/mit-license.php
*/

#include <cstdint>
#include <type_traits>
#include "ConvertPix.h"
#include "rgy_simd.h"

namespace {

// デコーダが返す画素形式に応じて、Avisynth側のビット深度へ変換する。
// 8bitはuint8_t、10/12bitおよびP010相当の16bitはuint16_tで保持する。
template <int dstDepth, int srcDepth>
void Convert1Depth(void* dst, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    using DstType = std::conditional_t<(dstDepth > 8), uint16_t, uint8_t>;
    using SrcType = std::conditional_t<(srcDepth > 8), uint16_t, uint8_t>;
    Convert1<DstType, SrcType, dstDepth, srcDepth, false>(
        (DstType*)dst, (const SrcType*)top, (const SrcType*)bottom,
        w, h, dpitch, tpitch, bpitch);
}

template <int dstDepth, int srcDepth>
void Convert2Depth(void* dstU, void* dstV, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    using DstType = std::conditional_t<(dstDepth > 8), uint16_t, uint8_t>;
    using SrcType = std::conditional_t<(srcDepth > 8), uint16_t, uint8_t>;
    using SrcInterleavedType = std::conditional_t<(srcDepth > 8), uint32_t, uint16_t>;
    Convert2<DstType, SrcType, SrcInterleavedType, dstDepth, srcDepth, false>(
        (DstType*)dstU, (DstType*)dstV, (const SrcType*)top, (const SrcType*)bottom,
        w, h, dpitch, tpitch, bpitch);
}

}

void Convert1_16_to_10(void* dst, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    Convert1<uint16_t, uint16_t, 10, 16, false>((uint16_t*)dst, (const uint16_t*)top, (const uint16_t*)bottom, w, h, dpitch, tpitch, bpitch);
}

void Convert1_16_to_12(void* dst, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    Convert1<uint16_t, uint16_t, 12, 16, false>((uint16_t*)dst, (const uint16_t*)top, (const uint16_t*)bottom, w, h, dpitch, tpitch, bpitch);
}

void Convert2_16_to_10(void* dstU, void* dstV, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    Convert2<uint16_t, uint16_t, uint32_t, 10, 16, false>((uint16_t*)dstU, (uint16_t*)dstV, (const uint16_t*)top, (const uint16_t*)bottom, w, h, dpitch, tpitch, bpitch);
}

void Convert2_16_to_12(void* dstU, void* dstV, const void* top, const void* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
    Convert2<uint16_t, uint16_t, uint32_t, 12, 16, false>((uint16_t*)dstU, (uint16_t*)dstV, (const uint16_t*)top, (const uint16_t*)bottom, w, h, dpitch, tpitch, bpitch);
}

ConvertPixFuncs::ConvertPixFuncs() :
    convert1(nullptr),
    convert2(nullptr),
    dstDepth(0),
    srcDepth(0) {}

ConvertPixFuncs::ConvertPixFuncs(int dstDepth, int srcDepth) :
    convert1(nullptr),
    convert2(nullptr),
    dstDepth(dstDepth),
    srcDepth(srcDepth) {
    const bool avx2 = ((get_availableSIMD() & RGY_SIMD::AVX2) == RGY_SIMD::AVX2);

    if (srcDepth == 8) {
        if (dstDepth == 10) {
            convert1 = &Convert1Depth<10, 8>;
            convert2 = &Convert2Depth<10, 8>;
        } else if (dstDepth == 12) {
            convert1 = &Convert1Depth<12, 8>;
            convert2 = &Convert2Depth<12, 8>;
        }
    } else if (srcDepth == 10) {
        if (dstDepth == 8) {
            convert1 = &Convert1Depth<8, 10>;
            convert2 = &Convert2Depth<8, 10>;
        } else if (dstDepth == 12) {
            convert1 = &Convert1Depth<12, 10>;
            convert2 = &Convert2Depth<12, 10>;
        }
    } else if (srcDepth == 12) {
        if (dstDepth == 8) {
            convert1 = &Convert1Depth<8, 12>;
            convert2 = &Convert2Depth<8, 12>;
        } else if (dstDepth == 10) {
            convert1 = &Convert1Depth<10, 12>;
            convert2 = &Convert2Depth<10, 12>;
        }
    } else if (srcDepth == 16) {
        if (dstDepth == 8) {
            convert1 = &Convert1Depth<8, 16>;
            convert2 = &Convert2Depth<8, 16>;
        } else if (dstDepth == 10) {
            convert1 = avx2 ? &Convert1_16_to_10_AVX2 : &Convert1_16_to_10;
            convert2 = avx2 ? &Convert2_16_to_10_AVX2 : &Convert2_16_to_10;
        } else if (dstDepth == 12) {
            convert1 = avx2 ? &Convert1_16_to_12_AVX2 : &Convert1_16_to_12;
            convert2 = avx2 ? &Convert2_16_to_12_AVX2 : &Convert2_16_to_12;
        }
    }
}
