import os
import pickle
import shutil
import time
import urllib.request
import zipfile

import pandas as pd
from anytree import Node

import census
import interface

TREE_SEPARATOR = "⤚"
NODE_FILENAME = "nodes_list.pickle"
ZIP_FILENAME = "download.zip"
TEMP_LOC = '\\temp'


def download_csv(url, keep_file, filename, remove_first_line = False):
    """
    Downloads a CSV file from statistics canada
    :param url: The URL of the csv file to download
    :param keep_file: The file that should be kept from the zip file
    :param filename: The final filename that the csv should be saved as
    :param remove_first_line: Should the first line of the CSV be removed? Some CSVs have an additional header text
    :return: None
    """
    # Create a temporary directory
    loc = os.getcwd() + TEMP_LOC + "\\"
    os.mkdir(loc)

    #Download the file as a zip file and extract it
    print("Start Download")
    urllib.request.urlretrieve(url,loc+ZIP_FILENAME)
    print("Downloaded")
    with zipfile.ZipFile(loc+ZIP_FILENAME, 'r') as zip_ref:
        zip_ref.extractall(loc)

    # Rename/move the file of interest and delete the temporary directory
    os.rename(loc+keep_file, os.getcwd()+"\\"+filename)
    print("Done")
    shutil.rmtree(loc)

    # Sometimes the first line has to be removed due to additional header text
    if remove_first_line:
        with open(filename, 'r') as fin:
            data = fin.read().splitlines(True)
        with open(filename, 'w') as fout:
            fout.writelines(data[1:])

def save_csv_parquet(cen):
    """
    Loading CSVs are timeconsuming. Read in the CSV and save it as a parquet file which will be quicker to load in the future
    :return: The CSV as a dataframe
    """
    df = pd.read_csv(cen.filename_csv, encoding="latin-1", dtype="str")
    df.to_parquet(cen.filename_par, compression=None)
    return df


def build_geographical_tree(geo_df):
    """
    Builds a tree of all the geographic regions, nested into provinces, censuses, and census sub-divisions
    :param geo_df: A dataframe of the geo_data.csv file provided by statistics canada
    :return:
    """
    canada = Node("Canada")

    # Standard geographical code
    # Ref https://www12.statcan.gc.ca/census-recensement/2021/ref/dict/az/definition-eng.cfm?ID=geo044
    geo_df["SGC"] = geo_df["Geo Code"].str[9:]

    prior_province = None
    prior_census = None

    for _index, geo in geo_df.iterrows():
        if len(geo["SGC"]) == 2:
            # This is a province
            prior_province = Node(geo["Geo Name"], canada)
        elif len(geo["SGC"]) == 4:
            # This is a census
            prior_census = Node(geo["Geo Name"], prior_province)
        elif len(geo["SGC"]) == 7:
            # This is a census subdivison
            Node(geo["Geo Name"], prior_census)
        else:
            raise Exception("Unexpected geographical code length")


def build_characteristic_tree(characteristic_list, leading_spaces=2):
    """
    Builds a tree of all the options in the characteristic tree. Items are indented in the tree based on their
    leading whitespace, with a specified number of spaces per indentation
    :param characteristic_list: A numpy array of strings, where leading spaces indicate their levels of indentation.
    :param leading_spaces: The number of spaces per indentation.
    For example:
    Vehicles
      Cars
        Mercedes
        Rolls-Royce
      Planes
        Airbus
    :return:A node tree with names including numbering
    """
    prior_whitespace = 0
    start_node = Node("Characteristic Types")
    parent = start_node
    prior = start_node

    "All prefixes have a trailing separator"
    prior_prefix = "0" + TREE_SEPARATOR

    total = len(characteristic_list)

    # Loop through all characteristics and build a tree
    for i, characteristic in enumerate(characteristic_list):

        print(f"Characteristic {i} of {total}")
        preprior = characteristic
        characteristic = characteristic.replace(u'\xa0', u' ')
        white_space_chars = int((len(characteristic) - len(characteristic.lstrip())) / leading_spaces)
        characteristic = characteristic.lstrip()

        if white_space_chars == 0:
            # Stems from the start node
            prior_prefix = str(int(prior_prefix.split(TREE_SEPARATOR)[0]) + 1) + TREE_SEPARATOR
            characteristic = prior_prefix + characteristic

            node = Node(characteristic, start_node)

        elif white_space_chars == prior_whitespace:
            # Stems from the same parent as the prior node

            prior_prefix = TREE_SEPARATOR.join(prior_prefix.split(TREE_SEPARATOR)[0:-2]) + TREE_SEPARATOR + str(
                int(prior_prefix.split(TREE_SEPARATOR)[-2]) + 1) + TREE_SEPARATOR

            characteristic = prior_prefix + characteristic

            node = Node(characteristic, parent)

        elif white_space_chars > prior_whitespace:
            # Is a child of the prior node
            prior_prefix += "1" + TREE_SEPARATOR
            characteristic = prior_prefix + characteristic

            node = Node(characteristic, prior)
            parent = prior

        else:
            # Has less indentation than the prior node, decrement the tree
            backup = prior_prefix
            # Loop through the number of decrements
            for i in range(int(prior_whitespace - white_space_chars)):
                prior_prefix = TREE_SEPARATOR.join(prior_prefix.split(TREE_SEPARATOR)[0:-2]) + TREE_SEPARATOR
                prior = prior.parent

            prior_prefix = TREE_SEPARATOR.join(prior_prefix.split(TREE_SEPARATOR)[0:-2]) + TREE_SEPARATOR + str(
                int(prior_prefix.split(TREE_SEPARATOR)[-2]) + 1) + TREE_SEPARATOR

            characteristic = prior_prefix + characteristic

            node = Node(characteristic, prior)
            parent = prior

        prior = node
        prior_whitespace = white_space_chars

    return start_node


def process_data():
    """
    Loads data from CSV files and builds a characteristic tree. This information is saved as a parquet and pickle respectively.
    :return:
    """
    nodes = []
    for i, cen in enumerate(census.censuses):
        print(cen.year)
        data_df = save_csv_parquet(cen)

        characteristic_list = data_df.where(data_df[cen.geo_col] == "Alberta")[
            cen.characteristic_col].dropna().to_numpy()

        nodes.append(build_characteristic_tree(characteristic_list, cen.leading_spaces))

    # Save the nodelist to a pickle
    file = open(NODE_FILENAME, "ab")
    pickle.dump(nodes, file)
    file.close()


def load_data():
    """
    Loads characteristic trees and dataframes from pickles and parquets respectively
    :return:
    """

    file = open(NODE_FILENAME, "rb")
    nodes = pickle.load(file)

    for i, cen in enumerate(census.censuses):
        cen.set_data_df(pd.read_parquet(cen.filename_par))
        cen.set_char_tree(nodes[i])


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print("RUNNING")

    if not os.path.isfile(census.censuses[0].filename_par):
        # Download CSVs
        for cen in census.censuses:
            download_csv(cen.url, cen.filename_keep, cen.filename_csv, cen.delete_first_line)
            print(f"Finished download of {cen.year} census data")

        process_data()
    else:
        print("Files already processed. No need to redownload files")


    current_time = time.time()
    geo_df = pd.read_csv("GeoData.CSV", encoding="latin-1")
    print(f"done loading geo data {time.time() - current_time} seconds")

    load_data()

    print(f"done loading data {time.time() - current_time} seconds")

    interface.generate_interface()