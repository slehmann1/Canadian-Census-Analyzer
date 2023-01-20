# Author: Sam Lehmann
# Network with him at: https://www.linkedin.com/in/samuellehmann/
# Date: 2023-01-19

class Census:
    def __init__(self, year, url, filename_keep, filename_csv, filename_par, leading_spaces, characteristic_col,
                 geo_col, total_col,
                 geocode_col, delete_first_line=False):
        """
        :param year: The year of the census
        :param url: The download url
        :param filename_keep: The file to keep from the downloaded zip file
        :param filename_csv: The csv filename
        :param filename_par: The parquet filename
        :param leading_spaces: The number of spaces used to indent each characteristic within the characteristic tree
        :param characteristic_col: The name of the column used to hold the characteristic type
        :param geo_col: The column used to hold the value "Alberta"
        :param total_col: The name of the column used to hold the data total
        :param geocode_col: The name of the column that holds the CSDUID
        :param delete_first_line: Whether the first line of the csv should be deleted
        """
        self.year = year
        self.url = url
        self.filename_keep = filename_keep
        self.filename_csv = filename_csv
        self.filename_par = filename_par
        self.leading_spaces = leading_spaces
        self.characteristic_col = characteristic_col
        self.geo_col = geo_col
        self.total_col = total_col
        self.geocode_col = geocode_col
        self.data_df = None
        self.char_tree = None
        self.delete_first_line = delete_first_line

    def set_data_df(self, data_df):
        self.data_df = data_df

    def set_char_tree(self, char_tree):
        self.char_tree = char_tree


censuses = [Census(2011,
                   "https://www12.statcan.gc.ca/census-recensement/2011/dp-pd/prof/details/download-telecharger/comprehensive/comp_download.cfm?CTLG=98-316-XWE2011001&FMT=CSV301&Lang=E&Tab=1&Geo1=PR&Code1=01&Geo2=PR&Code2=01&Data=Count&SearchText=&SearchType=Begins&SearchPR=01&B1=All&Custom=&TABID=1",
                   "98-316-XWE2011001-301.CSV", "2011CensusData.CSV", "2011CensusData.parquet", 3, "Characteristics",
                   "Prov_Name", "Total",
                   "Geo_Code", delete_first_line=True),
            Census(2016,
                   "https://www12.statcan.gc.ca/census-recensement/2016/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=055",
                   "98-401-X2016055_English_CSV_data.csv", "2016CensusData.CSV", "2016CensusData.parquet", 2,
                   "DIM: Profile of Census Divisions/Census Subdivisions (2247)", "GEO_NAME",
                   "Dim: Sex (3): Member ID: [1]: Total - Sex", "ALT_GEO_CODE"),
            Census(2021,
                   "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=005",
                   "98-401-X2021005_English_CSV_data.csv", "2021CensusData.CSV", "2021CensusData.parquet", 2,
                   "CHARACTERISTIC_NAME", "GEO_NAME",
                   "C1_COUNT_TOTAL", "ALT_GEO_CODE")]
