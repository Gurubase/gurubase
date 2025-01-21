#!/bin/bash

# Usage: ./create_tag.sh v1.0.0

set -e

cd /tmp && mkdir -p gurubase && cd gurubase

git clone git@github.com:Gurubase/gurubase.git

cd gurubase

git checkout master && git pull

git tag $1
git push origin $1

rm -rf /tmp/gurubase
