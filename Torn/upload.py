from rich import print
from rich.traceback import install

from Torn.credentials import load_credentials

install()

import paramiko
import os
import stat
import bcrypt


def upload_web():
    credentials = load_credentials()
    upload = credentials.get("upload")
    if upload:
        web_username = credentials.get("web_username")
        web_password = credentials.get("web_password")
        hostname = credentials.get("hostname")
        host_username = credentials.get("host_username")
        static_web_local_path = credentials.get("static_web_local_path")
        remote_path = credentials.get("remote_path")
        host_password = credentials.get("host_password")
        htpasswd_path_on_server = credentials.get("htpasswd_path_on_server")
        # primary_API_key = credentials.get("primary_API_key")
        return upload_to_web_host(
            hostname,
            host_username,
            host_password,
            static_web_local_path,
            remote_path,
            web_username,
            web_password,
            htpasswd_path_on_server,
        )
    else:
        return {upload:False}


def upload_to_web_host(
    hostname,
    host_username,
    host_password,
    path_to_local_copy_of_web_files,
    remote_path,
    web_username,
    web_password,
    htpasswd_path_on_server,
):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=host_username, password=host_password)
        sftp = ssh.open_sftp()

        def _upload_recursive(local, remote):
            for item in os.listdir(local):
                local_item = os.path.join(local, item)
                remote_item = os.path.join(remote, item)

                if os.path.isdir(local_item):
                    try:
                        sftp.mkdir(remote_item)
                    except IOError:
                        pass
                    _upload_recursive(local_item, remote_item)
                else:
                    sftp.put(local_item, remote_item)
                    print(f"Uploaded: {local_item} -> {remote_item}")

        # Create .htpasswd
        htpasswd_local_path = os.path.join(path_to_local_copy_of_web_files, ".htpasswd")
        create_htpasswd_bcrypt(htpasswd_local_path, web_username, web_password)

        # Create .htaccess
        htaccess_local_path = os.path.join(path_to_local_copy_of_web_files, ".htaccess")

        create_htaccess(
            htaccess_local_path, htpasswd_path_on_server
        )  # Path is relative to web root

        # Upload files recursively, starting from the local 'reports' directory
        _upload_recursive(path_to_local_copy_of_web_files, remote_path)

        # Upload .htpasswd and .htaccess to the root
        sftp.put(htpasswd_local_path, os.path.join(remote_path, ".htpasswd"))
        sftp.put(htaccess_local_path, os.path.join(remote_path, ".htaccess"))
        # Set permissions on .htpasswd (644)
        sftp.chmod(
            os.path.join(remote_path, ".htpasswd"),
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
        )
        sftp.chmod(
            os.path.join(remote_path, ".htaccess"),
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
        )

        # Create a basic error page
        error_page_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Internal Server Error</title>
        </head>
        <body>
            <h1>500 - Internal Server Error</h1>
            <p>Something went wrong. Please try again later.</p>
        </body>
        </html>
        """
        with open("error500.html", "w") as f:
            f.write(error_page_content)

        # Upload the error page
        sftp.put("error500.html", os.path.join(remote_path, "error500.html"))

        sftp.close()
        ssh.close()
        print(f"Directory uploaded: {path_to_local_copy_of_web_files} -> {remote_path}")
        return {"upload":True}
    except Exception as e:
        print(f"Error: {e}")
        return { "Error":e}


def create_htpasswd_bcrypt(filepath, username, password):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    with open(filepath, "w") as f:
        f.write(f"{username}:{hashed_password.decode('utf-8')}\n")


def create_htaccess(filepath, htpasswd_path_on_server):
    with open(filepath, "w") as f:
        f.write(
            f"""AuthType Basic
AuthName "Restricted Area - enter your faction name and password"
AuthUserFile {htpasswd_path_on_server}
Require valid-user
"""
        )
        # {web_username}



