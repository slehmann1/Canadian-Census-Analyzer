import webbrowser
import folium
import geopandas as gpd
import jinja2
import matplotlib.pyplot as plt
import time
import numpy as np

# Source for map data: https://www12.statcan.gc.ca/census-recensement/alternative_alternatif.cfm?l=eng&dispext=zip&teng=lcsd000b21a_e.zip&k=%20%20%20152326&loc=//www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip

FUNC_LIST = (lambda a: mean_difference(a), lambda a: mean_percent_change(a), lambda a: mean_percent_difference(a))
ROUND_DECS = 2

def plot_map(function_name, strings, census_data, func = None, type="csd"):
    """
    Creates a map and displays it using folium
    :param title: The title of the plot
    :param data: A tuple of data to be displayed
    :param strings: A tuple of the characteristic names to be plotted
    :param years: A tuple of the years plotted
    :param func: A function to act on data from each of the years
    :param type: The type of map to be displayed: CSD, Provinces, or LCD. See https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/figures/f1_1-eng.cfm
    :return:
    """

    if type == "csd":
        cad = gpd.read_file("mapData/simplified/Census Sub Divisions/lcsd000b21a_e.shp")
    elif type == "provinces":
        cad = gpd.read_file("mapData/simplified/Provinces/lpr_000b21a_e.shp")
    else:
        cad = gpd.read_file("mapData/simplified/Census Divisions/lcd_000b21a_e.shp")

    # Create data column for every type of data
    for census in census_data:
        cad[str(census.year)] = 0

    cad["include"] = True

    # Simplify first data
    census_data[0].data_df = census_data[0].data_df.query(f"{census_data[0].geocode_col} in @cad['CSDUID'] and @strings[0] in {census_data[0].characteristic_col}")

    if len(census_data) == 1:
        for index, datum in census_data[0].query(f"{census_data[0].characteristic_col} in @string_1").iterrows():
            # There is only one data listed
            cad.loc[cad["CSDUID"] == datum[datum.geocode_col], function_name] = datum[datum.total_col]
    else:
        # There are multiple data sources
        cad[function_name] = 0

        # Simplify the data by eliminating rows that are not needed
        # first reduce the first column to it's minimum length and then simplify the other columns based on the reduced first column
        for i in range(1, len(census_data)):
            x = census_data[i].data_df[census_data[i].geocode_col]
            census_data[0].data_df = census_data[0].data_df.query(f"{census_data[0].geocode_col} in @x")
        for i in range(1, len(census_data)):
            x = census_data[0].data_df[census_data[0].geocode_col]
            census_data[i].data_df = census_data[i].data_df.query(f"(`{census_data[i].characteristic_col}` in @strings[@i]) and ({census_data[i].geocode_col} in @x)")

        total = sum(1 for _ in census_data[0].data_df.query(f"{census_data[0].characteristic_col} in @strings[0]").iterrows())
        t = time.time()
        print(f"Start code of interest")
        count = 0
        for index, datum in census_data[0].data_df.query(f"{census_data[0].characteristic_col} in @strings[0]").iterrows():
            count +=1
            print(f"{count} of {total}")

            try:
                # Build a list of
                func_data = np.array([float(datum[census_data[0].total_col])])
                for i in range(1, len(census_data)):
                    func_data = np.append(func_data, float(census_data[i].data_df.query(f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[census_data[i].total_col]))

                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], function_name] = func(func_data)
            except (TypeError, ValueError):
                # If there is a data quality issue, the data is given as a NAN
                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], function_name] = np.NAN

            for i in range(0, len(census_data)):
                try:
                    cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[i].year)] = float(census_data[i].data_df.query(f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[census_data[i].total_col])
                except (TypeError, ValueError):
                    # If there is a data quality issue, the data is given as a NAN
                    cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[i].year)] = np.NAN



    print(f"End code of interest, time = {time.time() - t}")
    fig, ax = plt.subplots(1, figsize=(10, 6))

    # Create a duplicate copy of the data with outliers removed, prevents the colour bar from being thrown off, but
    # allows the data to still be inspected
    cad["Cleansed delta"] = clip_outliers(cad[function_name])
    cad = cad.loc[cad["include"] == True]

    m = folium.Map(location=[63, -102], zoom_start=4)

    # Add hover functionality.
    style_function = lambda x: {'fillColor': '#ffffff',
                                'color': '#000000',
                                'fillOpacity': 0.1,
                                'weight': 0.1}

    highlight_function = lambda x: {'fillColor': '#000000',
                                    'color': '#000000',
                                    'fillOpacity': 0.50,
                                    'weight': 0.1}

    #TODO: Make the colourmap uniform across the years

    if census_data[1].data_df is None:
        folium.Choropleth(
            geo_data=cad,
            data=cad,
            columns=["CSDUID", str(census_data[0].year)],
            key_on="feature.properties.CSDUID",
            fill_color='YlGnBu',
            fill_opacity=1,
            line_opacity=0.2,
            legend_name=strings[0],
            smooth_factor=0,
            Highlight=True,
            line_color="#0000",
            name=census_data[0].year,
            show=True,
            overlay=True,
            nan_fill_color="White"
        ).add_to(m)

        hover_bubble = folium.features.GeoJson(
            data=cad,
            style_function=style_function,
            control=False,
            highlight_function=highlight_function,
            tooltip=folium.features.GeoJsonTooltip(
                fields=[str(census_data[0].year), "CSDNAME", "CSDUID"],
                aliases=[str(census_data[0].year), "CSDNAME", "CSDUID"],
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
            )
        )

    else:
        folium.Choropleth(
            geo_data=cad,
            data=cad,
            columns=["CSDUID","Cleansed delta"],
            key_on="feature.properties.CSDUID",
            fill_color='YlGnBu',
            fill_opacity=1,
            line_opacity=0.2,
            legend_name=function_name,
            smooth_factor=0,
            Highlight=True,
            line_color="#0000",
            name=function_name,
            show=True,
            overlay=True,
            nan_fill_color="White"
        ).add_to(m)

        for i in range(0, len(census_data)):
            folium.Choropleth(
                geo_data=cad,
                data=cad,
                columns=["CSDUID", str(census_data[i].year)],
                key_on="feature.properties.CSDUID",
                fill_color='YlGnBu',
                fill_opacity=1,
                line_opacity=0.2,
                legend_name=census_data[i].data_df[census_data[i].characteristic_col].values[0],
                smooth_factor=0,
                Highlight=True,
                line_color="#0000",
                name=census_data[i].year,
                show=False,
                overlay=True,
                nan_fill_color="White"
            ).add_to(m)

        # Add a layer controller and override the default template to remove the baselayer box
        lc = folium.LayerControl(collapsed=False, tiles = False).add_to(m)
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

        fields = []
        for i in range(len(census_data)):
            fields.append(str(census_data[i].year))
        fields.extend([function_name, "CSDNAME", "CSDUID"])

        hover_bubble = folium.features.GeoJson(
            data=cad,
            style_function=style_function,
            control=False,
            highlight_function=highlight_function,
            tooltip=folium.features.GeoJsonTooltip(
                fields=fields,
                aliases=fields,
                style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
            )
        )

    m.add_child(hover_bubble)
    m.keep_in_front(hover_bubble)

    outfp = "map.html"
    m.save(outfp)
    webbrowser.open("map.html")


def mean_difference(data):
    diffs = []

    for i in range(1, len(data)):
        diffs.append(data[i] - data[i - 1])

    return np.round(np.mean(diffs), ROUND_DECS)


def mean_percent_difference(data):
    diffs = []
    for i in range(1, len(data)):
        if np.mean((data[i], data[i - 1])) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.mean((data[i], data[i - 1]))) * 100)

    return np.round(np.mean(diffs), ROUND_DECS)


def mean_percent_change(data):
    diffs = []
    for i in range(1, len(data)):
        if np.abs(data[i - 1]) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.abs(data[i - 1])) * 100)

    return np.round(np.mean(diffs), ROUND_DECS)


def clip_outliers(df):
    """
    Removes outliers for a pandas dataframe based on usage of the interquartile range
    :param df: The dataframe for outliers to be removed from
    :return:The dataframe with outliers clipped
    """
    iqr = df.quantile(0.75) - df.quantile(0.25)
    # Clip data that is 3 iqrs beyond the first or third quartile
    return df.clip(df.quantile(0.25) - 3 * iqr,df.quantile(0.75) + 3 * iqr )


