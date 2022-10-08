import pandas as pd
import numpy as np
import random

def generate_demands(n, demands, day_type):
    sd = 0.5 if day_type == "Saturday" else 1.5

    # generate demands
    generated_demands = [
        [
            max(0, round(demands[day_type][j] + random.normalvariate(0, sd)))
            for j in demands.index
        ] for _ in range(n)
    ]

    # convert generated demands to dataframe
    return pd.DataFrame(
        np.array(generated_demands).T, 
        columns=[f"Run {i+1}" for i in range(1000)], 
        index=demands.index
    )


if __name__ == "__main__":
    demands = pd.read_csv("./demand-estimation/output/MeanDemand.csv").set_index("Supermarket")

    # save generated demands to csv file
    saturday_demands = generate_demands(1000, demands, "Saturday")
    saturday_demands.to_csv("./simulation/output/test_saturday_demands.csv")

    weekday_demands = generate_demands(1000, demands, "Weekdays")
    weekday_demands.to_csv("./simulation/output/test_weekday_demands.csv")