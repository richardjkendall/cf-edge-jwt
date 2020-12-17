# CloudFront Edge Auth

This is a small lambda function which can be deployed on a CloudFront distribution (Viewer Request events) to check that the user is signed in and if not perform a sign-in process.

It works together with Keycloak and another API I developed.  The other API performs JWT validation and it had to be separated out because it uses the Python cryptography module which is too big to package in a Lambda@Edge function (max size 1MB).

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
  "VAL_API_URL": ""
  "MAX_AGE": ""
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

## Validate API

You can find the validate API here https://github.com/richardjkendall/validate-jwt-api
