# On Windows (Command Prompt)
env\Scripts\activate

# On Windows (PowerShell)
Set-ExecutionPolicy Unrestricted -Scope Process

env\Scripts\Activate.ps1

# On Unix
source env/bin/activate

# Windows PG
cd "Program Files\PostgreSQL\17\bin"

pg_ctl.exe -D "C:\Program Files\PostgreSQL\17\data" start