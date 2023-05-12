from mitmproxy import ctx
import mitmproxy.http

import re

class BlockDeviceInfo:
  def __init__(self):
    print('Loaded: Addon to block Kollus device info requests')

  def request(self, flow: mitmproxy.http.HTTPFlow):
    if (
      re.search(r"r-kr\.kollus\.com\/duplication\/player|mc-kr\.kollus\.com\/v\/playerbench", flow.request.pretty_url)
      or re.search(r"coloso\.us", flow.request.pretty_url)
    ):
      flow.kill()
      return

addons = [
  BlockDeviceInfo()
]