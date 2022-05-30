#
# A Test harness for this code
#

from flask import Flask, request, make_response, jsonify
from cf import handle_login, check_session

app = Flask(__name__)

def convert_headers(headers):
  h = {}
  for key,value in dict(headers).items():
    h[key] = [{
      "key": key,
      "value": value
    }]
  return h

@app.route("/")
def check():
  r = {
    "querystring": request.query_string.decode(),
    "headers": convert_headers(request.headers),
    "uri": request.path
  }
  r = check_session(r)
  return make_response(
    jsonify(r),
    200
  )


@app.route("/_login")
def hello_world():
  r = {
    "querystring": request.query_string.decode()
  }
  r = handle_login(r)
  return make_response(
    jsonify(r),
    200
  )

if __name__ == '__main__':
  app.run(debug=True, port=5000, host="0.0.0.0", threaded=True)