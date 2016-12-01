#!/bin/bash

INDEX=$1
AWS_PUBLIC_DS="https://s3.amazonaws.com"
CC="commoncrawl/cc-index/collections"

if [ ! -d "collections" ]; then
    mkdir collections
fi

if [ -z "$INDEX" ]; then
    INDEX="CC-MAIN-2015-18"
fi

if [ ! -d "collections/$INDEX" ]; then
    mkdir "collections/$INDEX"
    mkdir "collections/$INDEX/indexes"
fi

wget $AWS_PUBLIC_DS/$CC/$INDEX/metadata.yaml -O collections/$INDEX/metadata.yaml
wget $AWS_PUBLIC_DS/$CC/$INDEX/indexes/cluster.idx -O collections/$INDEX/indexes/cluster.idx
