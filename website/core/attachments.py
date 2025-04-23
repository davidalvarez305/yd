import os
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.datastructures import MultiValueDict
from django.conf import settings
from pydub import AudioSegment

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

                if content_type == "audio/webm":
                    file_name = create_generic_file_name(content_type=content_type)
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

        return self._convert_audio_format(request_file, file_name, "webm", "mp3", target_dir)

    def _convert_audio_format(self, django_request_file, file_name: str, from_format: str, to_format: str, target_dir: str) -> File:
        from_path = os.path.join(target_dir, file_name)
        to_file_name = file_name.replace(f".{from_format}", f".{to_format}")
        to_path = os.path.join(target_dir, to_file_name)

        try:
            with open(from_path, "wb") as tmp_file:
                for chunk in django_request_file.chunks():
                    tmp_file.write(chunk)

            audio = AudioSegment.from_file(from_path, format=from_format)
            audio.export(to_path, format=to_format, bitrate="192k")

            with open(to_path, "rb") as converted_file:
                return File(converted_file, name=to_file_name)

        except Exception as e:
            raise AttachmentProcessingError(f"Pydub conversion failed: {str(e)}") from e

        finally:
            if os.path.exists(from_path):
                os.remove(from_path)
            if os.path.exists(to_path):
                os.remove(to_path)

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