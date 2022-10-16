# imports
import csv
import pandas as pd
from matplotlib import pyplot as plt
import math


def get_demand_info():
    """
    Get date and demand info from the provided demand csv file.

    Returns:
    ---------
    date: Python list
        string representations of dates provided in the file
    demand_dict: dictionary
        keys correspond to name of supermarket, values are a list of number of pallets demanded on each day
    """
    with open('./foodstuffs-data/FoodstuffsDemands.csv', mode='r') as demand_data:
        demand = list(csv.reader(demand_data, delimiter=','))
        # extract dates as a list of strings
        date = [x[5:] for x in demand[0][1:]]

        # set up a dictionary with name of the supermarket as the key
        # and its corresponding list of demand each day as the value
        demand_dict = dict()
        for line in demand[1:]:
            demand_dict[line[0]] = [int(i) for i in line[1:]]
    return date, demand_dict


def plot_total_demand(date, demand_dict):
    """
    Plot a bar chart of total demand of all supermarkets given on each day.

    Parameters:
    ---------
    date: Python list
        string representations of dates provided in the file
    demand_dict: dictionary
        keys correspond to name of supermarket, values are a list of number of pallets demanded on each day
    """
    # sum elements at the same index for all lists in demand_dict
    demand_sum = [sum(x) for x in zip(*demand_dict.values())]

    # plot bar chart
    fig, ax = plt.subplots()
    fig.set_size_inches(20, 8, forward=True)
    ax.bar(x=date, height=demand_sum, width=0.4)
    plt.grid(True)
    plt.xlabel("Date")
    plt.ylabel("Number of pallets")
    plt.title("Total number of pallets demanded each day by supermarkets in 2022")
    plt.show()


def plot_demand_brand(date, demand_dict):
    """
    Plot side-by-side bar chart on the same scale comparing demand of 3 supermarket brands on each day.

    Parameters:
    ---------
    date: Python list
        string representations of dates provided in the file
    demand_dict: dictionary
        keys correspond to name of supermarket, values are a list of number of pallets demanded on each day
    """
    # store each supermarket in new dictionaries dedicated to specific brand
    four_square, new_world, pak = dict(), dict(), dict()
    for key in demand_dict:
        if "Four Square" in key:
            four_square[key] = demand_dict[key]
        elif "New World" in key:
            new_world[key] = demand_dict[key]
        else:
            pak[key] = demand_dict[key]

    # sum elements at the same index for all lists in each dictionary
    fs_sum = [sum(x) for x in zip(*four_square.values())]
    nw_sum = [sum(x) for x in zip(*new_world.values())]
    pks_sum = [sum(x) for x in zip(*pak.values())]
    df = pd.DataFrame({"Four Square": fs_sum, "New World": nw_sum, "Pak'n Save": pks_sum}, index=date)

    # plot bar chart
    df.plot.bar(figsize=(20, 8))
    plt.xlabel("Date")
    plt.ylabel("Number of pallets")
    plt.title("Number of pallets demanded each day by 3 supermarket brands in 2022")
    plt.show()


def write_demand_to_file(demand_dict):
    """
    Compute mean demand of each supermarket on weekdays and Saturdays and write to store_demand_plotting.txt
    Round mean demand of each supermarket up and write to store_demand.txt

    Parameters:
    ---------
    demand_dict: dictionary
        keys correspond to name of supermarket, values are a list of number of pallets demanded on each day
    """
    # set up txt files and write in headings
    store_demandP = open("./demand-estimation/output/store_demand_plotting.txt", "w")
    store_demand = open("./demand-estimation/output/store_demand.txt", "w")
    store_demandP.write("Brand,Location,Weekdays,Saturday\n")
    store_demand.write("Brand,Location,Weekdays,Saturday\n")
    for key in demand_dict:
        # filter out Sunday demands and compute mean
        weekday = [demand_dict[key][i] for i in range(len(demand_dict[key])) if i % 7 != 6 and i % 7 != 5]
        sat = [demand_dict[key][i] for i in range(len(demand_dict[key])) if i % 7 == 5]
        mean_wd = sum(weekday) / len(weekday)
        mean_sat = sum(sat) / len(sat)
        
        # separate the brand name and location
        if "New World" in key:
            brand = "New World"
            location = key.replace("New World ", "")
        elif "Four Square" in key:
            brand = "Four Square"
            location = key.replace("Four Square ", "")
        else:
            brand = "Pak 'n Save"
            location = key.replace("Pak 'n Save ", "")
        store_demandP.write(f"{brand},{location},{mean_wd},{mean_sat}\n")
        store_demand.write(f"{brand},{location},{math.ceil(mean_wd)},{math.ceil(mean_sat)}\n")
    store_demandP.close()
    store_demand.close()


if __name__ == "__main__":
    date_list, demand_dict = get_demand_info()
    plot_total_demand(date_list, demand_dict)
    plot_demand_brand(date_list, demand_dict)
    write_demand_to_file(demand_dict)
