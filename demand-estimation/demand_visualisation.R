library(tidyverse)
# read in data and convert to tibble
demand_data = read_delim("output/store_demand_plotting.txt",",")
demand_tibble = as_tibble(demand_data)

# plot scatter plot : x-axis weekdays, y-axis Saturdays
g=ggplot(demand_tibble,aes(x=Weekdays,y=Saturday))
g=g+geom_point(aes(color=Brand),size=3, alpha=0.7)
g=g+labs(title="Weekday vs Saturday demand means",subtitle="Coloured by Branch",
         y="number of pallets demanded on Saturdays", 
         x="number of pallets demanded on weekdays")
plot(g)

