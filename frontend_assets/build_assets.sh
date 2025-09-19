#!/usr/bin/env bash
set -v

assets_path=`realpath $(dirname $0)`
output_path=`realpath $(dirname $0)`/../output

(cd $assets_path;
    set -v;
    npm install;
    rm -rf $assets_path/static;
    mkdir $assets_path/static;
    rm $output_path/frontend_assets;
    mkdir -p $output_path
    ln -s $assets_path/static $output_path/frontend_assets;
    cp -r $assets_path/img $assets_path/static;
    npm run build;
)
