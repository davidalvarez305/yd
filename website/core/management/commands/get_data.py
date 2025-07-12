import paramiko
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Fetches JSON data from a remote Lightsail instance via SSH and copies it locally"

    def add_arguments(self, parser):
        parser.add_argument('--host', required=True, help='Remote Lightsail instance IP or hostname')
        parser.add_argument('--username', required=True, help='SSH username (e.g. ubuntu)')
        parser.add_argument('--key_path', required=True, help='Path to SSH private key')
        parser.add_argument('--remote_json_path', required=True, help='Path to save JSON on remote server')
        parser.add_argument('--local_path', required=True, help='Local path to save the JSON file')
        parser.add_argument('--psql_user', required=True, help='PostgreSQL user')
        parser.add_argument('--psql_db', required=True, help='PostgreSQL database')
        parser.add_argument('--query', required=False, default='SELECT * FROM your_table LIMIT 10', help='SQL query to execute')

    def handle(self, *args, **options):
        host = options['host']
        username = options['username']
        key_path = options['key_path']
        remote_json_path = options['remote_json_path']
        local_path = options['local_path']
        psql_user = options['psql_user']
        psql_db = options['psql_db']
        query = options['query']

        psql_cmd = f'psql -h localhost -U {psql_user} -d {psql_db} -p 5433 -c "SELECT row_to_json(t) FROM ({query}) t;"'

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.stdout.write(f'🔐 Connecting to {host} as {username}...')
            ssh.connect(host, port=22, username=username, key_filename=key_path)

            full_cmd = f'{psql_cmd} | jq "." > {remote_json_path}'
            self.stdout.write(f'📡 Executing: {full_cmd}')
            stdin, stdout, stderr = ssh.exec_command(full_cmd)

            std_out = stdout.read().decode()
            std_err = stderr.read().decode()
            if std_err:
                self.stderr.write(f'⚠️ Remote error:\n{std_err}')
                raise CommandError("Remote command failed")

            sftp = ssh.open_sftp()
            sftp.get(remote_json_path, local_path)
            sftp.close()
            self.stdout.write(self.style.SUCCESS(f'✅ File copied to {local_path}'))

        except Exception as e:
            raise CommandError(f'❌ Error: {e}')
        finally:
            ssh.close()