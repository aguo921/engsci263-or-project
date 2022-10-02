import numpy as np
import pandas as pd
from pulp import *
from route_generation import read_regions


def read_routes_costs(filename):
    df = pd.read_csv(filename)

    df = pd.melt(df, id_vars=['Route'], value_vars=['Cost', 'MainfreightCost']
                 , var_name='TruckType', value_name='RouteCost')

    routeNames = [f"r{i + 1}" for i in range(df['Route'].count())]
    df['RouteNum'] = routeNames

    df.set_index('RouteNum', drop=False, inplace=True)

    return df


if __name__ == "__main__":
    nodes = read_regions("nodes.csv")[0]  # read nodes, node demands are all  == 1
    routesDf = read_routes_costs("weekday_routes.csv")

    routes = []
    for node in nodes:
        routes.append([1 if node in routesDf['Route'][i] else 0 for i in routesDf.index])

    routesDf.to_csv("testing2.csv", index=True)

    routes = makeDict([nodes,routesDf['RouteNum']],routes,0)

    ownedTrucks = 12
    numShifts = 2

    # LP formulation
    vars = LpVariable.dicts("Route",routesDf['RouteNum'],cat=LpBinary)

    prob = LpProblem("Foodies VRP", LpMinimize)

    # objective function
    prob += lpSum([vars[i]*routesDf['RouteCost'][i] for i in routesDf.index]), "TotalCost"

    print(routes)
    # node constraint
    for i in nodes:
        prob += lpSum([vars[j]*routes[i][j] for j in routesDf.index]) == 1, f"{i}Demands"


    # truck constraints
    prob += lpSum([vars[i] for i in routesDf.index if routesDf['TruckType'][i] == 'Cost']) <= 24, 'TruckRestrictions'

    # Solving routines - no need to modify other than slotting your name and username in.
    prob.writeLP('Furniture.lp')

    prob.solve()

    print("Aryan Karan (akar444) \n")

    # The status of the solution is printed to the screen
    print("Status:", LpStatus[prob.status])

    # Each of the variables is printed with its resolved optimum value
    for v in prob.variables():
        print(v.name, "=", v.varValue)

    # The optimised objective function valof Ingredients pue is printed to the screen
    print("Total cost for VRP = ", value(prob.objective))
    print(routesDf.index)
