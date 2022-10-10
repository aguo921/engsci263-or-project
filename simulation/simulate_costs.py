import ast
import pandas as pd
import numpy as np

def calculate_route_time(route, durations, warehouse_weight=1, unloading=4, traffic_intensity=1):
    """ Calculate total time taken on route.

        Parameters
        ----------
        route : list
            List of nodes in route.
        durations : dataframe
            Durations between nodes.
        warehouse_weight : float (default=1)
            Value between 0 and 1. Weighting of arcs to and from the warehouse.
        unloading : int (default=4)
            Unloading time (min) at each store.
        traffic_intensity : float (default=1)
            Intensity of traffic.

        Returns
        -------
        time : float
            Total time taken on route.            
    """
    # calculate total unloading time at each store
    time = unloading * (len(route) - 2)

    # loop over trips between stores
    for i in range(len(route) - 1):
        # obtain source and destination stores of individual trip
        (source, destination) = route[i:i+2]
        
        # calculate travel time between stores
        travel_time = traffic_intensity * durations.Duration[source, destination]
        
        # decrease weighting of trips to and from the warehouse
        time += warehouse_weight * travel_time if ("Warehouse" in [source, destination]) else travel_time
            
    return time

def calculate_route_cost(route_time, shift_time=240, shift_cost=150, overtime_cost=200, mainfreight_cost=3000, mainfreight=False):
    """ Calculate the cost of a route.

        Parameters
        ----------
        route_time : float
            Total time in minutes for the route, including driving and unloading time.
        shift_time : int (default=240)
            Time in minutes for a shift.
        shift_cost : int (default=150)
            Operating cost per hour during a shift.
        overtime_cost : int (default=200)
            Cost per hour (in blocks) after shift hours.
        mainfreight_cost : int (default=3000)
            Cost per 4-hour block for leased Mainfreight trucks.
        mainfreight : boolean (default=False)
            Whether the truck is leased Mainfreight truck or not.

        Returns
        -------
        float
            Cost of the route.
    """
    # cost in 4-hour blocks for leasing Mainfreight trucks
    if mainfreight:
        return np.ceil(route_time / 240) * mainfreight_cost

    # owned Foodstuffs trucks
    if route_time < shift_time:
        # shift costs can be fractional
        return route_time * shift_cost / 60

    # overtime costs cannot be fractional
    return shift_time * shift_cost + (route_time - shift_time) * np.ceil(overtime_cost / 60)


def check_routes(routes, demands, durations, day_type, capacity=16):
    """ Check capacity constraints are satisfied and modify routes appropriately.

        Parameters
        ----------
        routes : dataframe
            Selected routes and corresponding costs to be modified depending on the actual demand.
        demands : dataframe
            Random realisations of demand for each store.
        durations : dataframe
            Travel durations between each store.
        day_type : string
            Whether it is a Saturday or weekday.
        capacity : int (default=16)
            Capacity of each truck.
    """
    # create a copy of the original routes
    routes_copy = routes.copy()

    # calculate traffic intensity factor
    traffic = 1.4 if day_type == "Weekdays" else 1.2

    # set up function to calculate total demand on route
    calculate_route_capacity = lambda route: sum(demands[store] for store in route[1:-1])

    # loop through each selected route
    for i in routes_copy.index:
        route = ast.literal_eval(routes_copy.Route[i])

        # check if capacity is exceeded
        if calculate_route_capacity(route) > capacity:
            # remove stores from route until capacity is satisfied and return new route
            new_route = remove_store(route, durations, calculate_route_capacity)

            # modify route and route cost after removing store(s)
            time = calculate_route_time(route, durations, traffic_intensity=traffic)
            routes.loc[i, "Route"] = str(route)
            routes.loc[i, "RouteCost"] = calculate_route_cost(time)

            # add new route to dataframe
            time = calculate_route_time(new_route, durations, traffic_intensity=traffic)
            routes.loc[len(routes.index)] = [
                str(new_route),
                "OwnedTruck",
                calculate_route_cost(time)
            ]


def remove_store(route, durations, capacity_func, capacity=16):
    """ Remove stores from a route until capacity constraint is met.

        Parameters
        ----------
        route : list
            List of locations to visit in order, in which stores will be deleted.
        durations : dataframe
            Travel durations between each pair of locations.
        capacity_func : callable
            Function to calculate total demand on a route.
        capacity : int (default=16)
            Truck capacity.
        
        Returns
        -------
        new_route : list
            List of new constructed route containing deleted stores from original route.
    """
    # initiailise stores to remove
    removed_stores = []

    # determine whether first or last store in route is closer
    remove_first = durations.Duration["Warehouse", route[1]] < durations.Duration[route[-2], "Warehouse"]
    remove_index = 1 if remove_first else -2

    # remove stores until capacity constraint satisfied
    while capacity_func(route) > capacity:
        removed_stores.append(route.pop(remove_index))

    # construct new route from removed stores
    new_route = ["Warehouse"] + removed_stores + ["Warehouse"]

    return new_route
        

def convert_to_mainfreight(routes, trucks=12, shifts=2):
    """ Lease out shifts to Mainfreight trucks until truck and shift availability constraints
        are satisifed.

        Parameters
        ----------
        routes : dataframe
            Dataframe containing routes and corresponding costs.
        trucks : int (default=12)
            Number of Foodstuffs trucks available.
        shifts : int (default=2)
            Number of shifts per day that each Foodstuffs truck can do.
    """
    # function to calculate number of routes done by owned trucks
    owned_routes = lambda: len(routes[routes.TruckType == 'OwnedTruck'])

    # convert routes done by owned trucks to Mainfreight trucks
    while owned_routes() > trucks * shifts:
        # find index of route done by owned truck with max cost
        index = routes[
            routes.RouteCost == max(routes[routes.TruckType == "OwnedTruck"].RouteCost)
        ].index[0]

        # set new route cost and truck type
        routes.loc[index, "RouteCost"] = 3000
        routes.loc[index, "TruckType"] = "LeasedTruck"


def simulate_runs(optimal_routes, demands, durations, day_type, trucks=12, shifts=2):
    """ Calculate actual costs on each realisation of demand.

        Parameters
        ----------
        optimal_routes : dataframe
            Optimal selected routes.
        demands : dataframe
            Random realisations of demand for each store.
        durations : dataframe
            Travel durations between each pair of stores.
        day_type : string
            Whether it is a Saturday or weekday.

        Returns
        -------
        dataframe
            Dataframe containing actual costs and number of Mainfreight trucks used per run.
    """
    # initiailise costs and Mainfreight trucks list
    costs = []
    mainfreight = []
    extra_trucks = []

    # loop through each realisation
    for run in demands.columns:
        # create a copy of the optimal route selection to modify
        routes = optimal_routes.copy()

        # modify routes based on actual demand
        check_routes(routes, demands[run], durations, day_type)

        # convert routes done by owned trucks to Mainfreight trucks
        convert_to_mainfreight(routes, trucks=trucks, shifts=shifts)

        # record total cost and number of Mainfreight turcks used
        costs.append(sum(routes.RouteCost))
        mainfreight.append(len(routes[routes.TruckType=="LeasedTruck"]))
        extra_trucks.append(len(routes) - len(optimal_routes))

    df = pd.DataFrame({
        "Cost": costs,
        "Mainfreight": mainfreight,
        "ExtraShifts": extra_trucks
    }, index=demands.columns)

    df.index.name = "Run"

    return df