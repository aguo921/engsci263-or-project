import random
import math
import pandas as pd

def calculate_route_capacity(route, demands, day_type):
    """ Calculate pallets delivered on route.

        Parameters
        ----------
        route : list
            List of nodes in route.
        demands : dataframe
            Demands at each node.
        day_type : string
            Whether the day is Saturday or a weekday.
        
        Returns
        -------
        capacity : int
            Number of pallets delivered on route.
    """
    # calculate total capacity of stores in route (excluding warehouse)
    capacity = sum(demands[day_type][store] for store in route[1:-1])

    return capacity


def calculate_route_time(route, durations, warehouse_weight=1, unloading=4, traffic=1):
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
        traffic : float (default=1)
            Traffic multiplier.

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
        
        # calculate travel time between stores according to traffic multiplier
        travel_time = traffic * durations.Duration[source, destination]
        
        # decrease weighting of trips to and from the warehouse
        travel_time *= warehouse_weight if ("Warehouse" in [source, destination]) else 1

        time += travel_time
            
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

    """
    # cost in 4-hour blocks for leasing Mainfreight trucks
    if mainfreight:
        return math.ceil(route_time / 240) * mainfreight_cost

    # owned Foodstuffs trucks
    if route_time < shift_time:
        # shift costs can be fractional
        return route_time * shift_cost / 60

    # overtime costs cannot be fractional
    return shift_time * shift_cost + (route_time - shift_time) * math.ceil(overtime_cost / 60)


def insert_store(route, nodes, demands, durations, day_type, capacity=16, dropout=0, warehouse_weight=1):
    """ Insert a store into the optimal position in a route.

        Parameters
        ----------
        route : list
            List of nodes in route.
        node : string
            Store to insert into route.
        durations : dataframe
            Duration between nodes.
        day_type : string
            Type of day.
        capacity : int (default=16)
            Capacity of truck.
        dropout : float (default=0)
            Value between 0 and 1. Rate at which better routes are dropped out.
        warehouse_weight : float (default=1)
            Value between 0 and 1. Weighting of arcs to and from warehouse.
        
        Returns
        -------
        dict
            Dictionary of optimal route containing its path, time, demand and cost.
    """
    # calculate capacity of old route
    old_capacity = calculate_route_capacity(route, demands, day_type)

    # calculate traffic intensity depending on if it is a weekday or Saturday
    traffic = 1.4 if day_type == "Weekdays" else 1.2

    # get list of possible stores to insert
    unvisited = [
        node for node in nodes 
        # store is unvisited
        if node not in route 
        # additional demand does not exceed capacity
        and old_capacity + demands[day_type][node] <= capacity
        # drop out some nodes at random
        and random.random() > dropout
    ]

    # exit algorithm if unvisited set is empty
    if len(unvisited) == 0:
        return None

    # initialise best route and time
    best_route = route.copy()
    best_route.insert(1, unvisited[0])
    best_time = calculate_route_time(best_route, durations, warehouse_weight=warehouse_weight)

    # loop over every unvisited store
    for node in unvisited:
        # loop over every possible position to insert store into route
        for position in range(2, len(route)):
            # calculate time of new route
            current_route = route.copy()
            current_route.insert(position, node)

            # replace best time if new route time is better
            current_time = calculate_route_time(current_route, durations, warehouse_weight=warehouse_weight)
            if current_time < best_time:
                best_route = current_route
                best_time = current_time

    # calculate demand, time and costs of best route
    route_capacity = calculate_route_capacity(best_route, demands, day_type)
    route_time = calculate_route_time(best_route, durations, traffic=traffic)
    cost = calculate_route_cost(route_time)
    mainfreight_cost = calculate_route_cost(route_time, mainfreight=True)

    return {
        "Route": best_route, 
        "Time": route_time, 
        "Demand": route_capacity, 
        "Cost": cost, 
        "MainfreightCost": mainfreight_cost
    }


def generate_routes(nodes, demands, durations, weekday=True, dropout=0, warehouse_weight=1):
    """ Generate feasible routes between warehouse and stores.

        Parameters
        ----------
        nodes : list
            List of nodes to travel to.
        demands : dataframe
            Demands at each node.
        durations : dataframe
            Durations between nodes.
        weekday : boolean (default=True)
            Whether the day is a weekday or not.
        dropout : float (default=0)
            Value between 0 and 1. Rate at which improved routes are dropped.
        warehouse_weight : float (default=1)
            Value between 0 and 1. Weighting of arcs to and from the warehouse in time calculations.

        Returns
        -------
        routes : list
            List of generated routes.
    """
    # initiate empty list of routes
    routes = []

    # obtain day type
    day_type = "Weekdays" if weekday else "Saturday"

    # loop over every store
    for store in nodes:
        # initialise route to store
        initial_route = ["Warehouse", store, "Warehouse"]

        # calculate time and costs of initial route
        route_time = calculate_route_time(initial_route, durations)
        cost = calculate_route_cost(route_time)
        mainfreight_cost = calculate_route_cost(route_time, mainfreight=True)
        route_capacity = calculate_route_capacity(initial_route, demands, day_type)

        route = {
            "Route": initial_route, 
            "Time": route_time,
            "Demand": route_capacity,
            "Cost": cost, 
            "MainfreightCost": mainfreight_cost
        }

        # keep inserting routes until capacity is reached
        while (route is not None):
            routes.append(route)
            route = insert_store(
                route["Route"], 
                nodes, 
                demands, 
                durations, 
                day_type, 
                dropout=dropout, 
                warehouse_weight=warehouse_weight
            )
            
    return routes


def remove_duplicate_routes(routes):
    """ Remove routes visiting identical stores.

        Parameters
        ----------
        routes : list
            List of routes.
        
        Returns
        -------
        routes : list
            List of routes with higher cost duplicates removed.
    """
    # find indices of routes to remove
    routes_to_remove = [
        # find index of higher cost route
        j if routes[i]["Cost"] < routes[j]["Cost"] else i
        # loop through every possible pair of routes
        for i in range(len(routes))
        for j in range(i + 1, len(routes))
        # check if routes contain identical stores
        if set(routes[i]["Route"]) == set(routes[j]["Route"])
    ]

    # remove routes
    routes = [route for i, route in enumerate(routes) if i not in routes_to_remove]

    return routes


def aggregate_routes(regions, demands, durations, weekday=True, dropouts=[0], warehouse_weights=[1]):
    """ Aggregate generated routes over multiple regions for different dropout rates and warehouse weights.

        Parameters
        ----------
        regions : list
            List of lists containing stores in each region.
        demands : dataframe
            Demands at each store.
        durations : dataframe
            Travel times between each store.
        weekday : boolean (default=True)
            Whether the day is a weekday or not.
        dropouts : list (default=[0])
            List of dropout rates.
        warehouse_weights : list (default=[1])
            List of warehouse weighting factors.

        Returns
        -------
        dataframe
            Dataframe of all generated routes across the regions.
    """
    # generate routes for each combination of region, dropout rate and warehouse weighting factor
    all_routes = [
        generate_routes(
            region, 
            demands, 
            durations, 
            weekday, 
            dropout=dropout, 
            warehouse_weight=weight
        )
        for region in regions
        for dropout in dropouts
        for weight in warehouse_weights
    ]

    # flatten routes array
    all_routes = [route for routes in all_routes for route in routes]

    # remove duplicate routes within list
    all_routes = remove_duplicate_routes(all_routes)

    # convert to dataframe
    return pd.DataFrame.from_dict(all_routes)


def read_regions(filename):
    """ Read region data from a file.

        Parameters
        ----------
        filename : string
            Name of file with region data.
        
        Returns
        -------
        regions : list
            List containing lists of nodes within each region.
    """
    df = pd.read_csv(filename)

    regions = [df[region].dropna().values.tolist() for region in df]

    return regions


if __name__ == "__main__":
    regions = read_regions("./route-generation/Regions.csv")

    demands = pd.read_csv("./demand-estimation/output/DemandEstimates.csv")\
        .set_index("Supermarket")

    durations = pd.read_csv("./route-generation/output/TravelCosts.csv")\
        .set_index(['From', 'To'])
    
    weekday_routes = aggregate_routes(
        regions, 
        demands, 
        durations
    )
    print(len(weekday_routes))
    print(weekday_routes.head())