import json
import logging
from urllib.parse import parse_qs

from utils import build_url, get_wkc, get_certs, post_to_url, validate_jwt, redirect, return_bad_request, set_cookies, get_cookies, ExpiredSignatureError

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s')
logger = logging.getLogger(__name__)

CONFIG = {}

# make sure we have the config data
logger.info("Global: getting config data")

# load the settings json
with open("settings.json") as f:
  CONFIG = json.load(f)

wkc_data = get_wkc(
  host=CONFIG["HOST"],
  realm=CONFIG["REALM"]
)
keys = get_certs(
  url=wkc_data["jwks_uri"]
)
aurl = build_url(
  base=wkc_data["authorization_endpoint"],
  client_id=CONFIG["CLIENT_ID"],
  response_type="code",
  redirect_uri=CONFIG["REDIRECT_URI"]
)
logger.info("Global: got auth URL: {url}".format(url=aurl))

def handle_login(request):
  logger.info("Starting handle_login")
  args = parse_qs(request["querystring"])
  try:
    auth_code = args["code"]
    logger.info("Got auth code from query string: {code}".format(code=auth_code))
    # swap the authorisation code for tokens
    resp = post_to_url(
      url=wkc_data["token_endpoint"],
      grant_type="authorization_code",
      client_id=CONFIG["CLIENT_ID"],
      client_secret=CONFIG["CLIENT_SECRET"],
      code=auth_code,
      redirect_uri=CONFIG["REDIRECT_URI"]
    )
    resp = json.loads(resp)
    logger.info("Exchanged authorisation code for tokens")
    # validate the token
    access_token = resp["access_token"]
    refresh_token = resp["refresh_token"]
    # prepare response
    r = redirect("/")
    cookies = {}
    cookies[CONFIG["AUTH_COOKIE"]] = access_token
    cookies[CONFIG["REFRESH_COOKIE"]] = refresh_token
    r = set_cookies(
      response=r,
      cookies=cookies,
      max_age=CONFIG.get("MAX_AGE", "10")
    )
    logger.info("Returning response to client")
    return r
  except KeyError:
    return return_bad_request("Bad request missing parameter")

def handle_logout(request):
  logger.info("Starting handle_logout")
  cookies = get_cookies(request["headers"])
  # check for refresh token, which we need to call logout
  if CONFIG["REFRESH_COOKIE"] in cookies:
    logger.info("Posting to logout URL")
    resp = post_to_url(
      url=wkc_data["end_session_endpoint"],
      client_id=CONFIG["CLIENT_ID"],
      client_secret=CONFIG["CLIENT_SECRET"],
      refresh_token=cookies[CONFIG["REFRESH_COOKIE"]]
    )
    logger.info("Back from post to logout URL, resp={r}".format(r=resp))
  # unset cookies
  r = redirect("/")
  cookies[CONFIG["AUTH_COOKIE"]] = ""
  cookies[CONFIG["REFRESH_COOKIE"]] = ""
  r = set_cookies(
    response=r,
    cookies=cookies
  )
  logger.info("Returning response to client")
  return r

def check_session(request):
  logger.info("Starting check_session")
  cookies = get_cookies(request["headers"])
  # check for auth token
  if CONFIG["AUTH_COOKIE"] in cookies:
    logger.info("Got access token")
    # try to validate the token
    try:
      decoded = validate_jwt(
        api=CONFIG["VAL_API_URL"],
        token=cookies[CONFIG["AUTH_COOKIE"]],
        key_set=keys,
        aud=CONFIG["CLIENT_ID"]
      )
      logger.info("Access token is valid")
      return request
    except ExpiredSignatureError as e:
      # token is not valid
      logger.info("Access token has expired, so going to attempt to refresh")
      if CONFIG["REFRESH_COOKIE"] in cookies:
        # we have a refresh token
        logger.info("Refreshing token")
        resp = post_to_url(
          url=wkc_data["token_endpoint"],
          grant_type="refresh_token",
          client_id=CONFIG["CLIENT_ID"],
          client_secret=CONFIG["CLIENT_SECRET"],
          refresh_token=cookies[CONFIG["REFRESH_COOKIE"]]
        )
        logger.info("Called to refresh token")
        resp = json.loads(resp)
        if "error" in resp:
          logger.info("There was an error refreshing the token, so need to log in again")
          return redirect(aurl)
        else:
          access_token = resp["access_token"]
          logger.info("Got new access token, returning to client")
          r = redirect("/")
          cookies[CONFIG["AUTH_COOKIE"]] = access_token
          r = set_cookies(
            response=r,
            cookies=cookies,
            max_age=CONFIG.get("MAX_AGE", "10")
          )
          return r
      else:
        # return a 302 redirect as we don't have a refresh token
        logger.info("No refresh token present, so need to log in again")
        return redirect(aurl)
  else:
    logger.info("No access token present, so need to log in")
    return redirect(aurl)

def lambda_handler(event, context):
  # get the request
  request = event["Records"][0]["cf"]["request"]
  # check if it is one of our special URIs: _login, _logout or otherwise
  uri = request["uri"]
  if uri == "/_login":
    return handle_login(request)
  elif uri == "/_logout":
    return handle_logout(request)
  else:
    return check_session(request)