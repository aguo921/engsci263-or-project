import ast
import math

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
    """
    # cost in 4-hour blocks for leasing Mainfreight trucks
    if mainfreight:
        return math.ceil(route_time / 240) * mainfreight_cost

    # owned Foodstuffs trucks
    else:
        if route_time < shift_time:
            # shift costs can be fractional
            return route_time * shift_cost / 60
        else:
            # overtime costs cannot be fractional
            return shift_time * shift_cost + (route_time - shift_time) * math.ceil(overtime_cost / 60)

def check_routes(routes, demands, run, durations, day_type, trucks=12, shifts=2, capacity=16):
    """ Check capacity constraints are satisfied and modify routes appropriately.

        Parameters
        ----------
        routes : dataframe
            Selected routes and corresponding costs.
        demands : dataframe
            Random realisations of demand for each store.
        run : string
            Run name.
        durations : dataframe
            Travel durations between each store.
        day_type : string
            Whether it is a Saturday or weekday.
        trucks : int (default=12)
            Number of owned trucks available.
        shifts : int (default=2)
            Number of shifts per day.
        capacity : int (default=16)
            Capacity of each truck.

        Returns
        -------
        modified_routes : dataframe
            Modified routes and corresponding costs to meet capacity constraints.
        total_cost : float
            Total actual cost for the day.
    """
    # initialise modified routes as a copy of original
    modified_routes = routes.copy()

    # initiailise stores to remove
    removed_stores = []

    # calculate current and potential owned routes
    total_owned_routes = trucks*shifts
    owned_routes = len(routes[routes.TruckType == 'OwnedTruck'])

    # calculate traffic intensity factor
    traffic = 1.4 if day_type == "Weekdays" else 1.2

    # set up function to calculate total demand on route
    calculate_route_capacity = lambda route: sum(demands[run][store] for store in route[1:-1])

    # loop through each selected route
    for i in routes.index:
        route = ast.literal_eval(modified_routes.Route[i])

        # check if capacity is exceeded
        if calculate_route_capacity(route) > capacity:
            # remove removes from last position of route until capacity is satisfied
            while calculate_route_capacity(route) > capacity:
                removed_stores.append(route.pop(-2))

            # calculate route time
            time = calculate_route_time(route, durations, traffic_intensity=traffic)

            # modify route and route cost after removing store(s)
            modified_routes.loc[i, "RouteCost"] = calculate_route_cost(time)
            modified_routes.loc[i, "Route"] = str(route)

    # loop through each removed store
    for store in removed_stores:
        # initialise route
        new_route = ["Warehouse", store, "Warehouse"]

        # calculate route time
        new_route_time = calculate_route_time(new_route, durations, traffic_intensity=traffic)

        # check if any owned routes are left
        if owned_routes < total_owned_routes:
            # use owned truck
            new_route_cost = calculate_route_cost(new_route_time)
            truck_type = "OwnedTruck"
            owned_routes += 1
        else:
            # use Mainfreight truck
            new_route_cost = calculate_route_cost(new_route_time, mainfreight=True)
            truck_type = "LeasedTruck"
        
        # add new row to modified routes dataframe
        modified_routes.loc[len(modified_routes.index)] = [str(new_route), truck_type, new_route_cost] 

    # calculate total cost
    total_cost = sum(modified_routes.RouteCost)

    return modified_routes, total_cost

def simulate_runs(fixed_routes, demands, durations, day_type):
    """ Calculate actual costs on each realisation of demand.

        Parameters
        ----------
        fixed_routes : dataframe
            Optimal selected routes.
        demands : dataframe
            Random realisations of demand for each store.
        durations : dataframe
            Travel durations between each pair of stores.
        day_type : string
            Whether it is a Saturday or weekday.

        Returns
        -------
        costs : list
            Actual costs of each realisation.
        mainfreight : list
            Number of mainfreight trucks used on each realisation.
    """
    # initiailise costs and Mainfreight trucks list
    costs = []
    mainfreight = []

    # loop through each realisation
    for run in demands.columns:
        # find modified routes and cost based on actual demand
        (routes, cost) = check_routes(fixed_routes, demands, run, durations, day_type)

        # record total cost and number of Mainfreight turcks used
        costs.append(cost)
        mainfreight.append(len(routes[routes.TruckType=="LeasedTruck"]))

    return costs, mainfreight