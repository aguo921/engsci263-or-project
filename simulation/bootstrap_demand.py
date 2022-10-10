import pandas as pd
import numpy as np

def transform_demand(demands):
    # pivot dates into a single column
    demands = demands.melt(id_vars="Supermarket", var_name="Date", value_name="Demand")

    # convert dates to datetime objects
    demands.Date = pd.to_datetime(demands.Date)

    # create column with day of the week
    demands["Weekday"] = demands.Date.dt.weekday

    # remove Sundays
    demands = demands[demands.Weekday != 6]

    # categorise days into Saturdays and weekdays
    demands["DayType"] = np.where(demands.Weekday == 5, "Saturday", "Weekdays")

    return demands


def bootstrap_demand(n, stores, demands, day_type):
    # obtain n samples of demand for each store
    bootstrapped_demands = [
        demands[
            (demands.Supermarket==store) & (demands.DayType==day_type)
        ].Demand.sample(n=n, replace=True).values.tolist()
        for store in stores
    ]
    
    # create dataframe with rows for each store and columns for each run
    df = pd.DataFrame(
        bootstrapped_demands,
        columns=[f"Run{i+1}" for i in range(n)],
        index=stores
    )
    df.index.name = "Supermarket"

    return df

if __name__ == "__main__":
    demands = pd.read_csv("./foodstuffs-data/FoodstuffsDemands.csv")
    stores = demands.Supermarket.values.tolist()
    demands = transform_demand(demands)

    sat_bootstrap = bootstrap_demand(1000, stores, demands, "Saturday")
    weekday_bootstrap = bootstrap_demand(1000, stores, demands, "Weekdays")

    sat_bootstrap.to_csv("./simulation/output/sat_bootstrap.csv")
    weekday_bootstrap.to_csv("./simulation/output/weekday_bootstrap.csv")