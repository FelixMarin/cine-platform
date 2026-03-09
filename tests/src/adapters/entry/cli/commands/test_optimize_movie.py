import pytest
import json
from unittest.mock import patch, MagicMock
from src.adapters.entry.cli.commands.optimize_movie import (
    FFmpegInfo,
    PipelineSelector,
    FFmpegRunner,
    check_container,
    FFMPEG_CONTAINER,
    SHARED_INPUT,
    SHARED_OUTPUT,
    SHARED_TEMP,
)


class TestFFmpegInfoConstants:
    def test_constants(self):
        assert FFMPEG_CONTAINER == "ffmpeg-cuda"
        assert SHARED_INPUT == "/shared/input"
        assert SHARED_OUTPUT == "/shared/outputs"
        assert SHARED_TEMP == "/shared/temp"


class TestFFmpegInfoMapToSharedPath:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_map_mnt_data_2tb(self, ffinfo):
        path = "/mnt/DATA_2TB/audiovisual/mkv/movie.mkv"
        result = ffinfo._map_to_shared_path(path)
        assert result == "/shared/outputs/movie.mkv"

    def test_map_app_uploads(self, ffinfo):
        path = "/app/uploads/movie.mkv"
        result = ffinfo._map_to_shared_path(path)
        assert result == "/shared/uploads/movie.mkv"

    def test_map_app_temp(self, ffinfo):
        path = "/app/temp/movie.mkv"
        result = ffinfo._map_to_shared_path(path)
        assert result == "/shared/temp/movie.mkv"

    def test_map_app_outputs(self, ffinfo):
        path = "/app/outputs/movie.mkv"
        result = ffinfo._map_to_shared_path(path)
        assert result == "/shared/outputs/movie.mkv"

    def test_map_unknown_path(self, ffinfo):
        path = "/other/path/movie.mkv"
        result = ffinfo._map_to_shared_path(path)
        assert result == "/shared/temp/movie.mkv"


class TestFFmpegInfoProbe:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_probe_success(self, ffinfo):
        mock_data = {
            "format": {"size": "1000000", "duration": "120.5"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24000/1001",
                }
            ],
        }

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_data)

        with patch("subprocess.run", return_value=mock_result):
            result = ffinfo.probe("/path/to/video.mkv")
            assert "format" in result

    def test_probe_failure(self, ffinfo):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = ffinfo.probe("/path/to/video.mkv")
            assert result == {}

    def test_probe_exception(self, ffinfo):
        with patch("subprocess.run", side_effect=Exception("Error")):
            result = ffinfo.probe("/path/to/video.mkv")
            assert result == {}


class TestFFmpegInfoGetInfo:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_get_info_empty_probe(self, ffinfo):
        with patch.object(ffinfo, "probe", return_value={}):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result == {}

    def test_get_info_video_stream(self, ffinfo):
        mock_data = {
            "format": {"size": "1000000000", "duration": "7200"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 3840,
                    "height": 2160,
                    "pix_fmt": "yuv420p10le",
                    "r_frame_rate": "24/1",
                    "color_transfer": "smpte2084",
                    "color_primaries": "bt2020",
                    "color_space": "bt2020nc",
                },
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")

            assert result["vcodec"] == "hevc"
            assert result["acodec"] == "aac"
            assert result["width"] == 3840
            assert result["height"] == 2160
            assert result["is_10bit"] is True
            assert result["is_hdr"] is True
            assert result["resolution_class"] == "UHD"
            assert result["fps"] == 24.0

    def test_get_info_sd_resolution(self, ffinfo):
        mock_data = {
            "format": {"size": "700000000", "duration": "5400"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 720,
                    "height": 480,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "30000/1001",
                }
            ],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result["resolution_class"] == "SD"

    def test_get_info_hd_resolution(self, ffinfo):
        mock_data = {
            "format": {"size": "700000000", "duration": "5400"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                }
            ],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result["resolution_class"] == "HD"

    def test_get_info_fhd_resolution(self, ffinfo):
        mock_data = {
            "format": {"size": "2000000000", "duration": "7200"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                }
            ],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result["resolution_class"] == "FHD"

    def test_get_info_4k_plus(self, ffinfo):
        mock_data = {
            "format": {"size": "8000000000", "duration": "7200"},
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 4096,
                    "height": 2160,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "24/1",
                }
            ],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result["resolution_class"] == "4K+"

    def test_get_info_no_video_stream(self, ffinfo):
        mock_data = {
            "format": {"size": "1000", "duration": "60"},
            "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        }

        with patch.object(ffinfo, "probe", return_value=mock_data):
            result = ffinfo.get_info("/path/to/video.mkv")
            assert result["vcodec"] is None
            assert result["resolution_class"] == "unknown"


class TestFFmpegInfoNvencAvailable:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_nvenc_available_true(self, ffinfo):
        mock_result = MagicMock()
        mock_result.stdout = "h264_nvenc encoder"

        with patch("subprocess.run", return_value=mock_result):
            assert ffinfo.nvenc_available() is True

    def test_nvenc_available_false(self, ffinfo):
        mock_result = MagicMock()
        mock_result.stdout = "libx264"

        with patch("subprocess.run", return_value=mock_result):
            assert ffinfo.nvenc_available() is False

    def test_nvenc_exception(self, ffinfo):
        with patch("subprocess.run", side_effect=Exception("Error")):
            assert ffinfo.nvenc_available() is False


class TestPipelineSelectorAutoProfile:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    @pytest.fixture
    def selector(self, ffinfo):
        return PipelineSelector(ffinfo)

    def test_hevc_10bit_hdr_with_nvenc(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=True):
            info = {
                "vcodec": "hevc",
                "is_10bit": True,
                "is_hdr": True,
                "resolution_class": "UHD",
            }
            result = selector.auto_profile(info)

            assert result["use_gpu"] is True
            assert result["vcodec_out"] == "h264_nvenc"
            assert "scale_cuda" in result["vf"]
            assert "HDR" in result["description"]

    def test_hevc_10bit_without_nvenc(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "hevc",
                "is_10bit": True,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["use_gpu"] is False
            assert result["vcodec_out"] == "libx265"
            assert "main10" in str(result["vparams"])

    def test_hevc_8bit_with_nvenc(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=True):
            info = {
                "vcodec": "hevc",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["use_gpu"] is True
            assert result["vcodec_out"] == "h264_nvenc"

    def test_h264_with_nvenc(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=True):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["use_gpu"] is True
            assert result["vcodec_out"] == "h264_nvenc"

    def test_h264_cpu_only(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "HD",
            }
            result = selector.auto_profile(info)

            assert result["use_gpu"] is False
            assert result["vcodec_out"] == "libx264"

    def test_av1(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "av1",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["vcodec_out"] == "libx265"

    def test_vp9(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "vp9",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["vcodec_out"] == "libx265"

    def test_unknown_codec(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "unknown",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)

            assert result["vcodec_out"] == "libx264"
            assert "fallback" in result["description"]

    def test_uhd_adds_scale_filter(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "hevc",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "UHD",
            }
            result = selector.auto_profile(info)

            assert result["vf"] is not None
            assert "scale" in result["vf"]


class TestBitrateByResolution:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    @pytest.fixture
    def selector(self, ffinfo):
        return PipelineSelector(ffinfo)

    def test_sd_bitrate(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "SD",
            }
            result = selector.auto_profile(info)
            assert result["target_bitrate"] == "800k"

    def test_hd_bitrate(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "HD",
            }
            result = selector.auto_profile(info)
            assert result["target_bitrate"] == "1500k"

    def test_fhd_bitrate(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "FHD",
            }
            result = selector.auto_profile(info)
            assert result["target_bitrate"] == "2500k"

    def test_uhd_bitrate(self, selector, ffinfo):
        with patch.object(ffinfo, "nvenc_available", return_value=False):
            info = {
                "vcodec": "h264",
                "is_10bit": False,
                "is_hdr": False,
                "resolution_class": "UHD",
            }
            result = selector.auto_profile(info)
            assert result["target_bitrate"] == "4000k"


class TestFFmpegRunnerMapToSharedPath:
    def test_runner_map_path(self):
        info = {"shared_path": "/shared/outputs/movie.mkv"}
        runner = FFmpegRunner(
            info, {"vf": None, "vcodec_out": "libx264", "vparams": []}
        )

        result = runner._map_to_shared_path("/mnt/DATA_2TB/audiovisual/mkv/output.mkv")
        assert result == "/shared/outputs/output.mkv"


class TestCheckContainer:
    def test_check_container_running(self):
        mock_result = MagicMock()
        mock_result.stdout = "ffmpeg-cuda"

        with patch("subprocess.run", return_value=mock_result):
            assert check_container() is True

    def test_check_container_not_running(self):
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            assert check_container() is False

    def test_check_container_exception(self):
        with patch("subprocess.run", side_effect=Exception("Error")):
            assert check_container() is False


class TestHDRDetection:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_pq_transfer(self, ffinfo):
        assert "smpte2084" in ffinfo.HDR_TRANSFER

    def test_hlg_transfer(self, ffinfo):
        assert "arib-std-b67" in ffinfo.HDR_TRANSFER

    def test_bt2020_primaries(self, ffinfo):
        assert "bt2020" in ffinfo.HDR_PRIMARIES


class Test10BitDetection:
    @pytest.fixture
    def ffinfo(self):
        return FFmpegInfo()

    def test_10bit_formats(self, ffinfo):
        assert "yuv420p10le" in ffinfo.PIX_FMT_10BIT
        assert "yuv422p10le" in ffinfo.PIX_FMT_10BIT
        assert "yuv444p10le" in ffinfo.PIX_FMT_10BIT
