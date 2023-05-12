#!/usr/bin/env python

import ffmpeg
import pycountry
import os
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import re
from pathlib import Path

console = logging.StreamHandler()
logger = logging.getLogger()
logger.addHandler(console)
logger.setLevel(logging.INFO)

from data_classes import *
from request_functions import *
from utils import get_containers

def start_download(video_info: tuple[str, str], server_info: ServerInfo):
    download_request_result = None
    while True:
        # Get metadata
        media_info = get_media_info(media_url=get_media_url(video_info[1]), server=server_info)

        if not media_info:
            logger.warning(f"Could not get media info; Retrying {video_info[1]}")
            continue
        
        filename = media_info.title + ".mp4"
        download_dir = os.path.realpath(DOWNLOAD_DIR + os.path.sep + video_info[0])
        filepath = download_dir + os.path.sep + filename
        filepath_tmp = filepath + ".tmp"
        
        # Create dir if not exists
        filepath_PATH = Path(download_dir)
        filepath_PATH.mkdir(parents=True, exist_ok=True)

        # Did we already download part of the file?
        if download_request_result:
            resume = DownloadResumeInfo(start=download_request_result.last_byte_pos)
        elif os.path.isfile(filepath_tmp):
            with open(filepath_tmp, 'rb') as fd:
                resume = DownloadResumeInfo(start=len(fd.read()))
            logger.info(f"[{media_info.title}] Resuming from {resume.start/1000000} MB")
        else:
            resume = None

        # Start check auth queries
        check_auth_thread_stop = start_check_auth(media_key=media_info.media_key, server=server_info)

        # Start download
        logger.debug(f"[{media_info.title}] Media Key: {media_info.media_key}; ", "Progress:", f"{resume.start/1000000} MB" if resume else None)
        download_request_result: DownloadResponse = download_request(media_key=media_info.media_key, server=server_info, resume=resume, retries=2, title=media_info.title)
        # Save downloaded data
        if download_request_result.data:
            with open(filepath_tmp, 'ab') as fd:
                fd.write(download_request_result.data)

        # Stop check auth queries
        check_auth_thread_stop[0] = True

        if download_request_result.success:
            result = DownloadResult(
                temporary_filepath=filepath_tmp,
                destination_filepath=filepath,
                media_info=media_info
            )
            logger.info(f"[{filename}] Finished downloading")
            break
    
    server_info.in_use = False
    assemble(result)
    return result


def assemble(download_result: DownloadResult):
    logger.info(f"[{download_result.media_info.title}] Embedding subtitles")

    input_ffmpeg = ffmpeg.input(download_result.temporary_filepath)
    video = input_ffmpeg.video
    audio = input_ffmpeg.audio

    subtitle_metadata = {}
    for i, subtitle in enumerate(download_result.media_info.subtitles):
        lang = pycountry.languages.get(alpha_2=subtitle.language).alpha_3
        subtitle_metadata.update({
            f"metadata:s:s:{i}": f"language={lang}",
        })

    ffmpeg.output(
        video, 
        audio, 
        *[ffmpeg.input(subtitle.url)["s"] for subtitle in download_result.media_info.subtitles],
        download_result.destination_filepath, 
        **subtitle_metadata, 
        **{
            "c:v": "copy", 
            "c:a": "copy", 
            "c:v:1": "mjpeg", 
            "disposition:v:1": "attached_pic", 
            "c:s": "mov_text"
        }
    ).overwrite_output().run()

    os.remove(download_result.temporary_filepath)


def start_downloads(urls: typing.List[tuple[str, str]], servers: typing.Iterable[ServerInfo]):
    with ThreadPoolExecutor() as executor:
        while urls:
            threads = []
            unused_servers = list(filter(lambda server: not server.in_use, servers))
            
            if unused_servers:
                for server in unused_servers:
                    if not urls:
                        break
                    
                    threads.append(executor.submit(
                        start_download, 
                        urls.pop(), 
                        server
                    ))
                    
                    server.in_use = True
            
            else:
                time.sleep(1)
    
    
if __name__ == "__main__":
    DOWNLOAD_DIR = "./downloads"

    with open("download_urls.txt", "r") as fd:
        url_matcher = re.compile(r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$")
        lines = [line.rstrip("\n") for line in fd.readlines()]
        
        current_course = "Unassigned"
        urls: list[tuple] = []
        for line in lines:
            if line.startswith("#"):
                current_course = line[2:]
            elif re.match(url_matcher, line):
                urls.append((current_course, line))

    with open("containers.txt", "r") as fd:
        containers = get_containers({line.rstrip("\n") for line in fd.readlines()})

    servers = [
        ServerInfo(
                    host="0.0.0.0",
                    protocol="http",
                    port=container.port,
                    in_use=False
        ) for container in containers
    ]

    start_downloads(urls, servers)