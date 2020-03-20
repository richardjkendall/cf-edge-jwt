#!/usr/bin/sh

rm function.zip
rm -R package/
mkdir package
pip install -r requirements.txt --target ./package 
find ./package -name "*.pyd" -type f -delete
find ./package -name "*.pyc" -type f -delete
rm package/bin/pyjwt
rm package/bin/chardetect
cd package
zip -r9 ${OLDPWD}/function.zip .
cd $OLDPWD
zip -g function.zip lambda.py utils.py
