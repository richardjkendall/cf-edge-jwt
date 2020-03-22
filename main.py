from flask import Flask, request, g, redirect, make_response

import urllib, json, requests
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)

WKC_URL = "https://{host}/auth/realms/{realm}/.well-known/openid-configuration"

CONFIG = {}

class ExpiredSignatureError(Exception):
    """Class for BadRequestException"""
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def insert_newlines(string, every=72):
  lines = []
  for i in range(0, len(string), every):
    lines.append(string[i:i+every])
  print(lines)
  return '\n'.join(lines)

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

def validate_jwt(token, key_set, aud):
  # post to API to validate
  r = requests.post(CONFIG["VAL_API_URL"], json={
    "token": token,
    "keys": key_set,
    "aud": aud
  })
  if r.status_code != 200:
    raise ExpiredSignatureError("Signature not validated")
  return r.content

# load the settings json
with open("settings.json") as f:
  CONFIG = json.load(f)

# make sure we have the config data
wkc_data = get_wkc(
  host=CONFIG["HOST"],
  realm=CONFIG["REALM"]
)
keys = get_certs(
  url=wkc_data["jwks_uri"]
)

@app.route("/")
def root():
  # get auth URL as we might need it
  au = build_url(
    base=wkc_data["authorization_endpoint"],
    client_id=CONFIG["CLIENT_ID"],
    response_type="code",
    redirect_uri="http://localhost:5000/_login"
  )
  logger.info("Got auth URL: {url}".format(url=au))
  # check for auth cookie
  if CONFIG["AUTH_COOKIE"] in request.cookies:
    # check it
    logger.info("Got access token")
    try:
      decoded = validate_jwt(
        token=request.cookies[CONFIG["AUTH_COOKIE"]],
        key_set=keys,
        aud=CONFIG["CLIENT_ID"]
      )
      logger.info("Access token is valid")
      return decoded
    except ExpiredSignatureError as e:
      logger.info("Access token has expired, so going to attempt to refresh")
      # the access token is expired, so lets try to refresh with the refresh token, if we have it
      if CONFIG["REFRESH_COOKIE"] in request.cookies:
        logger.info("There is a refresh token present")
        try:
          decoded = validate_jwt(
            token=request.cookies[CONFIG["REFRESH_COOKIE"]],
            key_set=keys,
            aud=CONFIG["CLIENT_ID"]
          )
          logger.info("Refresh token was validated")
          # refresh token is valid, so attempt to use it
          resp = post_to_url(
            url=wkc_data["token_endpoint"],
            grant_type="refresh_token",
            client_id=CONFIG["CLIENT_ID"],
            client_secret=CONFIG["CLIENT_SECRET"],
            refresh_token=request.cookies[CONFIG["REFRESH_COOKIE"]]
          )
          logger.info("Called to refresh token")
          resp = json.loads(resp)
          if "error" in resp:
            logger.info("There was an error refreshing the token, so need to log in again")
            return redirect(au)
          else:
            access_token = resp["access_token"]
            logger.info("Got new access token, returning to client")
            r = make_response(redirect("/"))
            r.set_cookie(CONFIG["AUTH_COOKIE"], access_token)
            return r
        except ExpiredSignatureError as e:
          # refresh token is not valid, so go and get new one
          logger.info("Refresh token not valid, so need to log in again")
          return redirect(au)
      else:
        # return a 302 redirect as we don't have a refresh token
        logger.info("No refresh token present, so need to log in again")
        return redirect(au)
  else:
    # return redirect to login as we don't have the auth cookie
    logger.info("No access token present, so need to log in")
    return redirect(au)

@app.route("/_login")
def login():
  # get the id_token
  auth_code = request.args.get("code")
  logger.info("Auth code: {code}".format(code=auth_code))
  resp = post_to_url(
    url=wkc_data["token_endpoint"],
    grant_type="authorization_code",
    client_id=CONFIG["CLIENT_ID"],
    client_secret=CONFIG["CLIENT_SECRET"],
    code=auth_code,
    redirect_uri="http://localhost:5000/_login"
  )
  resp = json.loads(resp)
  logger.info("Exchanged authorisation code for tokens")
  # validate the token
  access_token = resp["access_token"]
  refresh_token = resp["refresh_token"]
  decoded = validate_jwt(
    token=access_token,
    key_set=keys,
    aud=CONFIG["CLIENT_ID"]
  )
  # set the auth cookies
  r = make_response(redirect("/"))
  r.set_cookie(CONFIG["AUTH_COOKIE"], access_token)
  r.set_cookie(CONFIG["REFRESH_COOKIE"], refresh_token)
  return r

@app.route("/_logout")
def logout():
  # logout from keycloak, if we have the cookie to do it
  logger.info("Logging out")
  if CONFIG["REFRESH_COOKIE"] in request.cookies:
    resp = post_to_url(
      url=wkc_data["end_session_endpoint"][:-1],
      client_id=CONFIG["CLIENT_ID"],
      client_secret=CONFIG["CLIENT_SECRET"],
      refresh_token=request.cookies[CONFIG["REFRESH_COOKIE"]]
    )
  # unset cookies
  r = make_response(redirect("/"))
  r.set_cookie("auth", "", expires=0)
  r.set_cookie("rt", "", expires=0)
  return r

def run():
  """
  Runs the application server in a test context, not for production
  """
  app.run(debug=True, port=5000, host="0.0.0.0", threaded=True)

if __name__ == "__main__":
  run()