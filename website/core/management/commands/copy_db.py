import json
import os
import paramiko
from django.core.management.base import BaseCommand, CommandError
from website import settings

class Command(BaseCommand):
    help = "Dumps production database via SSH and restores it locally"

    def handle(self, *args, **options):
        with open(os.path.join(settings.PROJECT_ROOT, 'env.json'), "r") as f:
            env = json.load(f)

        remote_sql_path = env.get('remote_sql_path', 'prod.sql')
        local_sql_path = os.path.join(settings.PROJECT_ROOT, 'prod.sql')

        remote_server_ip = env.get("REMOTE_SERVER_IP")
        remote_server_username = env.get("REMOTE_SERVER_USERNAME")
        local_ssh_key_path = env.get("LOCAL_SSH_KEY_PATH")
        
        local_db_user = env.get("LOCAL_DB_USER")
        local_db_name = env.get("LOCAL_DB_NAME")
        local_db_port = env.get("LOCAL_DB_PORT")
        local_db_password = env.get("LOCAL_DB_PASSWORD")

        remote_db_user = env.get("REMOTE_DB_USER")
        remote_db_name = env.get("REMOTE_DB_NAME")
        remote_db_port = env.get("REMOTE_DB_PORT")
        remote_db_password = env.get("REMOTE_DB_PASSWORD")

        dump_cmd = f'PGPASSWORD="{remote_db_password}" pg_dump -h localhost -U {remote_db_user} -d {remote_db_name} -p {remote_db_port} > {remote_sql_path}'

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(remote_server_ip, port=22, username=remote_server_username, key_filename=local_ssh_key_path)

            self.stdout.write(f'📡 Executing remote dump...')
            stdin, stdout, stderr = ssh.exec_command(dump_cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                error = stderr.read().decode()
                raise CommandError(f"Remote pg_dump failed:\n{error}")

            # Copy file locally
            sftp = ssh.open_sftp()
            sftp.get(remote_sql_path, local_sql_path)

            # Cleanup
            sftp.remove(remote_sql_path)
            sftp.close()

            # 🔹 Drop & recreate local DB
            drop_cmd = f'PGPASSWORD="{local_db_password}" dropdb -U {local_db_user} -p {local_db_port} --if-exists {local_db_name}'
            create_cmd = f'PGPASSWORD="{local_db_password}" createdb -U {local_db_user} -p {local_db_port} {local_db_name}'

            self.stdout.write(f'🗑 Dropping local DB "{local_db_name}" (if exists)...')
            if os.system(drop_cmd) != 0:
                raise CommandError("Failed to drop local database")

            self.stdout.write(f'📦 Creating local DB "{local_db_name}"...')
            if os.system(create_cmd) != 0:
                raise CommandError("Failed to create local database")

            # Restore
            restore_cmd = f'PGPASSWORD="{local_db_password}" psql -U {local_db_user} -d {local_db_name} -p {local_db_port} -f {local_sql_path}'
            if os.system(restore_cmd) != 0:
                raise CommandError("Local restore failed")

        except Exception as e:
            raise CommandError(f'❌ Error: {e}')
        finally:
            ssh.close()