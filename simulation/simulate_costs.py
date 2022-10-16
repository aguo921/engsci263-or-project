import ast
import pandas as pd

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
        travel_time = traffic * durations.Duration[source, destination]
        
        # decrease weighting of trips to and from the warehouse
        travel_time *= warehouse_weight if ("Warehouse" in [source, destination]) else 1

        time += travel_time
            
    return time


def calculate_route_cost(route_time, shift_cost=150):
    """ Calculate the cost of a route.

        Parameters
        ----------
        route_time : float
            Total time in minutes for the route, including driving and unloading time.
        shift_cost : int (default=150)
            Operating cost per hour during a shift.

        Returns
        -------
        float
            Cost of the route.

        Notes
        -----
        Assume route time is under 4 hours and is done by an owned Foodstuffs truck.
    """
    return route_time * shift_cost / 60


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
        
        Returns
        -------
        num_removed_stores : int
            Number of stores that have been reallocated to new routes.
    """
    # create a copy of the original routes
    routes_copy = routes.copy()

    # calculate traffic intensity factor
    traffic = 1.4 if day_type == "Weekdays" else 1.2

    # set up function to calculate total demand on route
    calculate_route_capacity = lambda route: sum(demands[store] for store in route[1:-1])

    # initiailise list of removed stores
    removed_stores = []

    # loop through each selected route
    for i in routes_copy.index:
        route = ast.literal_eval(routes_copy.Route[i])

        # check if capacity is exceeded
        if calculate_route_capacity(route) > capacity:
            # remove store(s) from route until capacity constraint is satisfied
            removed_stores = removed_stores + remove_store(route, durations, calculate_route_capacity)

            # modify route and route cost after removing store(s)
            time = calculate_route_time(route, durations, traffic=traffic)
            routes.loc[i, "Route"] = str(route)
            routes.loc[i, "RouteCost"] = calculate_route_cost(time)

    # calculate the number of removed stores
    num_removed_stores = len(removed_stores)

    # get new routes from pool of removed stores
    new_routes = generate_routes(removed_stores, demands, durations, traffic=traffic)

    # add new routes to dataframe
    for route in new_routes:
        time = calculate_route_time(route, durations, traffic=traffic)
        routes.loc[len(routes.index)] = [
            str(route),
            "OwnedTruck",
            calculate_route_cost(time)
        ]
    
    return num_removed_stores


def insert_store(route, unvisited, demands, durations, capacity=16, shift_time=240, traffic=1):
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
        shift_time : int (default=240)
            Time in minutes per shift.
        traffic : float (default=1)
            Traffic multiplier affecting route time.

        Returns
        -------
        best_route : list
            List of nodes in optimal route.
    """
    # calculate capacity of current route
    old_capacity = sum(demands[store] for store in route[1:-1])

    # take out stores that do not satisfy capacity constraint
    unvisited = [
        node for node in unvisited
        if old_capacity + demands[node] <= capacity
    ]

    # exit algorithm if unvisited set is empty
    if len(unvisited) == 0:
        return None

    # initialise best route and time
    best_route = route.copy()
    best_route.insert(1, unvisited[0])
    best_time = calculate_route_time(best_route, durations, traffic=traffic)

    # loop over every unvisited store
    for node in unvisited:
        # loop over every possible position to insert store into route
        for position in range(2, len(route)):
            # calculate time of new route
            current_route = route.copy()
            current_route.insert(position, node)
            current_time = calculate_route_time(current_route, durations, traffic=traffic)

            # replace best time if new route time is better and capacity constraint is satisfied
            if current_time < best_time:
                best_route = current_route
                best_time = current_time

    # check time constraint is satisified
    if best_time > shift_time:
        return None
    
    # modify unvisited stores
    for store in best_route[1:-1]:
        if store in unvisited:
            unvisited.remove(store)

    return best_route


def generate_routes(nodes, demands, durations, traffic=1):
    """ Generate feasible routes between warehouse and stores.

        Parameters
        ----------
        nodes : list
            List of nodes to travel to.
        demands : dataframe
            Demands at each node.
        durations : dataframe
            Durations between nodes.
        traffic : float (default=1)
            Traffic intensity factor affecting route time.

        Returns
        -------
        routes : list
            List of generated routes.
    """
    # initiate empty list of routes
    routes = []

    # initialise unvisited nodes
    unvisited = nodes

    # continue until no more nodes are unvisited
    while len(unvisited) > 0:
        # initialise route
        route = ["Warehouse", unvisited.pop(), "Warehouse"]

        # keep inserting stores until constraints are not met
        while (route is not None):
            new_route = insert_store(
                route, 
                unvisited, 
                demands, 
                durations,
                traffic=traffic
            )

            if new_route is None:
                routes.append(route)
            route = new_route
    
    return routes


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

    # remove stores until capacity constraint satisfied
    while capacity_func(route) > capacity:
        # remove store closer to warehouse
        if durations.Duration["Warehouse", route[1]] < durations.Duration[route[-2], "Warehouse"]:
            removed_stores.append(route.pop(1))
        else:
            removed_stores.append(route.pop(-2))

    return removed_stores
        

def convert_to_mainfreight(routes, trucks=12, shifts=2, mainfreight_cost=3000):
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
        mainfreight_cost : int (default=3000)
            Cost of leasing a Mainfreight truck for 4 hours.
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
        routes.loc[index, "RouteCost"] = mainfreight_cost
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
        trucks : int (default=12)
            Number of Foodstuffs trucks available.
        shifts : int (default=2)
            Number of shifts per day for each truck.

        Returns
        -------
        df : dataframe
            Dataframe containing actual costs and number of Mainfreight trucks used per run.
    """
    # initiailise costs and Mainfreight trucks list
    costs = []
    mainfreight = []
    num_routes = []
    extra_stores = []

    # loop through each random demand realisation
    for run in demands.columns:
        # create a copy of the optimal route selection to modify
        routes = optimal_routes.copy()

        # modify routes based on actual demand
        extra_stores.append(check_routes(routes, demands[run], durations, day_type))

        # convert routes done by owned trucks to Mainfreight trucks
        convert_to_mainfreight(routes, trucks=trucks, shifts=shifts)

        # record total cost and number of Mainfreight turcks used
        costs.append(sum(routes.RouteCost))
        mainfreight.append(len(routes[routes.TruckType=="LeasedTruck"]))
        num_routes.append(len(routes))

    df = pd.DataFrame({
        "Cost": costs,
        "Mainfreight": mainfreight,
        "NumRoutes": num_routes,
        "ExtraStores": extra_stores
    }, index=demands.columns)

    df.index.name = "Run"

    return df