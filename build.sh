#!/bin/sh

rm function.zip
rm -R package/
mkdir package
pip install -r requirements.txt --target ./package 
cd package
zip -r9 ${OLDPWD}/function.zip .
cd $OLDPWD
zip -g function.zip lambda.py utils.py
