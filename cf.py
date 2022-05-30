import base64
import json
import logging
from urllib.parse import parse_qs

from utils import build_url, get_wkc, get_certs, post_to_url, validate_jwt, redirect, return_bad_request, set_cookies, get_cookies, ExpiredSignatureError, forbidden

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
  redirect_to = "/"
  # check if state is present
  if "state" in args:
    # need to decode state
    state = args["state"][0]
    logger.info("Got state of: {state}".format(state=state))
    state = base64.b64decode(state).decode("utf-8")
    logger.info("Decoded state: {state}".format(state=state))
    state = json.loads(state)
    if "source_url" in state:
      redirect_to = state["source_url"]
      logger.info("Got source url from state of {url}".format(url=redirect_to))
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
    access_token = resp["access_token"]
    refresh_token = resp["refresh_token"]
    # if there is an allowed group set, we need to check the token has the claim for that group
    if "ALLOWED_GROUP" in CONFIG:
      allowed_group = CONFIG["ALLOWED_GROUP"]
      if allowed_group != "":
        logger.info("Need to check groups")
        decoded_token = validate_jwt(
          api=CONFIG["VAL_API_URL"],
          token=access_token,
          key_set=keys,
          aud=CONFIG["CLIENT_ID"]
        )
        decoded_token = json.loads(decoded_token.decode("utf-8"))
        if "groups" in decoded_token:
          if allowed_group in decoded_token["groups"]:
            logger.info(f"user has expected group of {allowed_group}")
          else:
            logger.info(f"user is missing expected group of {allowed_group}")
            return forbidden(message="You are not in a group with access to this application")
        else:
          logger.info("no groups claim in token")
          return forbidden(message="You are not in a group with access to this application")
    # prepare response
    r = redirect(redirect_to)
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
  # update aurl with state data
  source_url = request["uri"]
  if request["querystring"]:
    source_url = source_url + "?{qs}".format(qs=request["querystring"])
  logger.info("Determined source_url is {s}".format(s=source_url))
  state = {
    "source_url": source_url
  }
  state = base64.b64encode(json.dumps(state).encode("utf-8")).decode("utf-8")
  logger.info("Encoded state: {state}".format(state=state))
  aurl_with_state = "{aurl}&state={state}".format(aurl=aurl, state=state)
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
        return redirect(aurl_with_state)
  else:
    logger.info("No access token present, so need to log in")
    return redirect(aurl_with_state)

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