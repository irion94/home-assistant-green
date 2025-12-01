# STT Accuracy Improvement Plan

**Date**: 2025-11-28
**Current Problem**: Polish STT accuracy is 0-25% (essentially unusable)
**Error Types**: Wrong words, missing words, extra words, gibberish - across all scenarios
**User Rating**: 0-25% accuracy

---

## Executive Summary

The current STT system uses:
- **Vosk**: `vosk-model-small-pl-0.22` (92MB, WER 11-18% on test sets)
- **Whisper**: `faster-whisper-base` (142MB)
- **Audio**: ReSpeaker 4 Mic Array with 2x gain boost
- **Confidence threshold**: 0.7 (Vosk→Whisper fallback trigger)

**Root Cause Analysis:**

1. **Model Limitations**:
   - Vosk small-pl is the ONLY Polish model available (no large model exists)
   - Whisper "base" is too small for Polish (research shows large models significantly better for non-English)
   - No model fine-tuning for home automation vocabulary

2. **Audio Quality Issues**:
   - ReSpeaker reports "max input: 0 channels" (ALSA misconfiguration)
   - Only 2x software gain (may be insufficient for far-field speech)
   - Using single channel (mono) - not leveraging beamforming capabilities

3. **Pipeline Configuration**:
   - Streaming STT may be introducing latency/quality tradeoffs
   - VAD parameters may be cutting off speech prematurely
   - Initial prompt hints good but may not cover all scenarios

---

## Improvement Options (Ranked by Impact)

### Option 1: Upgrade Whisper Model Size ⭐⭐⭐⭐⭐
**Impact**: High | **Effort**: Low | **Cost**: Medium (RAM/CPU)

**Rationale**:
- Research shows large models perform SIGNIFICANTLY better for Polish than small/base
- Current "base" model (142MB) → Upgrade to "large-v3" (~3GB)
- BIGOS V2 benchmark (2024): Whisper Large V3 is best accuracy for Polish
- faster-whisper optimized for Raspberry Pi (4x faster than original)

**Implementation**:
```yaml
# In docker-compose.yml wake-word service:
- WHISPER_MODEL=large-v3  # Currently: base
```

**Trade-offs**:
- ✅ Significant accuracy improvement for Polish
- ✅ Better handling of domain-specific vocabulary
- ❌ Higher RAM usage (~3GB vs 142MB)
- ❌ Slower inference (~2-3s vs 0.5s)
- ❌ First-time model download ~3GB

**Recommended**: YES - This is the single biggest improvement

---

### Option 2: Polish-Specific Whisper Distilled Model ⭐⭐⭐⭐
**Impact**: High | **Effort**: Medium | **Cost**: Low

**Rationale**:
- `distil-whisper-large-v3-pl` exists (3x faster, 49% smaller than large-v3)
- Optimized specifically for Polish language
- Better balance of speed/accuracy than generic models

**Implementation**:
Requires custom integration (not available in faster-whisper):
1. Download model from HuggingFace
2. Integrate with transformers library
3. Update whisper_client.py to use custom model

**Trade-offs**:
- ✅ 3x faster than large-v3
- ✅ Polish-specific optimizations
- ✅ Lower resource usage than large-v3
- ❌ Requires code changes (not drop-in replacement)
- ❌ Additional dependencies

**Recommended**: Consider after Option 1 testing

---

### Option 3: Fix Audio Hardware Configuration ⭐⭐⭐⭐
**Impact**: Medium-High | **Effort**: Medium | **Cost**: Zero

**Current Issues**:
- ReSpeaker reports 0 input channels (ALSA config issue)
- Not using beamforming (6-mic array → 1 channel mono)
- May need ALSA .asoundrc configuration

**Implementation**:
1. Create proper ALSA configuration for ReSpeaker
2. Enable beamforming (use preprocessed beam channel)
3. Test different gain levels (2x may be too conservative)
4. Verify microphone positioning and distance

**Diagnostic Steps**:
```bash
# Check if seeed-voicecard driver installed
arecord -l

# Test multi-channel recording
arecord -D hw:2,0 -f S16_LE -r 16000 -c 6 test.wav

# Check beamformed channel quality
# ReSpeaker channels: 0-3 = raw mics, 4 = beamformed, 5 = processed
```

**Trade-offs**:
- ✅ Free improvement (no model changes)
- ✅ Better noise rejection with beamforming
- ✅ Improved far-field performance
- ❌ Requires low-level audio debugging
- ❌ May need kernel module updates

**Recommended**: YES - Do in parallel with Option 1

---

### Option 4: Alternative Models (wav2vec2, Nemo) ⭐⭐⭐
**Impact**: Medium | **Effort**: High | **Cost**: High (complexity)

**Candidates**:
- **wav2vec2-large-xlsr-53-polish**: WER 14.21% on Common Voice Polish
- **NVIDIA Nemo**: Polish models available, similar performance to wav2vec2

**Challenges**:
- Raspberry Pi 4 evaluation shows high latency for real-time
- Requires PyTorch (large dependency footprint)
- Integration complexity (different pipeline than Vosk/Whisper)

**Trade-offs**:
- ✅ Potentially better accuracy than Whisper base
- ❌ High computational overhead
- ❌ Complex integration
- ❌ Slower than faster-whisper

**Recommended**: NO - Not worth complexity vs Whisper large-v3

---

### Option 5: Improve Vosk Performance ⭐⭐
**Impact**: Low | **Effort**: Medium | **Cost**: Zero

**Limitations**:
- NO large Polish model exists (only vosk-model-small-pl-0.22)
- Current model already optimized (WER 11-18% on benchmarks)

**Potential Improvements**:
1. **Custom language model adaptation**:
   - Train ARPA language model with home automation vocabulary
   - Vosk supports LM adaptation for domain-specific terms

2. **Adjust confidence threshold**:
   - Current: 0.7 (70%)
   - Lower → More Whisper fallback (slower but more accurate)
   - Higher → More Vosk usage (faster but less accurate)

**Implementation**:
```bash
# Create custom ARPA LM with home automation phrases
kaldi/egs/wsj/s5/utils/prepare_lang.sh \
  --vocabulary home_automation.txt \
  --arpa-lm output.arpa
```

**Trade-offs**:
- ✅ Free improvement
- ✅ Domain-specific vocabulary boost
- ❌ Limited impact (model fundamentally constrained)
- ❌ Requires Kaldi expertise

**Recommended**: MAYBE - Low priority, try after Options 1 & 3

---

### Option 6: Tune VAD and Audio Parameters ⭐⭐
**Impact**: Low-Medium | **Effort**: Low | **Cost**: Zero

**Current Configuration**:
```python
# In audio_capture.py:
silence_threshold = 1000       # Audio level below this = silence
silence_chunks_to_stop = 12    # ~1s of silence to stop
min_speech_chunks = 8          # Minimum ~0.7s of speech
```

**Potential Issues**:
- Cutting off speech too early (missing end of words)
- Not capturing complete utterances
- VAD too aggressive for Polish phonetics

**Implementation**:
```yaml
# Add to docker-compose.yml wake-word service environment:
- VAD_SILENCE_THRESHOLD=800    # Lower = more sensitive (currently 1000)
- VAD_SILENCE_CHUNKS=15        # Longer pause before stop (currently 12)
- VAD_MIN_SPEECH_CHUNKS=6      # Allow shorter commands (currently 8)
```

**Trade-offs**:
- ✅ Free tuning
- ✅ May capture more complete utterances
- ❌ Longer recordings (more processing time)
- ❌ May capture unwanted audio (false positives)

**Recommended**: MAYBE - Experimental, easy to test

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (Week 1)
**Goal**: Achieve 50-75% accuracy

1. **Upgrade Whisper to large-v3** ⭐⭐⭐⭐⭐
   - Change: `WHISPER_MODEL=large-v3` in docker-compose.yml
   - Test: Record 20 Polish commands, measure accuracy before/after
   - Expected: 50-100% improvement in transcription quality

2. **Fix ReSpeaker Audio Configuration** ⭐⭐⭐⭐
   - Verify ALSA driver installation
   - Test beamformed channel (channel 4 instead of channel 0)
   - Adjust gain if needed (try 3x-4x)
   - Expected: Better far-field recognition, less noise

3. **Tune Confidence Threshold** ⭐⭐
   - Lower to 0.5-0.6 to trigger Whisper more often
   - Monitor latency impact
   - Expected: More accurate results, slightly slower

### Phase 2: Advanced Optimization (Week 2-3)
**Goal**: Achieve 75-90% accuracy

4. **Consider Polish Distilled Whisper** ⭐⭐⭐⭐
   - If large-v3 too slow, integrate distil-whisper-large-v3-pl
   - 3x faster, similar accuracy

5. **Custom Vosk Language Model** ⭐⭐
   - Create domain-specific ARPA LM
   - Test if Vosk primary recognition improves

6. **VAD Parameter Tuning** ⭐⭐
   - Experiment with silence thresholds
   - Capture complete utterances

### Phase 3: Production Hardening (Week 4)
**Goal**: Reliable 90%+ accuracy

7. **Multi-Model Ensemble**
   - Use Vosk for quick commands (<3 words)
   - Use Whisper large-v3 for complex commands
   - Smart routing based on audio characteristics

8. **Continuous Monitoring**
   - Log all transcriptions with confidence scores
   - Identify failure patterns
   - Retrain/adapt models based on real usage

---

## Testing Methodology

### Baseline Test Set (Before Changes)
Create 20 test phrases covering:
- Short commands: "Zapal światło" (2 words)
- Medium commands: "Włącz światło w salonie" (4 words)
- Long commands: "Ustaw temperaturę w sypialni na dwadzieścia stopni" (7 words)
- Various rooms: salon, kuchnia, sypialnia, łazienka
- Different actions: włącz, wyłącz, ustaw, sprawdź, pokaż

### Accuracy Metrics
- **WER (Word Error Rate)**: Industry standard
- **Sentence Accuracy**: % of perfectly transcribed commands
- **Intent Accuracy**: % where intent correctly understood (even if words wrong)
- **Latency**: Time from speech end → transcription complete

### Test Procedure
1. Record each phrase 3 times in quiet room
2. Record each phrase 3 times with background noise (TV, music)
3. Record each phrase 3 times from 2-3 meters away
4. Calculate metrics for each configuration change

---

## Resource Requirements

### RAM Impact
| Configuration | Vosk | Whisper | Total | Available (RPi5 8GB) |
|---------------|------|---------|-------|----------------------|
| Current       | 92MB | 142MB   | ~234MB | ✅ OK |
| large-v3      | 92MB | ~3GB    | ~3.2GB | ✅ OK (but significant) |
| distil-pl     | 92MB | ~1.5GB  | ~1.6GB | ✅ Better fit |

### CPU Impact
| Model | Inference Time | Impact on UX |
|-------|---------------|--------------|
| base  | 0.5-1s | ✅ Instant |
| large-v3 | 2-4s | ⚠️ Noticeable delay |
| distil-pl | 1-1.5s | ✅ Acceptable |

### Storage Impact
| Model | Size | Available (SSD) |
|-------|------|-----------------|
| base  | 142MB | ✅ OK |
| large-v3 | ~3GB | ✅ OK (plenty of space) |

---

## Success Criteria

### Minimum Viable (Phase 1)
- ✅ 50% accuracy in quiet environment
- ✅ 70% intent recognition (even if words imperfect)
- ✅ 3-5s total latency (wake → response)

### Target (Phase 2)
- ✅ 75% accuracy in quiet environment
- ✅ 50% accuracy with background noise
- ✅ 85% intent recognition
- ✅ 4-6s total latency

### Ideal (Phase 3)
- ✅ 90% accuracy in quiet environment
- ✅ 75% accuracy with background noise
- ✅ 95% intent recognition
- ✅ 3-5s total latency (through optimization)

---

## Rollback Plan

If changes cause issues:

1. **Whisper Model Rollback**:
   ```yaml
   # Revert to base in docker-compose.yml:
   - WHISPER_MODEL=base
   ```

2. **Audio Config Rollback**:
   ```bash
   # Remove custom ALSA config
   rm /mnt/data-ssd/ha-data/alsa/.asoundrc
   docker compose restart wake-word
   ```

3. **VAD Rollback**:
   ```yaml
   # Remove VAD overrides from docker-compose.yml
   # Defaults will be used
   ```

All changes are configuration-only (no code modifications in Phase 1), making rollback trivial.

---

## Next Steps

1. **User Decision Required**:
   - Approve Phase 1 implementation plan?
   - Willing to accept 2-4s Whisper latency for better accuracy?
   - Prioritize accuracy over speed?

2. **Pre-Implementation**:
   - Create baseline test set (20 phrases)
   - Record current accuracy metrics
   - Backup current configuration

3. **Implementation Order**:
   - Start with Whisper large-v3 upgrade (biggest impact)
   - Parallel: Debug ReSpeaker audio config
   - Final: Tune confidence threshold based on results

---

## References

- [VOSK Models](https://alphacephei.com/vosk/models) - Polish model: WER 11-18%
- [BIGOS V2 Benchmark](https://papers.nips.cc/paper_files/paper/2024/file/69bddcea866e8210cf483769841282dd-Paper-Datasets_and_Benchmarks_Track.pdf) - 2024 Polish ASR evaluation
- [faster-whisper Performance](https://github.com/SYSTRAN/faster-whisper) - 4x speedup vs original
- [Polish Distil-Whisper](https://dataloop.ai/library/model/aspik101_distil-whisper-large-v3-pl/) - 3x faster, 49% smaller
- [wav2vec2 Polish Model](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-polish) - WER 14.21%
- [Vosk Language Model Adaptation](https://alphacephei.com/vosk/lm) - Custom vocabulary
- [ReSpeaker 4-Mic Array](https://wiki.seeedstudio.com/ReSpeaker_4_Mic_Array_for_Raspberry_Pi/) - Beamforming setup

---

## Appendix: Diagnostic Commands

### Check Current STT Performance
```bash
# View recent transcriptions
docker compose logs wake-word | grep -i "transcription"

# Check Whisper model being used
docker compose logs ai-gateway | grep -i "whisper"

# Monitor confidence scores
docker compose logs wake-word | grep -i "confidence"
```

### Audio Hardware Diagnostics
```bash
# List audio devices
docker compose exec wake-word python -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)}') for i in range(p.get_device_count())]"

# Test recording quality
docker compose exec wake-word arecord -D hw:2,0 -f S16_LE -r 16000 -c 6 -d 5 test.wav

# Check audio levels
docker compose logs wake-word | grep "Audio stats"
```

### Resource Monitoring
```bash
# RAM usage
docker stats --no-stream | grep -E "wake-word|ai-gateway"

# CPU usage during transcription
docker stats wake-word

# Storage check
du -sh /mnt/data-ssd/ha-data/wake-word-models/*
```
