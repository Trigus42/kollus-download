import docker
import time
import random
import string
import os
import sys

amount = int(sys.argv[1]) if sys.argv[1] else 1
containers = []

for i in range(amount):
    port = str(random.randint(10000, 60000))

    name = ''.join(random.choices(string.ascii_letters + string.digits, k=15))

    client = docker.from_env()
    container = client.containers.run(
        "scottyhardy/docker-wine",
        name=f"kollus_download_{''.join(random.choices(string.ascii_letters + string.digits, k=15))}",
        detach=True, 
        ports={f"80/tcp": port},
        network="kollus-client_net",
        entrypoint="",
        remove=True,
        volumes={
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "mount"): {
                'bind': '/mount', 
                'mode': 'ro'
            }
        },
        command=
        r"""
            /bin/sh -c " \
                wget http://mitm.it/cert/pem && \
                mv pem /usr/local/share/ca-certificates/mitmproxy.crt && \
                update-ca-certificates && \
                xvfb-run wine /mount/KollusPlayer3/KollusAgent.exe & \
                /mount/proxy/proxy \
            "
        """
    )

    print(f"{container.name}")
    
    containers.append(container)

for container in containers:
    while not "Connected to root\WMI WMI namespace".encode("utf-8") in container.logs():
        time.sleep(0.1)

    print(f"Container {container.name} finished startup")