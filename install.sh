#!/bin/sh

echo "{" >> "settings.json"
echo "  \"HOST\": \"$HOST\"," >> "settings.json"
echo "  \"REALM\": \"$REALM\"," >> "settings.json"
echo "  \"CLIENT_ID\": \"$CLIENT_ID\"," >> "settings.json"
echo "  \"CLIENT_SECRET\": \"$CLIENT_SECRET\"," >> "settings.json"
echo "  \"AUTH_COOKIE\": \"$AUTH_COOKIE\"," >> "settings.json"
echo "  \"REFRESH_COOKIE\": \"$REFRESH_COOKIE\"," >> "settings.json"
echo "  \"REDIRECT_URI\": \"$REDIRECT_URI\"," >> "settings.json"
echo "  \"VAL_API_URL\": \"$VAL_API_URL\"," >> "settings.json"
echo "  \"MAX_AGE\": \"$MAX_AGE\"," >> "settings.json"
echo "  \"ALLOWED_GROUP\": \"$ALLOWED_GROUP\"," >> "settings.json"
echo "  \"ACCESS_DENIED_MESSAGE\": \"$ACCESS_DENIED_MESSAGE\"," >> "settings.json"
echo "  \"STATE_SECRET\": \"$STATE_SECRET\"" >> "settings.json"
echo "}" >> "settings.json"

# remove test files
rm test.py
rm cf.py
