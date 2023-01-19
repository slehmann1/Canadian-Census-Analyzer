import math
import webbrowser
import folium
import geopandas as gpd
import jinja2
import numpy as np

# Source for map data: https://www12.statcan.gc.ca/census-recensement/alternative_alternatif.cfm?l=eng&dispext=zip&teng=lcsd000b21a_e.zip&k=%20%20%20152326&loc=//www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip

FUNC_LIST = (lambda a: mean_difference(a), lambda a: mean_percent_change(a), lambda a: mean_percent_difference(a))
_ROUND_DECS = 2
_THRESHOLD_LEVELS = 30
_START_LOCATION = [63, -102]


def plot_map(function_name, strings, census_data, func=None, type="Census Subdivisions", clipped=False):
    """
    Creates a map and displays it using folium
    :param census_data: A list of census objects
    :param function_name: The name of the function that operates on data from multiple years
    :param strings: A tuple of the characteristic names to be plotted
    :param func: A function to act on data from each of the years
    :param type: The type of map to be displayed: CSD, Provinces, or LCD. See https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/figures/f1_1-eng.cfm
    :param clipped: Whether or not data with the outliers clipped should be displayed
    :return:
    """
    cad = get_cad_file(type)
    geo_level, geo_name, prop_name = get_property_names(type)

    # Create data column for every type of data
    for census in census_data:
        cad[str(census.year)] = 0

    # Simplify first data
    census_data[0].data_df = census_data[0].data_df.query(
        f"{census_data[0].geocode_col} in @cad['{geo_level}'] and @strings[0] in `{census_data[0].characteristic_col}`")

    if len(census_data) == 1:  # There is only one year
        for index, datum in census_data[0].data_df.query(
                f"`{census_data[0].characteristic_col}` in @strings[0]").iterrows():
            try:
                cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], str(census_data[0].year)] = float(
                    datum[census_data[0].total_col])
            except (TypeError, ValueError):
                # If there is a data quality issue, the data is given as a NAN
                cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], str(census_data[0].year)] = np.NAN
    else:  # There are multiple data sources
        cad[function_name] = 0

        # Simplify the data by eliminating rows that are not needed
        # first reduce the first column to it's minimum length and then simplify the other columns based on the reduced first column
        for i in range(1, len(census_data)):
            x = census_data[i].data_df[census_data[i].geocode_col]
            census_data[0].data_df = census_data[0].data_df.query(f"{census_data[0].geocode_col} in @x")
        for i in range(1, len(census_data)):
            x = census_data[0].data_df[census_data[0].geocode_col]
            census_data[i].data_df = census_data[i].data_df.query(
                f"(`{census_data[i].characteristic_col}` in @strings[@i]) and ({census_data[i].geocode_col} in @x)")

        proc_rows(census_data, function_name, func, cad, geo_level, strings)

    m = folium.Map(location=_START_LOCATION, zoom_start=4)

    if len(census_data) == 1:
        if clipped:
            column = str(census_data[0].year) + " clipped"
            cad[str(census_data[0].year) + " clipped"] = clip_outliers(cad[str(census_data[0].year)])

        else:
            column = str(census_data[0].year)

        choro = gen_choropleth(cad, geo_level, column, prop_name, strings[0], census_data[0].year)
        choro.add_to(m)

        hover_fields = [str(census_data[0].year), geo_name, geo_level]

    else:
        if clipped:
            column = clip_df_column(function_name, cad)
        else:
            column = function_name

        choro = gen_choropleth(cad, geo_level, column, prop_name, function_name, function_name, show=False)
        choro.add_to(m)

        columns = []

        for i in range(0, len(census_data)):

            if clipped:
                columns.append(clip_df_column(str(census_data[i].year), cad))
            else:
                columns.append(str(census_data[i].year))

        thresholds = det_thresholds(cad, columns)

        for i, column in enumerate(columns):
            # Create the choropleth, where only the first year is shown
            choro = gen_choropleth(cad, geo_level, column, prop_name,
                                   census_data[i].data_df[census_data[i].characteristic_col].values[0],
                                   census_data[i].year, thresholds, show=i == 0)
            choro.add_to(m)

        lc = gen_layer_controller()
        lc.add_to(m)

        hover_fields = []
        for i in range(len(census_data)):
            hover_fields.append(str(census_data[i].year))
        hover_fields.extend([function_name, geo_name, geo_level])

    hover_bubble = gen_hover_bubble(cad, hover_fields)
    m.add_child(hover_bubble)
    m.keep_in_front(hover_bubble)

    output_map(m)


def clip_df_column(unclipped_column, df):
    """
    Adds a column of clipped values to a dataframe
    :param unclipped_column: The name of the column containing unclipped data
    :param df: The dataframe to modify
    :return: The name of the column added to the dataframe
    """
    column = unclipped_column + " clipped"
    df[unclipped_column + " clipped"] = clip_outliers(df[unclipped_column])
    return column


def proc_rows(census_data, function_name, func, cad, geo_level, strings):
    """
    Processes rows of a cad dataframe, populating a column for both annual data and function data
    :param census_data: A list of census objects
    :param function_name: The name of the function used to operate on multiple years
    :param func: The function that operates on data from multiple years
    :param cad: The pandas dataframe containing data to be modified
    :param geo_level: The geographic level used
    :param strings: A tuple of the characteristic names to be plotted
    :return: None. The data within the cad object is modified
    """
    total = sum(
        1 for _ in census_data[0].data_df.query(f"`{census_data[0].characteristic_col}` in @strings[0]").iterrows())
    count = 0

    for index, datum in census_data[0].data_df.query(
            f"`{census_data[0].characteristic_col}` in @strings[0]").iterrows():
        count += 1
        print(f"Currently processing {count} of {total} data rows")

        # Populate function data
        try:
            func_data = np.array([float(datum[census_data[0].total_col])])
            for i in range(1, len(census_data)):
                func_data = np.append(func_data, float(census_data[i].data_df.query(
                    f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[
                                                           census_data[i].total_col]))

            cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], function_name] = func(func_data)
        except (TypeError, ValueError):
            # If there is a data quality issue, the data is given as a NAN
            cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], function_name] = np.NAN

        # Populate annual data
        for i in range(0, len(census_data)):
            try:
                cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], str(census_data[i].year)] = float(
                    census_data[i].data_df.query(
                        f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[
                        census_data[i].total_col])

            except (TypeError, ValueError):
                # If there is a data quality issue, the data is given as a NAN
                cad.loc[cad[geo_level] == datum[census_data[0].geocode_col], str(census_data[i].year)] = np.NAN


def det_thresholds(cad, columns):
    """
    Returns a np array of a threshold scale that can be used in a Folium legend
    :param cad: The cad data
    :param columns: A list of strings corresponding to columns in the cad data
    :return: Threshold scale in the form of an np array
    """
    minimum, maximum = get_range(cad, columns)
    step_size = (maximum - minimum) / _THRESHOLD_LEVELS
    thresholds = np.arange(minimum, maximum + step_size, step_size)
    return thresholds


def get_range(df, columns):
    """
    Determines the range of values seen in multiple columns of a pandas dataframe
    :param df: The dataframe
    :param columns: A string value of the columns to be considered
    :return:
    """

    minimum, maximum = math.inf, -math.inf
    for column in columns:
        if df[column].max() > maximum:
            maximum = df[column].max()
        if df[column].min() < minimum:
            minimum = df[column].min()

    return minimum, maximum


def get_property_names(type):
    """
    Gets the property names of the cad file for a given type of census geography
    :param type: A string representing the type of geography desired: "Census Subdivisions", "Census Divisions", or "Provinces"
    :return: geo_level, geo_name, prop_name
    """

    if type == "Census Subdivisions":
        geo_level = "CSDUID"
        geo_name = "CSDNAME"
        prop_name = "feature.properties.CSDUID"
    elif type == "Provinces":
        geo_level = "PRUID"
        geo_name = "PRNAME"
        prop_name = "feature.properties.PRUID"
    elif type == "Census Divisions":
        geo_level = "CDUID"
        geo_name = "CDNAME"
        prop_name = "feature.properties.CDUID"
    else:
        raise ValueError("Incorrect type provided")

    return geo_level, geo_name, prop_name


def get_cad_file(type):
    """
    Reads the correct geopandas dataframe based on the type of geography desired
    :param type: A string representing the type of geography desired: "Census Subdivisions", "Census Divisions", or "Provinces"
    :return: A geopandas dataframe
    """
    if type == "Census Subdivisions":
        cad = gpd.read_file("mapData/simplified/Census Sub Divisions/lcsd000b21a_e.shp")
    elif type == "Provinces":
        cad = gpd.read_file("mapData/simplified/Provinces/lpr_000b21a_e.shp")
    elif type == "Census Divisions":
        cad = gpd.read_file("mapData/simplified/Census Divisions/lcd_000b21a_e.shp")
    else:
        raise ValueError("Incorrect type provided")
    return cad


def output_map(m):
    """
    Saves and opens a folium map
    :param m: A folium map
    :return: None
    """
    outfp = "map.html"
    m.save(outfp)
    webbrowser.open("map.html")


def gen_choropleth(data, column_1, column_2, key_on, legend_name, name, thresholds=None, show=True):
    """
    Creates a folium choropleth with the appropriate formatting
    :param show: Should the choropleth be shown by default?
    :param data: The data to be displayed
    :param column_1: The column used as the key column
    :param column_2: The data column
    :param key_on:
    :param legend_name: The name to be applied to the legend
    :param name: The name for the layer

    :return: A folium.choropleth object
    """
    if thresholds is not None:
        return folium.Choropleth(
            geo_data=data,
            data=data,
            columns=[column_1, column_2],
            key_on=key_on,
            fill_color='YlGnBu',
            fill_opacity=1,
            line_opacity=0.2,
            legend_name=legend_name,
            smooth_factor=0,
            Highlight=True,
            line_color="#0000",
            name=name,
            show=show,
            overlay=True,
            nan_fill_color="White",
            threshold_scale=thresholds
        )
    else:
        return folium.Choropleth(
            geo_data=data,
            data=data,
            columns=[column_1, column_2],
            key_on=key_on,
            fill_color='YlGnBu',
            fill_opacity=1,
            line_opacity=0.2,
            legend_name=legend_name,
            smooth_factor=0,
            Highlight=True,
            line_color="#0000",
            name=name,
            show=show,
            overlay=True,
            nan_fill_color="White"
        )


def gen_layer_controller():
    """
    Creates a formatted layer controller which may be added to a folium map
    :return:A Layer Control object
    """

    # Add a layer controller and override the default template to remove the baselayer box
    lc = folium.LayerControl(collapsed=False, tiles=False)
    lc._template = jinja2.Template("""
                {% macro script(this,kwargs) %}
                    var {{ this.get_name() }} = {
                        base_layers : {},
                        overlays :  {
                            {%- for key, val in this.overlays.items() %}
                            {{ key|tojson }} : {{val}},
                            {%- endfor %}
                        },
                    };
                    L.control.layers(
                        {{ this.get_name() }}.base_layers,
                        {{ this.get_name() }}.overlays,
                        {{ this.options|tojson }}
                    ).addTo({{this._parent.get_name()}});

                    {%- for val in this.layers_untoggle.values() %}
                    {{ val }}.remove();
                    {%- endfor %}
                {% endmacro %}
                """)
    return lc


def gen_hover_bubble(data, hover_fields):
    """
    Creates a hover bubble that may be applied to a folium map
    :param hover_fields: The fields of the data that should be displayed within the hover bubble
    :return: A GeoJson object representing a hover bubble
    """

    # Add hover functionality.
    def style_function(_):
        return {'fillColor': '#ffffff',
                'color': '#000000',
                'fillOpacity': 0.1,
                'weight': 0.1}

    def highlight_function(_):
        return {'fillColor': '#000000',
                'color': '#000000',
                'fillOpacity': 0.50,
                'weight': 0.1}

    hover_bubble = folium.features.GeoJson(
        data=data,
        style_function=style_function,
        control=False,
        highlight_function=highlight_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=hover_fields,
            aliases=hover_fields,
            style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
        )
    )
    return hover_bubble


def mean_difference(data):
    diffs = []

    for i in range(1, len(data)):
        diffs.append(data[i] - data[i - 1])

    return np.round(np.mean(diffs), _ROUND_DECS)


def mean_percent_difference(data):
    diffs = []
    for i in range(1, len(data)):
        if np.mean((data[i], data[i - 1])) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.mean((data[i], data[i - 1]))) * 100)

    return np.round(np.mean(diffs), _ROUND_DECS)


def mean_percent_change(data):
    diffs = []
    for i in range(1, len(data)):
        if np.abs(data[i - 1]) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.abs(data[i - 1])) * 100)

    return np.round(np.mean(diffs), _ROUND_DECS)


def clip_outliers(df):
    """
    Removes outliers for a pandas dataframe based on usage of the interquartile range
    :param df: The dataframe for outliers to be removed from
    :return:The dataframe with outliers clipped
    """
    iqr = df.quantile(0.75) - df.quantile(0.25)
    # Clip data that is 3 iqrs beyond the first or third quartile
    return df.clip(df.quantile(0.25) - 3 * iqr, df.quantile(0.75) + 3 * iqr)
