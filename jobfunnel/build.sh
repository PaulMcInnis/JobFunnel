#!/bin/bash
# start building the package
rm -rf build
mkdir -p build
cp lambda_function.py build/. 
cp jobfunnel.py build/.
cp glassdoor.py build/.
cp indeed.py build/.
cp monster.py build/.
cp database.py build/.
cp __init__.py build/.
mkdir -p ./build/config/
cp ./config/settings.yaml ./build/config/.
cp ./config/valid_options.py ./build/config/.
mkdir -p ./build/text/
cp ./text/user_agent_list.txt ./build/text/.
mkdir -p ./build/tools/
cp ./tools/delay.py ./build/tools/.
cp ./tools/filters.py ./build/tools/.
cp ./tools/tools.py ./build/tools/.
pip install -r requirements.txt -t ./build/.
cd build; zip -9qr '../build.zip' .
cd ..
rm -rf build