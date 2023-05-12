# Kollus Downloader

Disclaimer: This is a tool developed for educational and demonstration purposes only. By using this tool, you agree to the [these](disclaimer.md) terms and conditions.

# Setup

## Install requirements
```sh
python3 -m pip install -r requirements.txt
```

## Install Kollus Player
1. Get a copy of the [Kollus player](https://file.kollus.com/public/agent/KollusAgent-3.0.9.1.r1.exe)

2. Extract the files from the installation directory and put them under `server/mount/KollusPlayer3`. The folder should now contain `KollusAgent.exe` and `Kollus.exe` and a lot more files.

## Compile http-to-https-proxy
[Install go](https://go.dev/doc/install) and run `server/mount/http-to-https-proxy/compile.sh`

## Start mitm-proxy
```sh
mitmdump -s server/mitmproxy_addon.py
```

## Redirect traffic to mitm-proxy
```sh
iptables -t nat -A PREROUTING -s 172.18.0.0/16 -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A PREROUTING -s 172.18.0.0/16 -p tcp --dport 443 -j REDIRECT --to-port 8080
```

## Create docker network

```sh
docker network create --subnet=172.18.0.0/16 kollus-client_net
```


# Use

## Create containers

Run `server/create_containers.py [amount]` and create as many containers as you would like for parallel downloads. Add the container names (or ids) to the containers.txt file.

## Add URLs

Put all URLs to download from into `download_urls.txt`. For example:
```
# video_collection_1
https://v.kr.kollus.com/s?jwt=X&custom_key=X&uservalue0=X&uservalue1=X
https://v.kr.kollus.com/s?jwt=X&custom_key=X&uservalue0=X&uservalue1=X

# video_collection_2
https://v.kr.kollus.com/s?jwt=X&custom_key=X&uservalue0=X&uservalue1=X
https://v.kr.kollus.com/s?jwt=X&custom_key=X&uservalue0=X&uservalue1=X
```

# How it works

This tools simply acts like a web client to the Kollus Player but saves the recieved data to a file.