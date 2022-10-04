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
    capacity = 0
    for store in route[1:-1]:
        capacity += demands[demands.Supermarket==store].iloc[0][day_type]
    return capacity

def calculate_route_time(route, durations, localisation=1, unloading=4, traffic_intensity=1):
    """ Calculate total time taken on route.

        Parameters
        ----------
        route : list
            List of nodes in route.
        durations : dataframe
            Durations between nodes.
        localised : boolean (default=False)
            Whether to weight trips to and from the warehouse.
        unloading : int (default=4)
            Unloading time (min) at each store.
        traffic_intensity : float
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
        source = route[i]
        destination = route[i + 1]
        
        # calculate travel time between stores
        travel_time = traffic_intensity * durations.Duration[(durations.From==source) & (durations.To==destination)].iloc[0]
        
        # decrease weighting of trips to and from the warehouse
        if (source == "Warehouse" or destination == "Warehouse"):
            time += localisation * travel_time
        else:
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
    else:
        if route_time < shift_time:
            # shift costs can be fractional
            return route_time * shift_cost / 60
        else:
            # overtime costs cannot be fractional
            return shift_time * shift_cost + (route_time - shift_time) * math.ceiling(overtime_cost / 60)

def insert_store(route, nodes, demands, durations, day_type, capacity=16, dropout=0, localisation=1):
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
        
        Returns
        -------
        best_route : list
            List of nodes in optimal route.
        route_cost : float
            Cost of best route.
    """

    # get list of unvisited stores
    unvisited = [node for node in nodes if node not in route]

    if unvisited == []:
        return None

    # initiate best route and time
    best_route = route.copy()
    best_route.insert(1, unvisited[0])
    best_time = calculate_route_time(best_route, durations, localisation=localisation)
    best_store = unvisited[0]

    # loop over every unvisited store
    for node in unvisited:
        # loop over every possible position to insert store into route
        for position in range(2, len(route)):
            # calculate time of new route
            current_route = route.copy()
            current_route.insert(position, node)

            current_capacity = calculate_route_capacity(current_route, demands, day_type)
            if current_capacity > capacity:
                break

            current_time = calculate_route_time(current_route, durations, localisation=localisation)
            
            # replace best time if new route time is better
            if current_time < best_time and random.random() > dropout:
                best_route = current_route
                best_time = current_time
                best_store = node

    # calculate route time and capacity of best route
    route_time = calculate_route_time(best_route, durations)
    route_capacity = calculate_route_capacity(best_route, demands, day_type)
    
    if route_capacity <= capacity:
        # return best route if capacity constraint is satisfied
        cost = calculate_route_cost(route_time)
        mainfreight_cost = calculate_route_cost(route_time, mainfreight=True)
        return (best_route, cost, mainfreight_cost)
    else:
        # try to find a cheaper route with current store removed if capacity is reached
        new_nodes = [node for node in nodes if node != best_store]
        return insert_store(route, new_nodes, demands, durations, day_type, capacity, dropout)


def generate_routes(nodes, demands, durations, weekday=True, dropout=0, localisation=1):
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

        Returns
        -------
        routes : list
            List of generated routes.
    """
    # initiate empty list of routes
    routes = []

    # obtain day type
    if weekday:
        day_type = "Weekdays"
    else:
        day_type = "Saturday"

    # loop over every store
    for store in nodes:
        # initiate route to store
        initial_route = ["Warehouse", store, "Warehouse"]
        route_time = calculate_route_time(initial_route, durations)
        cost = calculate_route_cost(route_time)
        mainfreight_cost = calculate_route_cost(route_time, mainfreight=True)

        route = (initial_route, cost, mainfreight_cost)

        # keep inserting routes until capacity is reached
        while (route is not None):
            routes.append(route)
            route = insert_store(route[0], nodes, demands, durations, day_type, dropout=dropout, localisation=localisation)
            
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
            List of routes with duplicates removed.
    """
    routes_to_remove = []

    # loop over every possible pair of routes
    for i in range(len(routes)):
        for j in range(i + 1, len(routes)):
            # remove a route if they contain identical stores
            if set(routes[i][0]) == set(routes[j][0]):
                # record route to remove if it has a higher cost
                if routes[i][1] < routes[j][1]:
                    routes_to_remove.append(j)
                else:
                    routes_to_remove.append(i)

    # remove routes
    routes = [route for i, route in enumerate(routes) if i not in routes_to_remove]

    return routes

def aggregate_routes(regions, demands, durations, weekday=True, dropouts=[0], localisations=[1]):
    """ Aggregate generated routes over multiple regions for different dropout rates.

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

        Returns
        -------
        all_routes : list
            List of all generated routes across the regions.
    """
    all_routes = []
    for region in regions:
        for dropout in dropouts:
            for localisation in localisations:
                all_routes.append(generate_routes(region, demands, durations, weekday, dropout=dropout, localisation=localisation))

    all_routes = [route for routes in all_routes for route in routes]
    return remove_duplicate_routes(all_routes)

def convert_routes_to_dataframe(routes):
    """ Convert a list of tuples to a dataframe.

        Parameters
        ----------
        routes : list
            List of tuples containing routes, costs and Mainfreight costs.
        
        Returns
        -------
        dataframe
            Dataframe with a route in each row and costs in columns.
    """
    return pd.DataFrame({
        "Route": [route[0] for route in routes],
        "Cost": [route[1] for route in routes],
        "MainfreightCost": [route[2] for route in routes]
    })

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

    regions = []
    for region in df:
        stores = df[region].values.tolist()
        regions.append([store for store in stores if not pd.isna(store)])

    return regions