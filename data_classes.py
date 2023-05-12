from dataclasses import dataclass
import requests
import docker

@dataclass
class ServerInfo():
    host: str
    protocol: str
    port: str
    in_use: bool

@dataclass
class ContainerInfo():
    port: str
    model: docker.client.ContainerCollection.model | None

@dataclass
class SubtitleInfo():
    url: str
    name: str
    language: str  # ISO 3166-1 alpha-2

@dataclass
class Mediainfo():
    title: str
    title_raw: str
    subtitles: list[SubtitleInfo]
    media_key: str

@dataclass
class DownloadResult():
    temporary_filepath: str
    destination_filepath: str
    media_info: Mediainfo

@dataclass
class DownloadResponse():
    data: bytearray
    success: bool
    last_byte_pos: int
    expected_length: int

@dataclass
class DownloadResumeInfo():
    start: int

@dataclass
class MediaRequestResult():
    data: bytearray | None
    bytes_start: int | None
    bytes_end: int | None
    total_length: int | None
    error: bool
    raw_response: requests.Response | None