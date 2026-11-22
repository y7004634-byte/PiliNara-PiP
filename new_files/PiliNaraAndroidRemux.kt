package com.example.pilinara

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

/**
 * Copies existing H.264/H.265/AAC media samples into an MP4/M4A container.
 * No transcoding, no shell commands, and no external binary dependency.
 */
internal object PiliNaraAndroidRemux {
    fun remux(outputPath: String, videoPath: String?, audioPath: String?, audioOnly: Boolean): String {
        require(!audioPath.isNullOrBlank()) { "Missing audio input" }
        require(audioOnly || !videoPath.isNullOrBlank()) { "Missing video input" }
        val result = File(outputPath)
        result.parentFile?.mkdirs()
        require(File(audioPath).isFile) { "Audio file not found" }
        if (!audioOnly) require(File(videoPath!!).isFile) { "Video file not found" }

        var audioExtractor: MediaExtractor? = null
        var videoExtractor: MediaExtractor? = null
        var muxer: MediaMuxer? = null
        var started = false
        var success = false
        try {
            audioExtractor = MediaExtractor().apply { setDataSource(audioPath) }
            val audioTrack = findTrack(audioExtractor, "audio/")
            require(audioTrack >= 0) { "No audio track found in source" }
            audioExtractor.selectTrack(audioTrack)
            if (!audioOnly) {
                videoExtractor = MediaExtractor().apply { setDataSource(videoPath!!) }
                val videoTrack = findTrack(videoExtractor, "video/")
                require(videoTrack >= 0) { "No video track found in source" }
                videoExtractor.selectTrack(videoTrack)
            }
            muxer = MediaMuxer(result.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val outVideo = if (videoExtractor == null) -1 else {
                val inTrack = findTrack(videoExtractor, "video/")
                muxer.addTrack(videoExtractor.getTrackFormat(inTrack))
            }
            val outAudio = muxer.addTrack(audioExtractor.getTrackFormat(audioTrack))
            muxer.start()
            started = true

            val buffer = ByteBuffer.allocateDirect(8 * 1024 * 1024)
            val info = MediaCodec.BufferInfo()
            while (true) {
                val vTime = videoExtractor?.sampleTime ?: -1L
                val aTime = audioExtractor.sampleTime
                if (aTime < 0 && vTime < 0) break
                val useVideo = vTime >= 0 && (aTime < 0 || vTime <= aTime)
                val extractor = if (useVideo) videoExtractor!! else audioExtractor
                val track = if (useVideo) outVideo else outAudio
                buffer.clear()
                val size = extractor.readSampleData(buffer, 0)
                if (size < 0) {
                    extractor.advance()
                    continue
                }
                require(size <= buffer.capacity()) { "Sample exceeds maximum buffer" }
                info.set(0, size, extractor.sampleTime, extractor.sampleFlags)
                buffer.position(0)
                buffer.limit(size)
                muxer.writeSampleData(track, buffer, info)
                extractor.advance()
            }
            success = result.length() > 0
            require(success) { "Mux output empty" }
            return result.absolutePath
        } finally {
            if (started) {
                try { muxer?.stop() } catch (_: Exception) { success = false }
            }
            try { muxer?.release() } catch (_: Exception) {}
            try { audioExtractor?.release() } catch (_: Exception) {}
            try { videoExtractor?.release() } catch (_: Exception) {}
            if (!success) result.delete()
        }
    }

    private fun findTrack(extractor: MediaExtractor, prefix: String): Int {
        for (index in 0 until extractor.trackCount) {
            val mime = extractor.getTrackFormat(index).getString(MediaFormat.KEY_MIME)
            if (mime?.startsWith(prefix) == true) return index
        }
        return -1
    }
}
