import os
import glob
import posixpath
import paramiko
from django.core.management.base import BaseCommand, CommandError

"""
Example:
python manage.py scp `
  --host 12.34.56.78 `
  --username ubuntu `
  --key_path ~/.ssh/my-aws-key.pem `
  --remote_project_root /home/ubuntu/myproject `
  --remote_subdir data/imports `
  --local_dir ~/Downloads/files `
  --files '*.json'
"""

class Command(BaseCommand):
    help = "Uploads local files (supports wildcards) to a remote Django project directory via SSH"

    def add_arguments(self, parser):
        parser.add_argument('--host', required=True, help='Remote server IP or hostname')
        parser.add_argument('--username', required=True, help='SSH username (e.g., ubuntu)')
        parser.add_argument('--key_path', required=True, help='Path to SSH private key')
        parser.add_argument('--remote_project_root', required=True, help='Remote project root (e.g., /home/ubuntu/myapp)')
        parser.add_argument('--remote_subdir', required=False, default='', help='Optional subdirectory inside project root')
        parser.add_argument('--local_dir', required=True, help='Local directory to look for files')
        parser.add_argument('--files', nargs='+', required=True, help='File patterns or names (e.g. *.json file1.json)')

    def handle(self, *args, **options):
        host = options['host']
        username = options['username']
        key_path = options['key_path']
        remote_root = options['remote_project_root']
        remote_subdir = options['remote_subdir']
        local_dir = os.path.abspath(options['local_dir'])
        file_patterns = options['files']

        full_remote_dir = posixpath.join(remote_root, remote_subdir)

        if not os.path.isdir(local_dir):
            raise CommandError(f"❌ Local directory does not exist: {local_dir}")

        matched_files = []
        for pattern in file_patterns:
            expanded = glob.glob(os.path.join(local_dir, pattern))
            matched_files.extend(expanded)

        if not matched_files:
            raise CommandError("❌ No files matched the provided pattern(s)")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.stdout.write(f'🔐 Connecting to {host} as {username}...')
            ssh.connect(host, username=username, key_filename=key_path)

            sftp = ssh.open_sftp()

            try:
                sftp.chdir(full_remote_dir)
            except IOError:
                self.stdout.write(f'📁 Creating remote directory: {full_remote_dir}')
                parts = full_remote_dir.strip('/').split('/')
                current = ''
                for part in parts:
                    current = posixpath.join(current, part)
                    try:
                        sftp.chdir(current)
                    except IOError:
                        sftp.mkdir(current)
                        sftp.chdir(current)

            # Upload files
            for local_file in matched_files:
                if not os.path.isfile(local_file):
                    self.stderr.write(f'⚠️ Skipping (not a file): {local_file}')
                    continue
                filename = os.path.basename(local_file)
                remote_path = posixpath.join(full_remote_dir, filename)
                self.stdout.write(f'⬆️ Uploading {filename} → {remote_path}')
                sftp.put(local_file, remote_path)
                self.stdout.write(self.style.SUCCESS(f'✅ Uploaded {filename}'))

            sftp.close()

        except Exception as e:
            raise CommandError(f'❌ Upload failed: {e}')
        finally:
            ssh.close()