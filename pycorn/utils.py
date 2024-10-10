import numpy as np
import pandas as pd


def get_series_from_data(data, data_key_list,interpolate=True,lightweighting=10):
    try:
        # select the first injection as the injection timestamp
        inject_timestamp = data["Injection"]["data"][-1][0]
    except KeyError:
        inject_timestamp = 0

    data_series_list = []
    for data_key in data_key_list:
        data_array = np.array(data[data_key]["data"])#.astype(float)
        data_series = pd.Series(data=data_array[:, 1], index=data_array[:, 0].astype(float))
        # remove duplicates
        data_series = data_series[~data_series.index.duplicated()]
        # offset by the infection_timestamp

        data_series.index -= inject_timestamp

        data_series_list.append(data_series)

    df = pd.concat(data_series_list, axis=1)
    df.columns = data_key_list

    df = df.sort_index()
    df = df.reset_index(names=["mL"])

    if interpolate:
      df = df.interpolate(method='linear')

    if lightweighting:
      light_index = np.array(df.index[df.index%10==0])

      # オブジェクトタイプの列を選択
      object_columns = df.select_dtypes(include=['object']).columns

      # 全てのオブジェクト列でNaNでないインデックスを取得し、1つのリストにまとめる
      non_nan_indices = sorted(set(df[object_columns].dropna(how="all").index))

      light_index = np.append(light_index,non_nan_indices)
      light_index = sorted(set(light_index))
      
      df = df.loc[light_index]
      df = df.reset_index(drop=True)


    return df


def get_fraction_rectangle(frac_df):
    """
    AKTA chromatogramデータからFractionごとのindexを作成する関数。Fractions列は開始点のみで、残りはNaN。

    Args:
        df: pandas DataFrame. "mL", "UV 1_280", "Fractions"列を持つ必要がある。

    Returns:
        pandas DataFrame: 各Fractionの開始mL, 終了mL, 最大UV値,  index(開始mL,終了mL)を含むDataFrame。
                         エラー発生時はNoneを返す。
    """

    required_cols = ["mL", "UV 1_280", "Fractions"]
    if not all(col in frac_df.columns for col in required_cols):
        print("Error: DataFrame must contain columns 'mL', 'UV 1_280', and 'Fractions'.")
        return None

    df = frac_df.copy()


    fraction_starts = np.array(df["Fractions"].dropna())
    

    df = df.reset_index()

    #Fractions列の最初の値がNaNの場合の処理を追加
    if pd.isna(df.loc[0,"Fractions"]):
        print("Error: The first value of 'Fractions' column is NaN. Please check your data.")
        df.loc[0,"Fractions"] = "Waste"
        #return None

    # NaNを前の値で埋める(ffill)  →　最初のFractionはそのままNaNになるため、後処理が必要
    df["Fractions"] = df["Fractions"].fillna(method='ffill')


    #fraction_starts = df["Fractions"].unique()[1:]
    fraction_indices = []
    start_index=0

    for i, start in enumerate(fraction_starts):
        try:
            start_index = df.loc[start_index:][df.loc[start_index:]["Fractions"] == start].index[0]
            if i < len(fraction_starts) - 1:
                next_start_index = df.loc[start_index:][df.loc[start_index:,"Fractions"] == fraction_starts[i+1]].index[0]
                end_index = next_start_index
            else:
                end_index = len(df) -1

            start_ml = df["mL"].iloc[start_index]
            end_ml = df["mL"].iloc[end_index]
            max_uv = df["UV 1_280"].iloc[start_index:end_index+1].max()

            fraction_indices.append({
                "Fraction_Start": start,
                "Start_mL": start_ml,
                "End_mL": end_ml,
                "Max_UV": max_uv*1.05,
            })

        except IndexError:
            print(f"Error processing fraction starting at {start}. Check your data for inconsistencies.")
            return None

    return pd.DataFrame(fraction_indices)



