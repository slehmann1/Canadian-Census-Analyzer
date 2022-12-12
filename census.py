
class Census:
    def __init__(self, year, filename_csv, filename_par, leading_spaces, characteristic_col, geo_col, total_col,
                 geocode_col):
        """
        :param year: The year of the census
        :param filename_csv: The csv filename
        :param filename_par: The parquet filename
        :param leading_spaces: The number of spaces used to indent each characteristic within the characteristic tree
        :param characteristic_col: The name of the column used to hold the characteristic type
        :param geo_col: The column used to hold the value "Alberta"
        :param total_col: The name of the column used to hold the data total
        :param geocode_col: The name of the column that holds the CSDUID
        """
        self.year = year
        self.filename_csv = filename_csv
        self.filename_par = filename_par
        self.leading_spaces = leading_spaces
        self.characteristic_col = characteristic_col
        self.geo_col = geo_col
        self.total_col = total_col
        self.geocode_col = geocode_col
        self.data_df = None
        self.char_tree = None

    def set_data_df(self, data_df):
        self.data_df = data_df

    def set_char_tree(self, char_tree):
        self.char_tree = char_tree


censuses = [Census(2011, "2011CensusData.CSV", "2011CensusData.parquet", 3, "Characteristics", "Prov_Name", "Total",
                   "Geo_Code"),
            Census(2016, "2016CensusData.CSV", "2016CensusData.parquet", 2,
                   "DIM: Profile of Census Divisions/Census Subdivisions (2247)", "GEO_NAME",
                   "Dim: Sex (3): Member ID: [1]: Total - Sex", "ALT_GEO_CODE"),
            Census(2021, "2021CensusData.CSV", "2021CensusData.parquet", 2, "CHARACTERISTIC_NAME", "GEO_NAME",
                   "C1_COUNT_TOTAL", "ALT_GEO_CODE")]
