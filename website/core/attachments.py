from io import BytesIO
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

                if content_type.startswith("audio/"):
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

        return self._convert_audio_format(request_file, file_name, "mp3", target_dir)

    def _convert_audio_format(self, django_request_file, file_name: str, to_format: str, target_dir: str) -> File:
        from_path = os.path.join(target_dir, file_name)
        original_extension = os.path.splitext(from_path)[1].lstrip(".")
        to_file_name = file_name.replace(original_extension, to_format)

        try:
            with open(from_path, "wb") as tmp_file:
                for chunk in django_request_file.chunks():
                    tmp_file.write(chunk)

            audio = AudioSegment.from_file(from_path)
            buffer = BytesIO()
            audio.export(buffer, format=to_format, bitrate="192k")
            buffer.seek(0)

            return File(buffer, name=to_file_name)

        except Exception as e:
            raise AttachmentProcessingError(f"Audio conversion failed: {str(e)}") from e

        finally:
            if os.path.exists(from_path):
                os.remove(from_path)

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