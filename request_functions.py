import requests
import time
import re
import json
import urllib.parse
import logging
from concurrent.futures import ThreadPoolExecutor

from utils import get_sec_char
from data_classes import *

logger = logging.getLogger()

time_ext = lambda len=13: str(time.time_ns())[:(len-19)]

def get_media_url(url: str):
    # Get video player site and extract media url
    video_site_response = requests.get(url, timeout=5)
    found = re.findall(r"(mediaURL[^']+')([^']+)", video_site_response.text)

    if found:
        media_url = found[0][1]
        return media_url
    else:
        return None

def get_media_info(media_url: str | None, server: ServerInfo):
    if not media_url:
        return None

    # Get json with media info from kollus player program and extract media key
    info_json_url = f"{server.protocol}://{server.host}:{server.port}/stream/open?" + urllib.parse.urlencode({
            "path": media_url,
            "slcode": "en",
            "_": time_ext()
        }
    )

    info_dict = None
    for _ in range(3):
        try:
            info_json_response = requests.get(info_json_url, headers={'Host': 'proxy.catoms.net'}, timeout=5)
        except requests.exceptions.ReadTimeout:
            time.sleep(3)
            continue
        
        try:
            info_dict = json.loads(info_json_response.content.decode("utf-8"))["items"][0]
        except:
            continue

        break

    if info_dict:
        title_match = re.search(r"\d+_\d+_(?P<title>.+)", info_dict["title"])
        return Mediainfo(
            title = title_match.group("title") if title_match else info_dict["title"],
            title_raw = info_dict["title"],
            subtitles = [
                SubtitleInfo(
                    url=subtitle.get("url"),
                    name=subtitle.get("name"),
                    language=subtitle.get("language")
                ) for subtitle in info_dict["subtitle"]
            ] if "subtitle" in info_dict else [],
            media_key=info_dict["media_key"]
        )
    else:
        return None

def get_check_auth_url(media_key: str, server: ServerInfo):
    check_auth_script_url = f"{server.protocol}://{server.host}:{server.port}/{get_sec_char(mediaKey=media_key, numberOfChars=20)}?m=get&k1={media_key}&i=0&_={time_ext()}"
    check_auth_script = requests.get(check_auth_script_url, headers={'Host': 'proxy.catoms.net'}).text
    check_auth_url: str = re.findall(r"(var ajax_url =')([^']*)", check_auth_script)[0][1]
    check_auth_url = check_auth_url.replace(":8389", "").replace("https://proxy.catoms.net/", f"{server.protocol}://{server.host}:{server.port}/")

    return check_auth_url

def start_check_auth(media_key: str, server: ServerInfo):
    def checkAuth(url: str, count: int):
        try:
            requests.get(url+str(count)+"&_="+time_ext(), headers={'Host': 'proxy.catoms.net'}, timeout=5)
            return count + 2
        except requests.exceptions.Timeout as e:
            logger.debug(f"[{server.container.name}] Check-auth timed out ")
            return count

    def checkAuthThread(url: str, stop: list[bool]):
        check_auth_counter = 0
        while(not stop[0]):
            check_auth_counter = checkAuth(url, check_auth_counter)
            time.sleep(2)

    check_auth_url = get_check_auth_url(media_key, server)

    executor = ThreadPoolExecutor()
    check_auth_thread_stop = [False]
    thread = executor.submit(checkAuthThread, check_auth_url, check_auth_thread_stop)

    return check_auth_thread_stop

def media_request(bytes_start: int|str, media_key: str, server: ServerInfo):
    media_url = f"{server.protocol}://{server.host}:{server.port}/stream/play?media_key={media_key}&index=0&_{time_ext(10)}="

    try:
        response = requests.get(media_url, headers={
                "Host": "proxy.catoms.net",
                "Range": f"bytes={bytes_start}-"
            },
            timeout=120
        )

        failure = False
    except:
        failure = True

    if not failure and (range_header := response.headers.get('Content-Range')):
        return MediaRequestResult(
            data = response.content[:-1],
            bytes_start = int(range_header.split("/")[0].split("-")[0].split()[1]),
            bytes_end = int(range_header.split("/")[0].split("-")[1]),
            total_length = int(range_header.split("/")[1]),
            error = False,
            raw_response = response
        )
    else:
        return MediaRequestResult(
            data = None,
            bytes_start = None,
            bytes_end = None,
            total_length = None,
            error = True,
            raw_response = response if not failure else None
        )
    
def download_request(media_key: str, server: ServerInfo, resume: DownloadResumeInfo | None = None, retries: int = 1, title: str = ""):
    buffer = bytearray()
    bytes_start = resume.start if resume else 0
    media_response = None

    failures = 0
    while True:
        # Too many failed attempts
        if failures >= retries:
            return DownloadResponse(
                data=buffer,
                success=False,
                last_byte_pos=bytes_start,
                expected_length=media_response.total_length
            )
        
        # We are finished
        if media_response and not media_response.error and bytes_start >= media_response.total_length-1:
            return DownloadResponse(
                data=buffer,
                success=True,
                last_byte_pos=bytes_start,
                expected_length=media_response.total_length
            )
        
        media_response = media_request(bytes_start=bytes_start, media_key=media_key, server=server)

        logger.debug(f"[{title}] Recieved {len(media_response.data)/10**6 if media_response.data else 0} MB")

        # Retry if error
        if media_response.error or not len(media_response.data):
            failures += 1
            continue
        elif len(media_response.data) < 1000000:
            time.sleep(5)
            continue

        buffer.extend(media_response.data)
        bytes_start = len(buffer) + (resume.start if resume else 0)

        logger.info(f"[{title}] Progress: {'{:.2f}'.format(bytes_start/(media_response.total_length-1)*100)}% ({bytes_start/10**6} MB)")