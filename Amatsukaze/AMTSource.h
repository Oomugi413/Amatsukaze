/**
* Amtasukaze Avisynth Source Plugin
* Copyright (c) 2017-2019 Nekopanda
*
* This software is released under the MIT License.
* http://opensource.org/licenses/mit-license.php
*/
#pragma once

#include "common.h"
#include "rgy_util.h"
#include "AviSynthWrapper.h"

#include <memory>
#include <vector>
#include <array>
#include <mutex>
#include <set>
#include <deque>
#include <unordered_map>
#include <functional>
#include "ConvertPix.h"
#include "StreamReform.h"
#include "ReaderWriterFFmpeg.h"

namespace av {

struct FakeAudioSample {

    enum {
        MAGIC = 0xFACE0D10,
        VERSION = 1
    };

    int32_t magic;
    int32_t version;
    int64_t index;
};

struct AMTSourceData {
    std::vector<FilterSourceFrame> frames;
    std::vector<FilterAudioFrame> audioFrames;
};

class AMTSource : public IClip, AMTObject {
public:
    // AVFrameはコールバック内でのみ有効。呼び出し側では保持しないこと
    using DirectFrameCallback = std::function<void(int, const AVFrame*, const AVFrame*, int, int)>;
    using DirectAliasCallback = std::function<void(int, int)>;

private:
    const std::vector<FilterSourceFrame>& frames;
    const std::vector<FilterAudioFrame>& audioFrames;
    DecoderSetting decoderSetting;
    std::string filterdesc;
    int decodeThreads;
    int audioSamplesPerFrame;
    bool interlaced;

    bool outputQP; // QPテーブルを出力するか

    InputContext inputCtx;
    CodecContext codecCtx;

#if ENABLE_FFMPEG_FILTER
    FilterGraph filterGraph;
    AVFilterContext* bufferSrcCtx;
    AVFilterContext* bufferSinkCtx;
#endif

    AVStream *videoStream;

    std::unique_ptr<AMTSourceData> storage;

    struct CacheFrame {
        PVideoFrame data;
        int key;
    };

    std::map<int, CacheFrame*> frameCache;
    std::deque<CacheFrame*> recentAccessed;

    // デコードできなかったフレームの置換先リスト
    std::map<int, int> failedMap;

    VideoInfo vi;

    std::mutex mutex;

    File waveFile;

    int seekDistance;

    // OnFrameDecodedで直前にデコードされたフレーム
    // まだデコードしてない場合は-1
    int lastDecodeFrame;

    // codecCtxが直前にデコードしたフレーム番号
    // まだデコードしてない場合はnullptr
    std::unique_ptr<Frame> prevFrame;

    // 直前のnon B QPテーブル
    PVideoFrame nonBQPTable;

    ConvertPixFuncs convertPix;

    DirectFrameCallback directFrameCallback;
    bool directScanUsed;

    const AVCodec* getHWAccelCodec(AVCodecID vcodecId);

    void MakeCodecContext(IScriptEnvironment* env);

#if ENABLE_FFMPEG_FILTER
    void MakeFilterGraph(IScriptEnvironment* env);
#endif

    void MakeVideoInfo(const VideoFormat& vfmt, const AudioFormat& afmt);

    void UpdateVideoInfo(IScriptEnvironment* env);

    void ResetDecoder(IScriptEnvironment* env);

    template <typename T>
    void Copy1(T* dst, const T* top, const T* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
        for (int y = 0; y < h; y += 2) {
            T* dst0 = dst + dpitch * (y + 0);
            T* dst1 = dst + dpitch * (y + 1);
            const T* src0 = top + tpitch * (y + 0);
            const T* src1 = bottom + bpitch * (y + 1);
            memcpy(dst0, src0, sizeof(T) * w);
            memcpy(dst1, src1, sizeof(T) * w);
        }
    }

    template <typename T>
    void Copy2(T* dstU, T* dstV, const T* top, const T* bottom, int w, int h, int dpitch, int tpitch, int bpitch) {
        for (int y = 0; y < h; y += 2) {
            T* dstU0 = dstU + dpitch * (y + 0);
            T* dstU1 = dstU + dpitch * (y + 1);
            T* dstV0 = dstV + dpitch * (y + 0);
            T* dstV1 = dstV + dpitch * (y + 1);
            const T* src0 = top + tpitch * (y + 0);
            const T* src1 = bottom + bpitch * (y + 1);
            for (int x = 0; x < w; x++) {
                dstU0[x] = src0[x * 2 + 0];
                dstV0[x] = src0[x * 2 + 1];
                dstU1[x] = src1[x * 2 + 0];
                dstV1[x] = src1[x * 2 + 1];
            }
        }
    }

    template <typename T>
    void MergeField(PVideoFrame& dst, AVFrame* top, AVFrame* bottom, const int dstBitDepth, const int srcBitDepth, IScriptEnvironment* env) {
        const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get((AVPixelFormat)(top->format));
        if (!desc) {
            const char* formatName = av_get_pix_fmt_name((AVPixelFormat)(top->format));
            env->ThrowError("unsupported input pixel format: %s", formatName ? formatName : "unknown");
        }

        const bool nv12 = top->format == AV_PIX_FMT_NV12 || top->format == AV_PIX_FMT_P010LE;

        // P010を含む16bit格納形式はuint16_t、それ以外はuint8_tとして扱う。
        // Avisynth側の出力形式と入力AVFrameの形式が異なる場合はConvertPixFuncsを使用する。
        const int srcElementSize = (srcBitDepth > 8) ? sizeof(uint16_t) : sizeof(uint8_t);
        const int dstElementSize = (dstBitDepth > 8) ? sizeof(uint16_t) : sizeof(uint8_t);
        const void* srctY = top->data[0];
        const void* srctU = top->data[1];
        const void* srctV = (!nv12) ? top->data[2]
            : (const uint8_t*)top->data[1] + srcElementSize;
        const void* srcbY = bottom->data[0];
        const void* srcbU = bottom->data[1];
        const void* srcbV = (!nv12) ? bottom->data[2]
            : (const uint8_t*)bottom->data[1] + srcElementSize;
        void* dstY = dst->GetWritePtr(PLANAR_Y);
        void* dstU = dst->GetWritePtr(PLANAR_U);
        void* dstV = dst->GetWritePtr(PLANAR_V);

        const int srctPitchY = top->linesize[0] / srcElementSize;
        const int srctPitchUV = top->linesize[1] / srcElementSize;
        const int srcbPitchY = bottom->linesize[0] / srcElementSize;
        const int srcbPitchUV = bottom->linesize[1] / srcElementSize;
        const int dstPitchY = dst->GetPitch(PLANAR_Y) / dstElementSize;
        const int dstPitchUV = dst->GetPitch(PLANAR_U) / dstElementSize;
        const int widthUV = vi.width >> desc->log2_chroma_w;
        const int heightUV = vi.height >> desc->log2_chroma_h;

        if (dstBitDepth != srcBitDepth) {
            if (convertPix.convert1 && convertPix.convert2) {
                convertPix.convert1(dstY, srctY, srcbY, vi.width, vi.height, dstPitchY, srctPitchY, srcbPitchY);

                if (nv12) {
                    convertPix.convert2(dstU, dstV, srctU, srcbU, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
                } else {
                    convertPix.convert1(dstU, srctU, srcbU, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
                    convertPix.convert1(dstV, srctV, srcbV, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
                }
            } else {
                const char* formatName = av_get_pix_fmt_name((AVPixelFormat)(top->format));
                env->ThrowError("not supported conversion: %s (%dbit) -> Avisynth (%dbit)",
                    formatName ? formatName : "unknown", srcBitDepth, dstBitDepth);
            }
        } else {
            T* dstYTyped = (T*)dstY;
            T* dstUTyped = (T*)dstU;
            T* dstVTyped = (T*)dstV;
            const T* srctYTyped = (const T*)srctY;
            const T* srctUTyped = (const T*)srctU;
            const T* srctVTyped = (const T*)srctV;
            const T* srcbYTyped = (const T*)srcbY;
            const T* srcbUTyped = (const T*)srcbU;
            const T* srcbVTyped = (const T*)srcbV;

            Copy1<T>(dstYTyped, srctYTyped, srcbYTyped, vi.width, vi.height, dstPitchY, srctPitchY, srcbPitchY);

            if (nv12) {
                Copy2<T>(dstUTyped, dstVTyped, srctUTyped, srcbUTyped, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
            } else {
                Copy1<T>(dstUTyped, srctUTyped, srcbUTyped, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
                Copy1<T>(dstVTyped, srctVTyped, srcbVTyped, widthUV, heightUV, dstPitchUV, srctPitchUV, srcbPitchUV);
            }
        }
    }

    PVideoFrame MakeFrame(AVFrame * top, AVFrame * bottom, IScriptEnvironment * env);

    void MakeAndPutFrame(int n, Frame& top, Frame& bottom, IScriptEnvironment* env);

    void PutFrame(int n, const PVideoFrame & frame);

    int AVSFormatBitdepth(const int avsformat);
    int toAVSFormat(AVPixelFormat format, IScriptEnvironment * env);

#if ENABLE_FFMPEG_FILTER
    void InputFrameFilter(Frame* frame, bool enableOut, IScriptEnvironment* env);

    void OnFrameDecoded(Frame& frame, IScriptEnvironment* env);
#endif

    void OnFrameOutput(Frame& frame, IScriptEnvironment* env);

    void UpdateAccessed(CacheFrame* frame);

    void ClearFrameCache();

    int ForceGetFrameIndex(int n);

    int ResolveFrame(int n, IScriptEnvironment* env);

    void DecodeLoop(int goal, IScriptEnvironment* env);

    void registerFailedFrames(int begin, int end, int replace, IScriptEnvironment* env);

public:
    AMTSource(AMTContext& ctx,
        const tstring& srcpath,
        const tstring& audiopath,
        const VideoFormat& vfmt, const AudioFormat& afmt,
        const std::vector<FilterSourceFrame>& frames,
        const std::vector<FilterAudioFrame>& audioFrames,
        const DecoderSetting& decoderSetting,
        const int threads,
        const char* filterdesc,
        bool outputQP,
        IScriptEnvironment* env);

    ~AMTSource();

    void TransferStreamInfo(std::unique_ptr<AMTSourceData>&& streamInfo);

    PVideoFrame __stdcall GetFrame(int n, IScriptEnvironment* env);

    void ScanFramesDirect(int begin, int end,
        const DirectFrameCallback& frameCallback,
        const DirectAliasCallback& aliasCallback,
        IScriptEnvironment* env);

    void __stdcall GetAudio(void* buf, int64_t start, int64_t count, IScriptEnvironment* env);

    const VideoInfo& __stdcall GetVideoInfo();

    bool __stdcall GetParity(int n);

    int __stdcall SetCacheHints(int cachehints, int frame_range);
};

extern AMTContext* g_ctx_for_plugin_filter;

void SaveAMTSource(
    const tstring& savepath,
    const tstring& srcpath,
    const tstring& audiopath,
    const VideoFormat& vfmt, const AudioFormat& afmt,
    const std::vector<FilterSourceFrame>& frames,
    const std::vector<FilterAudioFrame>& audioFrames,
    const DecoderSetting& decoderSetting);

PClip LoadAMTSource(const tstring& loadpath, const char* filterdesc, bool outputQP, IScriptEnvironment* env);

std::unique_ptr<AMTSource> LoadAMTSourceDirect(AMTContext& ctx, const tstring& loadpath, int threads, IScriptEnvironment* env);

AVSValue CreateAMTSource(AVSValue args, void* user_data, IScriptEnvironment* env);

} // namespace av {
