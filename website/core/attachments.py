import os
import subprocess
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.datastructures import MultiValueDict
from django.conf import settings

from .utils import create_generic_file_name

class AttachmentProcessingError(Exception):
    pass

class AttachmentServiceMixin:
    def dispatch(self, request, *args, **kwargs):
        request._files = self._process_request_files(request)
        return super().dispatch(request, *args, **kwargs)

    def _process_request_files(self, request):
        upload_root = getattr(settings, "UPLOADS_ROOT", os.path.join(settings.BASE_DIR, "uploads"))
        os.makedirs(upload_root, exist_ok=True)

        processed_files = MultiValueDict()

        for key, file_list in request.FILES.lists():
            for request_file in file_list:
                content_type = request_file.content_type
                file_name = create_generic_file_name(content_type=content_type)

                if content_type == "audio/webm":
                    processed_file = self._handle_attachment(request_file, file_name, content_type, upload_root)
                    new_file = InMemoryUploadedFile(
                        file=processed_file.file,
                        field_name=key,
                        name=processed_file.name,
                        content_type="audio/mpeg",
                        size=processed_file.size,
                        charset=None
                    )
                    processed_files.appendlist(key, new_file)
                else:
                    processed_files.appendlist(key, request_file)

        return processed_files

    def _handle_attachment(self, request_file, file_name, content_type, upload_root) -> File:
        sub_dir = self._get_sub_dir(content_type)
        target_dir = os.path.join(upload_root, sub_dir)
        os.makedirs(target_dir, exist_ok=True)

        if content_type == "audio/webm":
            return self._convert_webm_to_mp3(request_file, file_name, target_dir)
        else:
            return self._save_file_to_dir(request_file, file_name, target_dir)

    def _get_sub_dir(self, content_type: str) -> str:
        main_type = content_type.split("/")[0]
        if main_type == "audio":
            return "audio"
        elif main_type == "image":
            return "images"
        elif main_type == "video":
            return "videos"
        else:
            return "misc"

    def _convert_webm_to_mp3(self, django_request_file, file_name: str, target_dir: str) -> File:
        webm_path = os.path.join(target_dir, file_name).replace("\\", "/")
        mp3_path = webm_path.replace(".webm", ".mp3")

        try:
            with open(webm_path, "wb") as tmp_webm:
                for chunk in django_request_file.chunks():
                    tmp_webm.write(chunk)

            command = [
                "ffmpeg", "-y", "-i", webm_path,
                "-codec:a", "libmp3lame", "-qscale:a", "2",
                mp3_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            with open(mp3_path, "rb") as mp3_file:
                return File(mp3_file, name=os.path.basename(mp3_path))

        except subprocess.CalledProcessError as e:
            raise AttachmentProcessingError(f"FFmpeg conversion failed: {e.stderr.decode()}") from e

        finally:
            if os.path.exists(webm_path):
                os.remove(webm_path)
            if os.path.exists(mp3_path):
                os.remove(mp3_path)

    def _save_file_to_dir(self, django_request_file, file_name: str, target_dir: str) -> File:
        file_path = os.path.join(target_dir, file_name)
        with open(file_path, "wb") as f:
            for chunk in django_request_file.chunks():
                f.write(chunk)

        with open(file_path, "rb") as saved_file:
            return File(saved_file, name=os.path.basename(file_path))