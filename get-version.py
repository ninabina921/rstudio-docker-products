#!/usr/bin/env python3
import re
import requests
import json
import argparse
import sys


def clean_product_version(version):
    if version == 'latest':
        version = 'release'
    return version


def clean_product_selection(product):
    pref = re.compile('^rstudio-')
    product = pref.sub('', product)

    suffix = re.compile('-preview$')
    product = suffix.sub('', product)

    session_pref = re.compile('^r-session')
    if session_pref.match(product):
        print(f"Swapping product '{product}' for 'workbench'", file=sys.stderr)
        product = 'workbench'

    connect_pref = re.compile('^rstudio-connect')
    if connect_pref.match(product):
        print(f"Swapping product '{product}' for 'connect'", file=sys.stderr)
        product = 'connect'

    return product


def rstudio_workbench_daily():
    daily_url = "https://dailies.rstudio.com/rstudioserver/pro/bionic/x86_64/"
    raw_daily = requests.get(daily_url).content

    version_regex = re.compile('rstudio-workbench-([0-9\.\-]*)-amd64.deb')
    version_match = version_regex.search(str(raw_daily))

    # group 0 = whole match, group 1 = first capture group
    return version_match.group(1)


def get_downloads_json():
    downloads_json_url = "https://rstudio.com/wp-content/downloads.json"
    raw_downloads_json = requests.get(downloads_json_url).content
    downloads_json = json.loads(raw_downloads_json)
    return downloads_json


def rstudio_workbench_preview():
    downloads_json = get_downloads_json()
    return downloads_json['rstudio']['pro']['preview']['version']


def get_local_version(product):
    if product == 'workbench':
        prefix = 'RSP'
    elif product == 'connect':
        prefix = 'RSC'
    elif product == 'package-manager':
        prefix = 'RSPM'
    else:
        raise ValueError(f'Invalid product {product}')

    with open('Makefile', 'r') as f:
        content = f.read()

    vers = re.compile(f'{prefix}_VERSION \?= (.*)')
    res = vers.search(content)
    # from the first capture group
    output_version = res[1]
    return output_version


def get_release_version(product):
    downloads_json = get_downloads_json()
    if product == 'workbench':
        return downloads_json['rstudio']['pro']['stable']['version']
    elif product == 'connect':
        return downloads_json['connect']['installer']['focal']['version']
    elif product == 'package-manager':
        return downloads_json['rspm']['installer']['focal']['version']
    else:
        raise ValueError(f'Invalid product {product}')


def rstudio_connect_daily():
    latest_url = "https://cdn.rstudio.com/connect/latest-packages.json"

    raw_content = requests.get(latest_url).content
    connect_build_info = json.loads(raw_content)

    # just grab the first... all we need is a version string... (for now)
    return connect_build_info['packages'][0]['version']


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arguments to determine product version")
    parser.add_argument(
        "product",
        type=str,
        nargs=1,
        help="The product to search. One of 'connect', 'workbench' or 'package-manager'"
    )
    parser.add_argument(
        "--type",
        type=str,
        nargs=1,
        help="The type of version to retrieve. One of 'daily', 'preview' or 'release' (default: 'release')",
        default=["release"]
    )
    args = parser.parse_args()

    selected_product = args.product[0]
    version_type = args.type[0]

    # clean off "rstudio-" prefix
    # TODO: allow aliases?
    selected_product = clean_product_selection(selected_product)

    version_type = clean_product_version(version_type)

    if selected_product not in ['workbench', 'package-manager', 'connect']:
        print(
            f"ERROR: Please choose a product from 'connect', 'workbench' or 'package-manager'. "
            f"You provided '{selected_product}'",
            file=sys.stderr
        )
        exit(1)

    if version_type not in ['daily', 'preview', 'release']:
        print(
            f"ERROR: Please choose a version type from 'daily', 'preview' or 'release'. "
            f"You provided '{version_type}'",
            file=sys.stderr
        )
        exit(1)

    print(f"Providing version for product: '{selected_product}' and version type: '{version_type}'", file=sys.stderr)

    if selected_product == 'workbench':
        if version_type == 'daily':
            version = rstudio_workbench_daily()
        elif version_type == 'preview':
            version = rstudio_workbench_preview()
        elif version_type == 'release':
            version = get_local_version(selected_product)
        else:
            print(
                f"ERROR: RStudio Workbench does not have the notion of a '{version_type}' version",
                file=sys.stderr
            )
            exit(1)
    elif selected_product == 'connect':
        if version_type == 'daily':
            version = rstudio_connect_daily()
        elif version_type == 'release':
            version = get_local_version(selected_product)
        else:
            print(
                f"ERROR: RStudio Connect does not have the notion of a '{version_type}' version",
                file=sys.stderr
            )
            exit(1)
    elif selected_product == 'package-manager':
        if version_type == 'release':
            version = get_local_version(selected_product)
        else:
            print(
                f"ERROR: RStudio Connect does not have the notion of a '{version_type}' version",
                file=sys.stderr
            )
            exit(1)
    else:
        print(
            f"ERROR: product '{selected_product}' with '{version_type}' version is not defined",
            file=sys.stderr
        )
        exit(1)

    print(f"Got {version_type} version: '{version}'", file=sys.stderr)
    print(version)
