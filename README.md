# CloudFront Edge Auth

## Latest Update 01/06/22

Now supports allowing/denying access based on group membership

## Introduction

This is a small lambda function which can be deployed on a CloudFront distribution (Viewer Request events) to check that the user is signed in and if not perform a sign-in process.

It works together with Keycloak and another API I developed.  The other API performs JWT validation and it had to be separated out because it uses the Python cryptography module which is too big to package in a Lambda@Edge function (max size 1MB).

It preserves the requested resource during a login event e.g. if the user attempts to access /deep/link/in/your/site then the final redirect after login will be back to this location.

## Requirements

The code looks for a file called `settings.json` to load its config (Lambda@Edge does not support environment variables).  The file should have the following structure

```json
{
  "HOST": "",
  "REALM": "",
  "CLIENT_ID": "",
  "CLIENT_SECRET": "",
  "AUTH_COOKIE": "",
  "REFRESH_COOKIE": "",
  "VAL_API_URL": "",
  "MAX_AGE": "",
  "REDIRECT_URI": "",
  "ALLOWED_GROUP": "",
  "ACCESS_DENIED_MESSAGE": "",
  "STATE_SECRET": ""
}
```

Where the values are

|Field|Value|
|---|---|
|HOST|DNS name of Keycloak host|
|REALM|Name of realm as configured on Keycloak - case sensitive|
|CLIENT_ID|ID for client as configured on Keycloak|
|CLIENT_SECRET|Secret for client as configured on Keycloak|
|AUTH_COOKIE|Name of the cookie used to store the JWT access token|
|REFRESH_COOKIE|Name of the cookie used to store the JWT refresh token|
|VAL_API_URL|URL for the JWT validate API|
|MAX_AGE|The max age the cookies will live, in seconds|
|REDIRECT_URI|Where should the IdP redirect back to, should be the CF distribution DNS name/alias with /_login on the end e.g. https://blah.com/_login
|ALLOWED_GROUP|What group needs to be present in the groups claim in order for access to be allowed|
|ACCESS_DENIED_MESSAGE|What message should be shown to a user who is denied access to to the site|
|STATE_SECRET|A secret string used to hash the state data and verify that the state received is valid|

## Validate API

You can find the validate API here https://github.com/richardjkendall/validate-jwt-api
