import pandas as pd
import ast

def transform_file(read_filename, write_filename):
    routes = pd.read_csv(read_filename)\
        .drop(columns=["RouteNum", "TruckType"])\
            .rename(columns={"RouteCost": "Cost"})

    for i in routes.index:
        route = ast.literal_eval(routes.Route[i])
        routes.loc[i, "Route"] = ", ".join(route[1:-1])
        routes.loc[i, "Cost"] = round(routes.loc[i, "Cost"], 2)
    
    routes.to_csv(write_filename, index=False)

def calculate_total_cost(filename):
    routes = pd.read_csv(filename)

    return round(sum(routes.RouteCost), 2)

if __name__ == "__main__":
    transform_file(
        "./linear-program/output/selectedRoutesSaturday.csv",
        "./linear-program/output/CleanSelectedRoutesSaturday.csv"
    )
    transform_file(
        "./linear-program/output/selectedRoutesWeekday.csv",
        "./linear-program/output/CleanSelectedRoutesWeekday.csv"
    )

    print(f"Saturday Cost: ${calculate_total_cost('./linear-program/output/selectedRoutesSaturday.csv')}")
    print(f"Weekday Cost: ${calculate_total_cost('./linear-program/output/selectedRoutesWeekday.csv')}")

