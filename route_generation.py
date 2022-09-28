import random

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
    for i in range(1, len(route) - 1):
        capacity += demands[demands.Supermarket==route[i]].iloc[0][day_type]
    return capacity

def calculate_route_time(route, durations, localised=False, unloading=4, traffic_intensity=1):
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
        if localised and (source == "Warehouse" or destination == "Warehouse"):
            time += 0.25 * travel_time
        else:
            time += travel_time
    return time

def calculate_route_cost(route_time, shift_time=240, shift_cost=150, overtime_cost=200):
    if route_time < shift_time:
        return route_time * shift_cost / 60
    else:
        cost = shift_time * shift_cost
        cost += (route_time - shift_time) * overtime_cost / 60
        return cost

def insert_store(route, nodes, demands, durations, day_type, capacity=16, dropout=0):
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
    best_time = calculate_route_time(best_route, durations, localised=True)

    # loop over every unvisited store
    for node in unvisited:
        # loop over every possible position to insert store into route
        for position in range(2, len(route)):
            # calculate time of new route
            current_route = route.copy()
            current_route.insert(position, node)
            current_time = calculate_route_time(current_route, durations, localised=True)

            # replace best time if new route time is better
            if current_time < best_time and random.random() > dropout:
                best_route = current_route
                best_time = current_time

    # calculate route time and capacity of best route
    route_time = calculate_route_time(best_route, durations)
    route_capacity = calculate_route_capacity(route, demands, day_type)
    
    # return best route if capacity constraint is satisfied
    if route_capacity <= capacity:
        route_cost = calculate_route_cost(route_time)
        return (best_route, route_cost)
    else:
        return None


def generate_routes(nodes, demands, durations, weekday=True, dropout=0):
    """ Generate feasible routes between warehouse and stores.

        Parameters
        ----------
        nodes : list
            List of nodes to travel to.
        demands : dataframe
            Demands at each node.
        durations : dataframe
            Durations between nodes.
        weekday : boolean
            Whether the day is a weekday or not.

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
        route_cost = calculate_route_cost(route_time)
        route = (initial_route, route_cost)

        # keep inserting routes until constraints are not met
        while (route is not None):
            routes.append(route)
            route = insert_store(route[0], nodes, demands, durations, day_type, dropout=dropout)
            
    return routes

def remove_duplicate_routes(routes, remove_identical=False):
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
                # remove route with higher cost
                if routes[i][1] < routes[j][1]:
                    routes_to_remove.append(j)
                else:
                    routes_to_remove.append(i)

    routes = [route for i, route in enumerate(routes) if i not in routes_to_remove]

    return routes

def write_routes(routes, filename):
    with open(filename, "w") as f:
        for route in routes:
            f.write(",".join(route[0]))
            f.write(":")
            f.write(str(route[1]))
            f.write("\n")

def read_routes(filename):
    routes = []
    with open(filename, "r") as f:
        for line in f:
            route, cost = line.split(":")
            cost = float(cost.strip())
            route = route.split(",")
            routes.append((route, cost))

    return routes