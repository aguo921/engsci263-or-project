import numpy as np
import pandas as pd
from pulp import *
from route_generation import read_regions


def read_routes_costs(filename):
    """ reads in a route file and returns a dataframe"""
    df = pd.read_csv(filename)

    dict = {'Cost': 'OwnedTruck',
           'MainfreightCost': 'LeasedTruck'}

    df.rename(columns=dict,inplace=True)

    df = pd.melt(df, id_vars=['Route'], value_vars=['OwnedTruck', 'LeasedTruck']
                 , var_name='TruckType', value_name='RouteCost')

    routeNames = [f"r{i + 1}" for i in range(df['Route'].count())]
    df['RouteNum'] = routeNames

    df = df[['RouteNum','Route','TruckType','RouteCost']]



    df.set_index('RouteNum', drop=False, inplace=True)


    return df

def route_selection_lp(routeCost, nodes, ownedTruck=12, numShifts=2):
    """ formulates and solves the route selection LP

        Parameters
        ----------
        routeCost : dataframe
            dataframe of routes and their costs.
        nodes : list
            list of all the nodes.
        ownedTruck : int (default=12)
            number of trucks owned by Foodstuffs.
        numShifts : int (default=2)
            number of shifts in one day

        Returns
        -------
        selectedRoutes : list
            List of all the route names selected by the LP
        objective: float
            The objective value cost of this formulation
    """
    # creates a matrix of routes that travel to each node
    routes = []
    for node in nodes:
        routes.append([1 if node in routeCost['Route'][i] else 0 for i in routeCost.index])

    # turns routes into a dictionary
    routes = makeDict([nodes, routeCost['RouteNum']], routes, 0)

    # LP formulation
    vars = LpVariable.dicts("Route", routeCost['RouteNum'], cat=LpBinary)

    prob = LpProblem("Foodies VRP", LpMinimize)

    # objective function
    prob += lpSum([vars[i] * routeCost['RouteCost'][i] for i in routeCost.index]), "TotalCost"

    # node constraint
    for node in nodes:
        prob += lpSum([vars[j] * routes[node][j] for j in routeCost.index]) == 1, f"{node}Demands"

    # truck constraints
    prob += lpSum(
        [vars[i] for i in routeCost.index if routeCost['TruckType'][i] == 'OwnedTruck']) <= ownedTruck*numShifts, 'TruckRestrictions'

    # Solving routines - no need to modify other than slotting your name and username in.
    prob.writeLP('RouteLP.lp')

    prob.solve()

    print("ENGSCI 263 OR Project Group 10 \n")

    # The status of the solution is printed to the screen
    print("Status:", LpStatus[prob.status])

    # Each of the variables is printed with its resolved optimum value
    selectedRoutes = []
    for v in prob.variables():
        if v.varValue == 1:
            selectedRoutes.append(v.name.split("_")[1])
        print(v.name, "=", v.varValue)

    # The optimised objective function valof Ingredients pue is printed to the screen
    print("Total cost for VRP = ", value(prob.objective))
    print(routeCost.index)

    return selectedRoutes, value(prob.objective)


if __name__ == "__main__":
    nodes = read_regions("nodes.csv")[0]  # read nodes
    weekdayRouteCosts = read_routes_costs("weekday_routes.csv")
    saturdayRouteCosts = read_routes_costs("saturday_routes.csv")

    selectedRoutesWeekday, objectiveWeekday = route_selection_lp(weekdayRouteCosts, nodes)

    df = pd.DataFrame(weekdayRouteCosts, index=selectedRoutesWeekday)
    df.drop(columns='RouteNum')
    df.to_csv("selectedRoutesWeekday.csv", index=False)

    selectedRoutesSaturday, objectiveSaturday = route_selection_lp(saturdayRouteCosts, nodes)

    df = pd.DataFrame(saturdayRouteCosts, index=selectedRoutesSaturday)
    df.drop(columns='RouteNum')
    df.to_csv("selectedRoutesSaturday.csv", index=False)



