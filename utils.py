import time
import typing
import docker
from docker import errors as docker_errors

from data_classes import *

# kollusPlayer3 > CreateCheckAuthJS > GetEncodedSecurChar

def get_sec_char(mediaKey, numberOfChars=20):
    if mediaKey:
        validChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        charCodeString = ""
        encodedChars = ""
        index = 0

        # time function to get unix timestamp
        date = str(time.time_ns())[:-6]

        for i in range(len(mediaKey)):
            charCodeString += str(
                str(len(validChars) % ord(mediaKey[i][0])) +
                date
            )

        for j in range(numberOfChars):
            charIndex = int(charCodeString[index]) + 1
            index += charIndex
            if index > len(validChars) - 1:
                index = int(index / len(validChars))
            encodedChars += validChars[index]

        return encodedChars

    return 1


def get_containers(ids_or_names: typing.Iterable[str]):
    containers: list[ContainerInfo] = []
    docker_client = docker.client.from_env()
    for container_id in ids_or_names:
        try:
            container = docker_client.containers.get(container_id)
            containers.append(
                ContainerInfo(
                    model=container, 
                    port=docker_client.api.port(container.id, 80)[0]["HostPort"]
                )
            )
        except docker_errors.NotFound:
            print(f"Container \"{container_id}\" not found; Skipping")

    return containers