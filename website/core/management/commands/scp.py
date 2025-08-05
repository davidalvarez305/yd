import os
import glob
import posixpath
import paramiko
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Sync files between local and remote server via SSH (supports upload/download)"

    def add_arguments(self, parser):
        parser.add_argument('--direction', choices=['upload', 'download'], required=True,
                            help="Specify direction: upload (local → remote) or download (remote → local)")
        parser.add_argument('--host', required=True, help='Remote server IP or hostname')
        parser.add_argument('--username', required=True, help='SSH username (e.g., ubuntu)')
        parser.add_argument('--key_path', required=True, help='Path to SSH private key')
        parser.add_argument('--remote_project_root', required=True, help='Remote base directory')
        parser.add_argument('--remote_subdir', default='', help='Optional remote subdirectory')
        parser.add_argument('--local_dir', required=True, help='Local base directory')
        parser.add_argument('--files', nargs='+', required=True, help='File patterns or exact paths')

    def handle(self, *args, **opts):
        direction = opts['direction']
        host = opts['host']
        username = opts['username']
        key_path = opts['key_path']
        remote_root = opts['remote_project_root']
        remote_subdir = opts['remote_subdir']
        local_dir = os.path.abspath(opts['local_dir'])
        file_inputs = opts['files']
        remote_dir = posixpath.join(remote_root, remote_subdir)

        if not os.path.isdir(local_dir):
            raise CommandError(f"❌ Local directory does not exist: {local_dir}")

        # Connect SSH + SFTP
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.stdout.write(f'🔐 Connecting to {host} as {username}...')
            ssh.connect(host, username=username, key_filename=key_path)
            sftp = ssh.open_sftp()

            if direction == 'upload':
                files = self._resolve_local_files(file_inputs, local_dir)
                self._ensure_remote_dir(sftp, remote_dir)
                for path in files:
                    basename = os.path.basename(path)
                    remote_path = posixpath.join(remote_dir, basename)
                    self.stdout.write(f'⬆️ Uploading {basename} → {remote_path}')
                    sftp.put(path, remote_path)
                    self.stdout.write(self.style.SUCCESS(f'✅ Uploaded {basename}'))

            elif direction == 'download':
                files = self._resolve_remote_files(sftp, file_inputs, remote_dir)
                for remote_file in files:
                    basename = posixpath.basename(remote_file)
                    local_path = os.path.join(local_dir, basename)
                    self.stdout.write(f'⬇️ Downloading {remote_file} → {local_path}')
                    sftp.get(remote_file, local_path)
                    self.stdout.write(self.style.SUCCESS(f'✅ Downloaded {basename}'))

            sftp.close()

        except Exception as e:
            raise CommandError(f'❌ Sync failed: {e}')
        finally:
            ssh.close()

    def _resolve_local_files(self, file_inputs, base_dir):
        files = []
        for item in file_inputs:
            if os.path.isfile(item):
                files.append(os.path.abspath(item))
            else:
                pattern_path = os.path.join(base_dir, item)
                expanded = glob.glob(pattern_path)
                if not expanded:
                    self.stderr.write(f"⚠️ No matches for pattern: {item}")
                files.extend(expanded)
        if not files:
            raise CommandError("❌ No local files matched.")
        return files

    def _resolve_remote_files(self, sftp, patterns, remote_dir):
        all_files = sftp.listdir(remote_dir)
        matched = []
        import fnmatch
        for pattern in patterns:
            filtered = fnmatch.filter(all_files, pattern)
            if not filtered:
                self.stderr.write(f"⚠️ No remote matches for pattern: {pattern}")
            for f in filtered:
                matched.append(posixpath.join(remote_dir, f))
        if not matched:
            raise CommandError("❌ No remote files matched.")
        return matched

    def _ensure_remote_dir(self, sftp, path):
        """Ensure remote directory exists (recursive mkdir)"""
        try:
            sftp.chdir(path)
        except IOError:
            parts = path.strip('/').split('/')
            current = ''
            for part in parts:
                current = posixpath.join(current, part)
                try:
                    sftp.chdir(current)
                except IOError:
                    sftp.mkdir(current)
                    sftp.chdir(current)