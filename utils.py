import urllib, json, requests, random, sys
import logging

logger = logging.getLogger(__name__)

WKC_URL = "https://{host}/auth/realms/{realm}/.well-known/openid-configuration"

class ExpiredSignatureError(Exception):
    """Class for BadRequestException"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def get_rand_string(number_of_characters):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    rnd = random.SystemRandom()
    out = ""
    for d in range(number_of_characters):
        i = rnd.randint(0, sys.maxsize)
        i = i % len(chars)
        out = out + chars[i:i+1]
    return out

def _split_cookies(cookie_str):
  cookies = {}
  for cookie in cookie_str.split("; "):
    cookie_bits = cookie.split("=")
    cookies[cookie_bits[0]] = cookie_bits[1]
  return cookies

def get_cookies(headers):
  response = {}
  if "cookie" in headers:
    cookies = headers["cookie"]
    for cookie in cookies:
      response.update(_split_cookies(cookie["value"]))
  return response

def make_response(code, description, headers = None):
  response = {
    "status": code,
    "statusDescription": description
  } 
  if headers:
    response["headers"] = headers
  return response

def redirect(url):
  return make_response(
    code="302",
    description="Found",
    headers={
      "location": [
        {
          "key": "Location",
          "value": url
        }
      ]
    }
  )

def forbidden(message):
  body = f"""<!doctype html>
  <html>
    <head>
      <title>Forbidden</title>
    </head>
    <body>
      <h1>Access is not allowed</h1>
      <p>{message}</p>
    </body>
  </html>
  """
  headers = {
    "content-type": [
      {
        "key": "Content-Type",
        "value": "text/html"
      }
    ]
  }
  response = make_response(
    code=403, 
    description="Forbidden", 
    headers=headers
  )
  response["body"] = body
  response["bodyEncoding"] = "text"
  return response

def set_cookies(response, cookies, max_age = None):
  headers = {}
  if "headers" in response:
    headers = response["headers"]
  cookies_list = []
  for key, value in cookies.items():
    expires = ""
    if value == "":
      expires = "; Expires=0"
    else:
      if max_age != None:
        expires = "; Max-Age={a}".format(a=max_age)
    cookies_list += [{
      "key": "Set-Cookie",
      "value": "{k}={v}; Secure; HttpOnly{e}".format(k=key, v=value, e=expires)
    }]
  headers["set-cookie"] = cookies_list
  response["headers"] = headers
  return response

def return_bad_request(description):
  return make_response(
    code="400",
    description=description
  )

def build_url(base, *args, **kwargs):
  url = base + "?"
  for key, value in kwargs.items():
    url = url + "{k}={v}&".format(k=key, v=value)
  return url[:-1]

def get_wkc(host, realm):
  url = WKC_URL.format(
    host=host,
    realm=realm
  )
  resp = urllib.request.urlopen(url).read().decode()
  data = json.loads(resp)
  return data

def get_certs(url):
  resp = urllib.request.urlopen(url).read().decode()
  data = json.loads(resp)["keys"]
  return data

def post_to_url(url, **kwargs):
  r = requests.post(url, data=kwargs)
  return r.content

def validate_jwt(api, token, key_set, aud):
  # post to API to validate
  r = requests.post(api, json={
    "token": token,
    "keys": key_set,
    "aud": aud
  })
  if r.status_code != 200:
    raise ExpiredSignatureError("Signature not validated")
  return r.content